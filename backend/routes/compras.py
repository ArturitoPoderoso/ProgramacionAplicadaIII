from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from sqlalchemy import func
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
    # Calcula el siguiente correlativo para la orden de compra segun el año actual
    year = datetime.now(PERU_TZ).year
    prefix = f"OC-{year}-"
    ultima_oc = db.query(models.OrdenCompra.correlativo)\
        .filter(models.OrdenCompra.correlativo.like(f"{prefix}%"))\
        .order_by(models.OrdenCompra.id_orden_compra.desc())\
        .first()

    if ultima_oc and ultima_oc[0]:
        try:
            last_num = int(ultima_oc[0].split("-")[-1])
            siguiente_num = last_num + 1
        except Exception:
            max_id = db.query(func.max(models.OrdenCompra.id_orden_compra)).scalar() or 0
            siguiente_num = max_id + 1
    else:
        siguiente_num = 1

    correlativo = f"{prefix}{siguiente_num:04d}"
    while db.query(models.OrdenCompra.id_orden_compra).filter(models.OrdenCompra.correlativo == correlativo).first():
        siguiente_num += 1
        correlativo = f"{prefix}{siguiente_num:04d}"

    return correlativo

@compras_bp.route("/api/compras/siguiente-correlativo", methods=["GET"])
def get_siguiente_correlativo_compra():
    # Devuelve el siguiente correlativo disponible para una orden de compra
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        correlativo = _calcular_siguiente_correlativo(db)
        return jsonify({"correlativo": correlativo}), 200
    except Exception as e:
        return jsonify({"error": f"Error al generar correlativo: {str(e)}"}), 500


@compras_bp.route("/api/compras", methods=["POST"])
def emitir_orden_compra():
    # Registra una nueva orden de compra con sus productos y proveedor
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no pueden emitir órdenes de compra"}), 403

    data = request.json or {}
    id_proveedor = data.get("id_proveedor")
    id_sede = data.get("id_sede")
    id_usuario = data.get("id_usuario")
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
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not proveedor:
            return jsonify({"error": "El proveedor seleccionado no existe o está inactivo."}), 404

        id_sede_final = int(id_sede) if id_sede else (proveedor.id_sede or 1)

        correlativo = _calcular_siguiente_correlativo(db)

        total_orden = 0.0
        detalles_a_crear = []

        for item in items:
            id_prod = item.get("id_producto")
            cant = int(item.get("cantidad", 0))
            precio_u = float(item.get("precio_unitario", 0.0))

            if not id_prod or cant <= 0 or precio_u <= 0:
                return jsonify({"error": "Datos de producto inválidos (cantidad y precio deben ser mayores a 0)."}), 400

            prod = db.query(models.Producto).filter(models.Producto.id_producto == id_prod).first()
            if not prod:
                return jsonify({"error": f"El producto ID {id_prod} no existe en el sistema."}), 404

            subtotal_item = round(cant * precio_u, 2)
            total_orden += subtotal_item

            detalles_a_crear.append({
                "id_producto": id_prod,
                "cantidad_solicitada": cant,
                "cantidad_recibida": 0,
                "precio_unitario": precio_u,
                "subtotal": subtotal_item
            })

        total_orden = round(total_orden, 2)

        if not id_usuario:
            primer_u = db.query(models.User).first()
            id_usuario = primer_u.id if primer_u else 1

        nueva_orden = models.OrdenCompra(
            correlativo=correlativo,
            id_proveedor=id_proveedor,
            id_sede=id_sede_final,
            id_usuario=id_usuario,
            fecha_esperada=fecha_esperada,
            estado="PENDIENTE",
            total=total_orden,
            observacion=observacion,
            estado_registro=1
        )
        db.add(nueva_orden)
        db.flush()

        for det in detalles_a_crear:
            nuevo_det = models.DetalleOrdenCompra(
                id_orden_compra=nueva_orden.id_orden_compra,
                id_producto=det["id_producto"],
                cantidad_solicitada=det["cantidad_solicitada"],
                cantidad_recibida=0,
                precio_unitario=det["precio_unitario"],
                subtotal=det["subtotal"]
            )
            db.add(nuevo_det)

        db.commit()
        id_creada = nueva_orden.id_orden_compra

        return jsonify({
            "message": f"Orden de compra {correlativo} emitida con éxito.",
            "id_orden_compra": id_creada,
            "correlativo": correlativo,
            "total": total_orden
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al emitir orden de compra: {str(e)}"}), 500


@compras_bp.route("/api/compras", methods=["GET"])
def get_compras():
    # Lista las ordenes de compra con filtros por sede, estado o busqueda
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

        # Paginacion opcional si la pide el frontend
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
    # Devuelve los datos y productos de una orden de compra especifica
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


@compras_bp.route("/api/compras/<int:id_orden>/recibir", methods=["POST"])
def recibir_orden_compra(id_orden):
    # Registra la recepcion de mercaderia, suma el stock al inventario y crea el movimiento de entrada
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no pueden recibir mercadería"}), 403

    db = get_db()
    try:
        orden = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_orden_compra == id_orden,
            models.OrdenCompra.estado_registro == 1
        ).first()

        if not orden:
            return jsonify({"error": "Orden de compra no encontrada."}), 404

        if orden.estado == "RECIBIDA":
            return jsonify({"error": f"La orden {orden.correlativo} ya fue recibida e ingresada al almacén anteriormente."}), 400

        if orden.estado == "ANULADA":
            return jsonify({"error": f"La orden {orden.correlativo} está anulada. No se puede recibir mercadería."}), 400

        prov = orden.proveedor
        prov_nombre = prov.razon_social if prov else "Proveedor"

        data = request.json or {}
        id_usuario = data.get("id_usuario") or orden.id_usuario

        orden.estado = "RECIBIDA"
        orden.fecha_recepcion = datetime.now()

        productos_ingresados = []
        for det in orden.detalles:
            cant_recibida = det.cantidad_solicitada
            det.cantidad_recibida = cant_recibida

            inv = db.query(models.InventarioSede).filter(
                models.InventarioSede.id_producto == det.id_producto,
                models.InventarioSede.id_sede == orden.id_sede
            ).first()

            if inv:
                inv.stock_actual = (inv.stock_actual or 0) + cant_recibida
                inv.precio_compra = det.precio_unitario
                inv.estado_registro = 1
            else:
                inv = models.InventarioSede(
                    id_producto=det.id_producto,
                    id_sede=orden.id_sede,
                    precio_compra=det.precio_unitario,
                    precio_venta=round(det.precio_unitario * 1.30, 2),
                    stock_actual=cant_recibida,
                    stock_minimo=5,
                    estado_registro=1
                )
                db.add(inv)

            mov = models.MovimientoAlmacen(
                id_producto=det.id_producto,
                id_sede=orden.id_sede,
                tipo="ENTRADA",
                cantidad=cant_recibida,
                id_usuario=id_usuario,
                observacion=f"Ingreso por Compra {orden.correlativo} - Proveedor: {prov_nombre}"
            )
            db.add(mov)

            prod = det.producto
            prod_nombre = prod.nombre if prod else f"ID {det.id_producto}"
            productos_ingresados.append(f"{prod_nombre} (+{cant_recibida} uds)")

        correlativo_final = orden.correlativo
        db.commit()

        return jsonify({
            "message": f"¡Mercadería de la orden {correlativo_final} recibida exitosamente! Se actualizó el stock en almacén.",
            "correlativo": correlativo_final,
            "estado": "RECIBIDA",
            "productos_ingresados": productos_ingresados
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al procesar la recepción de mercadería: {str(e)}"}), 500


@compras_bp.route("/api/compras/<int:id_orden>/anular", methods=["POST"])
def anular_orden_compra(id_orden):
    # Anula la orden y descuenta el stock si la mercaderia ya habia ingresado al almacen
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no pueden anular órdenes de compra"}), 403

    db = get_db()
    try:
        orden = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_orden_compra == id_orden,
            models.OrdenCompra.estado_registro == 1
        ).first()

        if not orden:
            return jsonify({"error": "Orden de compra no encontrada."}), 404

        if orden.estado == "ANULADA":
            return jsonify({"error": "Esta orden ya se encuentra anulada."}), 400

        data = request.json or {}
        motivo = str(data.get("motivo", "Anulación solicitada por el usuario")).strip()
        id_usuario = data.get("id_usuario") or orden.id_usuario

        if orden.estado == "RECIBIDA":
            for det in orden.detalles:
                inv = db.query(models.InventarioSede).filter(
                    models.InventarioSede.id_producto == det.id_producto,
                    models.InventarioSede.id_sede == orden.id_sede
                ).first()
                if not inv or inv.stock_actual < (det.cantidad_recibida or det.cantidad_solicitada):
                    prod = det.producto
                    prod_nombre = prod.nombre if prod else f"ID {det.id_producto}"
                    return jsonify({
                        "error": f"No se puede anular: El producto '{prod_nombre}' ya fue vendido o despachado y no cuenta con suficiente stock en almacén para revertir."
                    }), 400

            for det in orden.detalles:
                cant_a_revertir = det.cantidad_recibida or det.cantidad_solicitada
                inv = db.query(models.InventarioSede).filter(
                    models.InventarioSede.id_producto == det.id_producto,
                    models.InventarioSede.id_sede == orden.id_sede
                ).first()
                if inv:
                    inv.stock_actual -= cant_a_revertir

                mov = models.MovimientoAlmacen(
                    id_producto=det.id_producto,
                    id_sede=orden.id_sede,
                    tipo="SALIDA",
                    cantidad=cant_a_revertir,
                    id_usuario=id_usuario,
                    observacion=f"Reversión por Anulación de Compra {orden.correlativo}. Motivo: {motivo}"
                )
                db.add(mov)

        correlativo_anulada = orden.correlativo
        orden.estado = "ANULADA"
        orden.observacion = (orden.observacion or "") + f" [ANULADA: {motivo}]"
        db.commit()

        return jsonify({
            "message": f"Orden de compra {correlativo_anulada} anulada correctamente.",
            "correlativo": correlativo_anulada,
            "estado": "ANULADA"
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al anular la orden de compra: {str(e)}"}), 500

