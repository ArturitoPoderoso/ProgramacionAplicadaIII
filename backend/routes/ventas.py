import uuid
import json
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import get_db
from sunat_service import emitir_comprobante_sunat

ventas_bp = Blueprint("ventas", __name__)

PERU_TZ = timezone(timedelta(hours=-5))

def format_peru_datetime(dt):
    if not dt:
        return "N/A"
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(PERU_TZ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt.strftime("%d/%m/%Y %H:%M")


# Registra una nueva venta mediante Stored Procedure sp_procesar_venta
@ventas_bp.route("/api/ventas", methods=["POST"])
def create_venta():
    data = request.json or {}
    detalles = data.get("detalles", [])
    id_usuario = data.get("id_usuario") or 1
    descuento_total = float(data.get("descuento_total", 0.0))
    id_sede = data.get("id_sede") or 1
    
    if not detalles:
        return jsonify({"error": "La venta debe tener al menos un producto"}), 400
        
    db = get_db()
    try:
        correlativo = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"

        # Preparar detalles y calcular total
        detalles_sp = []
        subtotal_acumulado = 0.0
        for det in detalles:
            pu = float(det["precio_unitario"])
            du = float(det.get("descuento_unitario", 0.0))
            cant = int(det["cantidad"])
            sub = cant * (pu - du)
            subtotal_acumulado += sub
            detalles_sp.append({
                "id_producto": int(det["id_producto"]),
                "cantidad": cant,
                "precio_unitario": pu,
                "descuento_unitario": du,
                "subtotal": round(sub, 2)
            })

        total_venta = round(max(0.0, subtotal_acumulado), 2)
        cliente_nombre = str(data.get("cliente_nombre") or data.get("cliente") or "Cliente General").strip()
        cliente_doc = str(data.get("cliente_doc") or data.get("dni") or "").strip()
        cliente_tel = str(data.get("cliente_telefono") or data.get("telefono") or "").strip()
        id_cliente = data.get("id_cliente")

        # 1. Guardar o actualizar cliente mediante Stored Procedure sp_guardar_cliente
        if cliente_doc and not id_cliente:
            tipo_doc = "RUC" if len(cliente_doc) == 11 else "DNI"
            cli_res = db.execute(
                text("CALL sp_guardar_cliente(NULL, :tipo, :doc, :nom, :tel, NULL, NULL)"),
                {"tipo": tipo_doc, "doc": cliente_doc, "nom": cliente_nombre, "tel": cliente_tel}
            ).fetchone()
            if cli_res and cli_res[0]:
                id_cliente = cli_res[0]

        # 2. Procesar venta atómica mediante Stored Procedure sp_procesar_venta
        sp_res = db.execute(
            text("""
                CALL sp_procesar_venta(
                    :id_usuario, :id_sede, :id_cliente, :cliente_nombre, :cliente_doc,
                    :correlativo, :total, :descuento_total, :metodo_pago, CAST(:detalles AS jsonb),
                    NULL, NULL
                )
            """),
            {
                "id_usuario": id_usuario,
                "id_sede": id_sede,
                "id_cliente": id_cliente,
                "cliente_nombre": cliente_nombre,
                "cliente_doc": cliente_doc,
                "correlativo": correlativo,
                "total": total_venta,
                "descuento_total": descuento_total,
                "metodo_pago": data.get("metodo_pago", "Efectivo"),
                "detalles": json.dumps(detalles_sp)
            }
        ).fetchone()

        db.commit()

        id_venta_generada = sp_res[0] if sp_res else None
        mensaje_sp = sp_res[1] if sp_res and len(sp_res) > 1 else "Venta procesada exitosamente"

        # 3. Emisión Electrónica SUNAT integrada mediante microservicio oficial
        sunat_info = {}
        try:
            sunat_tipo = "01" if (cliente_doc and len(cliente_doc) == 11) else "03"
            payload_sunat = {
                "tipo_comprobante": sunat_tipo,
                "serie": "F001" if sunat_tipo == "01" else "B001",
                "cliente_tipo_doc": "6" if sunat_tipo == "01" else "1",
                "cliente_num_doc": cliente_doc if cliente_doc else "00000000",
                "cliente_razon_social": cliente_nombre,
                "cliente_direccion": "Lima, Perú",
                "metodo_pago": data.get("metodo_pago", "Efectivo"),
                "detalles": [
                    {
                        "codigo_producto": f"PROD-{d['id_producto']}",
                        "descripcion": f"Producto ID {d['id_producto']}",
                        "unidad_medida": "NIU",
                        "cantidad": d["cantidad"],
                        "precio_unitario": d["precio_unitario"],
                        "descuento_unitario": d.get("descuento_unitario", 0.0),
                        "subtotal": d["subtotal"]
                    }
                    for d in detalles_sp
                ]
            }
            res_sunat = emitir_comprobante_sunat(payload_sunat)
            if res_sunat and not res_sunat.get("error"):
                sunat_info = {
                    "emitido": True,
                    "numero_completo": res_sunat.get("numero_completo"),
                    "hash_cpe": res_sunat.get("hash_cpe"),
                    "codigo_qr": res_sunat.get("codigo_qr"),
                    "estado_sunat": res_sunat.get("estado_sunat"),
                    "pdf_url": res_sunat.get("pdf_url"),
                    "xml_url": res_sunat.get("xml_url")
                }
            else:
                sunat_info = {"emitido": False, "error": res_sunat.get("error", "Error SUNAT")}
        except Exception as e_sunat:
            sunat_info = {"emitido": False, "error": str(e_sunat)}

        return jsonify({
            "message": mensaje_sp,
            "id_venta": id_venta_generada,
            "correlativo": correlativo,
            "total": total_venta,
            "sunat": sunat_info
        }), 201

    except Exception as e:
        db.rollback()
        err_msg = str(e)
        if "Stock insuficiente" in err_msg or "inferior al costo" in err_msg:
            clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
            return jsonify({"error": clean_err}), 400
        return jsonify({"error": f"Error al procesar la venta: {err_msg}"}), 400


# Listar ventas para el historial mediante Función Almacenada fn_listar_ventas
@ventas_bp.route("/api/ventas", methods=["GET"])
def get_ventas():
    db = get_db()
    try:
        user_id = request.args.get("user_id", type=int)
        sede_id = request.args.get("sede_id", type=int)
        vendedor_id = request.args.get("vendedor_id", type=int)
        search = request.args.get("search", type=str)
        fecha_inicio_str = request.args.get("fecha_inicio")
        fecha_fin_str = request.args.get("fecha_fin")

        f_ini = None
        f_fin = None
        if fecha_inicio_str:
            try:
                f_ini = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
            except Exception:
                pass
        if fecha_fin_str:
            try:
                f_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d") + timedelta(days=1)
            except Exception:
                pass

        # Invocación de la función almacenada fn_listar_ventas
        rows = db.execute(
            text("""
                SELECT id_venta, correlativo, total, descuento_total, metodo_pago,
                       id_usuario, usuario_nombre, id_sede, sede_nombre,
                       id_cliente, cliente_nombre, cliente_doc, fecha_venta,
                       estado_registro, total_items, total_unidades
                FROM fn_listar_ventas(:p_id_sede, :p_id_usuario, :p_fecha_inicio, :p_fecha_fin, :p_search)
            """),
            {
                "p_id_sede": sede_id if sede_id else None,
                "p_id_usuario": vendedor_id if vendedor_id else None,
                "p_fecha_inicio": f_ini,
                "p_fecha_fin": f_fin,
                "p_search": search if search else None
            }
        ).fetchall()

        result_ventas = []
        total_monto = 0.0
        total_unidades = 0
        vendedores_conteo = {}

        for r in rows:
            vendedor_nom = r.usuario_nombre if r.usuario_nombre else "Desconocido"
            unidades_venta = int(r.total_unidades or 0)
            monto_venta = float(r.total or 0.0)

            total_monto += monto_venta
            total_unidades += unidades_venta
            vendedores_conteo[vendedor_nom] = vendedores_conteo.get(vendedor_nom, 0) + monto_venta

            result_ventas.append({
                "id_venta": r.id_venta,
                "correlativo": r.correlativo,
                "fecha": format_peru_datetime(r.fecha_venta),
                "total": round(monto_venta, 2),
                "descuento_total": round(float(r.descuento_total or 0.0), 2),
                "metodo_pago": r.metodo_pago,
                "unidades_totales": unidades_venta,
                "vendedor": vendedor_nom,
                "cliente": r.cliente_nombre or "Cliente General",
                "cliente_doc": r.cliente_doc or "",
                "id_cliente": r.id_cliente,
                "sede": r.sede_nombre or "Sede Central",
                "id_sede": r.id_sede,
                "id_usuario": r.id_usuario
            })

        top_vendedor = max(vendedores_conteo, key=vendedores_conteo.get) if vendedores_conteo else "N/A"

        kpis = {
            "monto_total": round(total_monto, 2),
            "unidades_totales": total_unidades,
            "total_comprobantes": len(result_ventas),
            "top_vendedor": top_vendedor
        }

        page = request.args.get("page", type=int)
        limit = request.args.get("limit", default=15, type=int)

        if page and page > 0:
            total_filtered = len(result_ventas)
            total_pages = (total_filtered + limit - 1) // limit if limit > 0 else 1
            start_idx = (page - 1) * limit
            paged_ventas = result_ventas[start_idx : start_idx + limit]
            return jsonify({
                "kpis": kpis,
                "ventas": paged_ventas,
                "total": total_filtered,
                "page": page,
                "pages": total_pages,
                "limit": limit
            }), 200

        return jsonify({"kpis": kpis, "ventas": result_ventas}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Obtener comprobante de venta mediante Funciones Almacenadas fn_obtener_venta_cabecera y fn_obtener_venta_detalle
@ventas_bp.route("/api/ventas/<int:id_venta>", methods=["GET"])
def get_detalle_venta(id_venta):
    db = get_db()
    try:
        cab = db.execute(
            text("""
                SELECT id_venta, correlativo, total, descuento_total, metodo_pago,
                       id_usuario, usuario_nombre, id_sede, sede_nombre, sede_direccion,
                       id_cliente, cliente_nombre, cliente_doc, fecha_venta, estado_registro
                FROM fn_obtener_venta_cabecera(:id_venta)
            """),
            {"id_venta": id_venta}
        ).fetchone()

        if not cab:
            return jsonify({"error": "Venta no encontrada"}), 404

        det_rows = db.execute(
            text("""
                SELECT id_detalle, id_producto, codigo_producto, producto_nombre,
                       cantidad, precio_unitario, descuento_unitario, subtotal
                FROM fn_obtener_venta_detalle(:id_venta)
            """),
            {"id_venta": id_venta}
        ).fetchall()

        detalles_res = [{
            "id_producto": d.id_producto,
            "codigo": d.codigo_producto or "PROD",
            "nombre": d.producto_nombre or "Producto",
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "descuento_unitario": d.descuento_unitario or 0.0,
            "subtotal": d.subtotal
        } for d in det_rows]

        data = {
            "id_venta": cab.id_venta,
            "correlativo": cab.correlativo,
            "fecha": format_peru_datetime(cab.fecha_venta),
            "total": round(float(cab.total or 0.0), 2),
            "descuento_total": round(float(cab.descuento_total or 0.0), 2),
            "metodo_pago": cab.metodo_pago,
            "vendedor": cab.usuario_nombre or "Sistema",
            "id_cliente": cab.id_cliente,
            "cliente": cab.cliente_nombre or "Cliente General",
            "cliente_doc": cab.cliente_doc or "",
            "dni": cab.cliente_doc or "",
            "sede_nombre": cab.sede_nombre or "Sede Central",
            "sede_direccion": cab.sede_direccion or "Av. Central 123",
            "sede_telefono": "01-1234567",
            "detalles": detalles_res
        }
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Anular venta y devolver stock al inventario mediante Stored Procedure sp_anular_venta
@ventas_bp.route("/api/ventas/<int:id_venta>/anular", methods=["POST"])
def anular_venta(id_venta):
    data = request.json or {}
    id_usuario = data.get("id_usuario") or 1
    motivo = str(data.get("motivo", "Anulación solicitada por el usuario")).strip()

    db = get_db()
    try:
        res = db.execute(
            text("CALL sp_anular_venta(:p_id_venta, :p_id_usuario, :p_motivo, NULL);"),
            {"p_id_venta": id_venta, "p_id_usuario": id_usuario, "p_motivo": motivo}
        ).fetchone()
        db.commit()
        mensaje = res[0] if res else "Venta anulada correctamente"
        return jsonify({"message": mensaje, "id_venta": id_venta}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
