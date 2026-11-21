import json
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from sqlalchemy import func, text
from database import get_db
import models

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
    # Calcula el siguiente correlativo para la orden de compra según el año actual
    year = datetime.now(PERU_TZ).year
    prefix = f"OC-{year}-"
    ultima_oc = db.execute(
        text("SELECT correlativo FROM ordenes_compra WHERE correlativo LIKE :prefix ORDER BY id_orden_compra DESC LIMIT 1"),
        {"prefix": f"{prefix}%"}
    ).fetchone()

    if ultima_oc and ultima_oc[0]:
        try:
            last_num = int(ultima_oc[0].split("-")[-1])
            siguiente_num = last_num + 1
        except Exception:
            max_id = db.execute(text("SELECT MAX(id_orden_compra) FROM ordenes_compra")).scalar() or 0
            siguiente_num = max_id + 1
    else:
        siguiente_num = 1

    correlativo = f"{prefix}{siguiente_num:04d}"
    while db.execute(text("SELECT id_orden_compra FROM ordenes_compra WHERE correlativo = :cor"), {"cor": correlativo}).fetchone():
        siguiente_num += 1
        correlativo = f"{prefix}{siguiente_num:04d}"

    return correlativo

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

        # Invocación de Stored Procedure sp_procesar_compra
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


@compras_bp.route("/api/compras", methods=["GET"])
def get_compras():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        id_sede = request.args.get("id_sede")
        estado_filtro = request.args.get("estado")
        search = (request.args.get("search") or "").strip().lower()

        query = db.query(models.OrdenCompra).options(
            joinedload(models.OrdenCompra.proveedor),
            joinedload(models.OrdenCompra.usuario),
            joinedload(models.OrdenCompra.sede),
            joinedload(models.OrdenCompra.detalles)
        ).filter(models.OrdenCompra.estado_registro == 1)

        if id_sede and str(id_sede).isdigit():
            query = query.filter(models.OrdenCompra.id_sede == int(id_sede))

        if estado_filtro and estado_filtro.upper() in ["PENDIENTE", "RECIBIDA", "ANULADA"]:
            query = query.filter(models.OrdenCompra.estado == estado_filtro.upper())

        ordenes = query.order_by(models.OrdenCompra.id_orden_compra.desc()).all()

        resultado = []
        for o in ordenes:
            prov = o.proveedor
            usuario = o.usuario
            sede = o.sede

            if search:
                matches_correlativo = search in (o.correlativo or "").lower()
                matches_prov = search in (prov.razon_social if prov else "").lower() or search in (prov.ruc if prov else "")
                if not (matches_correlativo or matches_prov):
                    continue

            total_unidades = sum(d.cantidad_solicitada for d in o.detalles)
            total_items = len(o.detalles)

            resultado.append({
                "id_orden_compra": o.id_orden_compra,
                "correlativo": o.correlativo,
                "id_proveedor": o.id_proveedor,
                "proveedor_nombre": prov.razon_social if prov else "Proveedor Desconocido",
                "proveedor_ruc": prov.ruc if prov else "",
                "proveedor_telefono": prov.telefono if prov else "",
                "proveedor_contacto": prov.nombre_contacto if prov else "",
                "id_sede": o.id_sede,
                "sede_nombre": sede.nombre if sede else "Sede Central",
                "id_usuario": o.id_usuario,
                "usuario_nombre": f"{usuario.first_name or ''} {usuario.last_name or ''}".strip() or (usuario.username if usuario else "Sistema"),
                "fecha_emision": format_peru_datetime(o.fecha_emision),
                "fecha_esperada": o.fecha_esperada or "",
                "fecha_recepcion": format_peru_datetime(o.fecha_recepcion),
                "estado": o.estado,
                "total": round(float(o.total or 0.0), 2),
                "total_items": total_items,
                "total_unidades": total_unidades,
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


@compras_bp.route("/api/compras/<int:id_orden>", methods=["GET"])
def get_detalle_compra(id_orden):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        orden = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_orden_compra == id_orden,
            models.OrdenCompra.estado_registro == 1
        ).first()

        if not orden:
            return jsonify({"error": "Orden de compra no encontrada."}), 404

        prov = orden.proveedor
        usuario = orden.usuario
        sede = orden.sede

        items = []
        for det in orden.detalles:
            prod = det.producto
            items.append({
                "id_detalle_oc": det.id_detalle_oc,
                "id_producto": det.id_producto,
                "codigo_producto": prod.codigo_producto if prod else f"PROD-{det.id_producto}",
                "nombre_producto": prod.nombre if prod else "Producto",
                "cantidad_solicitada": det.cantidad_solicitada,
                "cantidad_recibida": det.cantidad_recibida or 0,
                "precio_unitario": round(float(det.precio_unitario), 2),
                "subtotal": round(float(det.subtotal), 2)
            })

        data = {
            "id_orden_compra": orden.id_orden_compra,
            "correlativo": orden.correlativo,
            "id_proveedor": orden.id_proveedor,
            "proveedor_nombre": prov.razon_social if prov else "",
            "proveedor_ruc": prov.ruc if prov else "",
            "proveedor_telefono": prov.telefono if prov else "",
            "proveedor_correo": prov.correo if prov else "",
            "proveedor_contacto": prov.nombre_contacto if prov else "",
            "proveedor_direccion": prov.direccion if prov else "",
            "id_sede": orden.id_sede,
            "sede_nombre": sede.nombre if sede else "Sede Central",
            "sede_direccion": sede.direccion if sede else "",
            "usuario_nombre": f"{usuario.first_name or ''} {usuario.last_name or ''}".strip() or (usuario.username if usuario else "Sistema"),
            "fecha_emision": format_peru_datetime(orden.fecha_emision),
            "fecha_esperada": orden.fecha_esperada or "Inmediata",
            "fecha_recepcion": format_peru_datetime(orden.fecha_recepcion),
            "estado": orden.estado,
            "total": round(float(orden.total or 0.0), 2),
            "observacion": orden.observacion or "",
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

        # Invocación de Stored Procedure sp_recibir_compra
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

        # Invocación de Stored Procedure sp_anular_compra
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
