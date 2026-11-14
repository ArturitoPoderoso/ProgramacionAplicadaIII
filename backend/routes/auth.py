from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from database import get_db
import models

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    dni = str(data.get("dni", "")).strip()
    password = data.get("password")
    
    if not dni or not password:
        return jsonify({"error": "DNI y contraseña requeridos"}), 400

    try:
        db = get_db()
        user = db.query(models.User).options(
            joinedload(models.User.sede),
            joinedload(models.User.perfiles)
        ).filter(models.User.dni == dni).first()
        
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
            
        if user.password != password:
            return jsonify({"error": "Contraseña incorrecta"}), 401
            
        if not user.is_active:
            return jsonify({"error": "Usuario desactivado"}), 403

        res_data = {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "role": user.role,
            "roles": user.roles,
            "id_sede": user.id_sede,
            "location": user.sede.nombre if user.sede else "Sin sede"
        }
        return jsonify(res_data)
    except Exception as e:
        print("Login error:", str(e))
        return jsonify({"error": "Error de conexión a la base de datos."}), 500

