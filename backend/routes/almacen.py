from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from database import get_db
import models

almacen_bp = Blueprint("almacen", __name__)

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
    """Generador atómico de códigos correlativos de producto O(1)"""
    ultimo_prod = db.query(models.Producto.codigo_producto)\
        .filter(models.Producto.codigo_producto.like("PROD-%"))\
        .order_by(models.Producto.id_producto.desc())\
        .first()

    if ultimo_prod and ultimo_prod[0]:
        try:
            last_num = int(ultimo_prod[0].replace("PROD-", ""))
            siguiente_num = last_num + 1
        except Exception:
            max_id = db.query(func.max(models.Producto.id_producto)).scalar() or 0
            siguiente_num = max_id + 1
    else:
        max_id = db.query(func.max(models.Producto.id_producto)).scalar() or 0
        siguiente_num = max_id + 1

    codigo_siguiente = f"PROD-{siguiente_num:05d}"
    while db.query(models.Producto.id_producto).filter(models.Producto.codigo_producto == codigo_siguiente).first():
        siguiente_num += 1
        codigo_siguiente = f"PROD-{siguiente_num:05d}"

    return codigo_siguiente, siguiente_num

@almacen_bp.route("/api/productos", methods=["GET"])
def get_productos():
    sede_id = request.args.get("sede_id", type=int) or request.args.get("id_sede", type=int)
    search = (request.args.get("search") or "").strip()
    id_cat = request.args.get("id_categoria", type=int)
    id_subcat = request.args.get("id_subcategoria", type=int)
    page = request.args.get("page", type=int)
    limit = request.args.get("limit", default=20, type=int)

    db = get_db()
    
    query = db.query(models.Producto).filter(models.Producto.estado_registro == 1)
    if id_cat:
        query = query.filter(models.Producto.id_categoria == id_cat)
    if id_subcat:
        query = query.filter(models.Producto.id_subcategoria == id_subcat)
    if search:
        query = query.filter(
            (models.Producto.nombre.ilike(f"%{search}%")) | 
            (models.Producto.codigo_producto.ilike(f"%{search}%"))
        )

    # Si hay paginación solicitada
    if page and page > 0:
        total_items = query.count()
        total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
        productos = query.order_by(models.Producto.id_producto.asc()).offset((page - 1) * limit).limit(limit).all()
    else:
        total_items = None
        total_pages = None
        productos = query.order_by(models.Producto.id_producto.asc()).all()

    todas_categorias = db.query(models.Categoria).all()
    cat_dict = {c.id_categoria: c for c in todas_categorias}

    todas_subcategorias = db.query(models.Subcategoria).all()
    subcat_dict = {s.id_subcategoria: s for s in todas_subcategorias}
    
    # Optimización: Obtener inventario solo de los productos seleccionados (evita scans globales)
    prod_ids = [p.id_producto for p in productos]
    inv_dict = {}
    if prod_ids:
        inv_query = db.query(models.InventarioSede).filter(models.InventarioSede.id_producto.in_(prod_ids))
        if sede_id:
            inv_query = inv_query.filter(models.InventarioSede.id_sede == sede_id)
        inventarios = inv_query.all()
        for inv in inventarios:
            if inv.id_producto not in inv_dict:
                inv_dict[inv.id_producto] = inv
            
    result = []
    for p in productos:
        cat_nombre = "Sin categoría"
        subcat_nombre = "General"
        
        if p.id_categoria:
            cat = cat_dict.get(p.id_categoria)
            if cat:
                cat_nombre = cat.nombre

        if p.id_subcategoria:
            subcat = subcat_dict.get(p.id_subcategoria)
            if subcat:
                subcat_nombre = subcat.nombre
                if not p.id_categoria and subcat.id_categoria:
                    cat_padre = cat_dict.get(subcat.id_categoria)
                    if cat_padre:
                        cat_nombre = cat_padre.nombre
        
        inv = inv_dict.get(p.id_producto)
        precio_compra = inv.precio_compra if inv else 0.0
        precio_venta = inv.precio_venta if inv else 0.0
        stock_actual = inv.stock_actual if inv else 0
        stock_minimo = inv.stock_minimo if inv else 0
            
        result.append({
            "id_producto": p.id_producto,
            "codigo_producto": p.codigo_producto,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "precio_compra": precio_compra,
            "precio_venta": precio_venta,
            "stock_actual": stock_actual,
            "stock_minimo": stock_minimo,
            "categoria": cat_nombre,
            "subcategoria": subcat_nombre,
            "id_categoria": p.id_categoria,
            "id_subcategoria": p.id_subcategoria
        })

    if page and page > 0:
        return jsonify({
            "items": result,
            "total": total_items,
            "page": page,
            "pages": total_pages,
            "limit": limit
        }), 200

    return jsonify(result), 200

@almacen_bp.route("/api/productos/siguiente-codigo", methods=["GET"])
def get_siguiente_codigo_producto():
    db = get_db()
    codigo_siguiente, siguiente_num = _calcular_siguiente_codigo_producto(db)
    return jsonify({"codigo": codigo_siguiente, "numero": siguiente_num})

@almacen_bp.route("/api/productos", methods=["POST"])
def create_producto():
    data = request.json or {}
    db = get_db()
    
    id_usuario = data.get("id_usuario")
    usuario = db.query(models.User).filter(models.User.id == id_usuario).first()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 400
        
    id_sede = usuario.id_sede or 1
    
    codigo_input = str(data.get("codigo_producto", "")).strip()
    if not codigo_input:
        codigo_input, _ = _calcular_siguiente_codigo_producto(db)
        
    # Validación de seguridad: Mínimo 3 caracteres
    if len(codigo_input) < 3:
        return jsonify({"error": "El código de producto debe tener al menos 3 caracteres (Ej: PROD-00001)."}), 400

    existe = db.query(models.Producto).filter(models.Producto.codigo_producto == codigo_input).first()
    
    try:
        nuevo_producto = existe
        if not existe:
            nuevo_producto = models.Producto(
                codigo_producto=codigo_input,
                nombre=str(data.get("nombre")).strip(),
                descripcion=data.get("descripcion", ""),
                id_categoria=data.get("id_categoria"),
                id_subcategoria=data.get("id_subcategoria")
            )
            db.add(nuevo_producto)
            db.flush()

        # Crear inventario en la sede actual
        inventario = db.query(models.InventarioSede).filter(
            models.InventarioSede.id_producto == nuevo_producto.id_producto,
            models.InventarioSede.id_sede == id_sede
        ).first()
        
        if inventario:
            return jsonify({"error": "El producto ya existe en el inventario de tu sede"}), 400
            
        nuevo_inventario = models.InventarioSede(
            id_producto=nuevo_producto.id_producto,
            id_sede=id_sede,
            precio_compra=float(data.get("precio_compra", 0)),
            precio_venta=float(data.get("precio_venta", 0)),
            stock_actual=int(data.get("stock_actual", 0)),
            stock_minimo=int(data.get("stock_minimo", 0))
        )
        db.add(nuevo_inventario)
        
        # Registrar movimiento de entrada inicial
        if nuevo_inventario.stock_actual > 0:
            db.flush()
            movimiento = models.MovimientoAlmacen(
                id_producto=nuevo_producto.id_producto,
                id_sede=id_sede,
                tipo='ENTRADA',
                cantidad=nuevo_inventario.stock_actual,
                id_usuario=id_usuario,
                observacion="Stock inicial al crear/agregar producto a sede"
            )
            db.add(movimiento)
            
        db.commit()
        db.refresh(nuevo_producto)
        id_prod = nuevo_producto.id_producto
        return jsonify({"message": "Producto agregado a tu sede exitosamente", "id_producto": id_prod}), 201
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

        # Reassign products without subcategory to first subcategory of their parent category
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

