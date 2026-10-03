from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text, func
from sqlalchemy.orm import relationship
from database import Base

class Sede(Base):
    __tablename__ = "sedes"
    id_sede = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    direccion = Column(String)
    telefono = Column(String)
    estado_registro = Column(Integer, default=1)

class Perfil(Base):
    __tablename__ = "perfiles"
    id_perfil = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    descripcion = Column(String)
    estado_registro = Column(Integer, default=1)

class UsuarioPerfil(Base):
    __tablename__ = "usuario_perfiles"
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario', ondelete="CASCADE"), primary_key=True)
    id_perfil = Column(Integer, ForeignKey('perfiles.id_perfil', ondelete="CASCADE"), primary_key=True)
    estado_registro = Column(Integer, default=1)

class OpcionMenu(Base):
    __tablename__ = "opciones_menu"
    id_opcion_menu = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    url_menu = Column(String)
    descripcion = Column(String)
    id_padre = Column(Integer, ForeignKey('opciones_menu.id_opcion_menu', ondelete="CASCADE"))
    estado_registro = Column(Integer, default=1)

class OpcionMenuPerfil(Base):
    __tablename__ = "opciones_menu_perfiles"
    id_opcion_menu = Column(Integer, ForeignKey('opciones_menu.id_opcion_menu', ondelete="CASCADE"), primary_key=True)
    id_perfil = Column(Integer, ForeignKey('perfiles.id_perfil', ondelete="CASCADE"), primary_key=True)
    orden = Column(Integer, default=0)
    estado_registro = Column(Integer, default=1)

class User(Base):
    __tablename__ = "usuarios"

    id = Column("id_usuario", Integer, primary_key=True, index=True)
    first_name = Column("nombres", String, default="")
    last_name = Column("apellidos", String, default="")
    username = Column("nombre_usuario", String, index=True)
    email = Column("correo_electronico", String, default="")
    phone = Column("celular", String, default="")
    dni = Column("dni", String, default="")
    gender = Column("genero", String, default="")
    id_sede = Column("id_sede", Integer, ForeignKey('sedes.id_sede'))
    last_access = Column("ultimo_acceso", String, default="Nunca")
    is_active = Column("estado_registro", Integer, default=1)
    password = Column("clave", String, default="admin1234")

    # Relationship to Perfiles
    perfiles = relationship("Perfil", secondary="usuario_perfiles", lazy="joined")
    sede = relationship("Sede")

    @property
    def roles(self):
        if self.perfiles:
            return [perfil.nombre for perfil in self.perfiles]
        return ["Vendedor"]

    @property
    def role(self):
        if self.perfiles and len(self.perfiles) > 0:
            return self.perfiles[0].nombre
        return "Vendedor"

# --- Módulo de Almacén ---

class Categoria(Base):
    __tablename__ = "categorias"
    id_categoria = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    descripcion = Column(String)
    estado_registro = Column(Integer, default=1)

    productos = relationship("Producto", back_populates="categoria")

class Producto(Base):
    __tablename__ = "productos"
    id_producto = Column(Integer, primary_key=True, index=True)
    codigo_producto = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    descripcion = Column(String)
    id_categoria = Column(Integer, ForeignKey('categorias.id_categoria'))
    estado_registro = Column(Integer, default=1)

    categoria = relationship("Categoria", back_populates="productos")
    inventarios = relationship("InventarioSede", back_populates="producto")
    movimientos = relationship("MovimientoAlmacen", back_populates="producto")
    detalles_venta = relationship("DetalleVenta", back_populates="producto")

class InventarioSede(Base):
    __tablename__ = "inventario_sedes"
    id_inventario = Column(Integer, primary_key=True, index=True)
    id_producto = Column(Integer, ForeignKey('productos.id_producto', ondelete="CASCADE"))
    id_sede = Column(Integer, ForeignKey('sedes.id_sede', ondelete="CASCADE"))
    precio_compra = Column(Float, nullable=False)
    precio_venta = Column(Float, nullable=False)
    stock_actual = Column(Integer, default=0)
    stock_minimo = Column(Integer, default=0)
    estado_registro = Column(Integer, default=1)

    producto = relationship("Producto", back_populates="inventarios")
    sede = relationship("Sede")

class MovimientoAlmacen(Base):
    __tablename__ = "movimientos_almacen"
    id_movimiento = Column(Integer, primary_key=True, index=True)
    id_producto = Column(Integer, ForeignKey('productos.id_producto'))
    id_sede = Column(Integer, ForeignKey('sedes.id_sede'))
    tipo = Column(String, nullable=False) # 'ENTRADA', 'SALIDA', 'AJUSTE'
    cantidad = Column(Integer, nullable=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now())
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'))
    observacion = Column(Text)

    producto = relationship("Producto", back_populates="movimientos")
    usuario = relationship("User") 
    sede = relationship("Sede")

# --- Módulo de Ventas ---

class Venta(Base):
    __tablename__ = "ventas"
    id_venta = Column(Integer, primary_key=True, index=True)
    correlativo = Column(String, unique=True, index=True, nullable=False)
    fecha_venta = Column(DateTime(timezone=True), server_default=func.now())
    total = Column(Float, nullable=False)
    metodo_pago = Column(String, nullable=False) # Efectivo, Tarjeta, Yape
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'))
    id_sede = Column(Integer, ForeignKey('sedes.id_sede'))
    estado_registro = Column(Integer, default=1)

    usuario = relationship("User")
    sede = relationship("Sede")
    detalles = relationship("DetalleVenta", back_populates="venta")

class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"
    id_detalle = Column(Integer, primary_key=True, index=True)
    id_venta = Column(Integer, ForeignKey('ventas.id_venta', ondelete="CASCADE"))
    id_producto = Column(Integer, ForeignKey('productos.id_producto'))
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")
