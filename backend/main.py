from flask import Flask, request, jsonify
from flask_cors import CORS
from database import engine, SessionLocal
import models
from sqlalchemy.orm import joinedload

try:
    models.Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Error conectando a la BD: {e}")

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

@app.route("/api/categorias", methods=["GET"])
def get_categorias():
    db = get_db()
    categorias = db.query(models.Categoria).filter(models.Categoria.estado_registro == 1).all()
    db.close()
    return jsonify([{"id_categoria": c.id_categoria, "nombre": c.nombre, "descripcion": c.descripcion} for c in categorias])

@app.route("/api/productos", methods=["GET"])
def get_productos():
    # En multi-sede, idealmente consultamos el inventario de la sede del usuario.
    # Por ahora (simplificación frontend actual), traemos todo y mostramos el stock total 
    # o filtramos por sede si nos la envían.
    sede_id = request.args.get("sede_id", type=int)
    db = get_db()
    
    productos = db.query(models.Producto).filter(models.Producto.estado_registro == 1).all()
    result = []
    for p in productos:
        cat_nombre = p.categoria.nombre if p.categoria else "Sin categoría"
        
        # Obtener inventario
        inv = None
        if sede_id:
            inv = db.query(models.InventarioSede).filter(models.InventarioSede.id_producto == p.id_producto, models.InventarioSede.id_sede == sede_id).first()
        else:
            # Si no envían sede, devolvemos el primero (para mantener compatibilidad con interfaz actual)
            inv = db.query(models.InventarioSede).filter(models.InventarioSede.id_producto == p.id_producto).first()
            
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
        
    id_sede = usuario.id_sede
    
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
        total_venta = sum([float(d["cantidad"]) * float(d["precio_unitario"]) for d in detalles])
        
        nueva_venta = models.Venta(
            correlativo=correlativo,
            total=total_venta,
            metodo_pago=data.get("metodo_pago", "Efectivo"),
            id_usuario=id_usuario,
            id_sede=id_sede
        )
        db.add(nueva_venta)
        db.flush() 
        
        # Procesar detalles y descontar stock DE LA SEDE DEL USUARIO
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
                
            # Restar stock
            inventario.stock_actual -= cantidad
            
            # Crear detalle
            nuevo_detalle = models.DetalleVenta(
                id_venta=nueva_venta.id_venta,
                id_producto=producto.id_producto,
                cantidad=cantidad,
                precio_unitario=float(det["precio_unitario"]),
                subtotal=float(det["cantidad"]) * float(det["precio_unitario"])
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

if __name__ == "__main__":
    app.run(port=8000, debug=True)
