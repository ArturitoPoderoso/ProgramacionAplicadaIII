from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from database import get_db
import models

clientes_bp = Blueprint("clientes", __name__)

# Listar todos los clientes activos con opcion de busqueda
@clientes_bp.route("/api/clientes", methods=["GET"])
def get_clientes():
    db = get_db()
    try:
        search = (request.args.get("search") or "").strip().lower()
        page = request.args.get("page", type=int)
        limit = request.args.get("limit", default=20, type=int)

        query = db.query(models.Cliente).filter(models.Cliente.estado_registro == 1)

        if search:
            query = query.filter(
                (models.Cliente.numero_documento.ilike(f"%{search}%")) |
                (models.Cliente.nombres_razon_social.ilike(f"%{search}%")) |
                (models.Cliente.telefono.ilike(f"%{search}%")) |
                (models.Cliente.correo.ilike(f"%{search}%"))
            )

        query = query.order_by(models.Cliente.id_cliente.desc())

        if page and page > 0:
            total_items = query.count()
            total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
            clientes = query.offset((page - 1) * limit).limit(limit).all()
        else:
            total_items = None
            total_pages = None
            clientes = query.all()

        resultado = []
        for c in clientes:
            resultado.append({
                "id_cliente": c.id_cliente,
                "tipo_documento": c.tipo_documento or "DNI",
                "numero_documento": c.numero_documento,
                "nombres_razon_social": c.nombres_razon_social,
                "telefono": c.telefono or "",
                "correo": c.correo or "",
                "direccion": c.direccion or "",
                "fecha_registro": c.fecha_registro.strftime("%Y-%m-%d %H:%M") if c.fecha_registro else ""
            })

        if page and page > 0:
            return jsonify({
                "items": resultado,
                "total": total_items,
                "page": page,
                "pages": total_pages,
                "limit": limit
            }), 200

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({"error": f"Error al consultar clientes: {str(e)}"}), 500


# Busqueda rapida de cliente por DNI o RUC para autocompletar en caja y cotizaciones
@clientes_bp.route("/api/clientes/buscar/<doc>", methods=["GET"])
def buscar_cliente_por_doc(doc):
    db = get_db()
    try:
        doc_limpio = str(doc).strip()
        cliente = db.query(models.Cliente).filter(
            models.Cliente.numero_documento == doc_limpio,
            models.Cliente.estado_registro == 1
        ).first()

        if not cliente:
            return jsonify({"error": "Cliente no encontrado"}), 404

        return jsonify({
            "id_cliente": cliente.id_cliente,
            "tipo_documento": cliente.tipo_documento or "DNI",
            "numero_documento": cliente.numero_documento,
            "nombres_razon_social": cliente.nombres_razon_social,
            "telefono": cliente.telefono or "",
            "correo": cliente.correo or "",
            "direccion": cliente.direccion or ""
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error al buscar cliente: {str(e)}"}), 500


# Obtener los datos de un cliente especifico
@clientes_bp.route("/api/clientes/<int:id_cliente>", methods=["GET"])
def get_cliente(id_cliente):
    db = get_db()
    try:
        cliente = db.query(models.Cliente).filter(
            models.Cliente.id_cliente == id_cliente,
            models.Cliente.estado_registro == 1
        ).first()

        if not cliente:
            return jsonify({"error": "Cliente no encontrado"}), 404

        return jsonify({
            "id_cliente": cliente.id_cliente,
            "tipo_documento": cliente.tipo_documento or "DNI",
            "numero_documento": cliente.numero_documento,
            "nombres_razon_social": cliente.nombres_razon_social,
            "telefono": cliente.telefono or "",
            "correo": cliente.correo or "",
            "direccion": cliente.direccion or "",
            "fecha_registro": cliente.fecha_registro.strftime("%Y-%m-%d %H:%M") if cliente.fecha_registro else ""
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error al obtener cliente: {str(e)}"}), 500


# Registrar un nuevo cliente
@clientes_bp.route("/api/clientes", methods=["POST"])
def create_cliente():
    db = get_db()
    try:
        data = request.json or {}
        num_doc = str(data.get("numero_documento", "")).strip()
        nombre = str(data.get("nombres_razon_social", "")).strip()
        tipo_doc = str(data.get("tipo_documento", "DNI")).strip().upper()
        telefono = str(data.get("telefono", "")).strip()
        correo = str(data.get("correo", "")).strip()
        direccion = str(data.get("direccion", "")).strip()

        if not num_doc:
            return jsonify({"error": "El número de documento es obligatorio."}), 400

        if not nombre:
            return jsonify({"error": "El nombre o razón social es obligatorio."}), 400

        # Validaciones de formato peruano
        if tipo_doc == "DNI":
            if not num_doc.isdigit() or len(num_doc) != 8:
                return jsonify({"error": f"El DNI debe tener exactamente 8 dígitos numéricos (ingresaste {len(num_doc)})."}), 400
        elif tipo_doc == "RUC":
            if not num_doc.isdigit() or len(num_doc) != 11:
                return jsonify({"error": f"El RUC debe tener exactamente 11 dígitos numéricos (ingresaste {len(num_doc)})."}), 400
            if not (num_doc.startswith("10") or num_doc.startswith("20")):
                return jsonify({"error": "El RUC debe iniciar con '10' (Persona Natural) o '20' (Empresa)."}), 400

        # Validar si ya existe
        existente = db.query(models.Cliente).filter(
            models.Cliente.numero_documento == num_doc,
            models.Cliente.estado_registro == 1
        ).first()

        if existente:
            return jsonify({"error": f"El documento {num_doc} ya está registrado a nombre de '{existente.nombres_razon_social}'."}), 400

        # Si habia uno eliminado, lo reactivamos con la nueva informacion
        eliminado = db.query(models.Cliente).filter(
            models.Cliente.numero_documento == num_doc,
            models.Cliente.estado_registro == 0
        ).first()

        if eliminado:
            eliminado.tipo_documento = tipo_doc
            eliminado.nombres_razon_social = nombre
            eliminado.telefono = telefono
            eliminado.correo = correo
            eliminado.direccion = direccion
            eliminado.estado_registro = 1
            db.commit()
            db.refresh(eliminado)
            id_final = eliminado.id_cliente
        else:
            nuevo = models.Cliente(
                tipo_documento=tipo_doc,
                numero_documento=num_doc,
                nombres_razon_social=nombre,
                telefono=telefono,
                correo=correo,
                direccion=direccion,
                estado_registro=1
            )
            db.add(nuevo)
            db.commit()
            db.refresh(nuevo)
            id_final = nuevo.id_cliente

        return jsonify({
            "message": "Cliente registrado exitosamente",
            "id_cliente": id_final,
            "numero_documento": num_doc,
            "nombres_razon_social": nombre
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al registrar cliente: {str(e)}"}), 500


# Actualizar datos de un cliente
@clientes_bp.route("/api/clientes/<int:id_cliente>", methods=["PUT"])
def update_cliente(id_cliente):
    db = get_db()
    try:
        cliente = db.query(models.Cliente).filter(
            models.Cliente.id_cliente == id_cliente,
            models.Cliente.estado_registro == 1
        ).first()

        if not cliente:
            return jsonify({"error": "Cliente no encontrado"}), 404

        data = request.json or {}
        num_doc = str(data.get("numero_documento", cliente.numero_documento)).strip()
        tipo_doc = str(data.get("tipo_documento", cliente.tipo_documento or "DNI")).strip().upper()

        if num_doc != cliente.numero_documento:
            colision = db.query(models.Cliente).filter(
                models.Cliente.numero_documento == num_doc,
                models.Cliente.id_cliente != id_cliente,
                models.Cliente.estado_registro == 1
            ).first()
            if colision:
                return jsonify({"error": f"El documento {num_doc} ya está asignado a otro cliente ({colision.nombres_razon_social})."}), 400
            cliente.numero_documento = num_doc

        if "tipo_documento" in data:
            cliente.tipo_documento = tipo_doc
        if "nombres_razon_social" in data and str(data["nombres_razon_social"]).strip():
            cliente.nombres_razon_social = str(data["nombres_razon_social"]).strip()
        if "telefono" in data:
            cliente.telefono = str(data["telefono"]).strip()
        if "correo" in data:
            cliente.correo = str(data["correo"]).strip()
        if "direccion" in data:
            cliente.direccion = str(data["direccion"]).strip()

        db.commit()
        return jsonify({"message": "Cliente actualizado con éxito"}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al actualizar cliente: {str(e)}"}), 500


# Eliminar un cliente de forma logica
@clientes_bp.route("/api/clientes/<int:id_cliente>", methods=["DELETE"])
def delete_cliente(id_cliente):
    db = get_db()
    try:
        cliente = db.query(models.Cliente).filter(
            models.Cliente.id_cliente == id_cliente,
            models.Cliente.estado_registro == 1
        ).first()

        if not cliente:
            return jsonify({"error": "Cliente no encontrado"}), 404

        nombre_cliente = cliente.nombres_razon_social
        cliente.estado_registro = 0
        db.commit()
        return jsonify({"message": f"Cliente '{nombre_cliente}' eliminado exitosamente"}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al eliminar cliente: {str(e)}"}), 500
