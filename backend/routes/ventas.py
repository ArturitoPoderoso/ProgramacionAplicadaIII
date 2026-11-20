import uuid
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from database import get_db
import models

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

# Registra una nueva venta, valida stock y descuenta del inventario de la sede
@ventas_bp.route("/api/ventas", methods=["POST"])
def create_venta():
    data = request.json or {}
    detalles = data.get("detalles", [])
    id_usuario = data.get("id_usuario")
    descuento_total = float(data.get("descuento_total", 0.0))
    
    if not detalles:
        return jsonify({"error": "La venta debe tener al menos un producto"}), 400
        
    db = get_db()
    try:
        usuario = db.query(models.User).filter(models.User.id == id_usuario).first()
        if not usuario:
            raise Exception("Usuario no encontrado")
            
        id_sede = usuario.id_sede or 1
        
        # Generamos el correlativo del ticket de venta
        correlativo = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"
        
        # Calculamos subtotales y validamos cada producto
        subtotal_acumulado = 0.0
        detalles_procesados = []

        for det in detalles:
            producto = db.query(models.Producto).filter(models.Producto.id_producto == det["id_producto"]).first()
            if not producto:
                raise Exception(f"Producto con ID {det['id_producto']} no encontrado")
                
            inventario = db.query(models.InventarioSede).filter(
                models.InventarioSede.id_producto == producto.id_producto,
                models.InventarioSede.id_sede == id_sede
            ).first()
            
            if not inventario:
                raise Exception(f"El producto {producto.nombre} no existe en el inventario de esta sede.")
                
            cantidad = int(det["cantidad"])
            if inventario.stock_actual < cantidad:
                raise Exception(f"Stock insuficiente para {producto.nombre} en tu sede. Tienes: {inventario.stock_actual}")

            precio_unitario = float(det["precio_unitario"])
            descuento_unitario = float(det.get("descuento_unitario", 0.0))
            precio_efectivo_unitario = precio_unitario - descuento_unitario
            
            # Validamos que el precio con descuento no quede por debajo del costo de compra
            precio_compra = float(inventario.precio_compra) if (inventario.precio_compra is not None) else 0.0
            if precio_efectivo_unitario < precio_compra:
                raise Exception(f"No se puede aplicar descuento a '{producto.nombre}': El precio final de venta (S/ {precio_efectivo_unitario:.2f}) es inferior al costo de compra (S/ {precio_compra:.2f}).")

            subtotal_item = cantidad * precio_efectivo_unitario
            subtotal_acumulado += subtotal_item

            detalles_procesados.append({
                "producto": producto,
                "inventario": inventario,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "descuento_unitario": descuento_unitario,
                "subtotal": subtotal_item
            })

        total_venta = round(max(0.0, subtotal_acumulado), 2)

        # Identificar o vincular cliente si se envio en la venta
        id_cliente = data.get("id_cliente")
        cliente_nombre = str(data.get("cliente_nombre") or data.get("cliente") or "Cliente General").strip()
        cliente_doc = str(data.get("cliente_doc") or data.get("dni") or "").strip()

        if cliente_doc and not id_cliente:
            cli = db.query(models.Cliente).filter(models.Cliente.numero_documento == cliente_doc).first()
            if cli:
                id_cliente = cli.id_cliente
                if not cliente_nombre or cliente_nombre == "Cliente General":
                    cliente_nombre = cli.nombres_razon_social
            elif cliente_nombre and cliente_nombre != "Cliente General":
                tipo_doc = "RUC" if len(cliente_doc) == 11 else "DNI"
                nuevo_cli = models.Cliente(
                    tipo_documento=tipo_doc,
                    numero_documento=cliente_doc,
                    nombres_razon_social=cliente_nombre,
                    estado_registro=1
                )
                db.add(nuevo_cli)
                db.flush()
                id_cliente = nuevo_cli.id_cliente

        nueva_venta = models.Venta(
            correlativo=correlativo,
            total=total_venta,
            descuento_total=round(descuento_total, 2),
            metodo_pago=data.get("metodo_pago", "Efectivo"),
            id_usuario=id_usuario,
            id_sede=id_sede,
            id_cliente=id_cliente,
            cliente_nombre=cliente_nombre,
            cliente_doc=cliente_doc
        )
        db.add(nueva_venta)
        db.flush() 
        
        # Guardamos los items de la venta y descontamos el stock en la sede del usuario
        for item in detalles_procesados:
            producto = item["producto"]
            inventario = item["inventario"]
            cantidad = item["cantidad"]

            # Restar stock
            inventario.stock_actual -= cantidad
            
            # Crear detalle
            nuevo_detalle = models.DetalleVenta(
                id_venta=nueva_venta.id_venta,
                id_producto=producto.id_producto,
                cantidad=cantidad,
                precio_unitario=item["precio_unitario"],
                descuento_unitario=item["descuento_unitario"],
                subtotal=item["subtotal"]
            )
            db.add(nuevo_detalle)
            
            # Registrar salida en almacén de esta sede
            movimiento = models.MovimientoAlmacen(
                id_producto=producto.id_producto,
                id_sede=id_sede,
                tipo='SALIDA',
                cantidad=-cantidad,
                id_usuario=id_usuario,
                observacion=f"Venta ticket {correlativo}"
            )
            db.add(movimiento)
            
        db.commit()
        id_v = nueva_venta.id_venta
        
        sede = usuario.sede
        sede_nom = sede.nombre if sede else "Sede Principal"
        sede_dir = (sede.direccion if (sede and sede.direccion) else "Av. Central 123, Los Olivos")
        sede_tel = (sede.telefono if (sede and sede.telefono) else "01-1234567")
        vendedor_nom = f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username

        res_data = {
            "message": "Venta procesada exitosamente",
            "id_venta": id_v,
            "correlativo": correlativo,
            "total": total_venta,
            "metodo_pago": nueva_venta.metodo_pago,
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "sede_nombre": sede_nom,
            "sede_direccion": sede_dir,
            "sede_telefono": sede_tel,
            "vendedor": vendedor_nom,
            "id_cliente": id_cliente,
            "cliente": cliente_nombre,
            "dni": cliente_doc
        }
        return jsonify(res_data), 201
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# Consulta el listado de ventas para administradores y supervisores con filtros y totales
@ventas_bp.route("/api/ventas", methods=["GET"])
def get_ventas():
    user_role_hdr = request.headers.get("X-Role", "")
    if user_role_hdr and user_role_hdr.lower() == "vendedor":
        return jsonify({"error": "Acceso denegado: El historial de ventas solo está disponible para Administradores y Supervisores."}), 403

    db = get_db()
    try:
        user_id = request.args.get("user_id", type=int)
        sede_id = request.args.get("sede_id", type=int)

        # Validar rol de usuario si se envía user_id
        if user_id:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user_roles = [r.lower() for r in (user.roles or [])]
                is_admin = any("admin" in r for r in user_roles)
                is_supervisor = any("supervisor" in r for r in user_roles)
                is_vendedor = any("vendedor" in r for r in user_roles)

                if is_vendedor and not is_admin and not is_supervisor:
                    return jsonify({"error": "Acceso denegado: El historial de ventas solo está disponible para Administradores y Supervisores."}), 403

                # Si es Supervisor (y no Admin), forzar únicamente la sede asignada al supervisor
                if is_supervisor and not is_admin:
                    sede_id = user.id_sede or 1
                    
        vendedor_id = request.args.get("vendedor_id", type=int)
        search = request.args.get("search", type=str)
        fecha_inicio = request.args.get("fecha_inicio")
        fecha_fin = request.args.get("fecha_fin")

        query = db.query(models.Venta).options(
            joinedload(models.Venta.detalles),
            joinedload(models.Venta.usuario),
            joinedload(models.Venta.sede)
        ).filter(models.Venta.estado_registro == 1)

        if fecha_inicio:
            try:
                dt_ini_local = datetime.strptime(fecha_inicio, "%Y-%m-%d").replace(tzinfo=PERU_TZ)
                query = query.filter(models.Venta.fecha_venta >= dt_ini_local)
            except Exception:
                pass

        if fecha_fin:
            try:
                dt_fin_local = (datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1)).replace(tzinfo=PERU_TZ)
                query = query.filter(models.Venta.fecha_venta < dt_fin_local)
            except Exception:
                pass

        if sede_id:
            query = query.filter(models.Venta.id_sede == sede_id)

        if vendedor_id:
            query = query.filter(models.Venta.id_usuario == vendedor_id)

        ventas = query.order_by(models.Venta.fecha_venta.desc()).all()

        users_map = {u.id: u for u in db.query(models.User).all()}
        sedes_map = {s.id_sede: s for s in db.query(models.Sede).all()}

        result_ventas = []
        total_monto = 0.0
        total_unidades = 0
        vendedores_conteo = {}

        for v in ventas:
            u = users_map.get(v.id_usuario)
            s = sedes_map.get(v.id_sede)

            vendedor_nom = f"{u.first_name} {u.last_name}".strip() if u else "Desconocido"
            if not vendedor_nom or (u and vendedor_nom == u.username):
                vendedor_nom = u.username if u else "Desconocido"

            sede_nom = s.nombre if s else "Sede Principal"

            cli_nom = getattr(v, 'cliente_nombre', 'Cliente General') or 'Cliente General'
            cli_doc = getattr(v, 'cliente_doc', '') or ''

            if search:
                s_lower = search.lower().strip()
                match_correlativo = s_lower in (v.correlativo or "").lower()
                match_vendedor = s_lower in vendedor_nom.lower()
                match_cliente = s_lower in cli_nom.lower() or s_lower in cli_doc.lower()
                if not (match_correlativo or match_vendedor or match_cliente):
                    continue

            unidades_venta = sum([d.cantidad for d in v.detalles]) if v.detalles else 0
            fecha_str = format_peru_datetime(v.fecha_venta)

            total_monto += (v.total or 0.0)
            total_unidades += unidades_venta
            vendedores_conteo[vendedor_nom] = vendedores_conteo.get(vendedor_nom, 0) + (v.total or 0.0)

            result_ventas.append({
                "id_venta": v.id_venta,
                "correlativo": v.correlativo,
                "fecha": fecha_str,
                "total": round(v.total or 0.0, 2),
                "metodo_pago": v.metodo_pago,
                "unidades_totales": unidades_venta,
                "vendedor": vendedor_nom,
                "cliente": cli_nom,
                "cliente_doc": cli_doc,
                "id_cliente": getattr(v, 'id_cliente', None),
                "sede": sede_nom,
                "id_sede": v.id_sede,
                "id_usuario": v.id_usuario
            })

        top_vendedor = "N/A"
        if vendedores_conteo:
            top_vendedor = max(vendedores_conteo, key=vendedores_conteo.get)

        kpis = {
            "monto_total": round(total_monto, 2),
            "unidades_totales": total_unidades,
            "total_comprobantes": len(result_ventas),
            "top_vendedor": top_vendedor
        }

        # Paginacion opcional si el frontend la solicita
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


# Obtiene el detalle de una venta especifica para reimprimir o ver la boleta
@ventas_bp.route("/api/ventas/<int:id_venta>", methods=["GET"])
def get_detalle_venta(id_venta):
    db = get_db()
    try:
        venta = db.query(models.Venta).filter(models.Venta.id_venta == id_venta).first()
        if not venta:
            return jsonify({"error": "Venta no encontrada"}), 404

        u = db.query(models.User).filter(models.User.id == venta.id_usuario).first()
        s = db.query(models.Sede).filter(models.Sede.id_sede == venta.id_sede).first()

        vendedor_nom = f"{u.first_name} {u.last_name}".strip() if u else "Desconocido"
        if not vendedor_nom and u:
            vendedor_nom = u.username

        sede_nom = s.nombre if s else "Sede Principal"
        sede_dir = s.direccion if (s and s.direccion) else "Av. Central 123, Los Olivos"
        sede_tel = s.telefono if (s and s.telefono) else "01-1234567"

        detalles_res = []
        for d in venta.detalles:
            prod_nom = d.producto.nombre if d.producto else "Producto"
            prod_cod = d.producto.codigo_producto if d.producto else "PROD"
            detalles_res.append({
                "id_producto": d.id_producto,
                "codigo": prod_cod,
                "nombre": prod_nom,
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
                "descuento_unitario": getattr(d, 'descuento_unitario', 0.0) or 0.0,
                "subtotal": d.subtotal
            })

        data = {
            "id_venta": venta.id_venta,
            "correlativo": venta.correlativo,
            "fecha": format_peru_datetime(venta.fecha_venta),
            "total": venta.total,
            "descuento_total": getattr(venta, 'descuento_total', 0.0) or 0.0,
            "metodo_pago": venta.metodo_pago,
            "vendedor": vendedor_nom,
            "id_cliente": getattr(venta, 'id_cliente', None),
            "cliente": getattr(venta, 'cliente_nombre', 'Cliente General') or 'Cliente General',
            "cliente_doc": getattr(venta, 'cliente_doc', '') or '',
            "sede_nombre": sede_nom,
            "sede_direccion": sede_dir,
            "sede_telefono": sede_tel,
            "detalles": detalles_res
        }
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

