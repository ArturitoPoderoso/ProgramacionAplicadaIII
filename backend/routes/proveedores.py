from flask import Blueprint, request, jsonify
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from database import get_db
import models

proveedores_bp = Blueprint("proveedores", __name__)

def check_supervisor_or_admin(db, user_role, user_id=None):
    # Revisa si el usuario tiene rol de Administrador o Supervisor
    if user_role and user_role.lower() in ["administrador", "admin", "supervisor"]:
        return True
    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            roles = [r.lower() for r in (user.roles or [])]
            return any(r in ["administrador", "admin", "supervisor"] for r in roles)
    return False


@proveedores_bp.route("/api/proveedores", methods=["GET"])
def get_proveedores():
    # Lista los proveedores activos con sus productos y ordenes registradas
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no tienen acceso a proveedores"}), 403

    db = get_db()
    try:
        id_sede_param = request.args.get("id_sede") or request.args.get("sede_id")
        query = db.query(models.Proveedor).options(joinedload(models.Proveedor.sede)).filter(models.Proveedor.estado_registro == 1)
        if id_sede_param and str(id_sede_param).isdigit():
            query = query.filter(models.Proveedor.id_sede == int(id_sede_param))

        proveedores = query.order_by(models.Proveedor.razon_social.asc()).all()

        # Agrupamos en consultas directas para contar productos y ordenes por proveedor
        prods_map = dict(
            db.query(models.ProveedorProducto.id_proveedor, func.count(models.ProveedorProducto.id_proveedor_producto))
            .filter(models.ProveedorProducto.estado_registro == 1)
            .group_by(models.ProveedorProducto.id_proveedor)
            .all()
        )

        ordenes_map = dict(
            db.query(models.OrdenCompra.id_proveedor, func.count(models.OrdenCompra.id_orden_compra))
            .filter(models.OrdenCompra.estado_registro == 1)
            .group_by(models.OrdenCompra.id_proveedor)
            .all()
        )

        calif_map = dict(
            db.query(models.EvaluacionProveedor.id_proveedor, func.avg(models.EvaluacionProveedor.calificacion))
            .filter(models.EvaluacionProveedor.estado_registro == 1)
            .group_by(models.EvaluacionProveedor.id_proveedor)
            .all()
        )

        resultado = []
        for p in proveedores:
            total_prods = prods_map.get(p.id_proveedor, 0)
            total_ordenes = ordenes_map.get(p.id_proveedor, 0)
            promedio_calif = calif_map.get(p.id_proveedor, None)

            resultado.append({
                "id_proveedor": p.id_proveedor,
                "id_sede": p.id_sede,
                "sede_nombre": p.sede.nombre if p.sede else "Sin sede asignada",
                "ruc": p.ruc,
                "razon_social": p.razon_social,
                "nombre_contacto": p.nombre_contacto or "",
                "telefono": p.telefono or "",
                "correo": p.correo or "",
                "direccion": p.direccion or "",
                "condiciones_pago": p.condiciones_pago or "Contado",
                "total_productos": total_prods,
                "total_ordenes": total_ordenes,
                "calificacion_promedio": round(float(promedio_calif), 1) if promedio_calif else None,
                "fecha_registro": p.fecha_registro.strftime("%Y-%m-%d %H:%M") if p.fecha_registro else ""
            })

        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener proveedores: {str(e)}"}), 500


@proveedores_bp.route("/api/proveedores/<int:id_proveedor>", methods=["GET"])
def get_proveedor(id_proveedor):
    # Obtiene los datos de un proveedor por su ID
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        p = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not p:
            return jsonify({"error": "Proveedor no encontrado"}), 404

        total_prods = db.query(models.ProveedorProducto).filter(
            models.ProveedorProducto.id_proveedor == p.id_proveedor,
            models.ProveedorProducto.estado_registro == 1
        ).count()

        total_ordenes = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_proveedor == p.id_proveedor,
            models.OrdenCompra.estado_registro == 1
        ).count()

        data = {
            "id_proveedor": p.id_proveedor,
            "id_sede": p.id_sede,
            "sede_nombre": p.sede.nombre if p.sede else "Sin sede",
            "ruc": p.ruc,
            "razon_social": p.razon_social,
            "nombre_contacto": p.nombre_contacto or "",
            "telefono": p.telefono or "",
            "correo": p.correo or "",
            "direccion": p.direccion or "",
            "condiciones_pago": p.condiciones_pago or "Contado",
            "total_productos": total_prods,
            "total_ordenes": total_ordenes,
            "fecha_registro": p.fecha_registro.strftime("%Y-%m-%d %H:%M") if p.fecha_registro else ""
        }
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@proveedores_bp.route("/api/proveedores", methods=["POST"])
def create_proveedor():
    # Registra un nuevo proveedor validando formato de RUC y celular
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Solo Administrador o Supervisor pueden registrar proveedores"}), 403

    db = get_db()
    try:
        data = request.json or {}
        ruc = str(data.get("ruc", "")).strip()
        razon_social = str(data.get("razon_social", "")).strip()
        condiciones_pago = str(data.get("condiciones_pago", "")).strip()
        id_sede = data.get("id_sede")

        if not ruc:
            return jsonify({"error": "El RUC es obligatorio."}), 400

        if not ruc.isdigit():
            return jsonify({"error": "El RUC debe contener únicamente dígitos numéricos."}), 400

        if len(ruc) < 11:
            return jsonify({"error": f"Error en RUC: Tiene menos de 11 dígitos ({len(ruc)} dígitos). Debe tener exactamente 11 dígitos."}), 400

        if len(ruc) > 11:
            return jsonify({"error": f"Error en RUC: Tiene más de 11 dígitos ({len(ruc)} dígitos). Debe tener exactamente 11 dígitos."}), 400

        if not (ruc.startswith("10") or ruc.startswith("20")):
            return jsonify({"error": "Error en RUC: Debe iniciar obligatoriamente con '10' (Persona Natural con Negocio) o '20' (Persona Jurídica / Empresa)."}), 400

        if not razon_social:
            return jsonify({"error": "La Razón Social o nombre de la empresa es obligatorio."}), 400

        telefono = str(data.get("telefono", "")).strip()
        if not telefono:
            return jsonify({"error": "El Celular es obligatorio."}), 400

        if not telefono.isdigit():
            return jsonify({"error": "El Celular debe contener únicamente dígitos numéricos."}), 400

        if len(telefono) != 9:
            return jsonify({"error": f"Error en Celular: Debe tener exactamente 9 dígitos ({len(telefono)} dígitos ingresados)."}), 400

        if not telefono.startswith("9"):
            return jsonify({"error": "Error en Celular: Debe ser un número celular que comience con '9'."}), 400

        id_sede_final = int(id_sede) if id_sede and str(id_sede).isdigit() else 1

        # Validamos que no exista otro proveedor con el mismo RUC en la misma sede
        existente = db.query(models.Proveedor).filter(
            models.Proveedor.ruc == ruc,
            models.Proveedor.id_sede == id_sede_final,
            models.Proveedor.estado_registro == 1
        ).first()

        if existente:
            return jsonify({"error": f"El RUC {ruc} ya se encuentra registrado para '{existente.razon_social}' en esta sede."}), 400

        # Si había uno eliminado con el mismo RUC y sede, lo reactivamos con los datos nuevos
        eliminado_previo = db.query(models.Proveedor).filter(
            models.Proveedor.ruc == ruc,
            models.Proveedor.id_sede == id_sede_final,
            models.Proveedor.estado_registro == 0
        ).first()

        if eliminado_previo:
            eliminado_previo.id_sede = id_sede_final
            eliminado_previo.razon_social = razon_social
            eliminado_previo.nombre_contacto = str(data.get("nombre_contacto", "")).strip()
            eliminado_previo.telefono = telefono
            eliminado_previo.correo = str(data.get("correo", "")).strip()
            eliminado_previo.direccion = str(data.get("direccion", "")).strip()
            eliminado_previo.condiciones_pago = condiciones_pago or "Contado"
            eliminado_previo.estado_registro = 1
            db.commit()
            db.refresh(eliminado_previo)
            id_nuevo = eliminado_previo.id_proveedor
        else:
            nuevo = models.Proveedor(
                ruc=ruc,
                id_sede=id_sede_final,
                razon_social=razon_social,
                nombre_contacto=str(data.get("nombre_contacto", "")).strip(),
                telefono=telefono,
                correo=str(data.get("correo", "")).strip(),
                direccion=str(data.get("direccion", "")).strip(),
                condiciones_pago=condiciones_pago or "Contado",
                estado_registro=1
            )
            db.add(nuevo)
            db.commit()
            db.refresh(nuevo)
            id_nuevo = nuevo.id_proveedor

        return jsonify({
            "message": "Proveedor registrado con éxito.",
            "id_proveedor": id_nuevo
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al registrar proveedor: {str(e)}"}), 500


@proveedores_bp.route("/api/proveedores/<int:id_proveedor>", methods=["PUT"])
def update_proveedor(id_proveedor):
    # Actualiza los datos del proveedor
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not proveedor:
            return jsonify({"error": "Proveedor no encontrado"}), 404

        data = request.json or {}
        if "id_sede" in data and str(data["id_sede"]).isdigit():
            proveedor.id_sede = int(data["id_sede"])

        ruc_nuevo = str(data.get("ruc", proveedor.ruc)).strip()

        if ruc_nuevo != proveedor.ruc:
            if not ruc_nuevo.isdigit():
                return jsonify({"error": "El RUC debe contener únicamente dígitos numéricos."}), 400
            if len(ruc_nuevo) < 11:
                return jsonify({"error": f"Error en RUC: Tiene menos de 11 dígitos ({len(ruc_nuevo)} dígitos). Debe tener exactamente 11 dígitos."}), 400
            if len(ruc_nuevo) > 11:
                return jsonify({"error": f"Error en RUC: Tiene más de 11 dígitos ({len(ruc_nuevo)} dígitos). Debe tener exactamente 11 dígitos."}), 400
            if not (ruc_nuevo.startswith("10") or ruc_nuevo.startswith("20")):
                return jsonify({"error": "Error en RUC: Debe iniciar obligatoriamente con '10' (Persona Natural con Negocio) o '20' (Persona Jurídica / Empresa)."}), 400
            colision = db.query(models.Proveedor).filter(
                models.Proveedor.ruc == ruc_nuevo,
                models.Proveedor.id_sede == proveedor.id_sede,
                models.Proveedor.id_proveedor != id_proveedor,
                models.Proveedor.estado_registro == 1
            ).first()
            if colision:
                return jsonify({"error": f"El RUC {ruc_nuevo} ya pertenece a otro proveedor ({colision.razon_social}) en esta sede."}), 400
            proveedor.ruc = ruc_nuevo

        if "razon_social" in data and str(data["razon_social"]).strip():
            proveedor.razon_social = str(data["razon_social"]).strip()
        if "nombre_contacto" in data:
            proveedor.nombre_contacto = str(data["nombre_contacto"]).strip()
        if "telefono" in data:
            tel = str(data["telefono"]).strip()
            if not tel:
                return jsonify({"error": "El Celular es obligatorio."}), 400
            if not tel.isdigit():
                return jsonify({"error": "El Celular debe contener únicamente dígitos numéricos."}), 400
            if len(tel) != 9:
                return jsonify({"error": f"Error en Celular: Debe tener exactamente 9 dígitos (ingresaste {len(tel)} dígitos)."}), 400
            if not tel.startswith("9"):
                return jsonify({"error": "Error en Celular: Debe comenzar obligatoriamente con '9' (número celular)."}), 400
            proveedor.telefono = tel
        if "correo" in data:
            proveedor.correo = str(data["correo"]).strip()
        if "direccion" in data:
            proveedor.direccion = str(data["direccion"]).strip()
        if "condiciones_pago" in data and str(data["condiciones_pago"]).strip():
            proveedor.condiciones_pago = str(data["condiciones_pago"]).strip()

        db.commit()
        return jsonify({"message": "Proveedor actualizado correctamente."}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al actualizar proveedor: {str(e)}"}), 500


@proveedores_bp.route("/api/proveedores/<int:id_proveedor>", methods=["DELETE"])
def delete_proveedor(id_proveedor):
    # Desactiva un proveedor si no tiene ordenes de compra asociadas
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not proveedor:
            return jsonify({"error": "Proveedor no encontrado"}), 404

        compras_asociadas = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_proveedor == id_proveedor,
            models.OrdenCompra.estado_registro == 1
        ).count()

        if compras_asociadas > 0:
            return jsonify({
                "error": f"No se puede eliminar a '{proveedor.razon_social}' porque tiene {compras_asociadas} orden(es) de compra registrada(s). Por integridad contable y de auditoría la acción fue rechazada."
            }), 400

        nombre_prov = proveedor.razon_social
        proveedor.estado_registro = 0
        db.commit()
        return jsonify({"message": f"Proveedor '{nombre_prov}' eliminado con éxito."}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al eliminar proveedor: {str(e)}"}), 500


@proveedores_bp.route("/api/proveedores/<int:id_proveedor>/catalogo", methods=["GET"])
def get_catalogo_proveedor(id_proveedor):
    # Lista los productos asociados a este proveedor con su precio pactado
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not proveedor:
            return jsonify({"error": "Proveedor no encontrado"}), 404

        proveedor_info = {
            "id_proveedor": proveedor.id_proveedor,
            "ruc": proveedor.ruc,
            "razon_social": proveedor.razon_social,
            "id_sede": proveedor.id_sede,
            "sede_nombre": proveedor.sede.nombre if proveedor.sede else "Todas las sedes",
            "condiciones_pago": proveedor.condiciones_pago
        }

        sede_param = request.args.get("id_sede", type=int) or request.args.get("sede_id", type=int)
        id_sede_consulta = proveedor.id_sede or sede_param or 1

        items = db.query(models.ProveedorProducto).join(
            models.Producto, models.ProveedorProducto.id_producto == models.Producto.id_producto
        ).filter(
            models.ProveedorProducto.id_proveedor == id_proveedor,
            models.ProveedorProducto.estado_registro == 1,
            models.Producto.estado_registro == 1
        ).all()

        resultado = []
        for it in items:
            p = it.producto
            cat_nom = p.categoria.nombre if p.categoria else "Sin categoría"
            subcat_nom = p.subcategoria_rel.nombre if p.subcategoria_rel else None

            inv = db.query(models.InventarioSede).filter(
                models.InventarioSede.id_producto == p.id_producto,
                models.InventarioSede.id_sede == id_sede_consulta,
                models.InventarioSede.estado_registro == 1
            ).first()

            if not inv:
                inv = db.query(models.InventarioSede).filter(
                    models.InventarioSede.id_producto == p.id_producto,
                    models.InventarioSede.estado_registro == 1
                ).first()

            precio_oficial = round(float(inv.precio_compra), 2) if (inv and inv.precio_compra is not None) else round(float(it.precio_compra), 2)

            if inv and inv.precio_compra is not None and it.precio_compra != precio_oficial:
                it.precio_compra = precio_oficial

            resultado.append({
                "id_proveedor_producto": it.id_proveedor_producto,
                "id_producto": p.id_producto,
                "codigo_producto": p.codigo_producto,
                "nombre": p.nombre,
                "descripcion": p.descripcion or "",
                "categoria": cat_nom,
                "subcategoria": subcat_nom,
                "precio_compra": precio_oficial,
                "codigo_proveedor": it.codigo_proveedor or "",
                "fecha_registro": it.fecha_registro.strftime("%Y-%m-%d") if it.fecha_registro else ""
            })

        db.commit()
        return jsonify({
            "proveedor": proveedor_info,
            "productos": resultado
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error al cargar catálogo del proveedor: {str(e)}"}), 500


@proveedores_bp.route("/api/proveedores/<int:id_proveedor>/catalogo", methods=["POST"])
@proveedores_bp.route("/api/proveedores/<int:id_proveedor>/productos", methods=["POST"])
def asociar_producto_catalogo(id_proveedor):
    # Asocia un producto al proveedor o actualiza su precio de compra pactado
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        data = request.json or {}
        id_producto = data.get("id_producto")
        precio_compra = data.get("precio_compra")
        codigo_proveedor = str(data.get("codigo_proveedor", "")).strip()

        if not id_producto:
            return jsonify({"error": "Debe seleccionar un producto."}), 400

        try:
            precio_compra = float(precio_compra)
            if precio_compra <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            return jsonify({"error": "El precio de compra debe ser un número mayor a 0."}), 400

        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()
        if not proveedor:
            return jsonify({"error": "Proveedor no encontrado o inactivo"}), 404

        producto = db.query(models.Producto).filter(
            models.Producto.id_producto == id_producto,
            models.Producto.estado_registro == 1
        ).first()
        if not producto:
            return jsonify({"error": "Producto no encontrado o inactivo"}), 404

        existente = db.query(models.ProveedorProducto).filter(
            models.ProveedorProducto.id_proveedor == id_proveedor,
            models.ProveedorProducto.id_producto == id_producto
        ).first()

        if existente:
            existente.precio_compra = precio_compra
            if codigo_proveedor:
                existente.codigo_proveedor = codigo_proveedor
            existente.estado_registro = 1
            msg = f"Precio de compra actualizado a S/. {precio_compra:.2f} para '{producto.nombre}'."
        else:
            nuevo = models.ProveedorProducto(
                id_proveedor=id_proveedor,
                id_producto=id_producto,
                precio_compra=precio_compra,
                codigo_proveedor=codigo_proveedor,
                estado_registro=1
            )
            db.add(nuevo)
            msg = f"Producto '{producto.nombre}' incorporado al catálogo de {proveedor.razon_social} con precio S/. {precio_compra:.2f}."

        invs = db.query(models.InventarioSede).filter(models.InventarioSede.id_producto == id_producto).all()
        for inv in invs:
            inv.precio_compra = precio_compra

        db.commit()
        return jsonify({"message": msg}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al asociar producto: {str(e)}"}), 500


@proveedores_bp.route("/api/proveedores/<int:id_proveedor>/catalogo/<int:id_producto>", methods=["DELETE"])
def desasociar_producto_catalogo(id_proveedor, id_producto):
    # Quita un producto del catalogo de este proveedor
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        asoc = db.query(models.ProveedorProducto).filter(
            models.ProveedorProducto.id_proveedor == id_proveedor,
            models.ProveedorProducto.id_producto == id_producto
        ).first()

        if not asoc:
            return jsonify({"error": "El producto no está asociado a este proveedor."}), 404

        asoc.estado_registro = 0
        db.commit()
        return jsonify({"message": "Producto removido del catálogo del proveedor."}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al desasociar producto: {str(e)}"}), 500

