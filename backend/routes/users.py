from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import get_db

users_bp = Blueprint("users", __name__)

# Listado de sedes activas mediante Función Almacenada fn_listar_sedes
@users_bp.route("/api/sedes", methods=["GET"])
def get_sedes():
    db = get_db()
    try:
        rows = db.execute(text("SELECT id_sede, nombre, direccion, telefono FROM fn_listar_sedes()")).fetchall()
        return jsonify([{
            "id_sede": s.id_sede,
            "nombre": s.nombre,
            "direccion": s.direccion or "",
            "telefono": s.telefono or ""
        } for s in rows]), 200
    except Exception as e:
        return jsonify({"error": f"Error al listar sedes: {str(e)}"}), 500


# Listado de usuarios del sistema mediante Función Almacenada fn_listar_usuarios
@users_bp.route("/api/users", methods=["GET"])
def get_users():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    db = get_db()
    try:
        rows = db.execute(
            text("""
                SELECT id_usuario, nombre_usuario, nombres, apellidos, correo_electronico,
                       celular, dni, genero, id_sede, sede_nombre, ultimo_acceso,
                       estado_registro, roles
                FROM fn_listar_usuarios()
            """)
        ).fetchall()

        resultado = []
        for u in rows:
            roles = list(u.roles) if u.roles else ["Vendedor"]
            primary_role = roles[0] if roles else "Vendedor"

            resultado.append({
                "id": u.id_usuario,
                "first_name": u.nombres or "",
                "last_name": u.apellidos or "",
                "username": u.nombre_usuario or "",
                "email": u.correo_electronico or "",
                "phone": u.celular or "",
                "dni": u.dni or "",
                "role": primary_role,
                "roles": roles,
                "gender": u.genero or "",
                "id_sede": u.id_sede,
                "location": u.sede_nombre or "Sin sede",
                "last_access": u.ultimo_acceso or "Nunca",
                "is_active": u.estado_registro
            })

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({"error": f"Error al listar usuarios: {str(e)}"}), 500


# Creación de usuario mediante Stored Procedure sp_guardar_usuario
@users_bp.route("/api/users", methods=["POST"])
def create_user():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json or {}
    
    if user_role == "Supervisor" and data.get("role") in ["Administrador", "Supervisor"]:
        return jsonify({"error": "No tienes permisos para asignar este rol"}), 403
        
    db = get_db()
    try:
        id_sede = data.get("id_sede") or 1
        roles_list = data.get("roles", [])
        if not roles_list and data.get("role"):
            roles_list = [str(data.get("role")).strip()]

        res = db.execute(
            text("""
                CALL sp_guardar_usuario(
                    NULL, :nombres, :apellidos, :username, :email,
                    :phone, :dni, :gender, :id_sede, :roles, NULL, NULL
                )
            """),
            {
                "nombres": str(data.get("first_name", "")).strip(),
                "apellidos": str(data.get("last_name", "")).strip(),
                "username": str(data.get("username", "")).strip(),
                "email": str(data.get("email", "")).strip(),
                "phone": str(data.get("phone", "")).strip(),
                "dni": str(data.get("dni", "")).strip(),
                "gender": str(data.get("gender", "")).strip(),
                "id_sede": int(id_sede),
                "roles": roles_list
            }
        ).fetchone()
        db.commit()

        id_user = res[0] if res else None
        msg = res[1] if res and len(res) > 1 else "Usuario registrado exitosamente"

        return jsonify({"message": msg, "id": id_user}), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# Actualización de usuario mediante Stored Procedure sp_guardar_usuario
@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json or {}
    db = get_db()
    try:
        id_sede = data.get("id_sede")
        id_sede_final = int(id_sede) if id_sede and str(id_sede).isdigit() else None

        roles_list = data.get("roles")
        if roles_list is None and "role" in data:
            roles_list = [str(data["role"]).strip()]

        res = db.execute(
            text("""
                CALL sp_guardar_usuario(
                    :id_usuario, :nombres, :apellidos, :username, :email,
                    :phone, :dni, :gender, :id_sede, :roles, NULL, NULL
                )
            """),
            {
                "id_usuario": user_id,
                "nombres": str(data["first_name"]).strip() if "first_name" in data else None,
                "apellidos": str(data["last_name"]).strip() if "last_name" in data else None,
                "username": str(data["username"]).strip() if "username" in data else None,
                "email": str(data["email"]).strip() if "email" in data else None,
                "phone": str(data["phone"]).strip() if "phone" in data else None,
                "dni": str(data["dni"]).strip() if "dni" in data else None,
                "gender": str(data["gender"]).strip() if "gender" in data else None,
                "id_sede": id_sede_final,
                "roles": roles_list
            }
        ).fetchone()
        db.commit()

        msg = res[1] if res and len(res) > 1 else "Usuario actualizado exitosamente"
        return jsonify({"message": msg, "id": user_id}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# Desactivación de usuario mediante Stored Procedure sp_eliminar_usuario
@users_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role != "Administrador":
        return jsonify({"error": "Solo administradores pueden eliminar usuarios"}), 403

    db = get_db()
    try:
        res = db.execute(
            text("CALL sp_eliminar_usuario(:user_id, NULL)"),
            {"user_id": user_id}
        ).fetchone()
        db.commit()

        msg = res[0] if res else "Usuario desactivado exitosamente"
        return jsonify({"message": msg}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
