import json
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import get_db

compras_bp = Blueprint("compras", __name__)

PERU_TZ = timezone(timedelta(hours=-5))

def format_peru_datetime(dt):
    if not dt:
        return ""
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(PERU_TZ).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M")

def _calcular_siguiente_correlativo(db):
    row = db.execute(text("SELECT fn_siguiente_correlativo_oc()")).fetchone()
    return row[0] if row and row[0] else "OC-2026-0001"

@compras_bp.route("/api/compras/siguiente-correlativo", methods=["GET"])
def get_siguiente_correlativo_compra():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        correlativo = _calcular_siguiente_correlativo(db)
        return jsonify({"correlativo": correlativo}), 200
    except Exception as e:
        return jsonify({"error": f"Error al generar correlativo: {str(e)}"}), 500


# Emitir orden de compra mediante Stored Procedure sp_procesar_compra
@compras_bp.route("/api/compras", methods=["POST"])
def emitir_orden_compra():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no pueden emitir órdenes de compra"}), 403

    data = request.json or {}
    id_proveedor = data.get("id_proveedor")
    id_sede = data.get("id_sede") or 1
    id_usuario = data.get("id_usuario") or 1
    fecha_esperada = str(data.get("fecha_esperada", "")).strip()
    observacion = str(data.get("observacion", "")).strip()
    items = data.get("items", [])

    if not id_proveedor:
        return jsonify({"error": "Debes seleccionar un proveedor obligatorio para emitir la orden."}), 400

    if not items or len(items) == 0:
        return jsonify({"error": "La orden de compra debe incluir al menos un producto."}), 400

    if fecha_esperada:
        try:
            fecha_dt = datetime.strptime(fecha_esperada, "%Y-%m-%d").date()
            hoy_dt = datetime.now(PERU_TZ).date()
            if fecha_dt < hoy_dt:
                return jsonify({"error": f"La fecha esperada de entrega ({fecha_esperada}) no puede ser anterior a la fecha de hoy ({hoy_dt.strftime('%Y-%m-%d')})."}), 400
        except ValueError:
            pass

    db = get_db()
    try:
        correlativo = _calcular_siguiente_correlativo(db)
        total_orden = 0.0
        detalles_json = []

        for item in items:
            id_prod = int(item.get("id_producto", 0))
            cant = int(item.get("cantidad", 0))
            precio_u = float(item.get("precio_unitario", 0.0))

            if not id_prod or cant <= 0 or precio_u <= 0:
                return jsonify({"error": "Datos de producto inválidos (cantidad y precio deben ser mayores a 0)."}), 400

            subtotal_item = round(cant * precio_u, 2)
            total_orden += subtotal_item

            detalles_json.append({
                "id_producto": id_prod,
                "cantidad": cant,
                "precio_unitario": precio_u,
                "subtotal": subtotal_item
            })

        total_orden = round(total_orden, 2)

        res = db.execute(
            text("""
                CALL sp_procesar_compra(
                    :id_usuario, :id_sede, :id_proveedor, :correlativo,
                    :total, :fecha_esperada, :observacion,
                    CAST(:detalles AS jsonb), NULL, NULL
                )
            """),
            {
                "id_usuario": int(id_usuario),
                "id_sede": int(id_sede),
                "id_proveedor": int(id_proveedor),
                "correlativo": correlativo,
                "total": total_orden,
                "fecha_esperada": fecha_esperada if fecha_esperada else None,
                "observacion": observacion,
                "detalles": json.dumps(detalles_json)
            }
        ).fetchone()
        db.commit()

        id_creada = res[0] if res else None
        msg = res[1] if res and len(res) > 1 else f"Orden de compra {correlativo} emitida con éxito."

        return jsonify({
            "message": msg,
            "id_orden_compra": id_creada,
            "correlativo": correlativo,
            "total": total_orden
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al emitir orden de compra: {str(e)}"}), 500


# Listar órdenes de compra mediante Función Almacenada fn_listar_compras
@compras_bp.route("/api/compras", methods=["GET"])
def get_compras():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        id_sede = request.args.get("id_sede", type=int)
        estado_filtro = request.args.get("estado", type=str)
        search = request.args.get("search", type=str)

        rows = db.execute(
            text("""
                SELECT id_orden_compra, correlativo, id_proveedor, proveedor_nombre,
                       proveedor_ruc, proveedor_telefono, proveedor_contacto,
                       id_sede, sede_nombre, id_usuario, usuario_nombre,
                       fecha_emision, fecha_esperada, fecha_recepcion, estado,
                       total, observacion, total_items, total_unidades
                FROM fn_listar_compras(:p_id_sede, :p_estado, :p_search)
            """),
            {
                "p_id_sede": id_sede if id_sede else None,
                "p_estado": estado_filtro if estado_filtro else None,
                "p_search": search if search else None
            }
        ).fetchall()

        resultado = []
        for o in rows:
            resultado.append({
                "id_orden_compra": o.id_orden_compra,
                "correlativo": o.correlativo,
                "id_proveedor": o.id_proveedor,
                "proveedor_nombre": o.proveedor_nombre or "Proveedor Desconocido",
                "proveedor_ruc": o.proveedor_ruc or "",
                "proveedor_telefono": o.proveedor_telefono or "",
                "proveedor_contacto": o.proveedor_contacto or "",
                "id_sede": o.id_sede,
                "sede_nombre": o.sede_nombre or "Sede Central",
                "id_usuario": o.id_usuario,
                "usuario_nombre": o.usuario_nombre or "Sistema",
                "fecha_emision": format_peru_datetime(o.fecha_emision),
                "fecha_esperada": o.fecha_esperada or "",
                "fecha_recepcion": format_peru_datetime(o.fecha_recepcion),
                "estado": o.estado,
                "total": round(float(o.total or 0.0), 2),
                "total_items": int(o.total_items or 0),
                "total_unidades": int(o.total_unidades or 0),
                "observacion": o.observacion or ""
            })

        page = request.args.get("page", type=int)
        limit = request.args.get("limit", default=15, type=int)

        if page and page > 0:
            total_items = len(resultado)
            total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
            start_idx = (page - 1) * limit
            paged_resultado = resultado[start_idx : start_idx + limit]
            return jsonify({
                "items": paged_resultado,
                "total": total_items,
                "page": page,
                "pages": total_pages,
                "limit": limit
            }), 200

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({"error": f"Error al consultar compras: {str(e)}"}), 500


# Obtener detalle de orden de compra mediante Funciones Almacenadas fn_obtener_compra_cabecera y fn_obtener_compra_detalle
@compras_bp.route("/api/compras/<int:id_orden>", methods=["GET"])
def get_detalle_compra(id_orden):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        cab = db.execute(
            text("""
                SELECT id_orden_compra, correlativo, id_proveedor, proveedor_nombre,
                       proveedor_ruc, proveedor_telefono, proveedor_correo, proveedor_contacto,
                       proveedor_direccion, id_sede, sede_nombre, sede_direccion,
                       id_usuario, usuario_nombre, fecha_emision, fecha_esperada,
                       fecha_recepcion, estado, total, observacion
                FROM fn_obtener_compra_cabecera(:id_orden)
            """),
            {"id_orden": id_orden}
        ).fetchone()

        if not cab:
            return jsonify({"error": "Orden de compra no encontrada."}), 404

        det_rows = db.execute(
            text("""
                SELECT id_detalle_oc, id_producto, codigo_producto, nombre_producto,
                       cantidad_solicitada, cantidad_recibida, precio_unitario, subtotal
                FROM fn_obtener_compra_detalle(:id_orden)
            """),
            {"id_orden": id_orden}
        ).fetchall()

        items = [{
            "id_detalle_oc": d.id_detalle_oc,
            "id_producto": d.id_producto,
            "codigo_producto": d.codigo_producto or f"PROD-{d.id_producto}",
            "nombre_producto": d.nombre_producto or "Producto",
            "cantidad_solicitada": d.cantidad_solicitada,
            "cantidad_recibida": d.cantidad_recibida or 0,
            "precio_unitario": round(float(d.precio_unitario), 2),
            "subtotal": round(float(d.subtotal), 2)
        } for d in det_rows]

        data = {
            "id_orden_compra": cab.id_orden_compra,
            "correlativo": cab.correlativo,
            "id_proveedor": cab.id_proveedor,
            "proveedor_nombre": cab.proveedor_nombre or "",
            "proveedor_ruc": cab.proveedor_ruc or "",
            "proveedor_telefono": cab.proveedor_telefono or "",
            "proveedor_correo": cab.proveedor_correo or "",
            "proveedor_contacto": cab.proveedor_contacto or "",
            "proveedor_direccion": cab.proveedor_direccion or "",
            "id_sede": cab.id_sede,
            "sede_nombre": cab.sede_nombre or "Sede Central",
            "sede_direccion": cab.sede_direccion or "",
            "usuario_nombre": cab.usuario_nombre or "Sistema",
            "fecha_emision": format_peru_datetime(cab.fecha_emision),
            "fecha_esperada": cab.fecha_esperada or "Inmediata",
            "fecha_recepcion": format_peru_datetime(cab.fecha_recepcion),
            "estado": cab.estado,
            "total": round(float(cab.total or 0.0), 2),
            "observacion": cab.observacion or "",
            "items": items
        }

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": f"Error al obtener detalle de compra: {str(e)}"}), 500


# Recepción de mercadería mediante Stored Procedure sp_recibir_compra
@compras_bp.route("/api/compras/<int:id_orden>/recibir", methods=["POST"])
def recibir_orden_compra(id_orden):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no pueden recibir mercadería"}), 403

    db = get_db()
    try:
        data = request.json or {}
        id_usuario = data.get("id_usuario") or 1

        res = db.execute(
            text("CALL sp_recibir_compra(:id_orden, :id_usuario, NULL)"),
            {"id_orden": id_orden, "id_usuario": int(id_usuario)}
        ).fetchone()
        db.commit()

        msg = res[0] if res else "Mercadería recibida exitosamente."

        return jsonify({
            "message": msg,
            "estado": "RECIBIDA"
        }), 200

    except Exception as e:
        db.rollback()
        err_msg = str(e)
        if "ya fue recibida" in err_msg or "está anulada" in err_msg:
            clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
            return jsonify({"error": clean_err}), 400
        return jsonify({"error": f"Error al procesar la recepción de mercadería: {err_msg}"}), 500


# Anulación de compra mediante Stored Procedure sp_anular_compra
@compras_bp.route("/api/compras/<int:id_orden>/anular", methods=["POST"])
def anular_orden_compra(id_orden):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no pueden anular órdenes de compra"}), 403

    db = get_db()
    try:
        data = request.json or {}
        motivo = str(data.get("motivo", "Anulación solicitada por el usuario")).strip()
        id_usuario = data.get("id_usuario") or 1

        res = db.execute(
            text("CALL sp_anular_compra(:id_orden, :id_usuario, :motivo, NULL)"),
            {
                "id_orden": id_orden,
                "id_usuario": int(id_usuario),
                "motivo": motivo
            }
        ).fetchone()
        db.commit()

        msg = res[0] if res else "Orden de compra anulada correctamente."

        return jsonify({
            "message": msg,
            "estado": "ANULADA"
        }), 200

    except Exception as e:
        db.rollback()
        err_msg = str(e)
        if "ya se encuentra anulada" in err_msg or "No se puede anular" in err_msg:
            clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
            return jsonify({"error": clean_err}), 400
        return jsonify({"error": f"Error al anular la orden de compra: {err_msg}"}), 500
