from flask import Flask, request, jsonify
from flask_cors import CORS
from database import engine, SessionLocal
import models
from sqlalchemy.orm import joinedload
from sqlalchemy import text

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
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

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

@app.route("/api/productos", methods=["GET"])
def get_productos():
    sede_id = request.args.get("sede_id", type=int)
    db = get_db()
    
    # 1. Cargar todas las categorías en una sola consulta
    todas_categorias = db.query(models.Categoria).all()
    cat_dict = {c.id_categoria: c for c in todas_categorias}
    
    # 2. Cargar el inventario necesario en una sola consulta
    inv_query = db.query(models.InventarioSede)
    if sede_id:
        inv_query = inv_query.filter(models.InventarioSede.id_sede == sede_id)
    inventarios = inv_query.all()
    
    inv_dict = {}
    for inv in inventarios:
        if inv.id_producto not in inv_dict:
            inv_dict[inv.id_producto] = inv
            
    # 3. Cargar todos los productos de una sola vez
    productos = db.query(models.Producto).filter(models.Producto.estado_registro == 1).all()
    result = []
    
    for p in productos:
        cat_nombre = "Sin categoría"
        subcat_nombre = "General"
        
        cat = cat_dict.get(p.id_categoria)
        if cat:
            if cat.id_padre:
                subcat_nombre = cat.nombre
                padre = cat_dict.get(cat.id_padre)
                cat_nombre = padre.nombre if padre else "Sin categoría"
            else:
                cat_nombre = cat.nombre
                subcat_nombre = "General"
        
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
            "id_categoria": p.id_categoria
        })
    db.close()
    return jsonify(result)

@app.route("/api/productos", methods=["POST"])
def create_producto():
    data = request.json
    db = get_db()
    
    # Usuario y Sede que crea
    id_usuario = data.get("id_usuario")
    usuario = db.query(models.User).filter(models.User.id == id_usuario).first()
    if not usuario:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 400
        
    id_sede = usuario.id_sede or 1
    
    # Verificar si el código ya existe
    existe = db.query(models.Producto).filter(models.Producto.codigo_producto == data.get("codigo_producto")).first()
    
    try:
        nuevo_producto = existe
        if not existe:
            nuevo_producto = models.Producto(
                codigo_producto=str(data.get("codigo_producto")).strip(),
                nombre=str(data.get("nombre")).strip(),
                descripcion=data.get("descripcion", ""),
                id_categoria=data.get("id_categoria")
            )
            db.add(nuevo_producto)
            db.flush() # para obtener ID
            
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


if __name__ == "__main__":
    app.run(port=8000, debug=True)

