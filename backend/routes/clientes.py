from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import get_db

clientes_bp = Blueprint("clientes", __name__)

# Listar clientes mediante Función Almacenada fn_listar_clientes
@clientes_bp.route("/api/clientes", methods=["GET"])
def get_clientes():
    db = get_db()
    try:
        search = (request.args.get("search") or "").strip().lower()
        page = request.args.get("page", type=int)
        limit = request.args.get("limit", default=20, type=int)

        rows = db.execute(
            text("SELECT id_cliente, tipo_documento, numero_documento, nombre, telefono, fecha_registro FROM fn_listar_clientes(:p_search)"),
            {"p_search": search if search else None}
        ).fetchall()

        resultado = []
        for r in rows:
            resultado.append({
                "id_cliente": r.id_cliente,
                "tipo_documento": r.tipo_documento or "DNI",
                "numero_documento": r.numero_documento,
                "nombre": r.nombre,
                "nombres_razon_social": r.nombre,
                "telefono": r.telefono or "",
                "fecha_registro": r.fecha_registro.strftime("%Y-%m-%d %H:%M") if r.fecha_registro else ""
            })

        if page and page > 0:
            total_items = len(resultado)
            total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
            start_idx = (page - 1) * limit
            paged_items = resultado[start_idx : start_idx + limit]
            return jsonify({
                "items": paged_items,
                "total": total_items,
                "page": page,
                "pages": total_pages,
                "limit": limit
            }), 200

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({"error": f"Error al consultar clientes: {str(e)}"}), 500


# Búsqueda rápida de cliente mediante Función Almacenada fn_buscar_cliente
@clientes_bp.route("/api/clientes/buscar/<doc>", methods=["GET"])
def buscar_cliente_por_doc(doc):
    db = get_db()
    try:
        doc_limpio = str(doc).strip()
        row = db.execute(
            text("SELECT id_cliente, tipo_documento, numero_documento, nombre, telefono FROM fn_buscar_cliente(:criterio)"),
            {"criterio": doc_limpio}
        ).fetchone()

        if not row:
            return jsonify({"error": "Cliente no encontrado"}), 404

        return jsonify({
            "id_cliente": row.id_cliente,
            "tipo_documento": row.tipo_documento or "DNI",
            "numero_documento": row.numero_documento,
            "nombre": row.nombre,
            "nombres_razon_social": row.nombre,
            "telefono": row.telefono or ""
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error al buscar cliente: {str(e)}"}), 500


# Obtener datos de un cliente mediante Función Almacenada fn_obtener_cliente
@clientes_bp.route("/api/clientes/<int:id_cliente>", methods=["GET"])
def get_cliente(id_cliente):
    db = get_db()
    try:
        row = db.execute(
            text("SELECT id_cliente, tipo_documento, numero_documento, nombre, telefono, fecha_registro FROM fn_obtener_cliente(:id)"),
            {"id": id_cliente}
        ).fetchone()

        if not row:
            return jsonify({"error": "Cliente no encontrado"}), 404

        return jsonify({
            "id_cliente": row.id_cliente,
            "tipo_documento": row.tipo_documento or "DNI",
            "numero_documento": row.numero_documento,
            "nombre": row.nombre,
            "nombres_razon_social": row.nombre,
            "telefono": row.telefono or "",
            "fecha_registro": row.fecha_registro.strftime("%Y-%m-%d %H:%M") if row.fecha_registro else ""
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error al obtener cliente: {str(e)}"}), 500


# Registrar un nuevo cliente mediante Stored Procedure sp_guardar_cliente
@clientes_bp.route("/api/clientes", methods=["POST"])
def create_cliente():
    db = get_db()
    try:
        data = request.json or {}
        num_doc = str(data.get("numero_documento", "")).strip()
        nombre = str(data.get("nombre") or data.get("nombres_razon_social", "")).strip()
        tipo_doc = str(data.get("tipo_documento", "DNI")).strip().upper()
        telefono = str(data.get("telefono", "")).strip()

        if not num_doc:
            return jsonify({"error": "El número de documento es obligatorio."}), 400

        if not nombre:
            return jsonify({"error": "El nombre o razón social es obligatorio."}), 400

        if tipo_doc == "DNI":
            if not num_doc.isdigit() or len(num_doc) != 8:
                return jsonify({"error": f"El DNI debe tener exactamente 8 dígitos numéricos (ingresaste {len(num_doc)})."}), 400
        elif tipo_doc == "RUC":
            if not num_doc.isdigit() or len(num_doc) != 11:
                return jsonify({"error": f"El RUC debe tener exactamente 11 dígitos numéricos (ingresaste {len(num_doc)})."}), 400
            if not (num_doc.startswith("10") or num_doc.startswith("20")):
                return jsonify({"error": "El RUC debe iniciar con '10' (Persona Natural) o '20' (Empresa)."}), 400

        res = db.execute(
            text("CALL sp_guardar_cliente(NULL, :tipo_doc, :num_doc, :nombre, :telefono, NULL, NULL)"),
            {
                "tipo_doc": tipo_doc,
                "num_doc": num_doc,
                "nombre": nombre,
                "telefono": telefono
            }
        ).fetchone()
        db.commit()

        id_final = res[0] if res else None
        msg = res[1] if res and len(res) > 1 else "Cliente registrado exitosamente"

        return jsonify({
            "message": msg,
            "id_cliente": id_final,
            "numero_documento": num_doc,
            "nombre": nombre,
            "nombres_razon_social": nombre,
            "telefono": telefono
        }), 201

    except Exception as e:
        db.rollback()
        err_msg = str(e)
        if "ya está registrado" in err_msg:
            clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
            return jsonify({"error": clean_err}), 400
        return jsonify({"error": f"Error al registrar cliente: {err_msg}"}), 500


# Actualizar datos de un cliente mediante Stored Procedure sp_guardar_cliente
@clientes_bp.route("/api/clientes/<int:id_cliente>", methods=["PUT"])
def update_cliente(id_cliente):
    db = get_db()
    try:
        data = request.json or {}
        num_doc = str(data.get("numero_documento", "")).strip()
        nombre = str(data.get("nombre") or data.get("nombres_razon_social", "")).strip()
        tipo_doc = str(data.get("tipo_documento", "DNI")).strip().upper()
        telefono = str(data.get("telefono", "")).strip()

        res = db.execute(
            text("CALL sp_guardar_cliente(:id_cliente, :tipo_doc, :num_doc, :nombre, :telefono, NULL, NULL)"),
            {
                "id_cliente": id_cliente,
                "tipo_doc": tipo_doc if tipo_doc else None,
                "num_doc": num_doc if num_doc else None,
                "nombre": nombre if nombre else None,
                "telefono": telefono
            }
        ).fetchone()
        db.commit()

        msg = res[1] if res and len(res) > 1 else "Cliente actualizado con éxito"
        return jsonify({"message": msg, "id_cliente": id_cliente}), 200

    except Exception as e:
        db.rollback()
        err_msg = str(e)
        if "ya está registrado" in err_msg:
            clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
            return jsonify({"error": clean_err}), 400
        return jsonify({"error": f"Error al actualizar cliente: {err_msg}"}), 500


# Eliminar un cliente de forma lógica mediante Stored Procedure sp_eliminar_cliente
@clientes_bp.route("/api/clientes/<int:id_cliente>", methods=["DELETE"])
def delete_cliente(id_cliente):
    db = get_db()
    try:
        res = db.execute(
            text("CALL sp_eliminar_cliente(:id_cliente, NULL)"),
            {"id_cliente": id_cliente}
        ).fetchone()
        db.commit()

        msg = res[0] if res else "Cliente eliminado exitosamente"
        return jsonify({"message": msg}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al eliminar cliente: {str(e)}"}), 500
