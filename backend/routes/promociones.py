from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import get_db

promociones_bp = Blueprint("promociones", __name__)

# Listado general de promociones mediante Función Almacenada fn_listar_promociones
@promociones_bp.route("/api/promociones", methods=["GET"])
def get_promociones():
    db = get_db()
    try:
        sede_id = request.args.get("sede_id", type=int)
        rows = db.execute(
            text("""
                SELECT id_promocion, nombre, tipo_descuento, valor, aplica_a,
                       id_sede, sede_nombre, id_categoria, categoria_nombre,
                       id_producto, producto_nombre, fecha_inicio, fecha_fin,
                       estado_registro, creador
                FROM fn_listar_promociones(:sede_id)
            """),
            {"sede_id": sede_id if sede_id else None}
        ).fetchall()

        res = [{
            "id_promocion": p.id_promocion,
            "nombre": p.nombre,
            "tipo_descuento": p.tipo_descuento,
            "valor": p.valor,
            "aplica_a": p.aplica_a,
            "id_sede": p.id_sede,
            "sede_nombre": p.sede_nombre or "Todas las Sedes",
            "id_categoria": p.id_categoria,
            "categoria_nombre": p.categoria_nombre,
            "id_producto": p.id_producto,
            "producto_nombre": p.producto_nombre,
            "fecha_inicio": p.fecha_inicio,
            "fecha_fin": p.fecha_fin,
            "estado_registro": p.estado_registro,
            "creador": p.creador or "Sistema"
        } for p in rows]

        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Retorna solo las promociones vigentes hoy mediante Función Almacenada fn_listar_promociones_activas
@promociones_bp.route("/api/promociones/activas", methods=["GET"])
def get_promociones_activas():
    db = get_db()
    try:
        sede_id = request.args.get("sede_id", type=int) or 1
        today_str = datetime.now().strftime("%Y-%m-%d")

        rows = db.execute(
            text("""
                SELECT id_promocion, nombre, tipo_descuento, valor, aplica_a,
                       id_sede, sede_nombre, id_categoria, categoria_nombre,
                       id_producto, producto_nombre, fecha_inicio, fecha_fin
                FROM fn_listar_promociones_activas(:sede_id, :today)
            """),
            {"sede_id": sede_id, "today": today_str}
        ).fetchall()

        res = [{
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
        } for p in rows]

        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Crea una nueva promoción mediante Stored Procedure sp_guardar_promocion
@promociones_bp.route("/api/promociones", methods=["POST"])
def create_promocion():
    db = get_db()
    try:
        data = request.json or {}
        user_id = data.get("user_id") or 1
        id_sede = data.get("id_sede")

        res = db.execute(
            text("""
                CALL sp_guardar_promocion(
                    :nombre, :tipo_descuento, :valor, :aplica_a, :id_sede,
                    :id_categoria, :id_producto, :fecha_inicio, :fecha_fin,
                    :id_usuario, NULL, NULL
                )
            """),
            {
                "nombre": str(data.get("nombre", "")).strip(),
                "tipo_descuento": data.get("tipo_descuento", "PORCENTAJE"),
                "valor": float(data.get("valor", 0)),
                "aplica_a": data.get("aplica_a", "TODOS"),
                "id_sede": int(id_sede) if id_sede else None,
                "id_categoria": int(data.get("id_categoria")) if data.get("id_categoria") else None,
                "id_producto": int(data.get("id_producto")) if data.get("id_producto") else None,
                "fecha_inicio": data.get("fecha_inicio"),
                "fecha_fin": data.get("fecha_fin"),
                "id_usuario": int(user_id)
            }
        ).fetchone()
        db.commit()

        id_promo = res[0] if res else None
        msg = res[1] if res and len(res) > 1 else "Promoción creada exitosamente"

        return jsonify({"message": msg, "id_promocion": id_promo}), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# Desactiva una promoción mediante Stored Procedure sp_eliminar_promocion
@promociones_bp.route("/api/promociones/<int:id_promocion>", methods=["DELETE"])
def delete_promocion(id_promocion):
    db = get_db()
    try:
        res = db.execute(
            text("CALL sp_eliminar_promocion(:id_promocion, NULL)"),
            {"id_promocion": id_promocion}
        ).fetchone()
        db.commit()

        msg = res[0] if res else "Promoción eliminada exitosamente"
        return jsonify({"message": msg}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# Valida las credenciales de un supervisor mediante Función Almacenada fn_autenticar_usuario
@promociones_bp.route("/api/supervisor/autorizar", methods=["POST"])
def autorizar_supervisor():
    db = get_db()
    try:
        data = request.json or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Usuario y contraseña son requeridos"}), 400

        user = db.execute(
            text("SELECT id_usuario, nombre_usuario, clave, nombres, apellidos, roles FROM fn_autenticar_usuario(:user)"),
            {"user": username}
        ).fetchone()

        if not user or user.clave != password:
            return jsonify({"error": "Credenciales de Supervisor incorrectas"}), 401

        user_roles = [r.lower() for r in (user.roles or [])]
        is_supervisor_or_admin = any(role in r for r in user_roles for role in ["admin", "supervisor"])

        if not is_supervisor_or_admin:
            return jsonify({"error": "Acceso denegado: El usuario indicado no cuenta con perfil de Supervisor o Administrador."}), 403

        vendedor_nombre = f"{user.nombres} {user.apellidos}".strip() or user.nombre_usuario
        return jsonify({
            "autorizado": True,
            "message": "Autorización concedida por el supervisor",
            "supervisor": vendedor_nombre,
            "id_supervisor": user.id_usuario
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
