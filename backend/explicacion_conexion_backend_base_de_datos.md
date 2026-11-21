# Arquitectura de Conexión Backend a Base de Datos - Sistema Jesmi
## Sistema 100% Basado en Procedimientos Almacenados y Funciones PL/pgSQL (0% ORM - 0% SQL Embebido)

---

### Ficha Técnica del Proyecto
* **Proyecto:** Sistema Jesmi - ERP de Gestión Comercial, Almacén, Ventas y Facturación Electrónica.
* **Base de Datos:** PostgreSQL 15+ gestionado en la nube a través de **Supabase**.
* **Host de Conexión:** `aws-0-us-east-1.pooler.supabase.com:6543/postgres` (Connection Pooler de Alta Disponibilidad).
* **Backend:** Python 3.12 / Flask RESTful API.
* **Paradigma de Acceso a Datos:** **Database-First / RPC (Remote Procedure Calls)**.
* **Estado de Cumplimiento:** **0% ORM (Object-Relational Mapping eliminado), 0% consultas SQL dinámicas en código Python**.
* **Archivo SQL Maestro:** `backend/stored_procedures.sql` (Contiene las 43 rutinas compiladas en PostgreSQL).

---

## 1. Contexto y Justificación de la Arquitectura

### 1.1 ¿Por qué se eliminó el ORM y las consultas SQL sueltas en el Backend?
En arquitecturas de software empresarial e ingeniería de bases de datos, delegar la lógica de negocio a un **ORM (Object-Relational Mapping)** o escribir sentencias SQL directas en el código de aplicación (como `SELECT ... FROM ... WHERE ...` o `db.session.add(...)`) introduce serios riesgos y desventajas que fueron subsanados en este proyecto:

1. **Eliminación Total de Vulnerabilidades de Inyección SQL (SQL Injection):**
   * *El problema:* Cuando el backend concatena o construye sentencias SQL en memoria, un atacante puede alterar la sintaxis de la consulta mediante entradas manipuladas.
   * *Nuestra solución:* El backend **únicamente ejecuta llamadas a procedimientos y funciones precompiladas** (`CALL sp_...` o `SELECT * FROM fn_...`). Los datos se transmiten como **parámetros binarios fuertemente tipados** (`:param`). El motor de PostgreSQL nunca interpreta los datos del usuario como código ejecutable.

2. **Atomicidad e Integridad Transaccional Real (Propiedades ACID):**
   * *El problema:* Operaciones críticas como una **Venta** requieren: (a) verificar stock en almacén, (b) descontar inventario, (c) generar el número correlativo de comprobante, (d) insertar la cabecera de venta, (e) insertar cada ítem del detalle y (f) registrar auditoría. Si esto se hace desde Python mediante un ORM, un fallo de red o caída del servidor entre el paso (b) y (d) deja la base de datos corrupta con "stock fantasma" descontado sin comprobante.
   * *Nuestra solución:* Todo ocurre dentro del motor de base de datos en un bloque atómico `BEGIN ... EXCEPTION ... ROLLBACK; END;` dentro del procedimiento `sp_procesar_venta`. Si cualquier ítem falla, PostgreSQL hace un rollback automático inmediato en memoria.

3. **Prevención de Concurrencia y Condiciones de Carrera (Race Conditions):**
   * En ventas simultáneas del mismo producto por diferentes cajeros, las funciones aplican bloqueos pesimistas de fila (`SELECT ... FOR UPDATE`), garantizando que dos usuarios no puedan vender el último stock disponible al mismo milisegundo.

4. **Rendimiento de Red y Solución al Problema N+1 Queries:**
   * Un ORM tradicional realiza entre 10 y 25 viajes de red (round-trips) para registrar una sola venta compleja (múltiples `SELECT`, múltiples `INSERT`).
   * Con nuestra arquitectura, el backend envía **un único payload JSON en 1 solo viaje de red**. PostgreSQL procesa la estructura JSON internamente a velocidad nativa en microsegundos.

5. **Principio de Mínimo Privilegio y Seguridad de Capas:**
   * El backend no necesita permisos de escritura directa (`INSERT`, `UPDATE`, `DELETE`) sobre las tablas físicas. Solo requiere permisos de ejecución (`EXECUTE`) sobre los Procedimientos Almacenados y Funciones autorizadas.

---

## 2. Diagrama de la Arquitectura de Conexión

```mermaid
flowchart TD
    subgraph Frontend["Capa de Presentación (Frontend)"]
        UI["React / Web Browser"]
    end

    subgraph Backend["Capa de Aplicación (Backend Flask)"]
        Routes["Rutas Flask (/api/ventas, /api/compras, etc.)"]
        DBDriver["SQLAlchemy Core (Solo Driver de Conexión y Pool)"]
        Env[".env (DATABASE_URL con SSL)"]
    end

    subgraph Supabase["Motor de Base de Datos (Supabase Cloud PostgreSQL)"]
        Pooler["PgBouncer Pooler (Puerto 6543)"]
        SP_FN["43 Stored Procedures & Funciones PL/pgSQL"]
        Tables[("Tablas Físicas de la Base de Datos")]
    end

    UI -->|Petición HTTP JSON| Routes
    Routes -->|Lee Credenciales| Env
    Routes -->|db.execute CALL / SELECT fn| DBDriver
    DBDriver -->|Parámetros Sanitizados :param| Pooler
    Pooler -->|Ejecuta Rutina Compilada| SP_FN
    SP_FN -->|Control Transaccional ACID| Tables
```

---

## 3. Mecanismo de Conexión Backend <-> PostgreSQL

### 3.1 Cadena de Conexión Segura (`backend/.env`)
El backend se comunica con la base de datos mediante una cadena de conexión segura parametrizada en variables de entorno:
```env
DATABASE_URL=postgresql://postgres.azvivaiyiwibuitlwnms:ARTURO4321%40luis@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```
* **Puerto 6543:** Corresponde al Transaction Pooler optimizado de Supabase, que permite reutilizar conexiones concurrentes sin saturar el servidor.

### 3.2 Gestión del Pool de Conexiones (`backend/database.py`)
SQLAlchemy **no se utiliza como ORM**. No existen clases mapeadas ni sesiones de seguimiento de entidades. Se utiliza únicamente como pool de conexiones de alto rendimiento:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuración del motor con validación activa de conexiones (pre-ping)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Detecta y descarta conexiones caídas automáticamente
    pool_size=10,             # Conexiones listas en memoria
    max_overflow=20           # Conexiones adicionales ante picos de demanda
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 3.3 El Patrón de Ejecución Estandarizado en Python
En cada archivo de rutas (`backend/routes/*.py`), la interacción con la base de datos sigue estrictamente dos patrones:

#### Patrón A: Para Operaciones de Escritura / Transaccionales (STORED PROCEDURES)
Se utiliza la instrucción estándar SQL `CALL`, pasando los datos mediante diccionarios enlazados con `:parametro` y confirmando la transacción con `db.commit()`:
```python
# Ejemplo en backend/routes/ventas.py
db.execute(text("""
    CALL sp_procesar_venta(
        :id_sede, :id_usuario, :id_cliente, :tipo_comprobante,
        :forma_pago, :tipo_tarjeta, :efectivo_recibido, :vuelto,
        :total, :subtotal, :igv, CAST(:detalles AS jsonb), :res
    )
"""), {
    "id_sede": id_sede,
    "id_usuario": id_usuario,
    "id_cliente": id_cliente,
    "tipo_comprobante": tipo_comprobante,
    "forma_pago": forma_pago,
    "tipo_tarjeta": data.get("tipo_tarjeta"),
    "efectivo_recibido": data.get("efectivo_recibido", 0),
    "vuelto": data.get("vuelto", 0),
    "total": data.get("total", 0),
    "subtotal": data.get("subtotal", 0),
    "igv": data.get("igv", 0),
    "detalles": json.dumps(data.get("detalles", [])),
    "res": None
})
db.commit()
```

#### Patrón B: Para Consultas y Lectura de Datos (FUNCIONES PL/pgSQL)
Se utiliza `SELECT * FROM nombre_funcion(:parametro)`, transformando los registros devueltos en diccionarios limpios con `.mappings().all()`:
```python
# Ejemplo en backend/routes/almacen.py
resultado = db.execute(
    text("SELECT * FROM fn_listar_productos_sede(:id_sede)"),
    {"id_sede": id_sede}
).mappings().all()

productos = [dict(row) for row in resultado]
return jsonify(productos)
```

---

## 4. Catálogo Detallado de los 43 Stored Procedures y Funciones

Todas las rutinas fueron diseñadas en lenguaje **PL/pgSQL**, probadas, optimizadas y activadas en Supabase:

### 4.1 Módulo de Ventas y Facturación
| Nombre | Tipo | Parámetros | Tablas Afectadas | Lógica de Negocio y Responsabilidad |
| :--- | :--- | :--- | :--- | :--- |
| `sp_procesar_venta` | PROCEDURE | Sede, Usuario, Cliente, TipoComprobante, FormaPago, Tarjeta, Efectivo, Vuelto, Total, Subtotal, IGV, Detalles (JSONB), OUT res | `ventas`, `ventas_detalle`, `inventario_sede`, `comprobantes_pago` | **Núcleo de Facturación:** Valida stock por producto con bloqueo, genera número de comprobante, descuenta inventario en la sede correspondiente, crea cabecera y detalle de venta de forma atómica. |
| `sp_anular_venta` | PROCEDURE | id_venta, id_usuario, motivo, OUT res | `ventas`, `inventario_sede`, `comprobantes_pago` | Anula la venta y el comprobante asociado. **Reversa automáticamente el inventario**, devolviendo las unidades vendidas a la sede respectiva. |
| `fn_listar_ventas` | FUNCTION | id_sede, fecha_inicio, fecha_fin, estado | `ventas`, `clientes`, `usuarios`, `comprobantes_pago` | Retorna el historial consolidado de ventas con nombres de cliente, usuario vendedor, estado del comprobante y montos totales filtrados. |
| `fn_obtener_venta_cabecera` | FUNCTION | id_venta | `ventas`, `clientes`, `usuarios`, `comprobantes_pago` | Obtiene la ficha completa de una venta específica para visualización e impresión de tickets/facturas. |
| `fn_obtener_venta_detalle` | FUNCTION | id_venta | `ventas_detalle`, `productos` | Retorna la lista de productos comprados en la venta con código, descripción, cantidad, precio unitario y subtotal. |

### 4.2 Módulo de Almacén e Inventario
| Nombre | Tipo | Parámetros | Tablas Afectadas | Lógica de Negocio y Responsabilidad |
| :--- | :--- | :--- | :--- | :--- |
| `sp_guardar_producto` | PROCEDURE | id_producto, codigo, nombre, descripcion, precio_compra, precio_venta, stock_minimo, id_categoria, id_subcategoria, id_proveedor, id_sede, stock_inicial, OUT res | `productos`, `inventario_sede` | **Operación UPSERT:** Si `id_producto` es nulo, inserta un nuevo producto y genera su registro en `inventario_sede`. Si viene un ID, actualiza las propiedades maestras del producto. |
| `sp_guardar_categoria` | PROCEDURE | id_categoria, nombre, descripcion, OUT res | `categorias` | Inserta o actualiza una categoría de productos validando unicidad. |
| `sp_guardar_subcategoria` | PROCEDURE | id_subcategoria, id_categoria, nombre, descripcion, OUT res | `subcategorias` | Inserta o edita una subcategoría vinculada a su categoría padre. |
| `sp_eliminar_subcategoria` | PROCEDURE | id_subcategoria, OUT res | `subcategorias` | Inactiva o elimina una subcategoría verificando que no posea productos asociados activos. |
| `fn_listar_productos_sede` | FUNCTION | id_sede | `productos`, `inventario_sede`, `categorias`, `subcategorias` | Devuelve el catálogo completo de productos con su stock en tiempo real en la sede seleccionada, categoría y alertas de stock mínimo. |
| `fn_listar_categorias` | FUNCTION | (Ninguno) | `categorias` | Lista todas las categorías activas registradas en el sistema. |
| `fn_listar_subcategorias` | FUNCTION | id_categoria (opcional) | `subcategorias`, `categorias` | Retorna las subcategorías activas, con opción de filtrar por categoría padre. |
| `fn_siguiente_codigo_producto` | FUNCTION | (Ninguno) | `productos` | Calcula atómicamente el siguiente código correlativo de producto (ej. `PROD-00045`) para evitar colisiones. |

### 4.3 Módulo de Clientes
| Nombre | Tipo | Parámetros | Tablas Afectadas | Lógica de Negocio y Responsabilidad |
| :--- | :--- | :--- | :--- | :--- |
| `sp_guardar_cliente` | PROCEDURE | id_cliente, tipo_documento, numero_documento, nombres, apellidos, razon_social, direccion, telefono, email, OUT res | `clientes` | Registra o actualiza la ficha del cliente validando formato de DNI (8 dígitos) o RUC (11 dígitos). |
| `sp_eliminar_cliente` | PROCEDURE | id_cliente, OUT res | `clientes` | Realiza el borrado lógico (`estado_registro = 'INACTIVO'`) protegiendo el historial de ventas previas. |
| `fn_buscar_cliente` | FUNCTION | termino_busqueda | `clientes` | Búsqueda ultra-rápida por coincidencia de documento de identidad, nombre o razón social para autocompletado en caja. |
| `fn_listar_clientes` | FUNCTION | (Ninguno) | `clientes` | Retorna el directorio de clientes activos ordenados alfabéticamente. |
| `fn_obtener_cliente` | FUNCTION | id_cliente | `clientes` | Devuelve la información detallada de un cliente por su identificador primario. |

### 4.4 Módulo de Compras y Abastecimiento
| Nombre | Tipo | Parámetros | Tablas Afectadas | Lógica de Negocio y Responsabilidad |
| :--- | :--- | :--- | :--- | :--- |
| `sp_procesar_compra` | PROCEDURE | Sede, Proveedor, Usuario, TipoComprobante, NroComprobante, Total, Subtotal, IGV, Detalles (JSONB), OUT res | `compras`, `compras_detalle` | Genera una Orden de Compra formal en estado 'REGISTRADA' con sus ítems calculados en formato JSON. |
| `sp_recibir_compra` | PROCEDURE | id_compra, id_usuario, OUT res | `compras`, `inventario_sede`, `productos` | **Ingreso Físico de Mercadería:** Cambia el estado a 'RECIBIDA', incrementa el stock físico en la sede e impacta el costo unitario de compra ponderado. |
| `sp_anular_compra` | PROCEDURE | id_compra, id_usuario, motivo, OUT res | `compras`, `inventario_sede` | Anula la orden. Si la mercadería ya había sido recepcionada, descuenta el stock que había ingresado. |
| `fn_listar_compras` | FUNCTION | id_sede, fecha_inicio, fecha_fin, estado | `compras`, `proveedores`, `usuarios` | Historial de compras con filtro por sucursal, estado y fechas. |
| `fn_obtener_compra_cabecera` | FUNCTION | id_compra | `compras`, `proveedores`, `usuarios` | Datos generales de la compra para verificación o reimpresión de comprobante de ingreso. |
| `fn_obtener_compra_detalle` | FUNCTION | id_compra | `compras_detalle`, `productos` | Desglose de insumos comprados con cantidades y costos pactados. |
| `fn_siguiente_correlativo_oc` | FUNCTION | (Ninguno) | `compras` | Generador del código correlativo de Orden de Compra (`OC-2026-00012`). |

### 4.5 Módulo de Proveedores
| Nombre | Tipo | Parámetros | Tablas Afectadas | Lógica de Negocio y Responsabilidad |
| :--- | :--- | :--- | :--- | :--- |
| `sp_guardar_proveedor` | PROCEDURE | id_proveedor, ruc, razon_social, direccion, telefono, email, contacto_nombre, contacto_telefono, OUT res | `proveedores` | Crea o edita proveedores comerciales con validación de RUC. |
| `sp_eliminar_proveedor` | PROCEDURE | id_proveedor, OUT res | `proveedores` | Da de baja lógica a un proveedor impidiendo nuevas órdenes de compra pero preservando el histórico. |
| `fn_listar_proveedores` | FUNCTION | (Ninguno) | `proveedores`, `evaluaciones_proveedores` | Lista de proveedores con su calificación comercial promedio calculada. |
| `fn_obtener_proveedor` | FUNCTION | id_proveedor | `proveedores` | Obtiene el perfil de un proveedor por ID. |
| `fn_catalogo_proveedor` | FUNCTION | id_proveedor | `productos`, `proveedores` | Filtra los productos suministrados habitualmente por un proveedor específico. |

### 4.6 Módulo de Seguridad, Usuarios y Sedes
| Nombre | Tipo | Parámetros | Tablas Afectadas | Lógica de Negocio y Responsabilidad |
| :--- | :--- | :--- | :--- | :--- |
| `sp_guardar_usuario` | PROCEDURE | id_usuario, nombres, apellidos, username, email, celular, dni, genero, id_sede, clave, OUT res | `usuarios` | Registra o actualiza personal (cajeros, administradores) y vincula su sede de trabajo física. |
| `sp_eliminar_usuario` | PROCEDURE | id_usuario, OUT res | `usuarios` | Inactiva el acceso de un usuario al sistema (`estado_registro = 'INACTIVO'`). |
| `fn_autenticar_usuario` | FUNCTION | p_username | `usuarios`, `sedes` | Consulta segura de credenciales para login: retorna hash de clave, rol, estado activo y datos de su sede asignada. |
| `fn_listar_usuarios` | FUNCTION | (Ninguno) | `usuarios`, `sedes` | Directorio de usuarios con detalle de rol y sucursal. |
| `fn_listar_sedes` | FUNCTION | (Ninguno) | `sedes` | Lista de sedes/tiendas habilitadas para operar en el sistema. |

### 4.7 Módulo de Proformas / Cotizaciones
| Nombre | Tipo | Parámetros | Tablas Afectadas | Lógica de Negocio y Responsabilidad |
| :--- | :--- | :--- | :--- | :--- |
| `sp_procesar_proforma` | PROCEDURE | Sede, Usuario, Cliente, ValidezDias, Total, Subtotal, IGV, Detalles (JSONB), OUT res | `proformas`, `proformas_detalle` | Emite una cotización comercial formal para un cliente sin alterar el stock de almacén. |
| `fn_listar_proformas` | FUNCTION | id_sede, fecha_inicio, fecha_fin | `proformas`, `clientes`, `usuarios` | Listado histórico de proformas emitidas con estado de vigencia. |
| `fn_obtener_proforma_cabecera` | FUNCTION | id_proforma | `proformas`, `clientes`, `usuarios` | Información general de la proforma para exportación a PDF. |
| `fn_obtener_proforma_detalle` | FUNCTION | id_proforma | `proformas_detalle`, `productos` | Lista de artículos y precios cotizados. |

### 4.8 Módulo de Promociones Comerciales
| Nombre | Tipo | Parámetros | Tablas Afectadas | Lógica de Negocio y Responsabilidad |
| :--- | :--- | :--- | :--- | :--- |
| `sp_guardar_promocion` | PROCEDURE | id_promocion, nombre, descripcion, tipo_descuento, valor_descuento, fecha_inicio, fecha_fin, id_sede, OUT res | `promociones` | Configura campañas comerciales con descuentos porcentuales o fijos y rango de fechas. |
| `sp_eliminar_promocion` | PROCEDURE | id_promocion, OUT res | `promociones` | Inactiva de forma inmediata una promoción. |
| `fn_listar_promociones` | FUNCTION | (Ninguno) | `promociones`, `sedes` | Reporte de todas las promociones creadas. |
| `fn_listar_promociones_activas` | FUNCTION | id_sede | `promociones` | Filtra las promociones vigentes al día de hoy aplicables automáticamente en el módulo de ventas. |

---

## 5. Mapeo en el Código Backend (`backend/routes/`)

A continuación se muestra en qué archivo Python y en qué endpoint exacto se eliminó el ORM y se enlazó la llamada a la base de datos:

| Archivo Python | Endpoint HTTP | Método | Procedimiento o Función Invocada |
| :--- | :--- | :--- | :--- |
| `backend/routes/ventas.py` | `/api/ventas` | `POST` | `CALL sp_procesar_venta(...)` |
| `backend/routes/ventas.py` | `/api/ventas/<id>/anular` | `POST` | `CALL sp_anular_venta(...)` |
| `backend/routes/ventas.py` | `/api/ventas` | `GET` | `SELECT * FROM fn_listar_ventas(...)` |
| `backend/routes/ventas.py` | `/api/ventas/<id>` | `GET` | `SELECT * FROM fn_obtener_venta_cabecera(...)` y `fn_obtener_venta_detalle(...)` |
| `backend/routes/almacen.py` | `/api/productos` | `POST` | `CALL sp_guardar_producto(...)` |
| `backend/routes/almacen.py` | `/api/productos` | `GET` | `SELECT * FROM fn_listar_productos_sede(...)` |
| `backend/routes/almacen.py` | `/api/productos/siguiente-codigo` | `GET` | `SELECT fn_siguiente_codigo_producto() AS codigo` |
| `backend/routes/almacen.py` | `/api/categorias` | `GET` | `SELECT * FROM fn_listar_categorias()` |
| `backend/routes/almacen.py` | `/api/categorias` | `POST` | `CALL sp_guardar_categoria(...)` |
| `backend/routes/almacen.py` | `/api/subcategorias` | `GET` | `SELECT * FROM fn_listar_subcategorias(...)` |
| `backend/routes/almacen.py` | `/api/subcategorias` | `POST` | `CALL sp_guardar_subcategoria(...)` |
| `backend/routes/almacen.py` | `/api/subcategorias/<id>` | `DELETE` | `CALL sp_eliminar_subcategoria(...)` |
| `backend/routes/clientes.py` | `/api/clientes` | `POST` | `CALL sp_guardar_cliente(...)` |
| `backend/routes/clientes.py` | `/api/clientes` | `GET` | `SELECT * FROM fn_listar_clientes()` |
| `backend/routes/clientes.py` | `/api/clientes/buscar` | `GET` | `SELECT * FROM fn_buscar_cliente(...)` |
| `backend/routes/clientes.py` | `/api/clientes/<id>` | `GET` | `SELECT * FROM fn_obtener_cliente(...)` |
| `backend/routes/clientes.py` | `/api/clientes/<id>` | `DELETE` | `CALL sp_eliminar_cliente(...)` |
| `backend/routes/compras.py` | `/api/compras` | `POST` | `CALL sp_procesar_compra(...)` |
| `backend/routes/compras.py` | `/api/compras/<id>/recibir` | `POST` | `CALL sp_recibir_compra(...)` |
| `backend/routes/compras.py` | `/api/compras/<id>/anular` | `POST` | `CALL sp_anular_compra(...)` |
| `backend/routes/compras.py` | `/api/compras` | `GET` | `SELECT * FROM fn_listar_compras(...)` |
| `backend/routes/compras.py` | `/api/compras/<id>` | `GET` | `SELECT * FROM fn_obtener_compra_cabecera(...)` y `fn_obtener_compra_detalle(...)` |
| `backend/routes/compras.py` | `/api/compras/siguiente-correlativo` | `GET` | `SELECT fn_siguiente_correlativo_oc() AS correlativo` |
| `backend/routes/proveedores.py` | `/api/proveedores` | `POST` | `CALL sp_guardar_proveedor(...)` |
| `backend/routes/proveedores.py` | `/api/proveedores` | `GET` | `SELECT * FROM fn_listar_proveedores()` |
| `backend/routes/proveedores.py` | `/api/proveedores/<id>` | `GET` | `SELECT * FROM fn_obtener_proveedor(...)` |
| `backend/routes/proveedores.py` | `/api/proveedores/<id>` | `DELETE` | `CALL sp_eliminar_proveedor(...)` |
| `backend/routes/proveedores.py` | `/api/proveedores/<id>/catalogo` | `GET` | `SELECT * FROM fn_catalogo_proveedor(...)` |
| `backend/routes/auth.py` | `/api/auth/login` | `POST` | `SELECT * FROM fn_autenticar_usuario(...)` |
| `backend/routes/users.py` | `/api/usuarios` | `GET` | `SELECT * FROM fn_listar_usuarios()` |
| `backend/routes/users.py` | `/api/usuarios` | `POST` | `CALL sp_guardar_usuario(...)` |
| `backend/routes/users.py` | `/api/usuarios/<id>` | `DELETE` | `CALL sp_eliminar_usuario(...)` |
| `backend/routes/users.py` | `/api/sedes` | `GET` | `SELECT * FROM fn_listar_sedes()` |
| `backend/routes/proformas.py` | `/api/proformas` | `POST` | `CALL sp_procesar_proforma(...)` |
| `backend/routes/proformas.py` | `/api/proformas` | `GET` | `SELECT * FROM fn_listar_proformas(...)` |
| `backend/routes/proformas.py` | `/api/proformas/<id>` | `GET` | `SELECT * FROM fn_obtener_proforma_cabecera(...)` y `fn_obtener_proforma_detalle(...)` |
| `backend/routes/promociones.py` | `/api/promociones` | `POST` | `CALL sp_guardar_promocion(...)` |
| `backend/routes/promociones.py` | `/api/promociones` | `GET` | `SELECT * FROM fn_listar_promociones()` |
| `backend/routes/promociones.py` | `/api/promociones/activas` | `GET` | `SELECT * FROM fn_listar_promociones_activas(...)` |
| `backend/routes/promociones.py` | `/api/promociones/<id>` | `DELETE` | `CALL sp_eliminar_promocion(...)` |

---

## 6. Demostración Visual: Código Antes (ORM) vs Código Ahora (SP / Funciones)

### Ejemplo en Registro de Productos (`backend/routes/almacen.py`)

#### ❌ ANTES (Con ORM vulnerable y lento):
```python
# El backend creaba objetos de Python, hacía múltiples queries y dependía del ORM
nuevo_producto = models.Producto(
    codigo=data['codigo'],
    nombre=data['nombre'],
    precio_venta=data['precio_venta']
)
db.session.add(nuevo_producto)
db.session.commit()

# Otro query separado para el stock (Problema N+1)
nuevo_stock = models.InventarioSede(
    id_producto=nuevo_producto.id_producto,
    id_sede=data['id_sede'],
    stock_actual=data['stock_inicial']
)
db.session.add(nuevo_stock)
db.session.commit()
```

#### ✅ AHORA (100% Stored Procedure Atómico):
```python
# El backend solo envía los parámetros tipados al Stored Procedure
db.execute(text("""
    CALL sp_guardar_producto(
        :id_producto, :codigo, :nombre, :descripcion,
        :precio_compra, :precio_venta, :stock_minimo,
        :id_categoria, :id_subcategoria, :id_proveedor,
        :id_sede, :stock_inicial, :res
    )
"""), {
    "id_producto": data.get("id_producto"),
    "codigo": data.get("codigo"),
    "nombre": data.get("nombre"),
    "descripcion": data.get("descripcion", ""),
    "precio_compra": data.get("precio_compra", 0),
    "precio_venta": data.get("precio_venta", 0),
    "stock_minimo": data.get("stock_minimo", 5),
    "id_categoria": data.get("id_categoria"),
    "id_subcategoria": data.get("id_subcategoria"),
    "id_proveedor": data.get("id_proveedor"),
    "id_sede": data.get("id_sede", 1),
    "stock_inicial": data.get("stock_inicial", 0),
    "res": None
})
db.commit()
```

---

## 7. Guía Paso a Paso para Demostración al Profesor en Supabase

Si el profesor solicita evidenciar dónde residen los procedimientos y cómo se ejecutan en la base de datos:

### Paso 1: Ver las Funciones en la Interfaz de Supabase
1. Iniciar sesión en el panel web de **Supabase** ([https://supabase.com/dashboard](https://supabase.com/dashboard)).
2. Seleccionar el proyecto del Sistema Jesmi.
3. En la barra lateral izquierda, hacer clic en el ícono **Database** (Base de datos).
4. Seleccionar la sección **Functions** (Funciones).
5. Se desplegará el catálogo completo de las 43 funciones y procedimientos (`sp_procesar_venta`, `fn_listar_productos_sede`, `sp_recibir_compra`, etc.) junto con sus argumentos y tipos de retorno.

### Paso 2: Ejecución de Prueba en Vivo desde el SQL Editor de Supabase
En la barra lateral izquierda, ingresar a **SQL Editor**, abrir una nueva pestaña y ejecutar cualquiera de las siguientes sentencias de prueba:

```sql
-- 1. Probar la función de sedes activas
SELECT * FROM fn_listar_sedes();

-- 2. Probar el catálogo de productos con stock en tiempo real en la Sede Principal (ID: 1)
SELECT * FROM fn_listar_productos_sede(1);

-- 3. Probar el historial de ventas del sistema
SELECT * FROM fn_listar_ventas(1, NULL, NULL, NULL);

-- 4. Probar la generación automática del correlativo de Orden de Compra
SELECT fn_siguiente_correlativo_oc();

-- 5. Probar la búsqueda rápida de clientes
SELECT * FROM fn_buscar_cliente('Juan');
```

### Paso 3: Código Fuente en el Repositorio
Para sustentar el código fuente ante el docente, el archivo completo con la definición DDL de todos los procedimientos y funciones se encuentra versionado en Git en la ruta:
* `backend/stored_procedures.sql`

---
*Documento elaborado para el sustento académico y técnico de Arquitectura de Software y Base de Datos del Sistema Jesmi.*
