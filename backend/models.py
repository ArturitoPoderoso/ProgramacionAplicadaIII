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

# Modelos de categorias, subcategorias, productos e inventario por sede

class Categoria(Base):
    __tablename__ = "categorias"
    id_categoria = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    descripcion = Column(String)
    id_padre = Column(Integer, ForeignKey('categorias.id_categoria', ondelete="CASCADE"), nullable=True)
    estado_registro = Column(Integer, default=1)

    productos = relationship("Producto", back_populates="categoria")
    subcategorias = relationship("Subcategoria", back_populates="categoria", cascade="all, delete-orphan")

class Subcategoria(Base):
    __tablename__ = "subcategorias"
    id_subcategoria = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(String)
    id_categoria = Column(Integer, ForeignKey('categorias.id_categoria', ondelete="CASCADE"), nullable=False)
    estado_registro = Column(Integer, default=1)

    categoria = relationship("Categoria", back_populates="subcategorias")
    productos = relationship("Producto", back_populates="subcategoria_rel")

class Producto(Base):
    __tablename__ = "productos"
    id_producto = Column(Integer, primary_key=True, index=True)
    codigo_producto = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    descripcion = Column(String)
    id_categoria = Column(Integer, ForeignKey('categorias.id_categoria'), nullable=True)
    id_subcategoria = Column(Integer, ForeignKey('subcategorias.id_subcategoria'), nullable=True)
    estado_registro = Column(Integer, default=1)

    categoria = relationship("Categoria", back_populates="productos")
    subcategoria_rel = relationship("Subcategoria", back_populates="productos")
    inventarios = relationship("InventarioSede", back_populates="producto")
    movimientos = relationship("MovimientoAlmacen", back_populates="producto")
    detalles_venta = relationship("DetalleVenta", back_populates="producto")


class InventarioSede(Base):
    __tablename__ = "inventario_sedes"
    id_inventario = Column(Integer, primary_key=True, index=True)
    id_producto = Column(Integer, ForeignKey('productos.id_producto', ondelete="CASCADE"), index=True)
    id_sede = Column(Integer, ForeignKey('sedes.id_sede', ondelete="CASCADE"), index=True)
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
    id_producto = Column(Integer, ForeignKey('productos.id_producto'), index=True)
    id_sede = Column(Integer, ForeignKey('sedes.id_sede'), index=True)
    tipo = Column(String, nullable=False) # 'ENTRADA', 'SALIDA', 'AJUSTE'
    cantidad = Column(Integer, nullable=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'))
    observacion = Column(Text)

    producto = relationship("Producto", back_populates="movimientos")
    usuario = relationship("User") 
    sede = relationship("Sede")

# Modelos de clientes del negocio

class Cliente(Base):
    __tablename__ = "clientes"
    id_cliente = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String(20), default="DNI") # DNI, RUC, CE
    numero_documento = Column(String(20), unique=True, index=True, nullable=False)
    nombre = Column("nombre", String(150), nullable=False)
    telefono = Column(String(30), default="")
    estado_registro = Column(Integer, default=1)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())

    # Propiedad para mantener compatibilidad con nombres_razon_social
    @property
    def nombres_razon_social(self):
        return self.nombre

    @nombres_razon_social.setter
    def nombres_razon_social(self, value):
        self.nombre = value

    ventas = relationship("Venta", back_populates="cliente")
    proformas = relationship("Proforma", back_populates="cliente")

# Modelos de ventas y detalle de comprobantes

class Venta(Base):
    __tablename__ = "ventas"
    id_venta = Column(Integer, primary_key=True, index=True)
    correlativo = Column(String, unique=True, index=True, nullable=False)
    fecha_venta = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    total = Column(Float, nullable=False)
    descuento_total = Column(Float, default=0.0)
    metodo_pago = Column(String, nullable=False) # Efectivo, Tarjeta, Yape
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), index=True)
    id_sede = Column(Integer, ForeignKey('sedes.id_sede'), index=True)
    id_cliente = Column(Integer, ForeignKey('clientes.id_cliente', ondelete="SET NULL"), nullable=True)
    cliente_nombre = Column(String(150), default="Cliente General")
    cliente_doc = Column(String(30), default="")
    estado_registro = Column(Integer, default=1)

    usuario = relationship("User")
    sede = relationship("Sede")
    cliente = relationship("Cliente", back_populates="ventas")
    detalles = relationship("DetalleVenta", back_populates="venta")

class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"
    id_detalle = Column(Integer, primary_key=True, index=True)
    id_venta = Column(Integer, ForeignKey('ventas.id_venta', ondelete="CASCADE"), index=True)
    id_producto = Column(Integer, ForeignKey('productos.id_producto'), index=True)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    descuento_unitario = Column(Float, default=0.0)
    subtotal = Column(Float, nullable=False)

    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")

# Modelos de cotizaciones y proformas

class Proforma(Base):
    __tablename__ = "proformas"
    id_proforma = Column(Integer, primary_key=True, index=True)
    correlativo = Column(String, unique=True, index=True, nullable=False)
    fecha_emision = Column(DateTime(timezone=True), server_default=func.now())
    validez_dias = Column(Integer, default=7)
    id_cliente = Column(Integer, ForeignKey('clientes.id_cliente', ondelete="SET NULL"), nullable=True)
    cliente_nombre = Column(String, default="Cliente General")
    cliente_doc = Column(String, default="")
    total = Column(Float, nullable=False)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'))
    id_sede = Column(Integer, ForeignKey('sedes.id_sede'))
    estado_registro = Column(Integer, default=1)

    usuario = relationship("User")
    sede = relationship("Sede")
    cliente = relationship("Cliente", back_populates="proformas")
    detalles = relationship("DetalleProforma", back_populates="proforma")

class DetalleProforma(Base):
    __tablename__ = "detalle_proformas"
    id_detalle_proforma = Column(Integer, primary_key=True, index=True)
    id_proforma = Column(Integer, ForeignKey('proformas.id_proforma', ondelete="CASCADE"))
    id_producto = Column(Integer, ForeignKey('productos.id_producto'))
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    proforma = relationship("Proforma", back_populates="detalles")
    producto = relationship("Producto")


# Modelos de promociones y descuentos temporales

class Promocion(Base):
    __tablename__ = "promociones"
    id_promocion = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    tipo_descuento = Column(String(20), nullable=False, default="PORCENTAJE")
    valor = Column(Float, nullable=False, default=0.0)
    aplica_a = Column(String(20), nullable=False, default="TODOS")
    id_sede = Column(Integer, ForeignKey('sedes.id_sede', ondelete="SET NULL"), nullable=True)
    id_categoria = Column(Integer, ForeignKey('categorias.id_categoria', ondelete="SET NULL"), nullable=True)
    id_producto = Column(Integer, ForeignKey('productos.id_producto', ondelete="SET NULL"), nullable=True)
    fecha_inicio = Column(String(10), nullable=False)
    fecha_fin = Column(String(10), nullable=False)
    estado_registro = Column(Integer, default=1)
    id_usuario_creador = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    sede = relationship("Sede")
    categoria = relationship("Categoria")
    producto = relationship("Producto")
    creador = relationship("User")


# Modelos de proveedores, ordenes de compra y evaluaciones

class Proveedor(Base):
    __tablename__ = "proveedores"
    id_proveedor = Column(Integer, primary_key=True, index=True)
    id_sede = Column(Integer, ForeignKey('sedes.id_sede'), nullable=True)
    ruc = Column(String(20), index=True, nullable=False)
    razon_social = Column(String(150), nullable=False)
    nombre_contacto = Column(String(100), default="")
    telefono = Column(String(30), default="")
    correo = Column(String(120), default="")
    direccion = Column(String(250), default="")
    condiciones_pago = Column(String(80), nullable=False, default="Contado")
    estado_registro = Column(Integer, default=1)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())

    sede = relationship("Sede")
    productos_asociados = relationship("ProveedorProducto", back_populates="proveedor", cascade="all, delete-orphan")
    ordenes_compra = relationship("OrdenCompra", back_populates="proveedor")
    evaluaciones = relationship("EvaluacionProveedor", back_populates="proveedor", cascade="all, delete-orphan")


class ProveedorProducto(Base):
    __tablename__ = "proveedor_productos"
    id_proveedor_producto = Column(Integer, primary_key=True, index=True)
    id_proveedor = Column(Integer, ForeignKey('proveedores.id_proveedor', ondelete="CASCADE"), nullable=False, index=True)
    id_producto = Column(Integer, ForeignKey('productos.id_producto', ondelete="CASCADE"), nullable=False, index=True)
    precio_compra = Column(Float, nullable=False)
    codigo_proveedor = Column(String(50), default="")
    estado_registro = Column(Integer, default=1)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())

    proveedor = relationship("Proveedor", back_populates="productos_asociados")
    producto = relationship("Producto")


class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"
    id_orden_compra = Column(Integer, primary_key=True, index=True)
    correlativo = Column(String(30), unique=True, index=True, nullable=False)
    id_proveedor = Column(Integer, ForeignKey('proveedores.id_proveedor'), nullable=False, index=True)
    id_sede = Column(Integer, ForeignKey('sedes.id_sede'), nullable=False, index=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    fecha_emision = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    fecha_esperada = Column(String(15), default="")
    fecha_recepcion = Column(DateTime(timezone=True), nullable=True)
    estado = Column(String(25), default="PENDIENTE", index=True)  # PENDIENTE, RECIBIDA, ANULADA
    total = Column(Float, default=0.0)
    observacion = Column(Text, default="")
    estado_registro = Column(Integer, default=1)

    proveedor = relationship("Proveedor", back_populates="ordenes_compra")
    sede = relationship("Sede")
    usuario = relationship("User")
    detalles = relationship("DetalleOrdenCompra", back_populates="orden_compra", cascade="all, delete-orphan")
    evaluaciones = relationship("EvaluacionProveedor", back_populates="orden_compra")


class DetalleOrdenCompra(Base):
    __tablename__ = "detalle_ordenes_compra"
    id_detalle_oc = Column(Integer, primary_key=True, index=True)
    id_orden_compra = Column(Integer, ForeignKey('ordenes_compra.id_orden_compra', ondelete="CASCADE"), nullable=False, index=True)
    id_producto = Column(Integer, ForeignKey('productos.id_producto'), nullable=False, index=True)
    cantidad_solicitada = Column(Integer, nullable=False)
    cantidad_recibida = Column(Integer, default=0)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    orden_compra = relationship("OrdenCompra", back_populates="detalles")
    producto = relationship("Producto")


class EvaluacionProveedor(Base):
    __tablename__ = "evaluaciones_proveedores"
    id_evaluacion = Column(Integer, primary_key=True, index=True)
    id_proveedor = Column(Integer, ForeignKey('proveedores.id_proveedor', ondelete="CASCADE"), nullable=False)
    id_orden_compra = Column(Integer, ForeignKey('ordenes_compra.id_orden_compra', ondelete="SET NULL"), nullable=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    calificacion = Column(Integer, nullable=False)  # 1 a 5
    puntualidad = Column(Integer, default=5)
    calidad = Column(Integer, default=5)
    observaciones = Column(Text, nullable=False)
    fecha_evaluacion = Column(DateTime(timezone=True), server_default=func.now())
    estado_registro = Column(Integer, default=1)

    proveedor = relationship("Proveedor", back_populates="evaluaciones")
    orden_compra = relationship("OrdenCompra", back_populates="evaluaciones")
    usuario = relationship("User")



