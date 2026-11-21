from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import get_db

auth_bp = Blueprint("auth", __name__)

# Validación de credenciales de usuario mediante Función Almacenada fn_autenticar_usuario
@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    dni = str(data.get("dni", "")).strip()
    password = data.get("password")
    
    if not dni or not password:
        return jsonify({"error": "DNI y contraseña requeridos"}), 400

    try:
        db = get_db()
        user = db.execute(
            text("SELECT id_usuario, nombre_usuario, clave, nombres, apellidos, dni, id_sede, sede_nombre, estado_registro, roles FROM fn_autenticar_usuario(:p_username)"),
            {"p_username": dni}
        ).fetchone()

        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        if user.clave != password:
            return jsonify({"error": "Contraseña incorrecta"}), 401

        if user.estado_registro != 1:
            return jsonify({"error": "Usuario desactivado"}), 403

        roles = list(user.roles) if user.roles else ["Vendedor"]
        primary_role = roles[0] if roles else "Vendedor"

        res_data = {
            "id": user.id_usuario,
            "first_name": user.nombres,
            "last_name": user.apellidos,
            "username": user.nombre_usuario,
            "role": primary_role,
            "roles": roles,
            "id_sede": user.id_sede,
            "location": user.sede_nombre or "Sin sede"
        }
        return jsonify(res_data), 200

    except Exception as e:
        print("Login error:", str(e))
        return jsonify({"error": "Error de conexión a la base de datos."}), 500
