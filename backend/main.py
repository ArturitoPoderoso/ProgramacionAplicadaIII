from flask import Flask, request, jsonify, g
from flask_cors import CORS
from database import engine, SessionLocal
import models
from sqlalchemy.orm import joinedload
from sqlalchemy import text, func

try:
    models.Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE ventas ADD COLUMN IF NOT EXISTS descuento_total DOUBLE PRECISION DEFAULT 0.0;"))
        conn.execute(text("ALTER TABLE detalle_ventas ADD COLUMN IF NOT EXISTS descuento_unitario DOUBLE PRECISION DEFAULT 0.0;"))
        conn.commit()
except Exception as e:
    print(f"Error conectando o migrando BD: {e}")

app = Flask(__name__)
CORS(app)

def get_db():
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db

@app.teardown_appcontext
def teardown_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


@app.route("/")
def read_root():
    return jsonify({"message": "Bienvenido a la API del Sistema Jesmi"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
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
            db.close()
            return jsonify({"error": "Usuario no encontrado"}), 404
            
        if user.password != password:
            db.close()
            return jsonify({"error": "Contraseña incorrecta"}), 401
            
        if not user.is_active:
            db.close()
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
        db.close()
        return jsonify(res_data)
    except Exception as e:
        print("Login error:", str(e))
        return jsonify({"error": "Error de conexión a la base de datos."}), 500

@app.route("/api/users", methods=["GET"])
def get_users():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    db = get_db()
    users = db.query(models.User).options(joinedload(models.User.sede)).all()
    db.close()
    return jsonify([{
        "id": u.id,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "username": u.username,
        "email": u.email,
        "phone": u.phone,
        "dni": u.dni,
        "role": u.role,
        "roles": u.roles,
        "gender": u.gender,
        "id_sede": u.id_sede,
        "location": u.sede.nombre if u.sede else "Sin sede",
        "last_access": u.last_access,
        "is_active": u.is_active
    } for u in users])

@app.route("/api/users", methods=["POST"])
def create_user():
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json
    
    if user_role == "Supervisor" and data.get("role") in ["Administrador", "Supervisor"]:
        return jsonify({"error": "No tienes permisos para asignar este rol"}), 403
        
    db = get_db()
    
    # Resolver la sede a partir del nombre o usar id_sede (por defecto 1)
    sede_nombre = str(data.get("location", "")).strip()
    sede = db.query(models.Sede).filter(models.Sede.nombre.ilike(f"%{sede_nombre}%")).first()
    id_sede = sede.id_sede if sede else 1
    
    db_user = models.User(
        first_name=str(data.get("first_name", "")).strip(),
        last_name=str(data.get("last_name", "")).strip(),
        username=str(data.get("username", "")).strip(),
        email=str(data.get("email", "")).strip(),
        phone=str(data.get("phone", "")).strip(),
        dni=str(data.get("dni", "")).strip(),
        gender=str(data.get("gender", "")).strip(),
        id_sede=id_sede
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Asignar rol
    roles_list = data.get("roles", [])
    if not roles_list:
        role_name = str(data.get("role", "Vendedor")).strip()
        roles_list = [role_name]
        
    for role_name in roles_list:
        perfil = db.query(models.Perfil).filter(models.Perfil.nombre == role_name).first()
        if perfil:
            user_perfil = models.UsuarioPerfil(id_usuario=db_user.id, id_perfil=perfil.id_perfil)
            db.add(user_perfil)
    db.commit()
    
    db_user = db.query(models.User).options(joinedload(models.User.sede)).filter(models.User.id == db_user.id).first()
    
    result = {
        "id": db_user.id,
        "first_name": db_user.first_name,
        "last_name": db_user.last_name,
        "username": db_user.username,
        "email": db_user.email,
        "phone": db_user.phone,
        "dni": db_user.dni,
        "role": db_user.role,
        "roles": db_user.roles,
        "gender": db_user.gender,
        "id_sede": db_user.id_sede,
        "location": db_user.sede.nombre if db_user.sede else "Sin sede",
        "last_access": db_user.last_access,
        "is_active": db_user.is_active
    }
    db.close()
    return jsonify(result)

@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json
    db = get_db()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        db.close()
        return jsonify({"detail": "User not found"}), 404
        
    if user_role == "Supervisor" and db_user.role in ["Administrador", "Supervisor"]:
        db.close()
        return jsonify({"error": "No puedes modificar a este usuario"}), 403
        
    if user_role == "Supervisor" and data.get("role") in ["Administrador", "Supervisor"]:
        db.close()
        return jsonify({"error": "No tienes permisos para asignar este rol"}), 403
        
    if "first_name" in data: db_user.first_name = str(data["first_name"]).strip()
    if "last_name" in data: db_user.last_name = str(data["last_name"]).strip()
    if "username" in data: db_user.username = str(data["username"]).strip()
    if "email" in data: db_user.email = str(data["email"]).strip()
    if "phone" in data: db_user.phone = str(data["phone"]).strip()
    if "dni" in data: db_user.dni = str(data["dni"]).strip()
    if "gender" in data: db_user.gender = str(data["gender"]).strip()
    if "location" in data: 
        sede_nombre = str(data["location"]).strip()
        sede = db.query(models.Sede).filter(models.Sede.nombre.ilike(f"%{sede_nombre}%")).first()
        if sede:
            db_user.id_sede = sede.id_sede
            
    if "last_access" in data: db_user.last_access = data["last_access"]
    if "is_active" in data: db_user.is_active = data["is_active"]
    
    if "roles" in data or "role" in data:
        roles_list = data.get("roles")
        if not roles_list and "role" in data:
            roles_list = [str(data["role"]).strip()]
            
        if roles_list is not None:
            # Delete old roles
            db.query(models.UsuarioPerfil).filter(models.UsuarioPerfil.id_usuario == user_id).delete()
            for role_name in roles_list:
                perfil = db.query(models.Perfil).filter(models.Perfil.nombre == role_name).first()
                if perfil:
                    new_perfil = models.UsuarioPerfil(id_usuario=user_id, id_perfil=perfil.id_perfil)
                    db.add(new_perfil)
    
    db.commit()
    db_user = db.query(models.User).options(joinedload(models.User.sede)).filter(models.User.id == db_user.id).first()
    
    result = {
        "id": db_user.id,
        "first_name": db_user.first_name,
        "last_name": db_user.last_name,
        "username": db_user.username,
        "email": db_user.email,
        "phone": db_user.phone,
        "dni": db_user.dni,
        "role": db_user.role,
        "roles": db_user.roles,
        "gender": db_user.gender,
        "id_sede": db_user.id_sede,
        "location": db_user.sede.nombre if db_user.sede else "Sin sede",
        "last_access": db_user.last_access,
        "is_active": db_user.is_active
    }
    db.close()
    return jsonify(result)

@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    db = get_db()
    user = db.query(models.User).options(joinedload(models.User.sede)).filter(models.User.id == user_id).first()
    db.close()
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    return jsonify({
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "dni": user.dni,
        "role": user.role,
        "roles": user.roles,
        "gender": user.gender,
        "id_sede": user.id_sede,
        "location": user.sede.nombre if user.sede else "Sin sede",
        "is_active": user.is_active,
        "last_access": user.last_access
    })

@app.route("/api/users/<int:user_id>/password", methods=["PUT"])
def update_password(user_id):
    data = request.json
    new_password = data.get("password")
    
    if not new_password:
        return jsonify({"error": "La nueva contraseña es requerida"}), 400
        
    db = get_db()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    db_user.password = new_password
    db.commit()
    db.close()
    return jsonify({"message": "Contraseña actualizada exitosamente"})

@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403
        
    db = get_db()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        db.close()
        return jsonify({"detail": "User not found"}), 404
        
    if user_role == "Supervisor" and db_user.role in ["Administrador", "Supervisor"]:
        db.close()
        return jsonify({"error": "No puedes eliminar a este usuario"}), 403
    
    db.delete(db_user)
    db.commit()
    db.close()
    return jsonify({"message": "Usuario eliminado correctamente"})


# ==========================================
# RUTAS DE ALMACÉN
# ==========================================

@app.route("/api/categorias", methods=["GET", "POST"])
def handle_categorias():
    if request.method == "POST":
        data = request.json or {}
        nombre = str(data.get("nombre", "")).strip()
        if not nombre:
            return jsonify({"error": "El nombre de la categoría es obligatorio"}), 400

        db = get_db()
        existe = db.query(models.Categoria).filter(models.Categoria.nombre.ilike(nombre)).first()
        if existe:
            db.close()
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
        db.close()
        return jsonify({"message": "Categoría creada exitosamente", "id_categoria": cat_id}), 201

    # GET
    db = get_db()
    categorias = db.query(models.Categoria).filter(models.Categoria.estado_registro == 1).all()
    db.close()
    return jsonify([{
        "id_categoria": c.id_categoria,
        "nombre": c.nombre,
        "descripcion": c.descripcion,
        "id_padre": getattr(c, 'id_padre', None)
    } for c in categorias])

@app.route("/api/categorias/<int:cat_id>", methods=["PUT"])
def update_categoria(cat_id):
    data = request.json or {}
    nombre = str(data.get("nombre", "")).strip()
    if not nombre:
        return jsonify({"error": "El nombre de la categoría no puede estar vacío"}), 400

    db = get_db()
    cat = db.query(models.Categoria).filter(models.Categoria.id_categoria == cat_id).first()
    if not cat:
        db.close()
        return jsonify({"error": "Categoría no encontrada"}), 404

    cat.nombre = nombre
    if "descripcion" in data:
        cat.descripcion = data["descripcion"]
    if "id_padre" in data:
        cat.id_padre = int(data["id_padre"]) if data["id_padre"] and str(data["id_padre"]).isdigit() else None

    db.commit()
    db.close()
    return jsonify({"message": "Categoría actualizada exitosamente"})

# --- ENDPOINTS DEDICADOS PARA SUBCATEGORÍAS ---

@app.route("/api/subcategorias", methods=["GET", "POST"])
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
        db.close()
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
    db.close()
    return jsonify(res)

@app.route("/api/subcategorias/<int:sub_id>", methods=["PUT", "DELETE"])
def subcategoria_detail(sub_id):
    db = get_db()
    sub = db.query(models.Subcategoria).filter(models.Subcategoria.id_subcategoria == sub_id).first()
    if not sub:
        db.close()
        return jsonify({"error": "Subcategoría no encontrada"}), 404

    if request.method == "DELETE":
        sub.estado_registro = 0
        db.commit()
        db.close()
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
    db.close()
    return jsonify({"message": "Subcategoría actualizada exitosamente"})

@app.route("/api/productos", methods=["GET"])
def get_productos():
    sede_id = request.args.get("sede_id", type=int) or request.args.get("id_sede", type=int)
    db = get_db()
    
    todas_categorias = db.query(models.Categoria).all()
    cat_dict = {c.id_categoria: c for c in todas_categorias}

    todas_subcategorias = db.query(models.Subcategoria).all()
    subcat_dict = {s.id_subcategoria: s for s in todas_subcategorias}
    
    inv_query = db.query(models.InventarioSede)
    if sede_id:
        inv_query = inv_query.filter(models.InventarioSede.id_sede == sede_id)
    inventarios = inv_query.all()
    
    inv_dict = {}
    for inv in inventarios:
        if inv.id_producto not in inv_dict:
            inv_dict[inv.id_producto] = inv
            
    productos = db.query(models.Producto).filter(models.Producto.estado_registro == 1).all()
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
    db.close()
    return jsonify(result)

@app.route("/api/productos/siguiente-codigo", methods=["GET"])
def get_siguiente_codigo_producto():
    db = get_db()
    max_id = db.query(func.max(models.Producto.id_producto)).scalar() or 0
    siguiente_num = max_id + 1
    codigo_siguiente = f"PROD-{siguiente_num:05d}"
    
    while db.query(models.Producto).filter(models.Producto.codigo_producto == codigo_siguiente).first():
        siguiente_num += 1
        codigo_siguiente = f"PROD-{siguiente_num:05d}"
        
    db.close()
    return jsonify({"codigo": codigo_siguiente, "numero": siguiente_num})

@app.route("/api/productos", methods=["POST"])
def create_producto():
    data = request.json
    db = get_db()
    
    id_usuario = data.get("id_usuario")
    usuario = db.query(models.User).filter(models.User.id == id_usuario).first()
    if not usuario:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 400
        
    id_sede = usuario.id_sede or 1
    
    codigo_input = str(data.get("codigo_producto", "")).strip()
    if not codigo_input:
        max_id = db.query(func.max(models.Producto.id_producto)).scalar() or 0
        codigo_input = f"PROD-{(max_id + 1):05d}"
        
    # Validación de seguridad: Mínimo 3 caracteres
    if len(codigo_input) < 3:
        db.close()
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
            db.close()
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
        db.close()
        return jsonify({"message": "Producto agregado a tu sede exitosamente", "id_producto": id_prod}), 201
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

@app.route("/api/categorias/seed", methods=["POST"])
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
        db.close()
        return jsonify({"message": f"Subcategorías sembradas con éxito: {created} creadas, {reassigned} productos reasignados."}), 200
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

# ==========================================
# RUTAS DE VENTAS
# ==========================================

import uuid
from datetime import datetime

@app.route("/api/ventas", methods=["POST"])
def create_venta():
    data = request.json
    detalles = data.get("detalles", [])
    id_usuario = data.get("id_usuario")
    descuento_total = float(data.get("descuento_total", 0.0))
    
    if not detalles:
        return jsonify({"error": "La venta debe tener al menos un producto"}), 400
        
    db = get_db()
    try:
        usuario = db.query(models.User).filter(models.User.id == id_usuario).first()
        if not usuario:
            raise Exception("Usuario no encontrado")
            
        id_sede = usuario.id_sede or 1
        
        # Generar correlativo simple V-YYYYMMDDHHMMSS-RANDOM
        correlativo = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"
        
        # Calcular total bruto e individual
        subtotal_acumulado = 0.0
        detalles_procesados = []

        for det in detalles:
            producto = db.query(models.Producto).filter(models.Producto.id_producto == det["id_producto"]).first()
            if not producto:
                raise Exception(f"Producto con ID {det['id_producto']} no encontrado")
                
            inventario = db.query(models.InventarioSede).filter(
                models.InventarioSede.id_producto == producto.id_producto,
                models.InventarioSede.id_sede == id_sede
            ).first()
            
            if not inventario:
                raise Exception(f"El producto {producto.nombre} no existe en el inventario de esta sede.")
                
            cantidad = int(det["cantidad"])
            if inventario.stock_actual < cantidad:
                raise Exception(f"Stock insuficiente para {producto.nombre} en tu sede. Tienes: {inventario.stock_actual}")

            precio_unitario = float(det["precio_unitario"])
            descuento_unitario = float(det.get("descuento_unitario", 0.0))
            precio_efectivo_unitario = precio_unitario - descuento_unitario
            
            # REGLA DE ORO COMERCIAL: precio_efectivo >= precio_compra
            precio_compra = float(inventario.precio_compra) if (inventario.precio_compra is not None) else 0.0
            if precio_efectivo_unitario < precio_compra:
                raise Exception(f"No se puede aplicar descuento a '{producto.nombre}': El precio final de venta (S/ {precio_efectivo_unitario:.2f}) es inferior al costo de compra (S/ {precio_compra:.2f}).")

            subtotal_item = cantidad * precio_efectivo_unitario
            subtotal_acumulado += subtotal_item

            detalles_procesados.append({
                "producto": producto,
                "inventario": inventario,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "descuento_unitario": descuento_unitario,
                "subtotal": subtotal_item
            })

        total_venta = round(max(0.0, subtotal_acumulado), 2)

        nueva_venta = models.Venta(
            correlativo=correlativo,
            total=total_venta,
            descuento_total=round(descuento_total, 2),
            metodo_pago=data.get("metodo_pago", "Efectivo"),
            id_usuario=id_usuario,
            id_sede=id_sede
        )
        db.add(nueva_venta)
        db.flush() 
        
        # Procesar detalles y descontar stock DE LA SEDE DEL USUARIO
        for item in detalles_procesados:
            producto = item["producto"]
            inventario = item["inventario"]
            cantidad = item["cantidad"]

            # Restar stock
            inventario.stock_actual -= cantidad
            
            # Crear detalle
            nuevo_detalle = models.DetalleVenta(
                id_venta=nueva_venta.id_venta,
                id_producto=producto.id_producto,
                cantidad=cantidad,
                precio_unitario=item["precio_unitario"],
                descuento_unitario=item["descuento_unitario"],
                subtotal=item["subtotal"]
            )
            db.add(nuevo_detalle)
            
            # Registrar salida en almacén de esta sede
            movimiento = models.MovimientoAlmacen(
                id_producto=producto.id_producto,
                id_sede=id_sede,
                tipo='SALIDA',
                cantidad=-cantidad,
                id_usuario=id_usuario,
                observacion=f"Venta ticket {correlativo}"
            )
            db.add(movimiento)
            
        db.commit()
        id_v = nueva_venta.id_venta
        
        sede = usuario.sede
        sede_nom = sede.nombre if sede else "Sede Principal"
        sede_dir = (sede.direccion if (sede and sede.direccion) else "Av. Central 123, Los Olivos")
        sede_tel = (sede.telefono if (sede and sede.telefono) else "01-1234567")
        vendedor_nom = f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username

        res_data = {
            "message": "Venta procesada exitosamente",
            "id_venta": id_v,
            "correlativo": correlativo,
            "total": total_venta,
            "metodo_pago": nueva_venta.metodo_pago,
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "sede_nombre": sede_nom,
            "sede_direccion": sede_dir,
            "sede_telefono": sede_tel,
            "vendedor": vendedor_nom
        }
        db.close()
        return jsonify(res_data), 201
        
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/ventas", methods=["GET"])
def get_ventas():
    db = get_db()
    try:
        user_id = request.args.get("user_id", type=int)
        sede_id = request.args.get("sede_id", type=int)

        # Validar rol de usuario si se envía user_id
        if user_id:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user_roles = [r.lower() for r in (user.roles or [])]
                is_admin = any("admin" in r for r in user_roles)
                is_supervisor = any("supervisor" in r for r in user_roles)
                is_vendedor = any("vendedor" in r for r in user_roles)

                if is_vendedor and not is_admin and not is_supervisor:
                    db.close()
                    return jsonify({"error": "Acceso denegado: El historial de ventas solo está disponible para Administradores y Supervisores."}), 403

                # Si es Supervisor (y no Admin), forzar únicamente la sede asignada al supervisor
                if is_supervisor and not is_admin:
                    sede_id = user.id_sede or 1
        vendedor_id = request.args.get("vendedor_id", type=int)
        search = request.args.get("search", type=str)
        fecha_inicio = request.args.get("fecha_inicio")
        fecha_fin = request.args.get("fecha_fin")

        query = db.query(models.Venta).filter(models.Venta.estado_registro == 1)

        if fecha_inicio:
            try:
                dt_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                query = query.filter(models.Venta.fecha_venta >= dt_ini)
            except Exception:
                pass

        if fecha_fin:
            try:
                dt_fin = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(models.Venta.fecha_venta < dt_fin)
            except Exception:
                pass

        if sede_id:
            query = query.filter(models.Venta.id_sede == sede_id)

        if vendedor_id:
            query = query.filter(models.Venta.id_usuario == vendedor_id)

        ventas = query.order_by(models.Venta.fecha_venta.desc()).all()

        users_map = {u.id: u for u in db.query(models.User).all()}
        sedes_map = {s.id_sede: s for s in db.query(models.Sede).all()}

        result_ventas = []
        total_monto = 0.0
        total_unidades = 0
        vendedores_conteo = {}

        for v in ventas:
            u = users_map.get(v.id_usuario)
            s = sedes_map.get(v.id_sede)

            vendedor_nom = f"{u.first_name} {u.last_name}".strip() if u else "Desconocido"
            if not vendedor_nom or (u and vendedor_nom == u.username):
                vendedor_nom = u.username if u else "Desconocido"

            sede_nom = s.nombre if s else "Sede Principal"

            if search:
                s_lower = search.lower().strip()
                match_correlativo = s_lower in (v.correlativo or "").lower()
                match_vendedor = s_lower in vendedor_nom.lower()
                if not (match_correlativo or match_vendedor):
                    continue

            unidades_venta = sum([d.cantidad for d in v.detalles]) if v.detalles else 0
            fecha_str = v.fecha_venta.strftime("%d/%m/%Y %H:%M") if v.fecha_venta else "N/A"

            total_monto += (v.total or 0.0)
            total_unidades += unidades_venta
            vendedores_conteo[vendedor_nom] = vendedores_conteo.get(vendedor_nom, 0) + (v.total or 0.0)

            result_ventas.append({
                "id_venta": v.id_venta,
                "correlativo": v.correlativo,
                "fecha": fecha_str,
                "total": round(v.total or 0.0, 2),
                "metodo_pago": v.metodo_pago,
                "unidades_totales": unidades_venta,
                "vendedor": vendedor_nom,
                "sede": sede_nom,
                "id_sede": v.id_sede,
                "id_usuario": v.id_usuario
            })

        top_vendedor = "N/A"
        if vendedores_conteo:
            top_vendedor = max(vendedores_conteo, key=vendedores_conteo.get)

        kpis = {
            "monto_total": round(total_monto, 2),
            "unidades_totales": total_unidades,
            "total_comprobantes": len(result_ventas),
            "top_vendedor": top_vendedor
        }

        db.close()
        return jsonify({"kpis": kpis, "ventas": result_ventas}), 200

    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/ventas/<int:id_venta>", methods=["GET"])
def get_detalle_venta(id_venta):
    db = get_db()
    try:
        venta = db.query(models.Venta).filter(models.Venta.id_venta == id_venta).first()
        if not venta:
            db.close()
            return jsonify({"error": "Venta no encontrada"}), 404

        u = db.query(models.User).filter(models.User.id == venta.id_usuario).first()
        s = db.query(models.Sede).filter(models.Sede.id_sede == venta.id_sede).first()

        vendedor_nom = f"{u.first_name} {u.last_name}".strip() if u else "Desconocido"
        if not vendedor_nom and u:
            vendedor_nom = u.username

        sede_nom = s.nombre if s else "Sede Principal"
        sede_dir = s.direccion if (s and s.direccion) else "Av. Central 123, Los Olivos"
        sede_tel = s.telefono if (s and s.telefono) else "01-1234567"

        detalles_res = []
        for d in venta.detalles:
            prod_nom = d.producto.nombre if d.producto else "Producto"
            prod_cod = d.producto.codigo_producto if d.producto else "PROD"
            detalles_res.append({
                "id_producto": d.id_producto,
                "codigo": prod_cod,
                "nombre": prod_nom,
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
                "descuento_unitario": getattr(d, 'descuento_unitario', 0.0) or 0.0,
                "subtotal": d.subtotal
            })

        data = {
            "id_venta": venta.id_venta,
            "correlativo": venta.correlativo,
            "fecha": venta.fecha_venta.strftime("%d/%m/%Y %H:%M") if venta.fecha_venta else "N/A",
            "total": venta.total,
            "descuento_total": getattr(venta, 'descuento_total', 0.0) or 0.0,
            "metodo_pago": venta.metodo_pago,
            "vendedor": vendedor_nom,
            "sede_nombre": sede_nom,
            "sede_direccion": sede_dir,
            "sede_telefono": sede_tel,
            "detalles": detalles_res
        }
        db.close()
        return jsonify(data), 200
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 400


# ==========================================
# ENDPOINTS PROFORMAS / COTIZACIONES (HU15)
# ==========================================

@app.route("/api/proformas", methods=["POST"])
def registrar_proforma():
    data = request.json
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
                db.close()
                return jsonify({"error": "Únicamente en el perfil Vendedor se pueden emitir proformas."}), 403

        import datetime
        now = datetime.datetime.now()
        correlativo = f"P-{now.strftime('%Y%m%d%H%M%S')}"

        total_proforma = 0.0
        for item in detalles:
            sub = float(item["cantidad"]) * float(item["precio_unitario"])
            total_proforma += sub

        nueva_proforma = models.Proforma(
            correlativo=correlativo,
            cliente_nombre=cliente_nombre,
            cliente_doc=cliente_doc,
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
        db.close()

        return jsonify({
            "message": "Proforma registrada con éxito",
            "id_proforma": prof_id,
            "correlativo": correlativo
        }), 201

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/proformas", methods=["GET"])
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
                "cliente_nombre": p.cliente_nombre,
                "cliente_doc": p.cliente_doc,
                "total": p.total,
                "vendedor": vendedor_nom,
                "sede_nombre": s.nombre if s else "Sede Principal"
            })

        db.close()
        return jsonify(res), 200

    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/proformas/<int:id_proforma>", methods=["GET"])
def get_detalle_proforma(id_proforma):
    db = get_db()
    try:
        prof = db.query(models.Proforma).filter(models.Proforma.id_proforma == id_proforma).first()
        if not prof:
            db.close()
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
            "cliente_nombre": prof.cliente_nombre,
            "cliente_doc": prof.cliente_doc,
            "total": prof.total,
            "vendedor": vendedor_nom,
            "sede_nombre": sede_nom,
            "sede_direccion": sede_dir,
            "sede_telefono": sede_tel,
            "detalles": detalles_res
        }
        db.close()
        return jsonify(data), 200

    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 400


# --- Endpoints de Promociones y Autorizaciones por Supervisor ---

@app.route("/api/promociones", methods=["GET"])
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
        db.close()
        return jsonify(res), 200
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/promociones/activas", methods=["GET"])
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
        db.close()
        return jsonify(res), 200
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/promociones", methods=["POST"])
def create_promocion():
    db = get_db()
    try:
        data = request.json
        user_id = data.get("user_id")
        id_sede = data.get("id_sede")

        # Verificar rol si se envía user_id
        if user_id:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user_roles = [r.lower() for r in (user.roles or [])]
                if not any(role in r for r in user_roles for role in ["admin", "supervisor"]):
                    db.close()
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
        db.close()
        return jsonify({"message": "Promoción creada exitosamente", "id_promocion": nueva_promo.id_promocion}), 201
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/promociones/<int:id_promocion>", methods=["DELETE"])
def delete_promocion(id_promocion):
    db = get_db()
    try:
        promo = db.query(models.Promocion).filter(models.Promocion.id_promocion == id_promocion).first()
        if not promo:
            db.close()
            return jsonify({"error": "Promoción no encontrada"}), 404

        promo.estado_registro = 0
        db.commit()
        db.close()
        return jsonify({"message": "Promoción eliminada exitosamente"}), 200
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/supervisor/autorizar", methods=["POST"])
def autorizar_supervisor():
    db = get_db()
    try:
        data = request.json
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            db.close()
            return jsonify({"error": "Usuario y contraseña son requeridos"}), 400

        user = db.query(models.User).filter(
            models.User.username == username,
            models.User.is_active == 1
        ).first()

        if not user or user.password != password:
            db.close()
            return jsonify({"error": "Credenciales de Supervisor incorrectas"}), 401

        user_roles = [r.lower() for r in (user.roles or [])]
        is_supervisor_or_admin = any(role in r for r in user_roles for role in ["admin", "supervisor"])

        if not is_supervisor_or_admin:
            db.close()
            return jsonify({"error": "Acceso denegado: El usuario indicado no cuenta con perfil de Supervisor o Administrador."}), 403

        vendedor_nombre = f"{user.first_name} {user.last_name}".strip() or user.username
        db.close()
        return jsonify({
            "autorizado": True,
            "message": "Autorización concedida por el supervisor",
            "supervisor": vendedor_nombre,
            "id_supervisor": user.id
        }), 200

    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 400


# ==============================================================================
# --- MÓDULO DE PROVEEDORES Y CATÁLOGO (HU 22 & HU 23) ---
# ==============================================================================

def check_supervisor_or_admin(db, user_role, user_id=None):
    """Verifica si el rol o usuario tiene permisos de Supervisor o Administrador"""
    if user_role and user_role.lower() in ["administrador", "admin", "supervisor"]:
        return True
    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            roles = [r.lower() for r in (user.roles or [])]
            return any(r in ["administrador", "admin", "supervisor"] for r in roles)
    return False


@app.route("/api/proveedores", methods=["GET"])
def get_proveedores():
    """Listar todos los proveedores activos con resumen de catálogo y órdenes (filtrable por sede)"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no tienen acceso a proveedores"}), 403

    db = get_db()
    try:
        id_sede_param = request.args.get("id_sede") or request.args.get("sede_id")
        query = db.query(models.Proveedor).filter(models.Proveedor.estado_registro == 1)
        if id_sede_param and str(id_sede_param).isdigit():
            query = query.filter(models.Proveedor.id_sede == int(id_sede_param))

        proveedores = query.order_by(models.Proveedor.razon_social.asc()).all()
        resultado = []
        for p in proveedores:
            total_prods = db.query(models.ProveedorProducto).filter(
                models.ProveedorProducto.id_proveedor == p.id_proveedor,
                models.ProveedorProducto.estado_registro == 1
            ).count()

            total_ordenes = db.query(models.OrdenCompra).filter(
                models.OrdenCompra.id_proveedor == p.id_proveedor,
                models.OrdenCompra.estado_registro == 1
            ).count()

            # Promedio de calificación si tiene evaluaciones
            promedio_calif = db.query(func.avg(models.EvaluacionProveedor.calificacion)).filter(
                models.EvaluacionProveedor.id_proveedor == p.id_proveedor,
                models.EvaluacionProveedor.estado_registro == 1
            ).scalar()

            resultado.append({
                "id_proveedor": p.id_proveedor,
                "id_sede": p.id_sede,
                "sede_nombre": p.sede.nombre if p.sede else "Sin sede asignada",
                "ruc": p.ruc,
                "razon_social": p.razon_social,
                "nombre_contacto": p.nombre_contacto or "",
                "telefono": p.telefono or "",
                "correo": p.correo or "",
                "direccion": p.direccion or "",
                "condiciones_pago": p.condiciones_pago or "Contado",
                "total_productos": total_prods,
                "total_ordenes": total_ordenes,
                "calificacion_promedio": round(float(promedio_calif), 1) if promedio_calif else None,
                "fecha_registro": p.fecha_registro.strftime("%Y-%m-%d %H:%M") if p.fecha_registro else ""
            })

        db.close()
        return jsonify(resultado), 200
    except Exception as e:
        db.close()
        return jsonify({"error": f"Error al obtener proveedores: {str(e)}"}), 500


@app.route("/api/proveedores/<int:id_proveedor>", methods=["GET"])
def get_proveedor(id_proveedor):
    """Obtener un proveedor específico por ID"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        p = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not p:
            db.close()
            return jsonify({"error": "Proveedor no encontrado"}), 404

        total_prods = db.query(models.ProveedorProducto).filter(
            models.ProveedorProducto.id_proveedor == p.id_proveedor,
            models.ProveedorProducto.estado_registro == 1
        ).count()

        total_ordenes = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_proveedor == p.id_proveedor,
            models.OrdenCompra.estado_registro == 1
        ).count()

        data = {
            "id_proveedor": p.id_proveedor,
            "id_sede": p.id_sede,
            "sede_nombre": p.sede.nombre if p.sede else "Sin sede",
            "ruc": p.ruc,
            "razon_social": p.razon_social,
            "nombre_contacto": p.nombre_contacto or "",
            "telefono": p.telefono or "",
            "correo": p.correo or "",
            "direccion": p.direccion or "",
            "condiciones_pago": p.condiciones_pago or "Contado",
            "total_productos": total_prods,
            "total_ordenes": total_ordenes,
            "fecha_registro": p.fecha_registro.strftime("%Y-%m-%d %H:%M") if p.fecha_registro else ""
        }
        db.close()
        return jsonify(data), 200
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 500


@app.route("/api/proveedores", methods=["POST"])
def create_proveedor():
    """Registrar un nuevo proveedor (HU 22) con validación de RUC duplicado por sede y celular de 9 dígitos"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Solo Administrador o Supervisor pueden registrar proveedores"}), 403

    db = get_db()
    try:
        data = request.json or {}
        ruc = str(data.get("ruc", "")).strip()
        razon_social = str(data.get("razon_social", "")).strip()
        condiciones_pago = str(data.get("condiciones_pago", "")).strip()
        id_sede = data.get("id_sede")

        if not ruc:
            db.close()
            return jsonify({"error": "El RUC es obligatorio."}), 400

        if not ruc.isdigit():
            db.close()
            return jsonify({"error": "El RUC debe contener únicamente dígitos numéricos."}), 400

        if len(ruc) < 11:
            db.close()
            return jsonify({"error": f"Error en RUC: Tiene menos de 11 dígitos ({len(ruc)} dígitos). Debe tener exactamente 11 dígitos."}), 400

        if len(ruc) > 11:
            db.close()
            return jsonify({"error": f"Error en RUC: Tiene más de 11 dígitos ({len(ruc)} dígitos). Debe tener exactamente 11 dígitos."}), 400

        if not (ruc.startswith("10") or ruc.startswith("20")):
            db.close()
            return jsonify({"error": "Error en RUC: Debe iniciar obligatoriamente con '10' (Persona Natural con Negocio) o '20' (Persona Jurídica / Empresa)."}), 400

        if not razon_social:
            db.close()
            return jsonify({"error": "La Razón Social o nombre de la empresa es obligatorio."}), 400

        telefono = str(data.get("telefono", "")).strip()
        if not telefono:
            db.close()
            return jsonify({"error": "El Celular es obligatorio."}), 400

        if not telefono.isdigit():
            db.close()
            return jsonify({"error": "El Celular debe contener únicamente dígitos numéricos."}), 400

        if len(telefono) != 9:
            db.close()
            return jsonify({"error": f"Error en Celular: Debe tener exactamente 9 dígitos ({len(telefono)} dígitos ingresados)."}), 400

        if not telefono.startswith("9"):
            db.close()
            return jsonify({"error": "Error en Celular: Debe ser un número celular que comience con '9'."}), 400

        id_sede_final = int(id_sede) if id_sede and str(id_sede).isdigit() else 1

        # Criterio de Aceptación: Validar RUC registrado para la misma sede
        existente = db.query(models.Proveedor).filter(
            models.Proveedor.ruc == ruc,
            models.Proveedor.id_sede == id_sede_final,
            models.Proveedor.estado_registro == 1
        ).first()

        if existente:
            db.close()
            return jsonify({"error": f"El RUC {ruc} ya se encuentra registrado para '{existente.razon_social}' en esta sede."}), 400

        # Si había uno eliminado con el mismo RUC y sede, lo reactivamos con los datos nuevos
        eliminado_previo = db.query(models.Proveedor).filter(
            models.Proveedor.ruc == ruc,
            models.Proveedor.id_sede == id_sede_final,
            models.Proveedor.estado_registro == 0
        ).first()

        if eliminado_previo:
            eliminado_previo.id_sede = id_sede_final
            eliminado_previo.razon_social = razon_social
            eliminado_previo.nombre_contacto = str(data.get("nombre_contacto", "")).strip()
            eliminado_previo.telefono = telefono
            eliminado_previo.correo = str(data.get("correo", "")).strip()
            eliminado_previo.direccion = str(data.get("direccion", "")).strip()
            eliminado_previo.condiciones_pago = condiciones_pago or "Contado"
            eliminado_previo.estado_registro = 1
            db.commit()
            db.refresh(eliminado_previo)
            id_nuevo = eliminado_previo.id_proveedor
        else:
            nuevo = models.Proveedor(
                ruc=ruc,
                id_sede=id_sede_final,
                razon_social=razon_social,
                nombre_contacto=str(data.get("nombre_contacto", "")).strip(),
                telefono=telefono,
                correo=str(data.get("correo", "")).strip(),
                direccion=str(data.get("direccion", "")).strip(),
                condiciones_pago=condiciones_pago or "Contado",
                estado_registro=1
            )
            db.add(nuevo)
            db.commit()
            db.refresh(nuevo)
            id_nuevo = nuevo.id_proveedor

        db.close()
        return jsonify({
            "message": "Proveedor registrado con éxito.",
            "id_proveedor": id_nuevo
        }), 201

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": f"Error al registrar proveedor: {str(e)}"}), 500


@app.route("/api/proveedores/<int:id_proveedor>", methods=["PUT"])
def update_proveedor(id_proveedor):
    """Actualizar datos de un proveedor (HU 22)"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not proveedor:
            db.close()
            return jsonify({"error": "Proveedor no encontrado"}), 404

        data = request.json or {}
        if "id_sede" in data and str(data["id_sede"]).isdigit():
            proveedor.id_sede = int(data["id_sede"])

        ruc_nuevo = str(data.get("ruc", proveedor.ruc)).strip()

        if ruc_nuevo != proveedor.ruc:
            if not ruc_nuevo.isdigit():
                db.close()
                return jsonify({"error": "El RUC debe contener únicamente dígitos numéricos."}), 400
            if len(ruc_nuevo) < 11:
                db.close()
                return jsonify({"error": f"Error en RUC: Tiene menos de 11 dígitos ({len(ruc_nuevo)} dígitos). Debe tener exactamente 11 dígitos."}), 400
            if len(ruc_nuevo) > 11:
                db.close()
                return jsonify({"error": f"Error en RUC: Tiene más de 11 dígitos ({len(ruc_nuevo)} dígitos). Debe tener exactamente 11 dígitos."}), 400
            if not (ruc_nuevo.startswith("10") or ruc_nuevo.startswith("20")):
                db.close()
                return jsonify({"error": "Error en RUC: Debe iniciar obligatoriamente con '10' (Persona Natural con Negocio) o '20' (Persona Jurídica / Empresa)."}), 400
            # Validar que no choque con otro en la misma sede
            colision = db.query(models.Proveedor).filter(
                models.Proveedor.ruc == ruc_nuevo,
                models.Proveedor.id_sede == proveedor.id_sede,
                models.Proveedor.id_proveedor != id_proveedor,
                models.Proveedor.estado_registro == 1
            ).first()
            if colision:
                db.close()
                return jsonify({"error": f"El RUC {ruc_nuevo} ya pertenece a otro proveedor ({colision.razon_social}) en esta sede."}), 400
            proveedor.ruc = ruc_nuevo

        if "razon_social" in data and str(data["razon_social"]).strip():
            proveedor.razon_social = str(data["razon_social"]).strip()
        if "nombre_contacto" in data:
            proveedor.nombre_contacto = str(data["nombre_contacto"]).strip()
        if "telefono" in data:
            tel = str(data["telefono"]).strip()
            if not tel:
                db.close()
                return jsonify({"error": "El Celular es obligatorio."}), 400
            if not tel.isdigit():
                db.close()
                return jsonify({"error": "El Celular debe contener únicamente dígitos numéricos."}), 400
            if len(tel) != 9:
                db.close()
                return jsonify({"error": f"Error en Celular: Debe tener exactamente 9 dígitos (ingresaste {len(tel)} dígitos)."}), 400
            if not tel.startswith("9"):
                db.close()
                return jsonify({"error": "Error en Celular: Debe comenzar obligatoriamente con '9' (número celular)."}), 400
            proveedor.telefono = tel
        if "correo" in data:
            proveedor.correo = str(data["correo"]).strip()
        if "direccion" in data:
            proveedor.direccion = str(data["direccion"]).strip()
        if "condiciones_pago" in data and str(data["condiciones_pago"]).strip():
            proveedor.condiciones_pago = str(data["condiciones_pago"]).strip()

        db.commit()
        db.close()
        return jsonify({"message": "Proveedor actualizado correctamente."}), 200

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": f"Error al actualizar proveedor: {str(e)}"}), 500


@app.route("/api/proveedores/<int:id_proveedor>", methods=["DELETE"])
def delete_proveedor(id_proveedor):
    """
    Eliminar un proveedor (HU 22).
    Criterios de Aceptación:
    - Dado que un proveedor NO tiene compras asociadas, cuando el usuario lo elimina, entonces el sistema lo remueve.
    - Dado que un proveedor TIENE compras asociadas, cuando el usuario intenta eliminarlo, entonces el sistema impide la acción.
    """
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not proveedor:
            db.close()
            return jsonify({"error": "Proveedor no encontrado"}), 404

        # Validar si tiene compras asociadas
        compras_asociadas = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_proveedor == id_proveedor,
            models.OrdenCompra.estado_registro == 1
        ).count()

        if compras_asociadas > 0:
            db.close()
            return jsonify({
                "error": f"No se puede eliminar a '{proveedor.razon_social}' porque tiene {compras_asociadas} orden(es) de compra registrada(s). Por integridad contable y de auditoría la acción fue rechazada."
            }), 400

        # Eliminación lógica
        nombre_prov = proveedor.razon_social
        proveedor.estado_registro = 0
        db.commit()
        db.close()
        return jsonify({"message": f"Proveedor '{nombre_prov}' eliminado con éxito."}), 200

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": f"Error al eliminar proveedor: {str(e)}"}), 500


# ------------------------------------------------------------------------------
# --- CATÁLOGO DE PRODUCTOS DE PROVEEDOR (HU 23) ---
# ------------------------------------------------------------------------------

@app.route("/api/proveedores/<int:id_proveedor>/catalogo", methods=["GET"])
def get_catalogo_proveedor(id_proveedor):
    """Listar productos que provee este proveedor con su precio pactado"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not proveedor:
            db.close()
            return jsonify({"error": "Proveedor no encontrado"}), 404

        proveedor_info = {
            "id_proveedor": proveedor.id_proveedor,
            "ruc": proveedor.ruc,
            "razon_social": proveedor.razon_social,
            "id_sede": proveedor.id_sede,
            "sede_nombre": proveedor.sede.nombre if proveedor.sede else "Todas las sedes",
            "condiciones_pago": proveedor.condiciones_pago
        }

        # La sede del catálogo se determina prioritariamente por la sede del proveedor:
        # Proveedores de Olivos (id_sede=1) jalan de inventario Olivos.
        # Proveedores de SJL (id_sede=2) jalan de inventario SJL.
        sede_param = request.args.get("id_sede", type=int) or request.args.get("sede_id", type=int)
        id_sede_consulta = proveedor.id_sede or sede_param or 1

        items = db.query(models.ProveedorProducto).join(
            models.Producto, models.ProveedorProducto.id_producto == models.Producto.id_producto
        ).filter(
            models.ProveedorProducto.id_proveedor == id_proveedor,
            models.ProveedorProducto.estado_registro == 1,
            models.Producto.estado_registro == 1
        ).all()

        resultado = []
        for it in items:
            p = it.producto
            cat_nom = p.categoria.nombre if p.categoria else "Sin categoría"
            subcat_nom = p.subcategoria_rel.nombre if p.subcategoria_rel else None

            # Garantizar sincronización exacta con el precio oficial de compra de la sede asignada
            inv = db.query(models.InventarioSede).filter(
                models.InventarioSede.id_producto == p.id_producto,
                models.InventarioSede.id_sede == id_sede_consulta,
                models.InventarioSede.estado_registro == 1
            ).first()

            if not inv:
                inv = db.query(models.InventarioSede).filter(
                    models.InventarioSede.id_producto == p.id_producto,
                    models.InventarioSede.estado_registro == 1
                ).first()

            precio_oficial = round(float(inv.precio_compra), 2) if (inv and inv.precio_compra is not None) else round(float(it.precio_compra), 2)

            # Sincronizar permanentemente en proveedor_productos
            if inv and inv.precio_compra is not None and it.precio_compra != precio_oficial:
                it.precio_compra = precio_oficial

            resultado.append({
                "id_proveedor_producto": it.id_proveedor_producto,
                "id_producto": p.id_producto,
                "codigo_producto": p.codigo_producto,
                "nombre": p.nombre,
                "descripcion": p.descripcion or "",
                "categoria": cat_nom,
                "subcategoria": subcat_nom,
                "precio_compra": precio_oficial,
                "codigo_proveedor": it.codigo_proveedor or "",
                "fecha_registro": it.fecha_registro.strftime("%Y-%m-%d") if it.fecha_registro else ""
            })

        db.commit()
        db.close()
        return jsonify({
            "proveedor": proveedor_info,
            "productos": resultado
        }), 200

    except Exception as e:
        db.close()
        return jsonify({"error": f"Error al cargar catálogo del proveedor: {str(e)}"}), 500


@app.route("/api/proveedores/<int:id_proveedor>/catalogo", methods=["POST"])
def asociar_producto_catalogo(id_proveedor):
    """
    Asociar un producto a un proveedor con su precio de compra o actualizarlo (HU 23).
    Criterios de Aceptación:
    - Dado que el proveedor y el producto están registrados, cuando el usuario los asocia, el sistema guarda la relación.
    - Cuando el usuario ingresa el precio de compra, el sistema lo registra y sincroniza con el inventario de almacén.
    - Si el producto ya estaba asociado, actualiza su precio.
    - Un producto puede estar asociado también a otro proveedor.
    """
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        data = request.json or {}
        id_producto = data.get("id_producto")
        precio_compra = data.get("precio_compra")
        codigo_proveedor = str(data.get("codigo_proveedor", "")).strip()

        if not id_producto:
            db.close()
            return jsonify({"error": "Debe seleccionar un producto."}), 400

        try:
            precio_compra = float(precio_compra)
            if precio_compra <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            db.close()
            return jsonify({"error": "El precio de compra debe ser un número mayor a 0."}), 400

        # Verificar existencia
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()
        if not proveedor:
            db.close()
            return jsonify({"error": "Proveedor no encontrado o inactivo"}), 404

        producto = db.query(models.Producto).filter(
            models.Producto.id_producto == id_producto,
            models.Producto.estado_registro == 1
        ).first()
        if not producto:
            db.close()
            return jsonify({"error": "Producto no encontrado o inactivo"}), 404

        # Buscar si ya existe la asociación
        existente = db.query(models.ProveedorProducto).filter(
            models.ProveedorProducto.id_proveedor == id_proveedor,
            models.ProveedorProducto.id_producto == id_producto
        ).first()

        if existente:
            existente.precio_compra = precio_compra
            if codigo_proveedor:
                existente.codigo_proveedor = codigo_proveedor
            existente.estado_registro = 1
            msg = f"Precio de compra actualizado a S/. {precio_compra:.2f} para '{producto.nombre}'."
        else:
            nuevo = models.ProveedorProducto(
                id_proveedor=id_proveedor,
                id_producto=id_producto,
                precio_compra=precio_compra,
                codigo_proveedor=codigo_proveedor,
                estado_registro=1
            )
            db.add(nuevo)
            msg = f"Producto '{producto.nombre}' incorporado al catálogo de {proveedor.razon_social} con precio S/. {precio_compra:.2f}."

        # Sincronizar bidireccionalmente con el inventario de almacén (inventario_sedes)
        invs = db.query(models.InventarioSede).filter(models.InventarioSede.id_producto == id_producto).all()
        for inv in invs:
            inv.precio_compra = precio_compra

        db.commit()
        db.close()
        return jsonify({"message": msg}), 200

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": f"Error al asociar producto: {str(e)}"}), 500


@app.route("/api/proveedores/<int:id_proveedor>/catalogo/<int:id_producto>", methods=["DELETE"])
def desasociar_producto_catalogo(id_proveedor, id_producto):
    """Remover un producto del catálogo de un proveedor"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        asoc = db.query(models.ProveedorProducto).filter(
            models.ProveedorProducto.id_proveedor == id_proveedor,
            models.ProveedorProducto.id_producto == id_producto
        ).first()

        if not asoc:
            db.close()
            return jsonify({"error": "El producto no está asociado a este proveedor."}), 404

        asoc.estado_registro = 0
        db.commit()
        db.close()
        return jsonify({"message": "Producto removido del catálogo del proveedor."}), 200

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": f"Error al desasociar producto: {str(e)}"}), 500




# ==============================================================================
# --- MÓDULO DE COMPRAS (HU 19, HU 20 & HU 21) ---
# ==============================================================================

@app.route("/api/compras/siguiente-correlativo", methods=["GET"])
def get_siguiente_correlativo_compra():
    """Obtener el correlativo automático para la siguiente orden de compra (HU 19)"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        from datetime import datetime
        year = datetime.now().year
        # Contar órdenes existentes del año
        total_ordenes = db.query(models.OrdenCompra).count()
        siguiente_num = total_ordenes + 1
        correlativo = f"OC-{year}-{siguiente_num:04d}"

        # Verificar unicidad
        while db.query(models.OrdenCompra).filter(models.OrdenCompra.correlativo == correlativo).first():
            siguiente_num += 1
            correlativo = f"OC-{year}-{siguiente_num:04d}"

        db.close()
        return jsonify({"correlativo": correlativo}), 200
    except Exception as e:
        db.close()
        return jsonify({"error": f"Error al generar correlativo: {str(e)}"}), 500


@app.route("/api/compras", methods=["POST"])
def emitir_orden_compra():
    """Emitir una nueva orden de compra a un proveedor específico (HU 19)"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no pueden emitir órdenes de compra"}), 403

    data = request.json or {}
    id_proveedor = data.get("id_proveedor")
    id_sede = data.get("id_sede")
    id_usuario = data.get("id_usuario")
    fecha_esperada = str(data.get("fecha_esperada", "")).strip()
    observacion = str(data.get("observacion", "")).strip()
    items = data.get("items", [])

    if not id_proveedor:
        return jsonify({"error": "Debes seleccionar un proveedor obligatorio para emitir la orden."}), 400

    if not items or len(items) == 0:
        return jsonify({"error": "La orden de compra debe incluir al menos un producto."}), 400

    # Validar que la fecha esperada no sea anterior a hoy
    if fecha_esperada:
        try:
            from datetime import datetime
            fecha_dt = datetime.strptime(fecha_esperada, "%Y-%m-%d").date()
            hoy_dt = datetime.now().date()
            if fecha_dt < hoy_dt:
                return jsonify({"error": f"La fecha esperada de entrega ({fecha_esperada}) no puede ser anterior a la fecha de hoy ({hoy_dt.strftime('%Y-%m-%d')})."}), 400
        except ValueError:
            pass

    db = get_db()
    try:
        from datetime import datetime
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id_proveedor == id_proveedor,
            models.Proveedor.estado_registro == 1
        ).first()

        if not proveedor:
            db.close()
            return jsonify({"error": "El proveedor seleccionado no existe o está inactivo."}), 404

        # Determinar sede del proveedor o del usuario
        id_sede_final = int(id_sede) if id_sede else (proveedor.id_sede or 1)

        # Generar correlativo único
        year = datetime.now().year
        total_ordenes = db.query(models.OrdenCompra).count()
        siguiente_num = total_ordenes + 1
        correlativo = f"OC-{year}-{siguiente_num:04d}"
        while db.query(models.OrdenCompra).filter(models.OrdenCompra.correlativo == correlativo).first():
            siguiente_num += 1
            correlativo = f"OC-{year}-{siguiente_num:04d}"

        # Calcular subtotales y validar ítems
        total_orden = 0.0
        detalles_a_crear = []

        for item in items:
            id_prod = item.get("id_producto")
            cant = int(item.get("cantidad", 0))
            precio_u = float(item.get("precio_unitario", 0.0))

            if not id_prod or cant <= 0 or precio_u <= 0:
                db.close()
                return jsonify({"error": f"Datos de producto inválidos (cantidad y precio deben ser mayores a 0)."}), 400

            prod = db.query(models.Producto).filter(models.Producto.id_producto == id_prod).first()
            if not prod:
                db.close()
                return jsonify({"error": f"El producto ID {id_prod} no existe en el sistema."}), 404

            subtotal_item = round(cant * precio_u, 2)
            total_orden += subtotal_item

            detalles_a_crear.append({
                "id_producto": id_prod,
                "cantidad_solicitada": cant,
                "cantidad_recibida": 0,
                "precio_unitario": precio_u,
                "subtotal": subtotal_item
            })

        total_orden = round(total_orden, 2)

        # Buscar usuario emisor si no vino id_usuario
        if not id_usuario:
            primer_u = db.query(models.User).first()
            id_usuario = primer_u.id if primer_u else 1

        nueva_orden = models.OrdenCompra(
            correlativo=correlativo,
            id_proveedor=id_proveedor,
            id_sede=id_sede_final,
            id_usuario=id_usuario,
            fecha_esperada=fecha_esperada,
            estado="PENDIENTE",
            total=total_orden,
            observacion=observacion,
            estado_registro=1
        )
        db.add(nueva_orden)
        db.flush()

        # Agregar los detalles
        for det in detalles_a_crear:
            nuevo_det = models.DetalleOrdenCompra(
                id_orden_compra=nueva_orden.id_orden_compra,
                id_producto=det["id_producto"],
                cantidad_solicitada=det["cantidad_solicitada"],
                cantidad_recibida=0,
                precio_unitario=det["precio_unitario"],
                subtotal=det["subtotal"]
            )
            db.add(nuevo_det)

        db.commit()
        id_creada = nueva_orden.id_orden_compra
        db.close()

        return jsonify({
            "message": f"Orden de compra {correlativo} emitida con éxito.",
            "id_orden_compra": id_creada,
            "correlativo": correlativo,
            "total": total_orden
        }), 201

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": f"Error al emitir orden de compra: {str(e)}"}), 500


@app.route("/api/compras", methods=["GET"])
def get_compras():
    """Listar compras / órdenes de compra filtradas por sede del usuario (HU 21)"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        id_sede = request.args.get("id_sede")
        estado_filtro = request.args.get("estado")
        search = (request.args.get("search") or "").strip().lower()

        query = db.query(models.OrdenCompra).filter(models.OrdenCompra.estado_registro == 1)

        if id_sede and str(id_sede).isdigit():
            query = query.filter(models.OrdenCompra.id_sede == int(id_sede))

        if estado_filtro and estado_filtro.upper() in ["PENDIENTE", "RECIBIDA", "ANULADA"]:
            query = query.filter(models.OrdenCompra.estado == estado_filtro.upper())

        ordenes = query.order_by(models.OrdenCompra.id_orden_compra.desc()).all()

        resultado = []
        for o in ordenes:
            prov = o.proveedor
            usuario = o.usuario
            sede = o.sede

            if search:
                matches_correlativo = search in (o.correlativo or "").lower()
                matches_prov = search in (prov.razon_social if prov else "").lower() or search in (prov.ruc if prov else "")
                if not (matches_correlativo or matches_prov):
                    continue

            # Contar total de unidades solicitadas
            total_unidades = sum(d.cantidad_solicitada for d in o.detalles)
            total_items = len(o.detalles)

            resultado.append({
                "id_orden_compra": o.id_orden_compra,
                "correlativo": o.correlativo,
                "id_proveedor": o.id_proveedor,
                "proveedor_nombre": prov.razon_social if prov else "Proveedor Desconocido",
                "proveedor_ruc": prov.ruc if prov else "",
                "proveedor_telefono": prov.telefono if prov else "",
                "proveedor_contacto": prov.nombre_contacto if prov else "",
                "id_sede": o.id_sede,
                "sede_nombre": sede.nombre if sede else "Sede Central",
                "id_usuario": o.id_usuario,
                "usuario_nombre": f"{usuario.first_name or ''} {usuario.last_name or ''}".strip() or (usuario.username if usuario else "Sistema"),
                "fecha_emision": o.fecha_emision.strftime("%Y-%m-%d %H:%M") if o.fecha_emision else "",
                "fecha_esperada": o.fecha_esperada or "",
                "fecha_recepcion": o.fecha_recepcion.strftime("%Y-%m-%d %H:%M") if o.fecha_recepcion else "",
                "estado": o.estado,
                "total": round(float(o.total or 0.0), 2),
                "total_items": total_items,
                "total_unidades": total_unidades,
                "observacion": o.observacion or ""
            })

        db.close()
        return jsonify(resultado), 200

    except Exception as e:
        db.close()
        return jsonify({"error": f"Error al consultar compras: {str(e)}"}), 500


@app.route("/api/compras/<int:id_orden>", methods=["GET"])
def get_detalle_compra(id_orden):
    """Obtener el detalle completo de una orden de compra (HU 19, 20 & 21)"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado"}), 403

    db = get_db()
    try:
        orden = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_orden_compra == id_orden,
            models.OrdenCompra.estado_registro == 1
        ).first()

        if not orden:
            db.close()
            return jsonify({"error": "Orden de compra no encontrada."}), 404

        prov = orden.proveedor
        usuario = orden.usuario
        sede = orden.sede

        items = []
        for det in orden.detalles:
            prod = det.producto
            items.append({
                "id_detalle_oc": det.id_detalle_oc,
                "id_producto": det.id_producto,
                "codigo_producto": prod.codigo_producto if prod else f"PROD-{det.id_producto}",
                "nombre_producto": prod.nombre if prod else "Producto",
                "cantidad_solicitada": det.cantidad_solicitada,
                "cantidad_recibida": det.cantidad_recibida or 0,
                "precio_unitario": round(float(det.precio_unitario), 2),
                "subtotal": round(float(det.subtotal), 2)
            })

        data = {
            "id_orden_compra": orden.id_orden_compra,
            "correlativo": orden.correlativo,
            "id_proveedor": orden.id_proveedor,
            "proveedor_nombre": prov.razon_social if prov else "",
            "proveedor_ruc": prov.ruc if prov else "",
            "proveedor_telefono": prov.telefono if prov else "",
            "proveedor_correo": prov.correo if prov else "",
            "proveedor_contacto": prov.nombre_contacto if prov else "",
            "proveedor_direccion": prov.direccion if prov else "",
            "id_sede": orden.id_sede,
            "sede_nombre": sede.nombre if sede else "Sede Central",
            "sede_direccion": sede.direccion if sede else "",
            "usuario_nombre": f"{usuario.first_name or ''} {usuario.last_name or ''}".strip() or (usuario.username if usuario else "Sistema"),
            "fecha_emision": orden.fecha_emision.strftime("%Y-%m-%d %H:%M") if orden.fecha_emision else "",
            "fecha_esperada": orden.fecha_esperada or "Inmediata",
            "fecha_recepcion": orden.fecha_recepcion.strftime("%Y-%m-%d %H:%M") if orden.fecha_recepcion else "",
            "estado": orden.estado,
            "total": round(float(orden.total or 0.0), 2),
            "observacion": orden.observacion or "",
            "items": items
        }

        db.close()
        return jsonify(data), 200

    except Exception as e:
        db.close()
        return jsonify({"error": f"Error al obtener detalle de compra: {str(e)}"}), 500


@app.route("/api/compras/<int:id_orden>/recibir", methods=["POST"])
def recibir_orden_compra(id_orden):
    """
    Recepción de mercadería e ingreso automático de stock al almacén (HU 20).
    Aumenta el stock_actual en inventario_sedes y registra movimiento de ENTRADA.
    """
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no pueden recibir mercadería"}), 403

    db = get_db()
    try:
        from datetime import datetime
        orden = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_orden_compra == id_orden,
            models.OrdenCompra.estado_registro == 1
        ).first()

        if not orden:
            db.close()
            return jsonify({"error": "Orden de compra no encontrada."}), 404

        if orden.estado == "RECIBIDA":
            db.close()
            return jsonify({"error": f"La orden {orden.correlativo} ya fue recibida e ingresada al almacén anteriormente."}), 400

        if orden.estado == "ANULADA":
            db.close()
            return jsonify({"error": f"La orden {orden.correlativo} está anulada. No se puede recibir mercadería."}), 400

        prov = orden.proveedor
        prov_nombre = prov.razon_social if prov else "Proveedor"

        data = request.json or {}
        id_usuario = data.get("id_usuario") or orden.id_usuario

        # Actualizar estado de la orden
        orden.estado = "RECIBIDA"
        orden.fecha_recepcion = datetime.now()

        # Recorrer ítems y sumar stock a InventarioSede + Movimiento de Entrada
        productos_ingresados = []
        for det in orden.detalles:
            cant_recibida = det.cantidad_solicitada
            det.cantidad_recibida = cant_recibida

            # Buscar o crear inventario para esa sede
            inv = db.query(models.InventarioSede).filter(
                models.InventarioSede.id_producto == det.id_producto,
                models.InventarioSede.id_sede == orden.id_sede
            ).first()

            if inv:
                inv.stock_actual = (inv.stock_actual or 0) + cant_recibida
                inv.precio_compra = det.precio_unitario
                inv.estado_registro = 1
            else:
                inv = models.InventarioSede(
                    id_producto=det.id_producto,
                    id_sede=orden.id_sede,
                    precio_compra=det.precio_unitario,
                    precio_venta=round(det.precio_unitario * 1.30, 2),
                    stock_actual=cant_recibida,
                    stock_minimo=5,
                    estado_registro=1
                )
                db.add(inv)

            # Registrar movimiento de ENTRADA en kardex de almacén
            mov = models.MovimientoAlmacen(
                id_producto=det.id_producto,
                id_sede=orden.id_sede,
                tipo="ENTRADA",
                cantidad=cant_recibida,
                id_usuario=id_usuario,
                observacion=f"Ingreso por Compra {orden.correlativo} - Proveedor: {prov_nombre}"
            )
            db.add(mov)

            prod = det.producto
            prod_nombre = prod.nombre if prod else f"ID {det.id_producto}"
            productos_ingresados.append(f"{prod_nombre} (+{cant_recibida} uds)")

        correlativo_final = orden.correlativo
        db.commit()
        db.close()

        return jsonify({
            "message": f"¡Mercadería de la orden {correlativo_final} recibida exitosamente! Se actualizó el stock en almacén.",
            "correlativo": correlativo_final,
            "estado": "RECIBIDA",
            "productos_ingresados": productos_ingresados
        }), 200

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": f"Error al procesar la recepción de mercadería: {str(e)}"}), 500


@app.route("/api/compras/<int:id_orden>/anular", methods=["POST"])
def anular_orden_compra(id_orden):
    """Anular una orden de compra con reversión segura de stock si ya estaba recibida (HU 21)"""
    user_role = request.headers.get("X-Role", "Administrador")
    if user_role == "Vendedor":
        return jsonify({"error": "Acceso denegado: Vendedores no pueden anular órdenes de compra"}), 403

    db = get_db()
    try:
        orden = db.query(models.OrdenCompra).filter(
            models.OrdenCompra.id_orden_compra == id_orden,
            models.OrdenCompra.estado_registro == 1
        ).first()

        if not orden:
            db.close()
            return jsonify({"error": "Orden de compra no encontrada."}), 404

        if orden.estado == "ANULADA":
            db.close()
            return jsonify({"error": "Esta orden ya se encuentra anulada."}), 400

        data = request.json or {}
        motivo = str(data.get("motivo", "Anulación solicitada por el usuario")).strip()
        id_usuario = data.get("id_usuario") or orden.id_usuario

        # Si ya había sido recibida, debemos revertir el stock de almacén de forma segura
        if orden.estado == "RECIBIDA":
            # Verificar si hay suficiente stock disponible para descontar
            for det in orden.detalles:
                inv = db.query(models.InventarioSede).filter(
                    models.InventarioSede.id_producto == det.id_producto,
                    models.InventarioSede.id_sede == orden.id_sede
                ).first()
                if not inv or inv.stock_actual < (det.cantidad_recibida or det.cantidad_solicitada):
                    prod = det.producto
                    prod_nombre = prod.nombre if prod else f"ID {det.id_producto}"
                    db.close()
                    return jsonify({
                        "error": f"No se puede anular: El producto '{prod_nombre}' ya fue vendido o despachado y no cuenta con suficiente stock en almacén para revertir."
                    }), 400

            # Descontar stock y registrar salida
            for det in orden.detalles:
                cant_a_revertir = det.cantidad_recibida or det.cantidad_solicitada
                inv = db.query(models.InventarioSede).filter(
                    models.InventarioSede.id_producto == det.id_producto,
                    models.InventarioSede.id_sede == orden.id_sede
                ).first()
                if inv:
                    inv.stock_actual -= cant_a_revertir

                mov = models.MovimientoAlmacen(
                    id_producto=det.id_producto,
                    id_sede=orden.id_sede,
                    tipo="SALIDA",
                    cantidad=cant_a_revertir,
                    id_usuario=id_usuario,
                    observacion=f"Reversión por Anulación de Compra {orden.correlativo}. Motivo: {motivo}"
                )
                db.add(mov)

        correlativo_anulada = orden.correlativo
        orden.estado = "ANULADA"
        orden.observacion = (orden.observacion or "") + f" [ANULADA: {motivo}]"
        db.commit()
        db.close()

        return jsonify({
            "message": f"Orden de compra {correlativo_anulada} anulada correctamente.",
            "correlativo": correlativo_anulada,
            "estado": "ANULADA"
        }), 200

    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": f"Error al anular la orden de compra: {str(e)}"}), 500


if __name__ == "__main__":
    try:
        from waitress import serve
        print("[OK] Servidor backend optimizado arrancado en http://localhost:8000 (8 hilos)...")
        serve(app, host="0.0.0.0", port=8000, threads=8)
    except ImportError:
        app.run(port=8000, debug=True)



