-- =========================================================================
-- SISTEMA JESMI - SCRIPT MAESTRO DE RESTAURACIÓN Y CREACIÓN COMPLETA
-- Compatible con: Supabase, Neon, Railway y PostgreSQL 14+
-- INSTRUCCIONES:
-- 1. Abre el "SQL Editor" de tu nuevo proyecto de Supabase.
-- 2. Copia y pega TODO este contenido.
-- 3. Haz clic en "RUN". Todas las 20+ tablas y datos quedarán listos.
-- =========================================================================

-- LIMPIEZA INICIAL
DROP TABLE IF EXISTS evaluaciones_proveedores CASCADE;
DROP TABLE IF EXISTS detalle_ordenes_compra CASCADE;
DROP TABLE IF EXISTS ordenes_compra CASCADE;
DROP TABLE IF EXISTS proveedor_productos CASCADE;
DROP TABLE IF EXISTS proveedores CASCADE;
DROP TABLE IF EXISTS promociones CASCADE;
DROP TABLE IF EXISTS detalle_proformas CASCADE;
DROP TABLE IF EXISTS proformas CASCADE;
DROP TABLE IF EXISTS detalle_ventas CASCADE;
DROP TABLE IF EXISTS ventas CASCADE;
DROP TABLE IF EXISTS movimientos_almacen CASCADE;
DROP TABLE IF EXISTS inventario_sedes CASCADE;
DROP TABLE IF EXISTS productos CASCADE;
DROP TABLE IF EXISTS subcategorias CASCADE;
DROP TABLE IF EXISTS categorias CASCADE;
DROP TABLE IF EXISTS opciones_menu_perfiles CASCADE;
DROP TABLE IF EXISTS opciones_menu CASCADE;
DROP TABLE IF EXISTS usuario_perfiles CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;
DROP TABLE IF EXISTS perfiles CASCADE;
DROP TABLE IF EXISTS sedes CASCADE;

-- CREACIÓN DE TABLAS

CREATE TABLE sedes (
    id_sede SERIAL PRIMARY KEY,
    nombre VARCHAR UNIQUE NOT NULL,
    direccion VARCHAR,
    telefono VARCHAR,
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE perfiles (
    id_perfil SERIAL PRIMARY KEY,
    nombre VARCHAR UNIQUE NOT NULL,
    descripcion VARCHAR,
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nombres VARCHAR DEFAULT '',
    apellidos VARCHAR DEFAULT '',
    nombre_usuario VARCHAR,
    correo_electronico VARCHAR DEFAULT '',
    celular VARCHAR DEFAULT '',
    dni VARCHAR DEFAULT '',
    genero VARCHAR DEFAULT '',
    id_sede INTEGER REFERENCES sedes(id_sede),
    ultimo_acceso VARCHAR DEFAULT 'Nunca',
    estado_registro INTEGER DEFAULT 1,
    clave VARCHAR DEFAULT 'admin1234'
);

CREATE TABLE usuario_perfiles (
    id_usuario INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_perfil INTEGER REFERENCES perfiles(id_perfil) ON DELETE CASCADE,
    estado_registro INTEGER DEFAULT 1,
    PRIMARY KEY (id_usuario, id_perfil)
);

CREATE TABLE opciones_menu (
    id_opcion_menu SERIAL PRIMARY KEY,
    nombre VARCHAR NOT NULL,
    url_menu VARCHAR,
    descripcion VARCHAR,
    id_padre INTEGER REFERENCES opciones_menu(id_opcion_menu) ON DELETE CASCADE,
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE opciones_menu_perfiles (
    id_opcion_menu INTEGER REFERENCES opciones_menu(id_opcion_menu) ON DELETE CASCADE,
    id_perfil INTEGER REFERENCES perfiles(id_perfil) ON DELETE CASCADE,
    orden INTEGER DEFAULT 0,
    estado_registro INTEGER DEFAULT 1,
    PRIMARY KEY (id_opcion_menu, id_perfil)
);

CREATE TABLE categorias (
    id_categoria SERIAL PRIMARY KEY,
    nombre VARCHAR UNIQUE NOT NULL,
    descripcion VARCHAR,
    id_padre INTEGER REFERENCES categorias(id_categoria) ON DELETE CASCADE,
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE subcategorias (
    id_subcategoria SERIAL PRIMARY KEY,
    nombre VARCHAR NOT NULL,
    descripcion VARCHAR,
    id_categoria INTEGER REFERENCES categorias(id_categoria) ON DELETE CASCADE,
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE productos (
    id_producto SERIAL PRIMARY KEY,
    codigo_producto VARCHAR UNIQUE NOT NULL,
    nombre VARCHAR NOT NULL,
    descripcion VARCHAR,
    id_categoria INTEGER REFERENCES categorias(id_categoria),
    id_subcategoria INTEGER REFERENCES subcategorias(id_subcategoria),
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE inventario_sedes (
    id_inventario SERIAL PRIMARY KEY,
    id_producto INTEGER REFERENCES productos(id_producto) ON DELETE CASCADE,
    id_sede INTEGER REFERENCES sedes(id_sede) ON DELETE CASCADE,
    precio_compra DOUBLE PRECISION NOT NULL,
    precio_venta DOUBLE PRECISION NOT NULL,
    stock_actual INTEGER DEFAULT 0,
    stock_minimo INTEGER DEFAULT 0,
    estado_registro INTEGER DEFAULT 1,
    UNIQUE(id_producto, id_sede)
);

CREATE TABLE movimientos_almacen (
    id_movimiento SERIAL PRIMARY KEY,
    id_producto INTEGER REFERENCES productos(id_producto),
    id_sede INTEGER REFERENCES sedes(id_sede),
    tipo VARCHAR NOT NULL,
    cantidad INTEGER NOT NULL,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    observacion TEXT
);

CREATE TABLE ventas (
    id_venta SERIAL PRIMARY KEY,
    correlativo VARCHAR UNIQUE NOT NULL,
    fecha_venta TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total DOUBLE PRECISION NOT NULL,
    descuento_total DOUBLE PRECISION DEFAULT 0.0,
    metodo_pago VARCHAR NOT NULL,
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    id_sede INTEGER REFERENCES sedes(id_sede),
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE detalle_ventas (
    id_detalle SERIAL PRIMARY KEY,
    id_venta INTEGER REFERENCES ventas(id_venta) ON DELETE CASCADE,
    id_producto INTEGER REFERENCES productos(id_producto),
    cantidad INTEGER NOT NULL,
    precio_unitario DOUBLE PRECISION NOT NULL,
    descuento_unitario DOUBLE PRECISION DEFAULT 0.0,
    subtotal DOUBLE PRECISION NOT NULL
);

CREATE TABLE proformas (
    id_proforma SERIAL PRIMARY KEY,
    correlativo VARCHAR UNIQUE NOT NULL,
    fecha_emision TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    validez_dias INTEGER DEFAULT 7,
    cliente_nombre VARCHAR DEFAULT 'Cliente General',
    cliente_doc VARCHAR DEFAULT '',
    total DOUBLE PRECISION NOT NULL,
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    id_sede INTEGER REFERENCES sedes(id_sede),
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE detalle_proformas (
    id_detalle_proforma SERIAL PRIMARY KEY,
    id_proforma INTEGER REFERENCES proformas(id_proforma) ON DELETE CASCADE,
    id_producto INTEGER REFERENCES productos(id_producto),
    cantidad INTEGER NOT NULL,
    precio_unitario DOUBLE PRECISION NOT NULL,
    subtotal DOUBLE PRECISION NOT NULL
);

CREATE TABLE promociones (
    id_promocion SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tipo_descuento VARCHAR(20) NOT NULL DEFAULT 'PORCENTAJE',
    valor DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    aplica_a VARCHAR(20) NOT NULL DEFAULT 'TODOS',
    id_sede INTEGER REFERENCES sedes(id_sede) ON DELETE SET NULL,
    id_categoria INTEGER REFERENCES categorias(id_categoria) ON DELETE SET NULL,
    id_producto INTEGER REFERENCES productos(id_producto) ON DELETE SET NULL,
    fecha_inicio VARCHAR(10) NOT NULL,
    fecha_fin VARCHAR(10) NOT NULL,
    estado_registro INTEGER DEFAULT 1,
    id_usuario_creador INTEGER REFERENCES usuarios(id_usuario),
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE proveedores (
    id_proveedor SERIAL PRIMARY KEY,
    id_sede INTEGER REFERENCES sedes(id_sede),
    ruc VARCHAR(20) NOT NULL,
    razon_social VARCHAR(150) NOT NULL,
    nombre_contacto VARCHAR(100) DEFAULT '',
    telefono VARCHAR(30) DEFAULT '',
    correo VARCHAR(120) DEFAULT '',
    direccion VARCHAR(250) DEFAULT '',
    condiciones_pago VARCHAR(80) NOT NULL DEFAULT 'Contado',
    estado_registro INTEGER DEFAULT 1,
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE proveedor_productos (
    id_proveedor_producto SERIAL PRIMARY KEY,
    id_proveedor INTEGER REFERENCES proveedores(id_proveedor) ON DELETE CASCADE,
    id_producto INTEGER REFERENCES productos(id_producto) ON DELETE CASCADE,
    precio_compra DOUBLE PRECISION NOT NULL,
    codigo_proveedor VARCHAR(50) DEFAULT '',
    estado_registro INTEGER DEFAULT 1,
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ordenes_compra (
    id_orden_compra SERIAL PRIMARY KEY,
    correlativo VARCHAR(30) UNIQUE NOT NULL,
    id_proveedor INTEGER REFERENCES proveedores(id_proveedor),
    id_sede INTEGER REFERENCES sedes(id_sede),
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    fecha_emision TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fecha_esperada VARCHAR(15) DEFAULT '',
    fecha_recepcion TIMESTAMP WITH TIME ZONE,
    estado VARCHAR(25) DEFAULT 'PENDIENTE',
    total DOUBLE PRECISION DEFAULT 0.0,
    observacion TEXT DEFAULT '',
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE detalle_ordenes_compra (
    id_detalle_oc SERIAL PRIMARY KEY,
    id_orden_compra INTEGER REFERENCES ordenes_compra(id_orden_compra) ON DELETE CASCADE,
    id_producto INTEGER REFERENCES productos(id_producto),
    cantidad_solicitada INTEGER NOT NULL,
    cantidad_recibida INTEGER DEFAULT 0,
    precio_unitario DOUBLE PRECISION NOT NULL,
    subtotal DOUBLE PRECISION NOT NULL
);

CREATE TABLE evaluaciones_proveedores (
    id_evaluacion SERIAL PRIMARY KEY,
    id_proveedor INTEGER REFERENCES proveedores(id_proveedor) ON DELETE CASCADE,
    id_orden_compra INTEGER REFERENCES ordenes_compra(id_orden_compra) ON DELETE SET NULL,
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    calificacion INTEGER NOT NULL,
    puntualidad INTEGER DEFAULT 5,
    calidad INTEGER DEFAULT 5,
    observaciones TEXT NOT NULL,
    fecha_evaluacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    estado_registro INTEGER DEFAULT 1
);

-- INSERCIÓN DE DATOS DE NEGOCIO

-- Sedes
INSERT INTO sedes (id_sede, nombre, direccion, telefono, estado_registro) VALUES (1, 'Central Los Olivos', 'Av. Central 123, Los Olivos', '01-1234567', 1);
INSERT INTO sedes (id_sede, nombre, direccion, telefono, estado_registro) VALUES (2, 'Sucursal SJL', 'Av. Próceres 456, SJL', '01-7654321', 1);

-- Perfiles
INSERT INTO perfiles (id_perfil, nombre, descripcion, estado_registro) VALUES (1, 'Administrador', 'Control total del sistema', 1);
INSERT INTO perfiles (id_perfil, nombre, descripcion, estado_registro) VALUES (2, 'Supervisor', 'Supervisión de vendedores', 1);
INSERT INTO perfiles (id_perfil, nombre, descripcion, estado_registro) VALUES (3, 'Vendedor', 'Acceso limitado a ventas', 1);

-- Usuarios
INSERT INTO usuarios (id_usuario, nombres, apellidos, nombre_usuario, correo_electronico, celular, dni, genero, id_sede, ultimo_acceso, estado_registro, clave) VALUES (1, 'Lenin Allister', 'Alvarez Jara', 'Lenin', '2024023953@untv.edu.pe', '+51 939 949 438', '72644473', 'Masculino', 1, 'Nunca', 1, '123456');
INSERT INTO usuarios (id_usuario, nombres, apellidos, nombre_usuario, correo_electronico, celular, dni, genero, id_sede, ultimo_acceso, estado_registro, clave) VALUES (2, 'Juan David', 'Enriquez Coronel', 'JuanD', 'juandavid@gmail.com', '999888777', '98765432', 'Masculino', 2, 'Nunca', 1, 'admin1234');
INSERT INTO usuarios (id_usuario, nombres, apellidos, nombre_usuario, correo_electronico, celular, dni, genero, id_sede, ultimo_acceso, estado_registro, clave) VALUES (3, 'Denzel Leyton', 'Ccoyllo Siguenza', 'DenzelC', '2024002231@unfv.edu.pe', '999888111', '71528801', 'Masculino', 1, 'Nunca', 1, '123456');
INSERT INTO usuarios (id_usuario, nombres, apellidos, nombre_usuario, correo_electronico, celular, dni, genero, id_sede, ultimo_acceso, estado_registro, clave) VALUES (5, 'Luis Arturo', 'Alvarado Puyen', 'ArturoAP', '2024023935@unfv.edu.pe', '977748394', '74915722', 'Masculino', 2, 'Nunca', 1, 'admin1234');

-- Usuario Perfiles
INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro) VALUES (1, 1, 1);
INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro) VALUES (1, 3, 1);
INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro) VALUES (2, 3, 1);
INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro) VALUES (3, 2, 1);
INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro) VALUES (3, 3, 1);
INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro) VALUES (5, 1, 1);
INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro) VALUES (5, 3, 1);

-- Opciones de Menú
INSERT INTO opciones_menu (id_opcion_menu, nombre, url_menu, descripcion, id_padre, estado_registro) VALUES (1, 'Seguridad', '#', 'Módulo de administración', NULL, 1);
INSERT INTO opciones_menu (id_opcion_menu, nombre, url_menu, descripcion, id_padre, estado_registro) VALUES (2, 'Usuarios', 'dashboard.html', 'Gestión de usuarios', 1, 1);
INSERT INTO opciones_menu (id_opcion_menu, nombre, url_menu, descripcion, id_padre, estado_registro) VALUES (3, 'Mi Perfil', 'perfil.html', 'Perfil del usuario actual', 1, 1);
INSERT INTO opciones_menu_perfiles (id_opcion_menu, id_perfil, orden, estado_registro) VALUES (1, 1, 0, 1);
INSERT INTO opciones_menu_perfiles (id_opcion_menu, id_perfil, orden, estado_registro) VALUES (2, 1, 0, 1);
INSERT INTO opciones_menu_perfiles (id_opcion_menu, id_perfil, orden, estado_registro) VALUES (3, 1, 0, 1);

-- Categorías Principales
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (1, 'Herramientas Manuales', 'Martillos, destornilladores, alicates, etc.', NULL, 1);
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (2, 'Herramientas Eléctricas', 'Taladros, sierras, esmeriladoras.', NULL, 1);
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (3, 'Materiales de Construcción', 'Cemento, arena, ladrillos.', NULL, 1);
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (4, 'Pinturas y Acabados', 'Pinturas, brochas, rodillos, solventes.', NULL, 1);
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (5, 'Fontanería y Gas', 'Tubos, conexiones, grifería.', NULL, 1);
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (6, 'Electricidad e Iluminación', 'Cables, focos, interruptores.', NULL, 1);
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (7, 'Tornillería y Fijaciones', 'Clavos, tornillos, tuercas, tacos.', NULL, 1);
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (8, 'Seguridad y Protección', 'Cascos, guantes, lentes, botas.', NULL, 1);
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (9, 'Adhesivos y Selladores', 'Pegamentos, siliconas, cintas.', NULL, 1);
INSERT INTO categorias (id_categoria, nombre, descripcion, id_padre, estado_registro) VALUES (10, 'Jardinería', 'Mangueras, palas, abonos.', NULL, 1);

-- Subcategorías
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (1, 'Martillos y Combas', 'Subcategoría de 1', 1, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (2, 'Alicates y Tenazas', 'Subcategoría de 1', 1, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (3, 'Destornilladores y Llaves', 'Subcategoría de 1', 1, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (4, 'Taladros y Rotomartillos', 'Subcategoría de 2', 2, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (5, 'Amoladoras y Esmeriles', 'Subcategoría de 2', 2, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (6, 'Sierras y Cortadoras', 'Subcategoría de 2', 2, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (7, 'Cemento y Agregados', 'Subcategoría de 3', 3, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (8, 'Ladrillos y Bloques', 'Subcategoría de 3', 3, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (9, 'Fierros y Varillas', 'Subcategoría de 3', 3, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (10, 'Pinturas Látex', 'Subcategoría de 4', 4, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (11, 'Esmaltes Sintéticos', 'Subcategoría de 4', 4, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (12, 'Brochas y Rodillos', 'Subcategoría de 4', 4, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (13, 'Thinner y Disolventes', 'Subcategoría de 4', 4, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (14, 'Tubos y Conexiones PVC', 'Subcategoría de 5', 5, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (15, 'Grifería y Llaves', 'Subcategoría de 5', 5, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (16, 'Accesorios para Gas', 'Subcategoría de 5', 5, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (17, 'Cables y Conductores', 'Subcategoría de 6', 6, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (18, 'Tomacorrientes e Llaves Térmicas', 'Subcategoría de 6', 6, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (19, 'Focos y Luminarias LED', 'Subcategoría de 6', 6, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (20, 'Tornillos y Pijas', 'Subcategoría de 7', 7, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (21, 'Pernos y Tuercas', 'Subcategoría de 7', 7, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (22, 'Tarugos y Anclajes', 'Subcategoría de 7', 7, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (23, 'Cascos y Guantes', 'Subcategoría de 8', 8, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (24, 'Calzado y Lentes de Seguridad', 'Subcategoría de 8', 8, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (25, 'Siliconas y Masillas', 'Subcategoría de 9', 9, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (26, 'Pegamentos y Colas', 'Subcategoría de 9', 9, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (27, 'Mangueras y Aspersores', 'Subcategoría de 10', 10, 1);
INSERT INTO subcategorias (id_subcategoria, nombre, descripcion, id_categoria, estado_registro) VALUES (28, 'Herramientas de Jardín', 'Subcategoría de 10', 10, 1);

-- 100 Productos e Inventarios Multi-Sede
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (1, 'PR-MAN-001', 'Martillo de uña 16oz', 'Martillo de uña 16oz de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (1, 1, 1, 62.91, 78.95, 32, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (2, 1, 2, 62.91, 78.95, 25, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (2, 'PR-MAN-002', 'Destornillador Phillips', 'Destornillador Phillips de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (3, 2, 1, 25.87, 36.15, 58, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (4, 2, 2, 25.87, 36.15, 44, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (3, 'PR-MAN-003', 'Destornillador Plano', 'Destornillador Plano de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (5, 3, 1, 13.74, 18.33, 16, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (6, 3, 2, 13.74, 18.33, 15, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (4, 'PR-MAN-004', 'Alicate Universal', 'Alicate Universal de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (7, 4, 1, 25.46, 34.4, 16, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (8, 4, 2, 25.46, 34.4, 45, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (5, 'PR-MAN-005', 'Alicate de corte', 'Alicate de corte de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (9, 5, 1, 23.7, 32.71, 49, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (10, 5, 2, 23.7, 32.71, 36, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (6, 'PR-MAN-006', 'Llave Inglesa 10 pulgadas', 'Llave Inglesa 10 pulgadas de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (11, 6, 1, 25.62, 35.04, 15, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (12, 6, 2, 25.62, 35.04, 20, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (7, 'PR-MAN-007', 'Cinta Métrica 5m', 'Cinta Métrica 5m de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (13, 7, 1, 68.13, 89.8, 24, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (14, 7, 2, 68.13, 89.8, 23, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (8, 'PR-MAN-008', 'Nivel de burbuja', 'Nivel de burbuja de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (15, 8, 1, 91.19, 120.13, 20, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (16, 8, 2, 91.19, 120.13, 34, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (9, 'PR-MAN-009', 'Serrucho para madera', 'Serrucho para madera de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (17, 9, 1, 14.61, 20.74, 53, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (18, 9, 2, 14.61, 20.74, 26, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (10, 'PR-MAN-010', 'Juego de llaves Allen', 'Juego de llaves Allen de alta resistencia y durabilidad.', 1, 1, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (19, 10, 1, 77.83, 108.65, 49, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (20, 10, 2, 77.83, 108.65, 17, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (11, 'PR-ELE-001', 'Taladro Percutor 700W', 'Taladro Percutor 700W de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (21, 11, 1, 92.61, 122.77, 50, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (22, 11, 2, 92.61, 122.77, 28, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (12, 'PR-ELE-002', 'Amoladora Angular 4 1/2', 'Amoladora Angular 4 1/2 de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (23, 12, 1, 79.82, 109.65, 38, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (24, 12, 2, 79.82, 109.65, 22, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (13, 'PR-ELE-003', 'Sierra Circular 1500W', 'Sierra Circular 1500W de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (25, 13, 1, 68.71, 86.52, 29, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (26, 13, 2, 68.71, 86.52, 28, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (14, 'PR-ELE-004', 'Taladro Inalámbrico 20V', 'Taladro Inalámbrico 20V de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (27, 14, 1, 93.68, 133.13, 21, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (28, 14, 2, 93.68, 133.13, 34, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (15, 'PR-ELE-005', 'Lijadora Orbital', 'Lijadora Orbital de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (29, 15, 1, 30.74, 42.33, 38, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (30, 15, 2, 30.74, 42.33, 20, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (16, 'PR-ELE-006', 'Pistola de Calor', 'Pistola de Calor de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (31, 16, 1, 38.95, 50.32, 32, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (32, 16, 2, 38.95, 50.32, 14, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (17, 'PR-ELE-007', 'Sierra Caladora', 'Sierra Caladora de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (33, 17, 1, 60.21, 77.32, 30, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (34, 17, 2, 60.21, 77.32, 20, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (18, 'PR-ELE-008', 'Rotomartillo', 'Rotomartillo de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (35, 18, 1, 47.14, 61.47, 55, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (36, 18, 2, 47.14, 61.47, 45, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (19, 'PR-ELE-009', 'Sopladora', 'Sopladora de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (37, 19, 1, 25.55, 33.59, 18, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (38, 19, 2, 25.55, 33.59, 24, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (20, 'PR-ELE-010', 'Atornillador Eléctrico', 'Atornillador Eléctrico de alta resistencia y durabilidad.', 2, 4, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (39, 20, 1, 79.14, 111.67, 40, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (40, 20, 2, 79.14, 111.67, 27, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (21, 'PR-CON-001', 'Bolsa de Cemento 42.5kg', 'Bolsa de Cemento 42.5kg de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (41, 21, 1, 11.89, 17.03, 51, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (42, 21, 2, 11.89, 17.03, 30, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (22, 'PR-CON-002', 'Varilla de Fierro 1/2', 'Varilla de Fierro 1/2 de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (43, 22, 1, 24.92, 33.64, 56, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (44, 22, 2, 24.92, 33.64, 39, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (23, 'PR-CON-003', 'Ladrillo King Kong 18 huecos', 'Ladrillo King Kong 18 huecos de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (45, 23, 1, 18.72, 23.92, 50, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (46, 23, 2, 18.72, 23.92, 44, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (24, 'PR-CON-004', 'Arena Fina x saco', 'Arena Fina x saco de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (47, 24, 1, 29.38, 40.16, 52, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (48, 24, 2, 29.38, 40.16, 35, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (25, 'PR-CON-005', 'Arena Gruesa x saco', 'Arena Gruesa x saco de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (49, 25, 1, 38.22, 55.4, 23, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (50, 25, 2, 38.22, 55.4, 42, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (26, 'PR-CON-006', 'Piedra Chancada 1/2', 'Piedra Chancada 1/2 de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (51, 26, 1, 49.92, 69.95, 22, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (52, 26, 2, 49.92, 69.95, 19, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (27, 'PR-CON-007', 'Yeso en bolsa 25kg', 'Yeso en bolsa 25kg de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (53, 27, 1, 61.84, 87.1, 42, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (54, 27, 2, 61.84, 87.1, 14, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (28, 'PR-CON-008', 'Alambre cocido #16', 'Alambre cocido #16 de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (55, 28, 1, 40.24, 55.1, 44, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (56, 28, 2, 40.24, 55.1, 43, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (29, 'PR-CON-009', 'Pegamento para cerámicos', 'Pegamento para cerámicos de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (57, 29, 1, 28.38, 38.62, 15, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (58, 29, 2, 28.38, 38.62, 17, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (30, 'PR-CON-010', 'Fragua gris', 'Fragua gris de alta resistencia y durabilidad.', 3, 7, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (59, 30, 1, 66.67, 90.5, 32, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (60, 30, 2, 66.67, 90.5, 31, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (31, 'PR-PIN-001', 'Pintura Látex Blanco 1gl', 'Pintura Látex Blanco 1gl de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (61, 31, 1, 15.93, 21.3, 44, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (62, 31, 2, 15.93, 21.3, 10, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (32, 'PR-PIN-002', 'Pintura Esmalte Sintético Negro 1gl', 'Pintura Esmalte Sintético Negro 1gl de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (63, 32, 1, 90.89, 129.53, 31, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (64, 32, 2, 90.89, 129.53, 42, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (33, 'PR-PIN-003', 'Brocha 2 pulgadas', 'Brocha 2 pulgadas de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (65, 33, 1, 73.81, 99.76, 21, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (66, 33, 2, 73.81, 99.76, 29, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (34, 'PR-PIN-004', 'Brocha 4 pulgadas', 'Brocha 4 pulgadas de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (67, 34, 1, 80.91, 109.35, 27, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (68, 34, 2, 80.91, 109.35, 19, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (35, 'PR-PIN-005', 'Rodillo de espuma 9 pulgadas', 'Rodillo de espuma 9 pulgadas de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (69, 35, 1, 39.28, 50.37, 48, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (70, 35, 2, 39.28, 50.37, 10, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (36, 'PR-PIN-006', 'Thinner Acrílico 1gl', 'Thinner Acrílico 1gl de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (71, 36, 1, 59.31, 79.93, 22, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (72, 36, 2, 59.31, 79.93, 33, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (37, 'PR-PIN-007', 'Aguarrás 1gl', 'Aguarrás 1gl de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (73, 37, 1, 84.21, 119.27, 34, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (74, 37, 2, 84.21, 119.27, 25, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (38, 'PR-PIN-008', 'Lija al agua #180', 'Lija al agua #180 de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (75, 38, 1, 11.16, 15.91, 20, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (76, 38, 2, 11.16, 15.91, 15, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (39, 'PR-PIN-009', 'Lija al agua #220', 'Lija al agua #220 de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (77, 39, 1, 71.14, 100.54, 49, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (78, 39, 2, 71.14, 100.54, 18, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (40, 'PR-PIN-010', 'Pasta mural 1gl', 'Pasta mural 1gl de alta resistencia y durabilidad.', 4, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (79, 40, 1, 17.43, 23.44, 50, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (80, 40, 2, 17.43, 23.44, 20, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (41, 'PR-FON-001', 'Tubo PVC Agua 1/2', 'Tubo PVC Agua 1/2 de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (81, 41, 1, 29.59, 42.15, 42, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (82, 41, 2, 29.59, 42.15, 23, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (42, 'PR-FON-002', 'Codo PVC 1/2', 'Codo PVC 1/2 de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (83, 42, 1, 88.67, 124.23, 59, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (84, 42, 2, 88.67, 124.23, 22, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (43, 'PR-FON-003', 'Tee PVC 1/2', 'Tee PVC 1/2 de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (85, 43, 1, 69.45, 92.35, 57, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (86, 43, 2, 69.45, 92.35, 33, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (44, 'PR-FON-004', 'Pegamento PVC 1/4gl', 'Pegamento PVC 1/4gl de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (87, 44, 1, 44.99, 60.89, 22, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (88, 44, 2, 44.99, 60.89, 25, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (45, 'PR-FON-005', 'Cinta Teflón', 'Cinta Teflón de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (89, 45, 1, 26.0, 34.26, 52, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (90, 45, 2, 26.0, 34.26, 45, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (46, 'PR-FON-006', 'Llave de paso 1/2', 'Llave de paso 1/2 de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (91, 46, 1, 26.48, 34.27, 19, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (92, 46, 2, 26.48, 34.27, 13, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (47, 'PR-FON-007', 'Tubo CPVC 1/2', 'Tubo CPVC 1/2 de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (93, 47, 1, 26.38, 37.75, 36, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (94, 47, 2, 26.38, 37.75, 14, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (48, 'PR-FON-008', 'Caño para lavadero', 'Caño para lavadero de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (95, 48, 1, 51.76, 67.58, 46, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (96, 48, 2, 51.76, 67.58, 23, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (49, 'PR-FON-009', 'Válvula Check', 'Válvula Check de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (97, 49, 1, 53.99, 75.3, 51, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (98, 49, 2, 53.99, 75.3, 40, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (50, 'PR-FON-010', 'Manguera de abasto 1/2', 'Manguera de abasto 1/2 de alta resistencia y durabilidad.', 5, 14, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (99, 50, 1, 27.63, 37.15, 41, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (100, 50, 2, 27.63, 37.15, 22, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (51, 'PR-ILU-001', 'Cable THW 14 AWG x metro', 'Cable THW 14 AWG x metro de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (101, 51, 1, 14.39, 19.88, 37, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (102, 51, 2, 14.39, 19.88, 37, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (52, 'PR-ILU-002', 'Cable THW 12 AWG x metro', 'Cable THW 12 AWG x metro de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (103, 52, 1, 42.59, 60.6, 18, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (104, 52, 2, 42.59, 60.6, 16, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (53, 'PR-ILU-003', 'Interruptor Simple', 'Interruptor Simple de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (105, 53, 1, 11.39, 15.9, 21, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (106, 53, 2, 11.39, 15.9, 25, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (54, 'PR-ILU-004', 'Tomacorriente Doble', 'Tomacorriente Doble de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (107, 54, 1, 23.05, 31.28, 23, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (108, 54, 2, 23.05, 31.28, 37, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (55, 'PR-ILU-005', 'Foco LED 12W', 'Foco LED 12W de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (109, 55, 1, 22.33, 29.98, 19, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (110, 55, 2, 22.33, 29.98, 38, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (56, 'PR-ILU-006', 'Foco LED 18W', 'Foco LED 18W de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (111, 56, 1, 77.91, 110.73, 21, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (112, 56, 2, 77.91, 110.73, 13, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (57, 'PR-ILU-007', 'Cinta Aislante Negra', 'Cinta Aislante Negra de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (113, 57, 1, 64.04, 86.97, 15, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (114, 57, 2, 64.04, 86.97, 15, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (58, 'PR-ILU-008', 'Llave Termomagnética 2x16A', 'Llave Termomagnética 2x16A de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (115, 58, 1, 88.45, 125.58, 25, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (116, 58, 2, 88.45, 125.58, 36, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (59, 'PR-ILU-009', 'Caja Octogonal', 'Caja Octogonal de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (117, 59, 1, 49.22, 63.63, 40, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (118, 59, 2, 49.22, 63.63, 13, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (60, 'PR-ILU-010', 'Tubo Corrugado 20mm', 'Tubo Corrugado 20mm de alta resistencia y durabilidad.', 6, 17, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (119, 60, 1, 20.65, 25.82, 39, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (120, 60, 2, 20.65, 25.82, 26, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (61, 'PR-FIJ-001', 'Clavo para madera 2 pulgadas (kg)', 'Clavo para madera 2 pulgadas (kg) de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (121, 61, 1, 88.46, 124.47, 33, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (122, 61, 2, 88.46, 124.47, 37, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (62, 'PR-FIJ-002', 'Clavo para calamina', 'Clavo para calamina de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (123, 62, 1, 68.0, 94.93, 50, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (124, 62, 2, 68.0, 94.93, 41, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (63, 'PR-FIJ-003', 'Tornillo Drywall 1 1/4 (ciento)', 'Tornillo Drywall 1 1/4 (ciento) de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (125, 63, 1, 19.78, 25.9, 18, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (126, 63, 2, 19.78, 25.9, 44, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (64, 'PR-FIJ-004', 'Tarugo plástico 1/4', 'Tarugo plástico 1/4 de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (127, 64, 1, 11.43, 15.0, 18, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (128, 64, 2, 11.43, 15.0, 40, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (65, 'PR-FIJ-005', 'Tirafón 1/4 x 2', 'Tirafón 1/4 x 2 de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (129, 65, 1, 50.75, 72.09, 25, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (130, 65, 2, 50.75, 72.09, 13, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (66, 'PR-FIJ-006', 'Arandela plana 1/4', 'Arandela plana 1/4 de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (131, 66, 1, 91.51, 115.85, 26, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (132, 66, 2, 91.51, 115.85, 14, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (67, 'PR-FIJ-007', 'Tuerca hexagonal 1/4', 'Tuerca hexagonal 1/4 de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (133, 67, 1, 58.96, 81.66, 30, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (134, 67, 2, 58.96, 81.66, 35, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (68, 'PR-FIJ-008', 'Clavo de acero 2 pulgadas', 'Clavo de acero 2 pulgadas de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (135, 68, 1, 16.67, 23.81, 30, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (136, 68, 2, 16.67, 23.81, 12, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (69, 'PR-FIJ-009', 'Remache pop 1/8', 'Remache pop 1/8 de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (137, 69, 1, 61.12, 81.52, 52, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (138, 69, 2, 61.12, 81.52, 43, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (70, 'PR-FIJ-010', 'Gancho J para calamina', 'Gancho J para calamina de alta resistencia y durabilidad.', 7, 20, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (139, 70, 1, 34.16, 44.48, 57, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (140, 70, 2, 34.16, 44.48, 30, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (71, 'PR-SEG-001', 'Casco de seguridad Amarillo', 'Casco de seguridad Amarillo de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (141, 71, 1, 27.24, 36.21, 57, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (142, 71, 2, 27.24, 36.21, 29, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (72, 'PR-SEG-002', 'Guantes de cuero', 'Guantes de cuero de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (143, 72, 1, 46.69, 67.04, 19, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (144, 72, 2, 46.69, 67.04, 10, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (73, 'PR-SEG-003', 'Guantes de nitrilo', 'Guantes de nitrilo de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (145, 73, 1, 46.79, 67.83, 21, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (146, 73, 2, 46.79, 67.83, 14, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (74, 'PR-SEG-004', 'Lentes de seguridad transparentes', 'Lentes de seguridad transparentes de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (147, 74, 1, 53.85, 72.76, 23, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (148, 74, 2, 53.85, 72.76, 32, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (75, 'PR-SEG-005', 'Mascarilla N95', 'Mascarilla N95 de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (149, 75, 1, 84.4, 120.34, 38, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (150, 75, 2, 84.4, 120.34, 28, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (76, 'PR-SEG-006', 'Tapones de oído', 'Tapones de oído de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (151, 76, 1, 20.04, 28.39, 60, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (152, 76, 2, 20.04, 28.39, 29, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (77, 'PR-SEG-007', 'Chaleco reflectivo', 'Chaleco reflectivo de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (153, 77, 1, 60.44, 87.48, 56, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (154, 77, 2, 60.44, 87.48, 43, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (78, 'PR-SEG-008', 'Botas de jebe talla 40', 'Botas de jebe talla 40 de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (155, 78, 1, 6.7, 9.47, 34, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (156, 78, 2, 6.7, 9.47, 16, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (79, 'PR-SEG-009', 'Botas punta de acero talla 42', 'Botas punta de acero talla 42 de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (157, 79, 1, 89.56, 114.36, 22, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (158, 79, 2, 89.56, 114.36, 16, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (80, 'PR-SEG-010', 'Cinta de peligro 200m', 'Cinta de peligro 200m de alta resistencia y durabilidad.', 8, 23, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (159, 80, 1, 72.08, 92.34, 33, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (160, 80, 2, 72.08, 92.34, 23, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (81, 'PR-ADH-001', 'Silicona Transparente tubo', 'Silicona Transparente tubo de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (161, 81, 1, 69.87, 90.18, 55, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (162, 81, 2, 69.87, 90.18, 26, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (82, 'PR-ADH-002', 'Pegamento Soldimix', 'Pegamento Soldimix de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (163, 82, 1, 50.98, 66.29, 18, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (164, 82, 2, 50.98, 66.29, 15, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (83, 'PR-ADH-003', 'Triz', 'Triz de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (165, 83, 1, 62.45, 88.42, 17, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (166, 83, 2, 62.45, 88.42, 10, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (84, 'PR-ADH-004', 'Cinta Masking 1 pulgada', 'Cinta Masking 1 pulgada de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (167, 84, 1, 35.69, 45.55, 31, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (168, 84, 2, 35.69, 45.55, 20, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (85, 'PR-ADH-005', 'Cinta de embalaje transparente', 'Cinta de embalaje transparente de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (169, 85, 1, 71.97, 97.9, 42, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (170, 85, 2, 71.97, 97.9, 45, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (86, 'PR-ADH-006', 'Espuma de Poliuretano', 'Espuma de Poliuretano de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (171, 86, 1, 6.86, 8.68, 59, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (172, 86, 2, 6.86, 8.68, 19, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (87, 'PR-ADH-007', 'Pegamento de contacto africano', 'Pegamento de contacto africano de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (173, 87, 1, 54.56, 77.31, 52, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (174, 87, 2, 54.56, 77.31, 45, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (88, 'PR-ADH-008', 'Silicona acética blanca', 'Silicona acética blanca de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (175, 88, 1, 19.18, 24.46, 34, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (176, 88, 2, 19.18, 24.46, 33, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (89, 'PR-ADH-009', 'Cinta doble faz', 'Cinta doble faz de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (177, 89, 1, 86.01, 121.21, 17, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (178, 89, 2, 86.01, 121.21, 32, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (90, 'PR-ADH-010', 'Adhesivo de montaje', 'Adhesivo de montaje de alta resistencia y durabilidad.', 9, 25, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (179, 90, 1, 24.7, 32.11, 21, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (180, 90, 2, 24.7, 32.11, 32, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (91, 'PR-JAR-001', 'Manguera reforzada 15m', 'Manguera reforzada 15m de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (181, 91, 1, 75.43, 107.63, 41, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (182, 91, 2, 75.43, 107.63, 19, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (92, 'PR-JAR-002', 'Pistola de riego', 'Pistola de riego de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (183, 92, 1, 88.39, 114.67, 25, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (184, 92, 2, 88.39, 114.67, 21, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (93, 'PR-JAR-003', 'Pico con mango', 'Pico con mango de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (185, 93, 1, 84.45, 105.98, 36, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (186, 93, 2, 84.45, 105.98, 36, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (94, 'PR-JAR-004', 'Pala cuadrada', 'Pala cuadrada de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (187, 94, 1, 77.4, 110.13, 30, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (188, 94, 2, 77.4, 110.13, 27, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (95, 'PR-JAR-005', 'Tijera de podar', 'Tijera de podar de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (189, 95, 1, 20.17, 28.04, 39, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (190, 95, 2, 20.17, 28.04, 12, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (96, 'PR-JAR-006', 'Tierra de chacra x saco', 'Tierra de chacra x saco de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (191, 96, 1, 82.41, 106.68, 44, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (192, 96, 2, 82.41, 106.68, 32, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (97, 'PR-JAR-007', 'Abono Urea 1kg', 'Abono Urea 1kg de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (193, 97, 1, 33.16, 46.72, 29, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (194, 97, 2, 33.16, 46.72, 24, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (98, 'PR-JAR-008', 'Insecticida para plantas', 'Insecticida para plantas de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (195, 98, 1, 8.11, 10.45, 36, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (196, 98, 2, 8.11, 10.45, 27, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (99, 'PR-JAR-009', 'Maceta plástica nro 20', 'Maceta plástica nro 20 de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (197, 99, 1, 82.93, 119.7, 32, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (198, 99, 2, 82.93, 119.7, 32, 10, 1);
INSERT INTO productos (id_producto, codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro) VALUES (100, 'PR-JAR-010', 'Rastrillo de acero', 'Rastrillo de acero de alta resistencia y durabilidad.', 10, 27, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (199, 100, 1, 63.09, 83.91, 49, 10, 1);
INSERT INTO inventario_sedes (id_inventario, id_producto, id_sede, precio_compra, precio_venta, stock_actual, stock_minimo, estado_registro) VALUES (200, 100, 2, 63.09, 83.91, 31, 10, 1);

-- Directorio de Proveedores
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (1, 1, '20100010724', 'CORPORACION ACEROS AREQUIPA S.A.', 'Carlos Paredes', '01-5171800', 'ventas@acerosarequipa.com', 'Av. Enrique Meiggs 297, Callao', 'Credito 30 dias', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (2, 2, '20100010725', 'ACEROS AREQUIPA DISTRIBUCION', 'Rosa Quispe', '01-5171801', 'distribucion@acerosarequipa.com', 'Av. Próceres 1200, SJL', 'Contado', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (3, 1, '20100138981', 'EMPRESA SIDERURGICA DEL PERU S.A.A. (SIDERPERU)', 'Jorge Mendoza', '01-6186000', 'contacto@siderperu.com.pe', 'Av. Juan de Arona 151, San Isidro', 'Credito 15 dias', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (4, 1, '20100142822', 'MEXICHEM PERU S.A. (PAVCO)', 'Ana Maria Torres', '01-6276100', 'ventas.peru@pavco.com', 'Av. Nicolas de Pierola 750, Ate', 'Credito 30 dias', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (5, 2, '20100070972', 'CEMENTOS PACASMAYO S.A.A.', 'Luis Alberto Rios', '01-3176000', 'pacasmayo@cpacasmayo.com.pe', 'Calle La Colonia 180, Surco', 'Contado', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (6, 1, '20100047211', 'UNION DE CONCRETERAS S.A. (UNICON)', 'Patricia Vega', '01-2154600', 'pedidos@unicon.com.pe', 'Carretera Panamericana Sur Km 11.4', 'Credito 30 dias', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (7, 2, '20100109968', 'PRODUCTOS TISUR Y FIJACIONES S.A.', 'Guillermo Chavez', '01-4445566', 'fijaciones@tisur.com', 'Av. Industrial 555, Lima', 'Contado', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (8, 1, '20501827361', 'DISTRIBUIDORA FERRETERA CENTRAL S.A.C.', 'Elena Benites', '01-3329988', 'contacto@ferreteracentral.pe', 'Av. Colonial 1280, Lima', 'Credito 15 dias', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (9, 1, '20504789123', 'DISTRIBUIDORA FERRETERA DEL NORTE S.A.C.', 'Manuel Rojas', '01-5238899', 'ventas@ferreteranorte.com', 'Av. Universitaria 3450, Los Olivos', 'Credito 15 dias', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (10, 1, '20485961234', 'PINTURAS Y RECUBRIMIENTOS OLIVOS E.I.R.L.', 'Sonia Morales', '01-5287744', 'contacto@pinturasolivos.pe', 'Av. Las Palmeras 120, Los Olivos', 'Contado', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (11, 1, '20394857122', 'TUBOPLAST & VALVULAS NORTE S.A.C.', 'Ernesto Silva', '01-5341122', 'pedidos@tuboplastnorte.com', 'Av. Canta Callao 890, S.M.P.', 'Credito 30 dias', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (12, 1, '20593847111', 'HERRAMIENTAS PROFESIONALES OLIVOS S.A.C.', 'Fernando Castro', '01-5219900', 'contacto@herramientaspro.pe', 'Av. Antúnez de Mayolo 1420, Los Olivos', 'Contado', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (13, 2, '20192837465', 'CEMENTOS Y AGREGADOS SAN JUAN S.A.C.', 'Victor Hugo Flores', '01-3881144', 'ventas@cementossanjuan.pe', 'Av. Fernando Wiesse 2100, SJL', 'Contado', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (14, 2, '20601928374', 'DISTRIBUCIONES ELECTRICAS & CABLES SJL S.A.C.', 'Monica Estrada', '01-3765588', 'ventas@electricassjl.com', 'Av. Gran Chimú 980, Zárate, SJL', 'Credito 15 dias', 1);
INSERT INTO proveedores (id_proveedor, id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro) VALUES (15, 2, '20491827365', 'MATERIALES Y FIERROS EL CHINO S.A.C.', 'Arturo Chang', '01-3874422', 'ventaselchino@gmail.com', 'Av. Las Flores de Primavera 1540, SJL', 'Contado', 1);

-- Catálogo de Productos por Proveedor
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (1, 1, 12, 42.5, 'AA-VAR-12', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (2, 1, 18, 15.5, 'AA-ALAM-16', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (3, 1, 51, 6.5, 'AA-CLAV-MAD', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (4, 1, 52, 7.8, 'AA-CLAV-CAL', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (5, 1, 58, 8.2, 'AA-CLAV-ACE', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (6, 1, 60, 1.2, 'AA-GAN-J', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (7, 3, 12, 41.5, 'SID-VAR-12', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (8, 3, 18, 14.8, 'SID-ALAM-16', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (9, 3, 19, 18.5, 'SID-PEG-CER', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (10, 3, 51, 6.3, 'SID-CLAV-MAD', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (11, 3, 56, 0.25, 'SID-ARAN-14', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (12, 3, 57, 0.45, 'SID-TUERCA-14', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (13, 4, 31, 14.5, 'PAV-TUB-12', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (14, 4, 32, 2.2, 'PAV-COD-12', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (15, 4, 33, 2.8, 'PAV-TEE-12', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (16, 4, 34, 18.5, 'PAV-PEG-14', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (17, 4, 35, 1.5, 'PAV-TEF-01', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (18, 4, 36, 12.0, 'PAV-PASO-12', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (19, 4, 37, 18.0, 'PAV-CPVC-12', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (20, 4, 38, 24.5, 'PAV-CANO-LAV', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (21, 9, 1, 18.5, 'DFN-MART-16', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (22, 9, 2, 6.5, 'DFN-DEST-PH', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (23, 9, 3, 6.5, 'DFN-DEST-PL', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (24, 9, 4, 16.0, 'DFN-ALIC-UNI', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (25, 9, 6, 26.0, 'DFN-LLAV-ING', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (26, 9, 7, 9.0, 'DFN-WIN-5M', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (27, 9, 71, 10.5, 'DFN-SIL-TRP', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (28, 9, 72, 8.5, 'DFN-SOLDIMIX', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (29, 9, 73, 4.0, 'DFN-TRIZ', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (30, 10, 21, 38.0, 'PIN-LAT-BLA', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (31, 10, 22, 44.0, 'PIN-ESM-NEG', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (32, 10, 23, 4.5, 'PIN-BRO-2', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (33, 10, 24, 8.5, 'PIN-BRO-4', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (34, 10, 25, 12.0, 'PIN-ROD-ESP', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (35, 10, 26, 26.5, 'PIN-THI-ACR', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (36, 13, 11, 26.5, 'CSJ-CEM-SOL', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (37, 13, 13, 0.95, 'CSJ-LAD-KK', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (38, 13, 14, 38.0, 'CSJ-ARE-FIN', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (39, 13, 15, 34.0, 'CSJ-ARE-GRU', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (40, 13, 16, 42.0, 'CSJ-PIE-CHA', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (41, 13, 17, 14.5, 'CSJ-YESO-25', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (42, 14, 41, 1.8, 'DEC-THW-14', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (43, 14, 42, 2.6, 'DEC-THW-12', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (44, 14, 43, 5.5, 'DEC-INT-SIM', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (45, 14, 44, 7.8, 'DEC-TOM-DOB', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (46, 14, 45, 6.5, 'DEC-FOC-12W', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (47, 14, 46, 9.8, 'DEC-FOC-18W', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (48, 14, 47, 3.2, 'DEC-CIN-AIS', 1);
INSERT INTO proveedor_productos (id_proveedor_producto, id_proveedor, id_producto, precio_compra, codigo_proveedor, estado_registro) VALUES (49, 14, 48, 28.5, 'DEC-LLAV-TM', 1);

-- Ventas e Historial
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (1, 'B001-01001', '2026-11-12 15:41:01', 105.23, 0.0, 'Efectivo', 1, 1, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (2, 'B002-01002', '2026-11-11 14:41:01', 140.62, 0.0, 'Efectivo', 2, 2, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (3, 'B001-01003', '2026-11-10 13:41:01', 109.85, 0.0, 'Yape', 3, 1, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (4, 'B002-01004', '2026-11-09 12:41:01', 111.46, 0.0, 'Efectivo', 5, 2, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (5, 'B001-01005', '2026-11-08 11:41:01', 129.44, 0.0, 'Tarjeta', 1, 1, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (6, 'B002-01006', '2026-11-07 10:41:01', 86.09, 0.0, 'Yape', 5, 2, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (7, 'B001-01007', '2026-11-12 09:41:01', 132.8, 0.0, 'Tarjeta', 3, 1, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (8, 'B002-01008', '2026-11-11 08:41:01', 127.14, 0.0, 'Yape', 5, 2, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (9, 'B001-01009', '2026-11-10 07:41:01', 84.6, 0.0, 'Tarjeta', 1, 1, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (10, 'B002-01010', '2026-11-09 06:41:01', 122.86, 0.0, 'Tarjeta', 5, 2, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (11, 'B001-01011', '2026-11-08 05:41:01', 84.68, 0.0, 'Yape', 1, 1, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (12, 'B002-01012', '2026-11-07 04:41:01', 52.82, 0.0, 'Efectivo', 5, 2, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (13, 'B001-01013', '2026-11-12 03:41:01', 94.81, 0.0, 'Efectivo', 1, 1, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (14, 'B002-01014', '2026-11-11 02:41:01', 140.02, 0.0, 'Tarjeta', 5, 2, 1);
INSERT INTO ventas (id_venta, correlativo, fecha_venta, total, descuento_total, metodo_pago, id_usuario, id_sede, estado_registro) VALUES (15, 'B001-01015', '2026-11-10 01:41:01', 77.75, 0.0, 'Efectivo', 3, 1, 1);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (1, 1, 2, 2, 35.32, 0.0, 70.64);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (2, 1, 3, 1, 34.59, 0.0, 34.59);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (3, 2, 5, 3, 27.1, 0.0, 81.3);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (4, 2, 6, 2, 29.66, 0.0, 59.32);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (5, 3, 8, 3, 28.48, 0.0, 85.44);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (6, 3, 9, 1, 24.41, 0.0, 24.41);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (7, 4, 11, 3, 15.06, 0.0, 45.18);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (8, 4, 12, 2, 33.14, 0.0, 66.28);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (9, 5, 14, 2, 48.21, 0.0, 96.42);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (10, 5, 15, 1, 33.02, 0.0, 33.02);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (11, 6, 17, 1, 32.75, 0.0, 32.75);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (12, 6, 18, 2, 26.67, 0.0, 53.34);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (13, 7, 20, 3, 34.4, 0.0, 103.2);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (14, 7, 21, 2, 14.8, 0.0, 29.6);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (15, 8, 23, 3, 36.54, 0.0, 109.62);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (16, 8, 24, 1, 17.52, 0.0, 17.52);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (17, 9, 26, 2, 30.05, 0.0, 60.1);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (18, 9, 27, 1, 24.5, 0.0, 24.5);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (19, 10, 29, 2, 38.65, 0.0, 77.3);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (20, 10, 30, 2, 22.78, 0.0, 45.56);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (21, 11, 32, 1, 33.04, 0.0, 33.04);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (22, 11, 33, 2, 25.82, 0.0, 51.64);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (23, 12, 35, 1, 22.86, 0.0, 22.86);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (24, 12, 36, 2, 14.98, 0.0, 29.96);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (25, 13, 38, 1, 36.39, 0.0, 36.39);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (26, 13, 39, 2, 29.21, 0.0, 58.42);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (27, 14, 41, 3, 40.14, 0.0, 120.42);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (28, 14, 42, 1, 19.6, 0.0, 19.6);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (29, 15, 44, 1, 46.24, 0.0, 46.24);
INSERT INTO detalle_ventas (id_detalle, id_venta, id_producto, cantidad, precio_unitario, descuento_unitario, subtotal) VALUES (30, 15, 45, 1, 31.51, 0.0, 31.51);

-- AJUSTE DE SECUENCIAS POSTGRESQL (Para que los IDs automáticos continúen sin error)
SELECT setval('sedes_id_sede_seq', COALESCE((SELECT MAX(id_sede) FROM sedes), 1));
SELECT setval('perfiles_id_perfil_seq', COALESCE((SELECT MAX(id_perfil) FROM perfiles), 1));
SELECT setval('usuarios_id_usuario_seq', COALESCE((SELECT MAX(id_usuario) FROM usuarios), 1));
SELECT setval('opciones_menu_id_opcion_menu_seq', COALESCE((SELECT MAX(id_opcion_menu) FROM opciones_menu), 1));
SELECT setval('categorias_id_categoria_seq', COALESCE((SELECT MAX(id_categoria) FROM categorias), 1));
SELECT setval('subcategorias_id_subcategoria_seq', COALESCE((SELECT MAX(id_subcategoria) FROM subcategorias), 1));
SELECT setval('productos_id_producto_seq', COALESCE((SELECT MAX(id_producto) FROM productos), 1));
SELECT setval('inventario_sedes_id_inventario_seq', COALESCE((SELECT MAX(id_inventario) FROM inventario_sedes), 1));
SELECT setval('proveedores_id_proveedor_seq', COALESCE((SELECT MAX(id_proveedor) FROM proveedores), 1));
SELECT setval('proveedor_productos_id_proveedor_producto_seq', COALESCE((SELECT MAX(id_proveedor_producto) FROM proveedor_productos), 1));
SELECT setval('ventas_id_venta_seq', COALESCE((SELECT MAX(id_venta) FROM ventas), 1));
SELECT setval('detalle_ventas_id_detalle_seq', COALESCE((SELECT MAX(id_detalle) FROM detalle_ventas), 1));

-- FIN DEL SCRIPT. BASE DE DATOS RESTAURADA CON ÉXITO.
