from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import get_db

proveedores_bp = Blueprint("proveedores", __name__)

# Listar proveedores mediante Función Almacenada fn_listar_proveedores
@proveedores_bp.route("/api/proveedores", methods=["GET"])
def get_proveedores():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no tienen acceso a proveedores"}), 403

    db = get_db()
    try:
        id_sede_param = request.args.get("id_sede") or request.args.get("sede_id")
        id_sede = int(id_sede_param) if id_sede_param and str(id_sede_param).isdigit() else None

        rows = db.execute(
            text("""
                SELECT id_proveedor, id_sede, sede_nombre, ruc, razon_social,
                       nombre_contacto, telefono, correo, direccion, condiciones_pago,
                       total_productos, total_ordenes, calificacion_promedio, fecha_registro
                FROM fn_listar_proveedores(:p_id_sede)
            """),
            {"p_id_sede": id_sede}
        ).fetchall()

        resultado = []
        for p in rows:
            resultado.append({
                "id_proveedor": p.id_proveedor,
                "id_sede": p.id_sede,
                "sede_nombre": p.sede_nombre or "Sin sede asignada",
                "ruc": p.ruc,
                "razon_social": p.razon_social,
                "nombre_contacto": p.nombre_contacto or "",
                "telefono": p.telefono or "",
                "correo": p.correo or "",
                "direccion": p.direccion or "",
                "condiciones_pago": p.condiciones_pago or "Contado",
                "total_productos": int(p.total_productos or 0),
                "total_ordenes": int(p.total_ordenes or 0),
                "calificacion_promedio": round(float(p.calificacion_promedio), 1) if p.calificacion_promedio else None,
                "fecha_registro": p.fecha_registro.strftime("%Y-%m-%d %H:%M") if p.fecha_registro else ""
            })

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({"error": f"Error al obtener proveedores: {str(e)}"}), 500


# Obtener datos de un proveedor mediante Función Almacenada fn_obtener_proveedor
@proveedores_bp.route("/api/proveedores/<int:id_proveedor>", methods=["GET"])
def get_proveedor(id_proveedor):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        p = db.execute(
            text("""
                SELECT id_proveedor, id_sede, sede_nombre, ruc, razon_social,
                       nombre_contacto, telefono, correo, direccion, condiciones_pago,
                       total_productos, total_ordenes, fecha_registro
                FROM fn_obtener_proveedor(:id_proveedor)
            """),
            {"id_proveedor": id_proveedor}
        ).fetchone()

        if not p:
            return jsonify({"error": "Proveedor no encontrado"}), 404

        data = {
            "id_proveedor": p.id_proveedor,
            "id_sede": p.id_sede,
            "sede_nombre": p.sede_nombre or "Sin sede",
            "ruc": p.ruc,
            "razon_social": p.razon_social,
            "nombre_contacto": p.nombre_contacto or "",
            "telefono": p.telefono or "",
            "correo": p.correo or "",
            "direccion": p.direccion or "",
            "condiciones_pago": p.condiciones_pago or "Contado",
            "total_productos": int(p.total_productos or 0),
            "total_ordenes": int(p.total_ordenes or 0),
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


# Obtener catálogo del proveedor mediante Función Almacenada fn_catalogo_proveedor
@proveedores_bp.route("/api/proveedores/<int:id_proveedor>/catalogo", methods=["GET"])
def get_catalogo_proveedor(id_proveedor):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        rows = db.execute(
            text("""
                SELECT id_proveedor_producto, id_producto, codigo_producto, nombre_producto,
                       precio_pactado, plazo_entrega_dias, es_principal
                FROM fn_catalogo_proveedor(:id_proveedor)
            """),
            {"id_proveedor": id_proveedor}
        ).fetchall()

        catalogo = [{
            "id_proveedor_producto": r.id_proveedor_producto,
            "id_producto": r.id_producto,
            "codigo_producto": r.codigo_producto or "",
            "nombre_producto": r.nombre_producto or "Producto desconocido",
            "precio_pactado": round(float(r.precio_pactado), 2),
            "plazo_entrega_dias": r.plazo_entrega_dias or 1,
            "es_principal": bool(r.es_principal)
        } for r in rows]

        return jsonify(catalogo), 200

    except Exception as e:
        return jsonify({"error": f"Error al obtener catálogo del proveedor: {str(e)}"}), 500
