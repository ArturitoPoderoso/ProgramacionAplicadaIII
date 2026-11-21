from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import get_db

almacen_bp = Blueprint("almacen", __name__)

# Gestión de categorías de productos mediante Stored Procedures y SQL directo
@almacen_bp.route("/api/categorias", methods=["GET", "POST"])
def handle_categorias():
    db = get_db()
    if request.method == "POST":
        data = request.json or {}
        nombre = str(data.get("nombre", "")).strip()
        if not nombre:
            return jsonify({"error": "El nombre de la categoría es obligatorio"}), 400

        id_padre = data.get("id_padre")
        id_padre_final = int(id_padre) if id_padre and str(id_padre).isdigit() else None
        descripcion = str(data.get("descripcion", "")).strip()

        try:
            res = db.execute(
                text("CALL sp_guardar_categoria(NULL, :nombre, :descripcion, :id_padre, NULL, NULL)"),
                {"nombre": nombre, "descripcion": descripcion, "id_padre": id_padre_final}
            ).fetchone()
            db.commit()

            cat_id = res[0] if res else None
            msg = res[1] if res and len(res) > 1 else "Categoría creada exitosamente"
            return jsonify({"message": msg, "id_categoria": cat_id}), 201

        except Exception as e:
            db.rollback()
            err_msg = str(e)
            if "ya existe" in err_msg:
                clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
                return jsonify({"error": clean_err}), 400
            return jsonify({"error": f"Error al crear categoría: {err_msg}"}), 500

    # GET
    try:
        rows = db.execute(
            text("SELECT id_categoria, nombre, descripcion, id_padre FROM fn_listar_categorias()")
        ).fetchall()

        return jsonify([{
            "id_categoria": r.id_categoria,
            "nombre": r.nombre,
            "descripcion": r.descripcion or "",
            "id_padre": r.id_padre
        } for r in rows]), 200

    except Exception as e:
        return jsonify({"error": f"Error al listar categorías: {str(e)}"}), 500


@almacen_bp.route("/api/categorias/<int:cat_id>", methods=["PUT"])
def update_categoria(cat_id):
    data = request.json or {}
    nombre = str(data.get("nombre", "")).strip()
    if not nombre:
        return jsonify({"error": "El nombre de la categoría no puede estar vacío"}), 400

    id_padre = data.get("id_padre")
    id_padre_final = int(id_padre) if id_padre and str(id_padre).isdigit() else None
    descripcion = str(data.get("descripcion", "")).strip()

    db = get_db()
    try:
        res = db.execute(
            text("CALL sp_guardar_categoria(:id_cat, :nombre, :descripcion, :id_padre, NULL, NULL)"),
            {"id_cat": cat_id, "nombre": nombre, "descripcion": descripcion, "id_padre": id_padre_final}
        ).fetchone()
        db.commit()

        msg = res[1] if res and len(res) > 1 else "Categoría actualizada exitosamente"
        return jsonify({"message": msg}), 200

    except Exception as e:
        db.rollback()
        err_msg = str(e)
        if "ya existe" in err_msg:
            clean_err = err_msg.split("CONTEXT:")[0].replace("pgcode: P0001", "").strip()
            return jsonify({"error": clean_err}), 400
        return jsonify({"error": f"Error al actualizar categoría: {err_msg}"}), 500


@almacen_bp.route("/api/subcategorias", methods=["GET", "POST"])
def subcategorias():
    db = get_db()
    if request.method == "POST":
        data = request.json or {}
        nombre = str(data.get("nombre", "")).strip()
        id_categoria = data.get("id_categoria")
        
        if not nombre:
            return jsonify({"error": "El nombre de la subcategoría es obligatorio"}), 400
        if not id_categoria:
            return jsonify({"error": "La categoría padre es obligatoria para la subcategoría"}), 400

        descripcion = str(data.get("descripcion", "")).strip()

        try:
            res = db.execute(
                text("CALL sp_guardar_subcategoria(NULL, :nombre, :descripcion, :id_cat, NULL, NULL)"),
                {"nombre": nombre, "descripcion": descripcion, "id_cat": int(id_categoria)}
            ).fetchone()
            db.commit()

            sub_id = res[0] if res else None
            msg = res[1] if res and len(res) > 1 else "Subcategoría creada exitosamente"
            return jsonify({"message": msg, "id_subcategoria": sub_id}), 201

        except Exception as e:
            db.rollback()
            return jsonify({"error": f"Error al crear subcategoría: {str(e)}"}), 500

    # GET
    try:
        id_cat = request.args.get("id_categoria", type=int)
        rows = db.execute(
            text("SELECT id_subcategoria, nombre, descripcion, id_categoria, categoria_nombre FROM fn_listar_subcategorias(:id_cat)"),
            {"id_cat": id_cat if id_cat else None}
        ).fetchall()

        return jsonify([{
            "id_subcategoria": r.id_subcategoria,
            "nombre": r.nombre,
            "descripcion": r.descripcion or "",
            "id_categoria": r.id_categoria,
            "categoria_nombre": r.categoria_nombre
        } for r in rows]), 200

    except Exception as e:
        return jsonify({"error": f"Error al listar subcategorías: {str(e)}"}), 500


@almacen_bp.route("/api/subcategorias/<int:sub_id>", methods=["PUT", "DELETE"])
def subcategoria_detail(sub_id):
    db = get_db()
    if request.method == "DELETE":
        try:
            res = db.execute(
                text("CALL sp_eliminar_subcategoria(:sub_id, NULL)"),
                {"sub_id": sub_id}
            ).fetchone()
            db.commit()
            msg = res[0] if res else "Subcategoría eliminada exitosamente"
            return jsonify({"message": msg}), 200
        except Exception as e:
            db.rollback()
            return jsonify({"error": f"Error al eliminar subcategoría: {str(e)}"}), 500

    # PUT
    data = request.json or {}
    nombre = str(data.get("nombre", "")).strip() if "nombre" in data else None
    descripcion = str(data.get("descripcion", "")).strip() if "descripcion" in data else None
    id_cat = int(data.get("id_categoria")) if "id_categoria" in data and str(data.get("id_categoria")).isdigit() else None

    try:
        res = db.execute(
            text("CALL sp_guardar_subcategoria(:sub_id, :nombre, :descripcion, :id_cat, NULL, NULL)"),
            {"sub_id": sub_id, "nombre": nombre, "descripcion": descripcion, "id_cat": id_cat}
        ).fetchone()
        db.commit()

        msg = res[1] if res and len(res) > 1 else "Subcategoría actualizada exitosamente"
        return jsonify({"message": msg}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al actualizar subcategoría: {str(e)}"}), 500


def _calcular_siguiente_codigo_producto(db):
    row = db.execute(text("SELECT fn_siguiente_codigo_producto()")).fetchone()
    codigo_siguiente = row[0] if row and row[0] else "PROD-00001"
    try:
        siguiente_num = int(codigo_siguiente.replace("PROD-", ""))
    except Exception:
        siguiente_num = 1
    return codigo_siguiente, siguiente_num


# Listado de productos por sede usando la función almacenada fn_listar_productos_sede
@almacen_bp.route("/api/productos", methods=["GET"])
def get_productos():
    sede_id = request.args.get("sede_id", type=int) or request.args.get("id_sede", type=int) or 1
    search = (request.args.get("search") or "").strip().lower()
    id_cat = request.args.get("id_categoria", type=int)
    id_subcat = request.args.get("id_subcategoria", type=int)
    page = request.args.get("page", type=int)
    limit = request.args.get("limit", default=20, type=int)

    db = get_db()
    try:
        rows = db.execute(
            text("""
                SELECT id_producto, codigo_producto, nombre, descripcion,
                       precio_venta, precio_compra, stock_actual, stock_minimo,
                       categoria, id_categoria, id_subcategoria, sede_id
                FROM fn_listar_productos_sede(:sede_id)
            """),
            {"sede_id": sede_id}
        ).fetchall()

        resultado = []
        for r in rows:
            if id_cat and r.id_categoria != id_cat:
                continue
            if id_subcat and r.id_subcategoria != id_subcat:
                continue
            if search:
                if (search not in (r.nombre or "").lower()) and (search not in (r.codigo_producto or "").lower()):
                    continue

            resultado.append({
                "id_producto": r.id_producto,
                "codigo_producto": r.codigo_producto,
                "nombre": r.nombre,
                "descripcion": r.descripcion or "",
                "precio_compra": round(float(r.precio_compra or 0.0), 2),
                "precio_venta": round(float(r.precio_venta or 0.0), 2),
                "stock_actual": int(r.stock_actual or 0),
                "stock_minimo": int(r.stock_minimo or 0),
                "categoria": r.categoria or "Sin categoría",
                "subcategoria": "General",
                "id_categoria": r.id_categoria,
                "id_subcategoria": r.id_subcategoria
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
        return jsonify({"error": f"Error al listar productos: {str(e)}"}), 500


@almacen_bp.route("/api/productos/siguiente-codigo", methods=["GET"])
def get_siguiente_codigo_producto():
    db = get_db()
    codigo_siguiente, siguiente_num = _calcular_siguiente_codigo_producto(db)
    return jsonify({"codigo": codigo_siguiente, "numero": siguiente_num})


# Creación o actualización de producto mediante Stored Procedure sp_guardar_producto
@almacen_bp.route("/api/productos", methods=["POST"])
def create_producto():
    data = request.json or {}
    db = get_db()
    try:
        id_usuario = data.get("id_usuario") or 1
        id_sede = data.get("id_sede") or 1

        codigo_input = str(data.get("codigo_producto", "")).strip()
        if not codigo_input:
            codigo_input, _ = _calcular_siguiente_codigo_producto(db)

        if len(codigo_input) < 3:
            return jsonify({"error": "El código de producto debe tener al menos 3 caracteres (Ej: PROD-00001)."}), 400

        nombre = str(data.get("nombre", "")).strip()
        if not nombre:
            return jsonify({"error": "El nombre del producto es obligatorio."}), 400

        descripcion = str(data.get("descripcion", "")).strip()
        id_categoria = data.get("id_categoria")
        id_subcategoria = data.get("id_subcategoria")
        precio_venta = float(data.get("precio_venta", 0.0))
        precio_compra = float(data.get("precio_compra", 0.0))
        stock_actual = int(data.get("stock_actual", 0))
        stock_minimo = int(data.get("stock_minimo", 5))

        # Invocación de Stored Procedure sp_guardar_producto
        res = db.execute(
            text("""
                CALL sp_guardar_producto(
                    NULL, :codigo, :nombre, :descripcion, :id_cat, :id_subcat,
                    :precio_venta, :precio_compra, :stock_actual, :stock_minimo,
                    :id_sede, :id_usuario, NULL, NULL
                )
            """),
            {
                "codigo": codigo_input,
                "nombre": nombre,
                "descripcion": descripcion,
                "id_cat": int(id_categoria) if id_categoria else None,
                "id_subcat": int(id_subcategoria) if id_subcategoria else None,
                "precio_venta": precio_venta,
                "precio_compra": precio_compra,
                "stock_actual": stock_actual,
                "stock_minimo": stock_minimo,
                "id_sede": int(id_sede),
                "id_usuario": int(id_usuario)
            }
        ).fetchone()
        db.commit()

        id_prod = res[0] if res else None
        msg = res[1] if res and len(res) > 1 else "Producto agregado a tu sede exitosamente"

        return jsonify({"message": msg, "id_producto": id_prod}), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
