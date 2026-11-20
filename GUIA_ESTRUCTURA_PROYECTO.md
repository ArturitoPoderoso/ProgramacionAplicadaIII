# GUÍA DE ESTRUCTURA Y ARCHIVOS — SISTEMA JESMI

Documento de referencia rápida que explica de forma concisa el propósito de cada carpeta, subcarpeta y archivo dentro del proyecto.

---

## 1. Árbol General del Proyecto

```text
Sistema Jesmi/
├── backend/
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── almacen.py
│   │   ├── auth.py
│   │   ├── clientes.py
│   │   ├── compras.py
│   │   ├── proformas.py
│   │   ├── promociones.py
│   │   ├── proveedores.py
│   │   ├── users.py
│   │   └── ventas.py
│   ├── .env.example
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── Procfile
│   └── requirements.txt
├── frontend/
│   ├── assets/
│   │   └── Jessmi.jpg
│   ├── modals/
│   │   ├── modals_clientes.html
│   │   ├── modals_compras.html
│   │   ├── modals_productos.html
│   │   ├── modals_promociones.html
│   │   ├── modals_proveedores.html
│   │   ├── modals_usuarios.html
│   │   └── modals_ventas.html
│   ├── views/
│   │   ├── almacen.html
│   │   ├── caja.html
│   │   ├── clientes.html
│   │   ├── compras_emitir.html
│   │   ├── compras_historial.html
│   │   ├── historial_ventas.html
│   │   ├── perfil.html
│   │   ├── proformas.html
│   │   ├── promociones.html
│   │   ├── proveedores.html
│   │   └── usuarios.html
│   ├── almacen.js
│   ├── app.js
│   ├── caja.js
│   ├── clientes.js
│   ├── compras.js
│   ├── config.js
│   ├── dashboard.css
│   ├── dashboard.html
│   ├── dashboard.js
│   ├── historial_ventas.js
│   ├── index.html
│   ├── proformas.js
│   ├── promociones.js
│   ├── proveedores.js
│   ├── router.js
│   ├── styles.css
│   └── vercel.json
├── .gitignore
├── ARQUITECTURA_Y_DOCUMENTACION_SISTEMA.md
├── DOCUMENTACION_ESCALAMIENTO_FRONTEND_Y_BACKEND.md
└── INFORME_DAILY_HU_19_A_23.md
```

---

## 2. Raíz del Proyecto

| Archivo | Descripción |
| :--- | :--- |
| **`.gitignore`** | Define qué archivos y carpetas locales nunca deben subirse al repositorio (entornos virtuales `venv`, claves `.env`, caché). |
| **`DOCUMENTACION_ESCALAMIENTO_FRONTEND_Y_BACKEND.md`** | Manual técnico detallado sobre la arquitectura escalable, modularización SPA, índices de base de datos y compresión GZIP. |
| **`ARQUITECTURA_Y_DOCUMENTACION_SISTEMA.md`** | Documento con la arquitectura global, diagramas de flujo y modelos del sistema comercial. |
| **`INFORME_DAILY_HU_19_A_23.md`** | Reporte de avance y especificación funcional de compras, almacén y proveedores. |

---

## 3. Backend (`/backend`)

Contiene la API REST desarrollada en Python con Flask y SQLAlchemy, conectada a la base de datos PostgreSQL (Supabase).

### Archivos Principales
| Archivo | Para qué sirve |
| :--- | :--- |
| **`main.py`** | Punto de entrada del servidor. Configura Flask, activa compresión GZIP, registra las rutas modulares y levanta el servidor con Waitress en el puerto 8000. |
| **`database.py`** | Gestiona la conexión a PostgreSQL con SQLAlchemy usando un pool de conexiones optimizado para la nube. |
| **`models.py`** | Define todas las tablas y relaciones de la base de datos (usuarios, productos, sedes, ventas, compras, proveedores, proformas y promociones). |
| **`requirements.txt`** | Lista de librerías Python requeridas (`Flask`, `SQLAlchemy`, `psycopg2-binary`, `waitress`, etc.). |
| **`Procfile`** | Comando de arranque para despliegue en plataformas en la nube como Render o Heroku. |
| **`.env.example`** | Plantilla de ejemplo con las variables de entorno necesarias (`DATABASE_URL`). |
| **`.env`** | *(Local)* Archivo privado con las credenciales reales de conexión a la base de datos. |

### Subcarpeta: `backend/routes/`
Agrupa los controladores modulares (Blueprints) que atienden las solicitudes de la API:

| Archivo | Para qué sirve |
| :--- | :--- |
| **`__init__.py`** | Exporta todos los Blueprints para que `main.py` los registre limpiamente en una sola línea. |
| **`auth.py`** | Controla el inicio de sesión (`/api/login`), verificando DNI, clave y retornando roles y sede. |
| **`users.py`** | CRUD de usuarios del sistema, asignación de roles múltiples y listado de sedes. |
| **`almacen.py`** | Gestión de categorías, subcategorías, catálogo de productos y stock por sede. |
| **`ventas.py`** | Emisión de ventas en caja, descuento automático de inventario e historial de comprobantes. |
| **`compras.py`** | Emisión de órdenes de compra, recepción de mercadería al almacén y anulación de órdenes. |
| **`proveedores.py`** | Registro de proveedores, validación de RUC/celular y catálogo de precios pactados. |
| **`clientes.py`** | Gestión de clientes, búsqueda rápida por documento (DNI/RUC) y cartera de contactos. |
| **`proformas.py`** | Registro y consulta de cotizaciones/proformas para clientes emitidas por vendedores. |
| **`promociones.py`** | Creación de campañas de descuento por producto o sede, y autorización de supervisor en caja. |

---

## 4. Frontend (`/frontend`)

Contiene la interfaz de usuario moderna diseñada bajo una arquitectura SPA (Single Page Application) sin recarga de página.

### Archivos Raíz del Frontend
| Archivo | Para qué sirve |
| :--- | :--- |
| **`index.html`** | Pantalla de inicio de sesión (Login) con selector de roles si el usuario tiene más de un perfil. |
| **`dashboard.html`** | Estructura principal del panel administrativo: barra superior, menú lateral y el contenedor dinámico de vistas. |
| **`styles.css`** | Estilos visuales del login (tarjeta, degradados, inputs e iconos). |
| **`dashboard.css`** | Hoja de estilos del dashboard (sidebar, tablas, botones, modales y diseño responsivo). |
| **`config.js`** | Detecta automáticamente si la app corre en `localhost:8000` o en producción (`Render`) para fijar la URL de la API. |
| **`router.js`** | Enrutador SPA. Carga las vistas HTML y los modales bajo demanda en el DOM sin recargar la página. |
| **`app.js`** | Maneja la lógica del formulario de login y la selección de rol del usuario. |
| **`dashboard.js`** | Controla la navegación del dashboard, modales de confirmación, cierre de sesión y bus de eventos. |
| **`caja.js`** | Lógica del Punto de Venta (POS): carrito, lector de código de barras, cálculo de promociones y emisión de boletas. |
| **`almacen.js`** | Lógica de inventario: catálogo de productos, filtros por categoría/sede y creación de nuevos artículos. |
| **`historial_ventas.js`** | Consulta de ventas pasadas, filtros por fecha/sede/vendedor y reimpresión de comprobantes. |
| **`compras.js`** | Emisión de órdenes de compra a proveedores, historial de órdenes y recepción de mercadería al almacén. |
| **`proveedores.js`** | Mantenimiento de proveedores, validaciones peruanas (RUC de 11 dígitos, celular de 9) y precios pactados. |
| **`clientes.js`** | Mantenimiento y búsqueda de clientes, validaciones de DNI/RUC y filtro en tiempo real. |
| **`proformas.js`** | Emisión de cotizaciones para clientes y descarga o impresión en formato proforma. |
| **`promociones.js`** | Creación y administración de promociones temporales, descuentos por porcentaje y montos fijos. |
| **`vercel.json`** | Configuración de enrutamiento y encabezados para despliegue estático en Vercel. |

### Subcarpeta: `frontend/views/`
Vistas HTML modulares que el enrutador (`router.js`) inserta dinámicamente dentro de `dashboard.html`:

| Vista HTML | Pantalla que representa |
| :--- | :--- |
| **`caja.html`** | Pantalla del Punto de Venta (caja registradora con carrito y panel de cobro). |
| **`almacen.html`** | Pantalla de inventario con tabla de productos, stock y alertas de reposición. |
| **`compras_emitir.html`** | Pantalla para armar y emitir una orden de compra a un proveedor. |
| **`compras_historial.html`** | Pantalla del historial de órdenes de compra con botones de recepción y anulación. |
| **`historial_ventas.html`** | Pantalla de auditoría de ventas con tarjetas de totales y tabla filtrable. |
| **`usuarios.html`** | Pantalla de administración de cuentas de usuario, roles y sedes asignadas. |
| **`proveedores.html`** | Pantalla del directorio de proveedores y catálogo de productos asociados. |
| **`clientes.html`** | Pantalla del directorio de clientes, tarjetas estadísticas y cartera de contactos. |
| **`proformas.html`** | Pantalla de emisión y consulta de cotizaciones para clientes. |
| **`promociones.html`** | Pantalla de creación de descuentos comerciales y campañas vigentes. |
| **`perfil.html`** | Pantalla de información personal del usuario logueado y cambio de contraseña. |

### Subcarpeta: `frontend/modals/`
Ventanas emergentes (modales) reutilizables que se cargan en segundo plano una sola vez:

| Archivo Modal | Formularios que contiene |
| :--- | :--- |
| **`modals_ventas.html`** | Modal de confirmación de cobro, modal de boleta de venta y modal de autorización de supervisor. |
| **`modals_productos.html`** | Modales para crear/editar productos, categorías y subcategorías. |
| **`modals_compras.html`** | Modales para ver el detalle de una compra, recibir mercadería y anular orden. |
| **`modals_proveedores.html`** | Modales para registrar proveedor y asociar productos con precios de compra pactados. |
| **`modals_clientes.html`** | Modal para registrar y editar información de clientes con validación de documento. |
| **`modals_promociones.html`** | Modal para crear nuevas promociones temporales. |
| **`modals_usuarios.html`** | Modal para crear y editar cuentas de empleados y asignar perfiles. |

### Subcarpeta: `frontend/assets/`
| Archivo | Descripción |
| :--- | :--- |
| **`Jessmi.jpg`** | Logotipo oficial de la empresa ferretera Sistema Jesmi utilizado en el login y en las boletas. |

