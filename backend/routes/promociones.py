from datetime import datetime
from flask import Blueprint, request, jsonify
from database import get_db
import models

promociones_bp = Blueprint("promociones", __name__)

# Listado general de promociones registradas
@promociones_bp.route("/api/promociones", methods=["GET"])
def get_promociones():
    db = get_db()
    try:
        sede_id = request.args.get("sede_id", type=int)
        query = db.query(models.Promocion).filter(models.Promocion.estado_registro == 1)

        if sede_id:
            query = query.filter((models.Promocion.id_sede == None) | (models.Promocion.id_sede == sede_id))

        promos = query.order_by(models.Promocion.id_promocion.desc()).all()
        res = []
        for p in promos:
            res.append({
                "id_promocion": p.id_promocion,
                "nombre": p.nombre,
                "tipo_descuento": p.tipo_descuento,
                "valor": p.valor,
                "aplica_a": p.aplica_a,
                "id_sede": p.id_sede,
                "sede_nombre": p.sede.nombre if p.sede else "Todas las Sedes",
                "id_categoria": p.id_categoria,
                "categoria_nombre": p.categoria.nombre if p.categoria else None,
                "id_producto": p.id_producto,
                "producto_nombre": p.producto.nombre if p.producto else None,
                "fecha_inicio": p.fecha_inicio,
                "fecha_fin": p.fecha_fin,
                "estado_registro": p.estado_registro,
                "creador": p.creador.username if p.creador else "Sistema"
            })
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Retorna solo las promociones vigentes hoy para aplicar en la caja
@promociones_bp.route("/api/promociones/activas", methods=["GET"])
def get_promociones_activas():
    db = get_db()
    try:
        sede_id = request.args.get("sede_id", type=int)
        today_str = datetime.now().strftime("%Y-%m-%d")
        query = db.query(models.Promocion).filter(
            models.Promocion.estado_registro == 1,
            models.Promocion.fecha_inicio <= today_str,
            models.Promocion.fecha_fin >= today_str
        )

        if sede_id:
            query = query.filter((models.Promocion.id_sede == None) | (models.Promocion.id_sede == sede_id))

        promos = query.all()

        res = []
        for p in promos:
            res.append({
                "id_promocion": p.id_promocion,
                "nombre": p.nombre,
                "tipo_descuento": p.tipo_descuento,
                "valor": p.valor,
                "aplica_a": p.aplica_a,
                "id_sede": p.id_sede,
                "id_categoria": p.id_categoria,
                "id_producto": p.id_producto,
                "fecha_inicio": p.fecha_inicio,
                "fecha_fin": p.fecha_fin
            })
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Crea una nueva promocion o descuento por producto, categoria o global
@promociones_bp.route("/api/promociones", methods=["POST"])
def create_promocion():
    db = get_db()
    try:
        data = request.json or {}
        user_id = data.get("user_id")
        id_sede = data.get("id_sede")

        # Verificar rol si se envía user_id
        if user_id:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user_roles = [r.lower() for r in (user.roles or [])]
                if not any(role in r for r in user_roles for role in ["admin", "supervisor"]):
                    return jsonify({"error": "Acceso denegado: Solo Administradores y Supervisores pueden crear campañas de descuento."}), 403
                
                # Si el usuario es Supervisor y no envió id_sede, asignar automáticamente su sede
                if "supervisor" in user_roles and "admin" not in user_roles and not id_sede:
                    id_sede = user.id_sede

        nueva_promo = models.Promocion(
            nombre=data.get("nombre"),
            tipo_descuento=data.get("tipo_descuento", "PORCENTAJE"),
            valor=float(data.get("valor", 0)),
            aplica_a=data.get("aplica_a", "TODOS"),
            id_sede=id_sede,
            id_categoria=data.get("id_categoria"),
            id_producto=data.get("id_producto"),
            fecha_inicio=data.get("fecha_inicio"),
            fecha_fin=data.get("fecha_fin"),
            id_usuario_creador=user_id,
            estado_registro=1
        )
        db.add(nueva_promo)
        db.commit()
        db.refresh(nueva_promo)
        return jsonify({"message": "Promoción creada exitosamente", "id_promocion": nueva_promo.id_promocion}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# Desactiva una promocion
@promociones_bp.route("/api/promociones/<int:id_promocion>", methods=["DELETE"])
def delete_promocion(id_promocion):
    db = get_db()
    try:
        promo = db.query(models.Promocion).filter(models.Promocion.id_promocion == id_promocion).first()
        if not promo:
            return jsonify({"error": "Promoción no encontrada"}), 404

        promo.estado_registro = 0
        db.commit()
        return jsonify({"message": "Promoción eliminada exitosamente"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# Valida las credenciales de un supervisor para autorizar un descuento especial en caja
@promociones_bp.route("/api/supervisor/autorizar", methods=["POST"])
def autorizar_supervisor():
    db = get_db()
    try:
        data = request.json or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Usuario y contraseña son requeridos"}), 400

        user = db.query(models.User).filter(
            models.User.username == username,
            models.User.is_active == 1
        ).first()

        if not user or user.password != password:
            return jsonify({"error": "Credenciales de Supervisor incorrectas"}), 401

        user_roles = [r.lower() for r in (user.roles or [])]
        is_supervisor_or_admin = any(role in r for r in user_roles for role in ["admin", "supervisor"])

        if not is_supervisor_or_admin:
            return jsonify({"error": "Acceso denegado: El usuario indicado no cuenta con perfil de Supervisor o Administrador."}), 403

        vendedor_nombre = f"{user.first_name} {user.last_name}".strip() or user.username
        return jsonify({
            "autorizado": True,
            "message": "Autorización concedida por el supervisor",
            "supervisor": vendedor_nombre,
            "id_supervisor": user.id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

