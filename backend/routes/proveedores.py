from flask import Blueprint, request, jsonify
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload
from database import get_db
import models

proveedores_bp = Blueprint("proveedores", __name__)

def check_supervisor_or_admin(db, user_role, user_id=None):
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


# Registrar un nuevo proveedor mediante Stored Procedure sp_guardar_proveedor
@proveedores_bp.route("/api/proveedores", methods=["POST"])
def create_proveedor():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Solo Administrador o Supervisor pueden registrar proveedores"}), 403

    db = get_db()
    try:
        data = request.json or {}
        ruc = str(data.get("ruc", "")).strip()
        razon_social = str(data.get("razon_social", "")).strip()
        condiciones_pago = str(data.get("condiciones_pago", "Contado")).strip()
        id_sede = data.get("id_sede")

        if not ruc:
            return jsonify({"error": "El RUC es obligatorio."}), 400

        if not ruc.isdigit():
            return jsonify({"error": "El RUC debe contener únicamente dígitos numéricos."}), 400

        if len(ruc) != 11:
            return jsonify({"error": f"Error en RUC: Debe tener exactamente 11 dígitos (ingresaste {len(ruc)})."}), 400

        if not (ruc.startswith("10") or ruc.startswith("20")):
            return jsonify({"error": "Error en RUC: Debe iniciar obligatoriamente con '10' (Persona Natural con Negocio) o '20' (Persona Jurídica / Empresa)."}), 400

        if not razon_social:
            return jsonify({"error": "La Razón Social o nombre de la empresa es obligatorio."}), 400

        telefono = str(data.get("telefono", "")).strip()
        if not telefono:
            return jsonify({"error": "El Celular es obligatorio."}), 400

        if not telefono.isdigit() or len(telefono) != 9 or not telefono.startswith("9"):
            return jsonify({"error": "Error en Celular: Debe contener exactamente 9 dígitos y comenzar con '9'."}), 400

        id_sede_final = int(id_sede) if id_sede and str(id_sede).isdigit() else 1

        # Invocación de Stored Procedure sp_guardar_proveedor
        res = db.execute(
            text("""
                CALL sp_guardar_proveedor(
                    NULL, :id_sede, :ruc, :razon_social, :nombre_contacto,
                    :telefono, :correo, :direccion, :condiciones_pago, NULL, NULL
                )
            """),
            {
                "id_sede": id_sede_final,
                "ruc": ruc,
                "razon_social": razon_social,
                "nombre_contacto": str(data.get("nombre_contacto", "")).strip(),
                "telefono": telefono,
                "correo": str(data.get("correo", "")).strip(),
                "direccion": str(data.get("direccion", "")).strip(),
                "condiciones_pago": condiciones_pago
            }
        ).fetchone()
        db.commit()

        id_nuevo = res[0] if res else None
        msg = res[1] if res and len(res) > 1 else "Proveedor registrado con éxito."

        return jsonify({
            "message": msg,
            "id_proveedor": id_nuevo
        }), 201

    except Exception as e:
        db.rollback()
        err_msg = str(e)
        if "ya se encuentra registrado" in err_msg:
            clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
            return jsonify({"error": clean_err}), 400
        return jsonify({"error": f"Error al registrar proveedor: {err_msg}"}), 500


# Actualizar datos de un proveedor mediante Stored Procedure sp_guardar_proveedor
@proveedores_bp.route("/api/proveedores/<int:id_proveedor>", methods=["PUT"])
def update_proveedor(id_proveedor):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        data = request.json or {}
        id_sede = int(data.get("id_sede", 1))
        ruc = str(data.get("ruc", "")).strip()
        razon_social = str(data.get("razon_social", "")).strip()
        telefono = str(data.get("telefono", "")).strip()

        # Invocación de Stored Procedure sp_guardar_proveedor
        res = db.execute(
            text("""
                CALL sp_guardar_proveedor(
                    :id_proveedor, :id_sede, :ruc, :razon_social, :nombre_contacto,
                    :telefono, :correo, :direccion, :condiciones_pago, NULL, NULL
                )
            """),
            {
                "id_proveedor": id_proveedor,
                "id_sede": id_sede,
                "ruc": ruc if ruc else None,
                "razon_social": razon_social if razon_social else None,
                "nombre_contacto": str(data.get("nombre_contacto", "")).strip(),
                "telefono": telefono if telefono else None,
                "correo": str(data.get("correo", "")).strip(),
                "direccion": str(data.get("direccion", "")).strip(),
                "condiciones_pago": str(data.get("condiciones_pago", "Contado")).strip()
            }
        ).fetchone()
        db.commit()

        msg = res[1] if res and len(res) > 1 else "Proveedor actualizado correctamente."
        return jsonify({"message": msg}), 200

    except Exception as e:
        db.rollback()
        err_msg = str(e)
        if "ya pertenece a otro proveedor" in err_msg:
            clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
            return jsonify({"error": clean_err}), 400
        return jsonify({"error": f"Error al actualizar proveedor: {err_msg}"}), 500


# Eliminar un proveedor mediante Stored Procedure sp_eliminar_proveedor
@proveedores_bp.route("/api/proveedores/<int:id_proveedor>", methods=["DELETE"])
def delete_proveedor(id_proveedor):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        # Invocación de Stored Procedure sp_eliminar_proveedor
        res = db.execute(
            text("CALL sp_eliminar_proveedor(:id_proveedor, NULL)"),
            {"id_proveedor": id_proveedor}
        ).fetchone()
        db.commit()

        msg = res[0] if res else "Proveedor eliminado con éxito."
        return jsonify({"message": msg}), 200

    except Exception as e:
        db.rollback()
        err_msg = str(e)
        if "No se puede eliminar" in err_msg:
            clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
            return jsonify({"error": clean_err}), 400
        return jsonify({"error": f"Error al eliminar proveedor: {err_msg}"}), 500


@proveedores_bp.route("/api/proveedores/<int:id_proveedor>/catalogo", methods=["GET"])
def get_catalogo_proveedor(id_proveedor):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        rows = db.query(models.ProveedorProducto).options(
            joinedload(models.ProveedorProducto.producto)
        ).filter(
            models.ProveedorProducto.id_proveedor == id_proveedor,
            models.ProveedorProducto.estado_registro == 1
        ).all()

        catalogo = []
        for r in rows:
            prod = r.producto
            catalogo.append({
                "id_proveedor_producto": r.id_proveedor_producto,
                "id_producto": r.id_producto,
                "codigo_producto": prod.codigo_producto if prod else "",
                "nombre_producto": prod.nombre if prod else "Producto desconocido",
                "precio_pactado": round(float(r.precio_pactado), 2),
                "plazo_entrega_dias": r.plazo_entrega_dias or 1,
                "es_principal": bool(r.es_principal)
            })

        return jsonify(catalogo), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener catálogo del proveedor: {str(e)}"}), 500
