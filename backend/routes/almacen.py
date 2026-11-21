from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from sqlalchemy import func, text
from database import get_db
import models

almacen_bp = Blueprint("almacen", __name__)

# Gestión de categorías de productos
@almacen_bp.route("/api/categorias", methods=["GET", "POST"])
def handle_categorias():
    if request.method == "POST":
        data = request.json or {}
        nombre = str(data.get("nombre", "")).strip()
        if not nombre:
            return jsonify({"error": "El nombre de la categoría es obligatorio"}), 400

        db = get_db()
        existe = db.query(models.Categoria).filter(models.Categoria.nombre.ilike(nombre)).first()
        if existe:
            return jsonify({"error": "La categoría ya existe"}), 400

        id_padre = data.get("id_padre")
        if id_padre and str(id_padre).isdigit():
            id_padre = int(id_padre)
        else:
            id_padre = None

        nueva_cat = models.Categoria(
            nombre=nombre,
            descripcion=data.get("descripcion", ""),
            id_padre=id_padre
        )
        db.add(nueva_cat)
        db.commit()
        cat_id = nueva_cat.id_categoria
        return jsonify({"message": "Categoría creada exitosamente", "id_categoria": cat_id}), 201

    # GET
    db = get_db()
    categorias = db.query(models.Categoria).filter(models.Categoria.estado_registro == 1).all()
    return jsonify([{
        "id_categoria": c.id_categoria,
        "nombre": c.nombre,
        "descripcion": c.descripcion,
        "id_padre": getattr(c, 'id_padre', None)
    } for c in categorias])

@almacen_bp.route("/api/categorias/<int:cat_id>", methods=["PUT"])
def update_categoria(cat_id):
    data = request.json or {}
    nombre = str(data.get("nombre", "")).strip()
    if not nombre:
        return jsonify({"error": "El nombre de la categoría no puede estar vacío"}), 400

    db = get_db()
    cat = db.query(models.Categoria).filter(models.Categoria.id_categoria == cat_id).first()
    if not cat:
        return jsonify({"error": "Categoría no encontrada"}), 404

    cat.nombre = nombre
    if "descripcion" in data:
        cat.descripcion = data["descripcion"]
    if "id_padre" in data:
        cat.id_padre = int(data["id_padre"]) if data["id_padre"] and str(data["id_padre"]).isdigit() else None

    db.commit()
    return jsonify({"message": "Categoría actualizada exitosamente"})

@almacen_bp.route("/api/subcategorias", methods=["GET", "POST"])
def subcategorias():
    if request.method == "POST":
        data = request.json or {}
        nombre = str(data.get("nombre", "")).strip()
        id_categoria = data.get("id_categoria")
        
        if not nombre:
            return jsonify({"error": "El nombre de la subcategoría es obligatorio"}), 400
        if not id_categoria:
            return jsonify({"error": "La categoría padre es obligatoria para la subcategoría"}), 400

        db = get_db()
        nueva_sub = models.Subcategoria(
            nombre=nombre,
            descripcion=data.get("descripcion", ""),
            id_categoria=int(id_categoria)
        )
        db.add(nueva_sub)
        db.commit()
        sub_id = nueva_sub.id_subcategoria
        return jsonify({"message": "Subcategoría creada exitosamente", "id_subcategoria": sub_id}), 201

    # GET
    id_cat = request.args.get("id_categoria", type=int)
    db = get_db()
    query = db.query(models.Subcategoria).options(joinedload(models.Subcategoria.categoria)).filter(models.Subcategoria.estado_registro == 1)
    if id_cat:
        query = query.filter(models.Subcategoria.id_categoria == id_cat)
        
    subcats = query.all()
    res = [{
        "id_subcategoria": s.id_subcategoria,
        "nombre": s.nombre,
        "descripcion": s.descripcion,
        "id_categoria": s.id_categoria,
        "categoria_nombre": s.categoria.nombre if s.categoria else "General"
    } for s in subcats]
    return jsonify(res)

@almacen_bp.route("/api/subcategorias/<int:sub_id>", methods=["PUT", "DELETE"])
def subcategoria_detail(sub_id):
    db = get_db()
    sub = db.query(models.Subcategoria).filter(models.Subcategoria.id_subcategoria == sub_id).first()
    if not sub:
        return jsonify({"error": "Subcategoría no encontrada"}), 404

    if request.method == "DELETE":
        sub.estado_registro = 0
        db.commit()
        return jsonify({"message": "Subcategoría eliminada exitosamente"})

    # PUT
    data = request.json or {}
    if "nombre" in data and data["nombre"]:
        sub.nombre = str(data["nombre"]).strip()
    if "descripcion" in data:
        sub.descripcion = str(data["descripcion"]).strip()
    if "id_categoria" in data and data["id_categoria"]:
        sub.id_categoria = int(data["id_categoria"])

    db.commit()
    return jsonify({"message": "Subcategoría actualizada exitosamente"})

def _calcular_siguiente_codigo_producto(db):
    # Genera el siguiente correlativo para el código de producto (ej: PROD-00045)
    ultimo_prod = db.execute(
        text("SELECT codigo_producto FROM productos WHERE codigo_producto LIKE 'PROD-%' ORDER BY id_producto DESC LIMIT 1")
    ).fetchone()

    if ultimo_prod and ultimo_prod[0]:
        try:
            last_num = int(ultimo_prod[0].replace("PROD-", ""))
            siguiente_num = last_num + 1
        except Exception:
            max_id = db.execute(text("SELECT MAX(id_producto) FROM productos")).scalar() or 0
            siguiente_num = max_id + 1
    else:
        max_id = db.execute(text("SELECT MAX(id_producto) FROM productos")).scalar() or 0
        siguiente_num = max_id + 1

    codigo_siguiente = f"PROD-{siguiente_num:05d}"
    while db.execute(text("SELECT id_producto FROM productos WHERE codigo_producto = :cod"), {"cod": codigo_siguiente}).fetchone():
        siguiente_num += 1
        codigo_siguiente = f"PROD-{siguiente_num:05d}"

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
        # Llamada a la función PL/pgSQL fn_listar_productos_sede
        rows = db.execute(
            text("""
                SELECT id_producto, codigo_producto, nombre, descripcion,
                       precio_venta, precio_compra, stock_actual, stock_minimo,
                       categoria, id_categoria, id_subcategoria, sede_id
                FROM fn_listar_productos_sede(:sede_id)
            """),
            {"sede_id": sede_id}
        ).fetchall()

        # Filtrado en memoria si hay parámetros adicionales
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

@almacen_bp.route("/api/categorias/seed", methods=["POST"])
def seed_subcategorias():
    db = get_db()
    try:
        subcats_map = {
            1: ["Martillos y Combas", "Alicates y Tenazas", "Destornilladores y Llaves"],
            2: ["Taladros y Rotomartillos", "Amoladoras y Esmeriles", "Sierras y Cortadoras"],
            3: ["Cemento y Agregados", "Ladrillos y Bloques", "Fierros y Varillas"],
            4: ["Pinturas Látex", "Esmaltes Sintéticos", "Brochas y Rodillos", "Thinner y Disolventes"],
            5: ["Tubos y Conexiones PVC", "Grifería y Llaves", "Accesorios para Gas"],
            6: ["Cables y Conductores", "Tomacorrientes e Llaves Térmicas", "Focos y Luminarias LED"],
            7: ["Tornillos y Pijas", "Pernos y Tuercas", "Tarugos y Anclajes"],
            8: ["Cascos y Guantes", "Calzado y Lentes de Seguridad"],
            9: ["Siliconas y Masillas", "Pegamentos y Colas"],
            10: ["Mangueras y Aspersores", "Herramientas de Jardín"]
        }

        created = 0
        for parent_id, sub_names in subcats_map.items():
            parent = db.query(models.Categoria).filter(models.Categoria.id_categoria == parent_id).first()
            if not parent:
                continue
            for name in sub_names:
                exist = db.query(models.Categoria).filter(models.Categoria.nombre == name, models.Categoria.id_padre == parent_id).first()
                if not exist:
                    db.add(models.Categoria(nombre=name, descripcion=f"Subcategoría de {parent.nombre}", id_padre=parent_id, estado_registro=1))
                    created += 1
        db.commit()

        prods = db.query(models.Producto).all()
        reassigned = 0
        for prod in prods:
            if prod.id_categoria and prod.id_categoria in subcats_map:
                first_sub = db.query(models.Categoria).filter(models.Categoria.id_padre == prod.id_categoria).first()
                if first_sub:
                    prod.id_categoria = first_sub.id_categoria
                    reassigned += 1
        db.commit()
        return jsonify({"message": f"Subcategorías sembradas con éxito: {created} creadas, {reassigned} productos reasignados."}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
