from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from database import get_db
import models

users_bp = Blueprint("users", __name__)

# Listado de sedes activas para selectores y filtros
@users_bp.route("/api/sedes", methods=["GET"])
def get_sedes():
    db = get_db()
    sedes = db.query(models.Sede).filter(models.Sede.estado_registro == 1).all()
    return jsonify([{
        "id_sede": s.id_sede,
        "nombre": s.nombre,
        "direccion": s.direccion,
        "telefono": s.telefono
    } for s in sedes])

# Listado de usuarios del sistema con sus sedes y roles (admin o supervisor)
@users_bp.route("/api/users", methods=["GET"])
def get_users():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    db = get_db()
    users = db.query(models.User).options(joinedload(models.User.sede)).all()
    return jsonify([{
        "id": u.id,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "username": u.username,
        "email": u.email,
        "phone": u.phone,
        "dni": u.dni,
        "role": u.role,
        "roles": u.roles,
        "gender": u.gender,
        "id_sede": u.id_sede,
        "location": u.sede.nombre if u.sede else "Sin sede",
        "last_access": u.last_access,
        "is_active": u.is_active
    } for u in users])

# Creacion de un nuevo usuario en la base de datos
@users_bp.route("/api/users", methods=["POST"])
def create_user():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json or {}
    
    if user_role == "Supervisor" and data.get("role") in ["Administrador", "Supervisor"]:
        return jsonify({"error": "No tienes permisos para asignar este rol"}), 403
        
    db = get_db()
    
    # Buscamos la sede por nombre o dejamos la sede 1 por defecto
    sede_nombre = str(data.get("location", "")).strip()
    sede = db.query(models.Sede).filter(models.Sede.nombre.ilike(f"%{sede_nombre}%")).first()
    id_sede = sede.id_sede if sede else 1
    
    db_user = models.User(
        first_name=str(data.get("first_name", "")).strip(),
        last_name=str(data.get("last_name", "")).strip(),
        username=str(data.get("username", "")).strip(),
        email=str(data.get("email", "")).strip(),
        phone=str(data.get("phone", "")).strip(),
        dni=str(data.get("dni", "")).strip(),
        gender=str(data.get("gender", "")).strip(),
        id_sede=id_sede
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Asignamos los roles al nuevo usuario
    roles_list = data.get("roles", [])
    if not roles_list:
        role_name = str(data.get("role", "Vendedor")).strip()
        roles_list = [role_name]
        
    for role_name in roles_list:
        perfil = db.query(models.Perfil).filter(models.Perfil.nombre == role_name).first()
        if perfil:
            user_perfil = models.UsuarioPerfil(id_usuario=db_user.id, id_perfil=perfil.id_perfil)
            db.add(user_perfil)
    db.commit()
    
    db_user = db.query(models.User).options(joinedload(models.User.sede)).filter(models.User.id == db_user.id).first()
    
    result = {
        "id": db_user.id,
        "first_name": db_user.first_name,
        "last_name": db_user.last_name,
        "username": db_user.username,
        "email": db_user.email,
        "phone": db_user.phone,
        "dni": db_user.dni,
        "role": db_user.role,
        "roles": db_user.roles,
        "gender": db_user.gender,
        "id_sede": db_user.id_sede,
        "location": db_user.sede.nombre if db_user.sede else "Sin sede",
        "last_access": db_user.last_access,
        "is_active": db_user.is_active
    }
    return jsonify(result)

# Actualiza los datos personales, sede o roles del usuario
@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json or {}
    db = get_db()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return jsonify({"detail": "User not found"}), 404
        
    if user_role == "Supervisor" and db_user.role in ["Administrador", "Supervisor"]:
        return jsonify({"error": "No puedes modificar a este usuario"}), 403
        
    if user_role == "Supervisor" and data.get("role") in ["Administrador", "Supervisor"]:
        return jsonify({"error": "No tienes permisos para asignar este rol"}), 403
        
    if "first_name" in data: db_user.first_name = str(data["first_name"]).strip()
    if "last_name" in data: db_user.last_name = str(data["last_name"]).strip()
    if "username" in data: db_user.username = str(data["username"]).strip()
    if "email" in data: db_user.email = str(data["email"]).strip()
    if "phone" in data: db_user.phone = str(data["phone"]).strip()
    if "dni" in data: db_user.dni = str(data["dni"]).strip()
    if "gender" in data: db_user.gender = str(data["gender"]).strip()
    if "location" in data: 
        sede_nombre = str(data["location"]).strip()
        sede = db.query(models.Sede).filter(models.Sede.nombre.ilike(f"%{sede_nombre}%")).first()
        if sede:
            db_user.id_sede = sede.id_sede
            
    if "last_access" in data: db_user.last_access = data["last_access"]
    if "is_active" in data: db_user.is_active = data["is_active"]
    
    if "roles" in data or "role" in data:
        roles_list = data.get("roles")
        if not roles_list and "role" in data:
            roles_list = [str(data["role"]).strip()]
            
        if roles_list is not None:
            # Reemplazamos los roles asignados por la nueva lista
            db.query(models.UsuarioPerfil).filter(models.UsuarioPerfil.id_usuario == user_id).delete()
            for role_name in roles_list:
                perfil = db.query(models.Perfil).filter(models.Perfil.nombre == role_name).first()
                if perfil:
                    new_perfil = models.UsuarioPerfil(id_usuario=user_id, id_perfil=perfil.id_perfil)
                    db.add(new_perfil)
    
    db.commit()
    db_user = db.query(models.User).options(joinedload(models.User.sede)).filter(models.User.id == db_user.id).first()
    
    result = {
        "id": db_user.id,
        "first_name": db_user.first_name,
        "last_name": db_user.last_name,
        "username": db_user.username,
        "email": db_user.email,
        "phone": db_user.phone,
        "dni": db_user.dni,
        "role": db_user.role,
        "roles": db_user.roles,
        "gender": db_user.gender,
        "id_sede": db_user.id_sede,
        "location": db_user.sede.nombre if db_user.sede else "Sin sede",
        "last_access": db_user.last_access,
        "is_active": db_user.is_active
    }
    return jsonify(result)

# Obtiene la informacion de un usuario por su ID
@users_bp.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    db = get_db()
    user = db.query(models.User).options(joinedload(models.User.sede)).filter(models.User.id == user_id).first()
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    return jsonify({
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "dni": user.dni,
        "role": user.role,
        "roles": user.roles,
        "gender": user.gender,
        "id_sede": user.id_sede,
        "location": user.sede.nombre if user.sede else "Sin sede",
        "is_active": user.is_active,
        "last_access": user.last_access
    })

# Actualiza la contraseña del usuario
@users_bp.route("/api/users/<int:user_id>/password", methods=["PUT"])
def update_password(user_id):
    data = request.json or {}
    new_password = data.get("password")
    
    if not new_password:
        return jsonify({"error": "La nueva contraseña es requerida"}), 400
        
    db = get_db()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    db_user.password = new_password
    db.commit()
    return jsonify({"message": "Contraseña actualizada exitosamente"})

# Elimina un usuario del sistema (solo admin o supervisor autorizado)
@users_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    db = get_db()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return jsonify({"detail": "User not found"}), 404
        
    if user_role == "Supervisor" and db_user.role in ["Administrador", "Supervisor"]:
        return jsonify({"error": "No puedes eliminar a este usuario"}), 403
    
    db.delete(db_user)
    db.commit()
    return jsonify({"message": "Usuario eliminado correctamente"})

