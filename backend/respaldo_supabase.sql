-- =========================================================================
-- SCRIPT DE RESPALDO Y CREACIÓN (VERSIÓN MULTI-SEDE) 
-- PARA BASE DE DATOS SUPABASE
-- Copia todo este texto y pégalo en el "SQL Editor" de tu nuevo Supabase, 
-- luego dale a "Run" para crear las tablas y restaurar tus datos.
-- =========================================================================

-- 0. LIMPIEZA DE TABLAS ANTERIORES (Por si acaso ya existían)
DROP TABLE IF EXISTS detalle_ventas CASCADE;
DROP TABLE IF EXISTS ventas CASCADE;
DROP TABLE IF EXISTS movimientos_almacen CASCADE;
DROP TABLE IF EXISTS inventario_sedes CASCADE;
DROP TABLE IF EXISTS productos CASCADE;
DROP TABLE IF EXISTS categorias CASCADE;
DROP TABLE IF EXISTS opciones_menu_perfiles CASCADE;
DROP TABLE IF EXISTS opciones_menu CASCADE;
DROP TABLE IF EXISTS usuario_perfiles CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;
DROP TABLE IF EXISTS perfiles CASCADE;
DROP TABLE IF EXISTS sedes CASCADE;

-- 1. CREACIÓN DE TABLAS

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
    estado_registro INTEGER DEFAULT 1
);

CREATE TABLE productos (
    id_producto SERIAL PRIMARY KEY,
    codigo_producto VARCHAR UNIQUE NOT NULL,
    nombre VARCHAR NOT NULL,
    descripcion VARCHAR,
    id_categoria INTEGER REFERENCES categorias(id_categoria),
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
    subtotal DOUBLE PRECISION NOT NULL
);


-- 2. RESTAURACIÓN DE DATOS BASE

-- Sedes
INSERT INTO sedes (id_sede, nombre, direccion, telefono, estado_registro) VALUES 
(1, 'Central Los Olivos', 'Av. Central 123, Los Olivos', '01-1234567', 1),
(2, 'Sucursal SJL', 'Av. Próceres 456, SJL', '01-7654321', 1);

-- Perfiles
INSERT INTO perfiles (id_perfil, nombre, descripcion, estado_registro) VALUES 
(1, 'Administrador', 'Control total del sistema', 1),
(2, 'Supervisor', 'Supervisión de vendedores', 1),
(3, 'Vendedor', 'Acceso limitado a ventas', 1);

-- Usuarios (Ahora asignados a un id_sede)
INSERT INTO usuarios (id_usuario, nombres, apellidos, nombre_usuario, correo_electronico, celular, dni, genero, id_sede, clave, ultimo_acceso, estado_registro) VALUES 
(3, 'Denzel Leyton', 'Ccoyllo Siguenza', 'DenzelC', '2024002231@unfv.edu.pe', '999888111', '71528801', 'Masculino', 1, '123456', 'Nunca', 1),
(5, 'Luis Arturo', 'Alvarado Puyen', 'ArturoAP', '2024023935@unfv.edu.pe', '977748394', '74915722', 'Masculino', 2, 'admin1234', 'Nunca', 1),
(1, 'Lenin Allister', 'Alvarez Jara', 'Lenin', '2024023953@untv.edu.pe', '+51 939 949 438', '72644473-6', 'Masculino', 1, '123456', 'Nunca', 1),
(2, 'Juan David', 'Enriquez Coronel', 'JuanD', 'juandavid@gmail.com', '999888777', '9876543', 'Masculino', 2, 'admin1234', 'Nunca', 1);

-- Perfiles por Usuario
INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro) VALUES 
(2, 3, 1),
(5, 1, 1),
(5, 3, 1),
(1, 1, 1),
(1, 3, 1),
(3, 2, 1),
(3, 3, 1);

-- Opciones de Menú (SPA - Se pueden dejar para referencia o acceso lógico)
INSERT INTO opciones_menu (id_opcion_menu, nombre, url_menu, descripcion, id_padre, estado_registro) VALUES 
(1, 'Seguridad', '#', 'Módulo de administración', NULL, 1),
(2, 'Usuarios', 'dashboard.html', 'Gestión de usuarios', 1, 1),
(3, 'Mi Perfil', 'perfil.html', 'Perfil del usuario actual', 1, 1);

INSERT INTO opciones_menu_perfiles (id_opcion_menu, id_perfil, orden, estado_registro) VALUES 
(1, 1, 0, 1),
(2, 1, 0, 1),
(3, 1, 0, 1);


-- 3. AJUSTE DE SECUENCIAS
SELECT setval('sedes_id_sede_seq', (SELECT MAX(id_sede) FROM sedes));
SELECT setval('perfiles_id_perfil_seq', (SELECT MAX(id_perfil) FROM perfiles));
SELECT setval('usuarios_id_usuario_seq', (SELECT MAX(id_usuario) FROM usuarios));
SELECT setval('opciones_menu_id_opcion_menu_seq', (SELECT MAX(id_opcion_menu) FROM opciones_menu));
