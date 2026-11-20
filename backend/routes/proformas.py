from datetime import datetime
from flask import Blueprint, request, jsonify
from database import get_db
import models

proformas_bp = Blueprint("proformas", __name__)

# Guarda una nueva cotizacion o proforma emitida por un vendedor
@proformas_bp.route("/api/proformas", methods=["POST"])
def registrar_proforma():
    data = request.json or {}
    id_usuario = data.get("id_usuario")
    id_sede = data.get("id_sede")
    cliente_nombre = data.get("cliente_nombre", "Cliente General").strip() or "Cliente General"
    cliente_doc = data.get("cliente_doc", "").strip()
    validez_dias = int(data.get("validez_dias", 7))
    detalles = data.get("detalles", [])

    if not id_usuario or not id_sede or not detalles:
        return jsonify({"error": "Faltan datos obligatorios (id_usuario, id_sede, detalles)"}), 400

    db = get_db()
    try:
        rol_solicitante = data.get("rol", "").strip()
        user = db.query(models.User).filter(models.User.id == id_usuario).first()
        if user:
            if not rol_solicitante:
                rol_solicitante = user.role

            if rol_solicitante.lower() != "vendedor":
                return jsonify({"error": "Únicamente en el perfil Vendedor se pueden emitir proformas."}), 403

        now = datetime.now()
        correlativo = f"P-{now.strftime('%Y%m%d%H%M%S')}"

        total_proforma = 0.0
        for item in detalles:
            sub = float(item["cantidad"]) * float(item["precio_unitario"])
            total_proforma += sub

        # Identificar o registrar cliente si se envio en la cotizacion
        id_cliente = data.get("id_cliente")
        if cliente_doc and not id_cliente:
            cli = db.query(models.Cliente).filter(models.Cliente.numero_documento == cliente_doc).first()
            if cli:
                id_cliente = cli.id_cliente
                if not cliente_nombre or cliente_nombre == "Cliente General":
                    cliente_nombre = cli.nombres_razon_social
            elif cliente_nombre and cliente_nombre != "Cliente General":
                tipo_doc = "RUC" if len(cliente_doc) == 11 else "DNI"
                nuevo_cli = models.Cliente(
                    tipo_documento=tipo_doc,
                    numero_documento=cliente_doc,
                    nombres_razon_social=cliente_nombre,
                    estado_registro=1
                )
                db.add(nuevo_cli)
                db.flush()
                id_cliente = nuevo_cli.id_cliente

        nueva_proforma = models.Proforma(
            correlativo=correlativo,
            cliente_nombre=cliente_nombre,
            cliente_doc=cliente_doc,
            id_cliente=id_cliente,
            validez_dias=validez_dias,
            total=round(total_proforma, 2),
            id_usuario=id_usuario,
            id_sede=id_sede
        )
        db.add(nueva_proforma)
        db.flush()

        for item in detalles:
            sub = float(item["cantidad"]) * float(item["precio_unitario"])
            det_prof = models.DetalleProforma(
                id_proforma=nueva_proforma.id_proforma,
                id_producto=item["id_producto"],
                cantidad=int(item["cantidad"]),
                precio_unitario=float(item["precio_unitario"]),
                subtotal=round(sub, 2)
            )
            db.add(det_prof)

        db.commit()
        prof_id = nueva_proforma.id_proforma

        return jsonify({
            "message": "Proforma registrada con éxito",
            "id_proforma": prof_id,
            "correlativo": correlativo
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# Lista el historial de proformas emitidas con filtros por sede o cliente
@proformas_bp.route("/api/proformas", methods=["GET"])
def get_proformas():
    db = get_db()
    try:
        id_usuario = request.args.get("id_usuario", type=int)
        sede_id = request.args.get("sede_id", type=int)
        search = request.args.get("search", "").strip()

        query = db.query(models.Proforma).filter(models.Proforma.estado_registro == 1)

        if id_usuario:
            user = db.query(models.User).filter(models.User.id == id_usuario).first()
            if user:
                roles = [r.lower() for r in (user.roles or [])]
                if "vendedor" in roles and "administrador" not in roles:
                    query = query.filter(models.Proforma.id_sede == user.id_sede)
                elif "supervisor" in roles and "administrador" not in roles:
                    query = query.filter(models.Proforma.id_sede == user.id_sede)

        if sede_id:
            query = query.filter(models.Proforma.id_sede == sede_id)

        if search:
            query = query.filter(
                (models.Proforma.correlativo.ilike(f"%{search}%")) |
                (models.Proforma.cliente_nombre.ilike(f"%{search}%")) |
                (models.Proforma.cliente_doc.ilike(f"%{search}%"))
            )

        proformas = query.order_by(models.Proforma.fecha_emision.desc()).all()

        res = []
        for p in proformas:
            u = db.query(models.User).filter(models.User.id == p.id_usuario).first()
            s = db.query(models.Sede).filter(models.Sede.id_sede == p.id_sede).first()
            
            vendedor_nom = f"{u.first_name} {u.last_name}".strip() if u else "Desconocido"
            if not vendedor_nom and u:
                vendedor_nom = u.username

            res.append({
                "id_proforma": p.id_proforma,
                "correlativo": p.correlativo,
                "fecha_emision": p.fecha_emision.strftime("%d/%m/%Y %H:%M") if p.fecha_emision else "N/A",
                "validez_dias": p.validez_dias,
                "id_cliente": getattr(p, 'id_cliente', None),
                "cliente_nombre": p.cliente_nombre,
                "cliente_doc": p.cliente_doc,
                "total": p.total,
                "vendedor": vendedor_nom,
                "sede_nombre": s.nombre if s else "Sede Principal"
            })

        return jsonify(res), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Obtiene el detalle de una proforma para visualizacion o impresion
@proformas_bp.route("/api/proformas/<int:id_proforma>", methods=["GET"])
def get_detalle_proforma(id_proforma):
    db = get_db()
    try:
        prof = db.query(models.Proforma).filter(models.Proforma.id_proforma == id_proforma).first()
        if not prof:
            return jsonify({"error": "Proforma no encontrada"}), 404

        u = db.query(models.User).filter(models.User.id == prof.id_usuario).first()
        s = db.query(models.Sede).filter(models.Sede.id_sede == prof.id_sede).first()

        vendedor_nom = f"{u.first_name} {u.last_name}".strip() if u else "Desconocido"
        if not vendedor_nom and u:
            vendedor_nom = u.username

        sede_nom = s.nombre if s else "Sede Principal"
        sede_dir = s.direccion if (s and s.direccion) else "Av. Central 123, Los Olivos"
        sede_tel = s.telefono if (s and s.telefono) else "01-1234567"

        detalles_res = []
        for d in prof.detalles:
            prod_nom = d.producto.nombre if d.producto else "Producto"
            prod_cod = d.producto.codigo_producto if d.producto else "PROD"
            detalles_res.append({
                "id_producto": d.id_producto,
                "codigo": prod_cod,
                "nombre": prod_nom,
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
                "subtotal": d.subtotal
            })

        data = {
            "id_proforma": prof.id_proforma,
            "correlativo": prof.correlativo,
            "fecha_emision": prof.fecha_emision.strftime("%d/%m/%Y %H:%M") if prof.fecha_emision else "N/A",
            "validez_dias": prof.validez_dias,
            "id_cliente": getattr(prof, 'id_cliente', None),
            "cliente_nombre": prof.cliente_nombre,
            "cliente_doc": prof.cliente_doc,
            "total": prof.total,
            "vendedor": vendedor_nom,
            "sede_nombre": sede_nom,
            "sede_direccion": sede_dir,
            "sede_telefono": sede_tel,
            "detalles": detalles_res
        }
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

