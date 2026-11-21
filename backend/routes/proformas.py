import json
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import get_db

proformas_bp = Blueprint("proformas", __name__)

PERU_TZ = timezone(timedelta(hours=-5))

def format_peru_datetime(dt):
    if not dt:
        return ""
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(PERU_TZ).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M")


# Guarda una nueva cotización o proforma mediante Stored Procedure sp_procesar_proforma
@proformas_bp.route("/api/proformas", methods=["POST"])
def registrar_proforma():
    data = request.json or {}
    id_usuario = data.get("id_usuario")
    id_sede = data.get("id_sede")
    cliente_nombre = str(data.get("cliente_nombre", "Cliente General")).strip() or "Cliente General"
    cliente_doc = str(data.get("cliente_doc", "")).strip()
    validez_dias = int(data.get("validez_dias", 7))
    detalles = data.get("detalles", [])

    if not id_usuario or not id_sede or not detalles:
        return jsonify({"error": "Faltan datos obligatorios (id_usuario, id_sede, detalles)"}), 400

    db = get_db()
    try:
        total_proforma = 0.0
        detalles_json = []
        for item in detalles:
            pu = float(item["precio_unitario"])
            cant = int(item["cantidad"])
            sub = cant * pu
            total_proforma += sub
            detalles_json.append({
                "id_producto": int(item["id_producto"]),
                "cantidad": cant,
                "precio_unitario": pu,
                "subtotal": round(sub, 2)
            })

        total_proforma = round(total_proforma, 2)

        res = db.execute(
            text("""
                CALL sp_procesar_proforma(
                    :id_usuario, :id_sede, :cliente_nombre, :cliente_doc,
                    :validez_dias, :total, CAST(:detalles AS jsonb),
                    NULL, NULL, NULL
                )
            """),
            {
                "id_usuario": int(id_usuario),
                "id_sede": int(id_sede),
                "cliente_nombre": cliente_nombre,
                "cliente_doc": cliente_doc,
                "validez_dias": validez_dias,
                "total": total_proforma,
                "detalles": json.dumps(detalles_json)
            }
        ).fetchone()
        db.commit()

        id_prof = res[0] if res else None
        correlativo = res[1] if res and len(res) > 1 else ""
        msg = res[2] if res and len(res) > 2 else "Proforma registrada con éxito"

        return jsonify({
            "message": msg,
            "id_proforma": id_prof,
            "correlativo": correlativo
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# Lista el historial de proformas mediante Función Almacenada fn_listar_proformas
@proformas_bp.route("/api/proformas", methods=["GET"])
def get_proformas():
    db = get_db()
    try:
        sede_id = request.args.get("sede_id", type=int)
        search = request.args.get("search", "").strip()

        rows = db.execute(
            text("""
                SELECT id_proforma, correlativo, fecha_emision, validez_dias,
                       cliente_nombre, cliente_doc, total, id_usuario, usuario_nombre,
                       id_sede, sede_nombre, id_cliente
                FROM fn_listar_proformas(:p_id_sede, :p_search)
            """),
            {
                "p_id_sede": sede_id if sede_id else None,
                "p_search": search if search else None
            }
        ).fetchall()

        resultado = []
        for p in rows:
            resultado.append({
                "id_proforma": p.id_proforma,
                "correlativo": p.correlativo,
                "cliente_nombre": p.cliente_nombre or "Cliente General",
                "cliente_doc": p.cliente_doc or "",
                "id_cliente": p.id_cliente,
                "validez_dias": p.validez_dias,
                "total": round(float(p.total or 0.0), 2),
                "fecha_emision": format_peru_datetime(p.fecha_emision),
                "vendedor": p.usuario_nombre or "Sistema",
                "sede": p.sede_nombre or "Sede Central"
            })

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Obtener detalle de una proforma mediante Funciones Almacenadas fn_obtener_proforma_cabecera y fn_obtener_proforma_detalle
@proformas_bp.route("/api/proformas/<int:id_proforma>", methods=["GET"])
def get_detalle_proforma(id_proforma):
    db = get_db()
    try:
        cab = db.execute(
            text("""
                SELECT id_proforma, correlativo, fecha_emision, validez_dias,
                       cliente_nombre, cliente_doc, total, id_usuario, usuario_nombre,
                       id_sede, sede_nombre, sede_direccion, id_cliente
                FROM fn_obtener_proforma_cabecera(:id_proforma)
            """),
            {"id_proforma": id_proforma}
        ).fetchone()

        if not cab:
            return jsonify({"error": "Proforma no encontrada"}), 404

        det_rows = db.execute(
            text("""
                SELECT id_detalle_proforma, id_producto, codigo_producto, nombre_producto,
                       cantidad, precio_unitario, subtotal
                FROM fn_obtener_proforma_detalle(:id_proforma)
            """),
            {"id_proforma": id_proforma}
        ).fetchall()

        items = [{
            "id_producto": d.id_producto,
            "codigo": d.codigo_producto or f"PROD-{d.id_producto}",
            "nombre": d.nombre_producto or "Producto",
            "cantidad": d.cantidad,
            "precio_unitario": round(float(d.precio_unitario), 2),
            "subtotal": round(float(d.subtotal), 2)
        } for d in det_rows]

        data = {
            "id_proforma": cab.id_proforma,
            "correlativo": cab.correlativo,
            "fecha_emision": format_peru_datetime(cab.fecha_emision),
            "validez_dias": cab.validez_dias,
            "cliente": cab.cliente_nombre or "Cliente General",
            "cliente_doc": cab.cliente_doc or "",
            "id_cliente": cab.id_cliente,
            "total": round(float(cab.total or 0.0), 2),
            "vendedor": cab.usuario_nombre or "Sistema",
            "sede_nombre": cab.sede_nombre or "Sede Central",
            "sede_direccion": cab.sede_direccion or "Av. Central 123",
            "detalles": items
        }

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
