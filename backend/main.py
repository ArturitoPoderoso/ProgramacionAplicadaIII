from flask import Flask, request, jsonify
from flask_cors import CORS
from database import engine, SessionLocal
import models

models.Base.metadata.create_all(bind=engine)

app = Flask(__name__)
CORS(app)

def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

@app.route("/")
def read_root():
    return jsonify({"message": "Bienvenido a la API del Sistema Jesmi"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    dni = str(data.get("dni", "")).strip()
    password = data.get("password")
    
    if not dni or not password:
        return jsonify({"error": "DNI y contraseña requeridos"}), 400
        
    db = get_db()
    user = db.query(models.User).filter(models.User.dni == dni).first()
    db.close()
    
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    if user.password != password:
        return jsonify({"error": "Contraseña incorrecta"}), 401
        
    if not user.is_active:
        return jsonify({"error": "Usuario desactivado"}), 403
        
    return jsonify({
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "role": user.role,
        "roles": user.roles,
        "location": getattr(user, "location", "SJL")
    })

@app.route("/api/users", methods=["GET"])
def get_users():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    db = get_db()
    users = db.query(models.User).all()
    db.close()
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
        "location": u.location,
        "last_access": u.last_access,
        "is_active": u.is_active
    } for u in users])

@app.route("/api/users", methods=["POST"])
def create_user():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json
    
    if user_role == "Supervisor" and data.get("role") in ["Administrador", "Supervisor"]:
        return jsonify({"error": "No tienes permisos para asignar este rol"}), 403
        
    db = get_db()
    db_user = models.User(
        first_name=str(data.get("first_name", "")).strip(),
        last_name=str(data.get("last_name", "")).strip(),
        username=str(data.get("username", "")).strip(),
        email=str(data.get("email", "")).strip(),
        phone=str(data.get("phone", "")).strip(),
        dni=str(data.get("dni", "")).strip(),
        gender=str(data.get("gender", "")).strip(),
        location=str(data.get("location", "")).strip()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Asignar rol
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
        "location": db_user.location,
        "last_access": db_user.last_access,
        "is_active": db_user.is_active
    }
    db.close()
    return jsonify(result)

@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json
    db = get_db()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        db.close()
        return jsonify({"detail": "User not found"}), 404
        
    if user_role == "Supervisor" and db_user.role in ["Administrador", "Supervisor"]:
        db.close()
        return jsonify({"error": "No puedes modificar a este usuario"}), 403
        
    if user_role == "Supervisor" and data.get("role") in ["Administrador", "Supervisor"]:
        db.close()
        return jsonify({"error": "No tienes permisos para asignar este rol"}), 403
        
    if "first_name" in data: db_user.first_name = str(data["first_name"]).strip()
    if "last_name" in data: db_user.last_name = str(data["last_name"]).strip()
    if "username" in data: db_user.username = str(data["username"]).strip()
    if "email" in data: db_user.email = str(data["email"]).strip()
    if "phone" in data: db_user.phone = str(data["phone"]).strip()
    if "dni" in data: db_user.dni = str(data["dni"]).strip()
    if "gender" in data: db_user.gender = str(data["gender"]).strip()
    if "location" in data: db_user.location = str(data["location"]).strip()
    if "last_access" in data: db_user.last_access = data["last_access"]
    if "is_active" in data: db_user.is_active = data["is_active"]
    
    if "roles" in data or "role" in data:
        roles_list = data.get("roles")
        if not roles_list and "role" in data:
            roles_list = [str(data["role"]).strip()]
            
        if roles_list is not None:
            # Delete old roles
            db.query(models.UsuarioPerfil).filter(models.UsuarioPerfil.id_usuario == user_id).delete()
            for role_name in roles_list:
                perfil = db.query(models.Perfil).filter(models.Perfil.nombre == role_name).first()
                if perfil:
                    new_perfil = models.UsuarioPerfil(id_usuario=user_id, id_perfil=perfil.id_perfil)
                    db.add(new_perfil)
    
    db.commit()
    db.refresh(db_user)
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
        "location": db_user.location,
        "last_access": db_user.last_access,
        "is_active": db_user.is_active
    }
    db.close()
    return jsonify(result)

@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    db = get_db()
    user = db.query(models.User).filter(models.User.id == user_id).first()
    db.close()
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
        "location": user.location,
        "is_active": user.is_active,
        "last_access": user.last_access
    })

@app.route("/api/users/<int:user_id>/password", methods=["PUT"])
def update_password(user_id):
    data = request.json
    new_password = data.get("password")
    
    if not new_password:
        return jsonify({"error": "La nueva contraseña es requerida"}), 400
        
    db = get_db()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    db_user.password = new_password
    db.commit()
    db.close()
    return jsonify({"message": "Contraseña actualizada exitosamente"})

@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    db = get_db()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        db.close()
        return jsonify({"detail": "User not found"}), 404
        
    if user_role == "Supervisor" and db_user.role in ["Administrador", "Supervisor"]:
        db.close()
        return jsonify({"error": "No puedes eliminar a este usuario"}), 403
    
    db.delete(db_user)
    db.commit()
    db.close()
    return jsonify({"message": "Usuario eliminado correctamente"})

if __name__ == "__main__":
    app.run(port=8000, debug=True)
