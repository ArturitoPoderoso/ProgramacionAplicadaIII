# SISTEMA JESMI - ARQUITECTURA, DOCUMENTACIÓN TÉCNICA Y GUÍA DE ESCALABILIDAD

**Ferretería JESSMI - Sistema Integral de Gestión Comercial (ERP / POS)**  
**Versión de Arquitectura:** 2.0.0 (Modular SPA & Blueprints)  
**Última Actualización:** Noviembre 2026  

---

## 1. RESUMEN EJECUTIVO Y STACK TECNOLÓGICO

El **Sistema Jesmi** es una plataforma integral para ferreterías que gestiona inventarios, ventas en caja (POS), emisión de cotizaciones/proformas, gestión de compras y proveedores, control de usuarios y roles, y auditoría comercial.

### Stack Técnico
* **Backend:** Python 3.14+, Flask 3.x, SQLAlchemy 2.x, Psycopg2-binary, Waitress (servidor WSGI multi-hilo para producción en Windows/Linux).
* **Base de Datos:** PostgreSQL en la nube alojado en **Supabase** con Connection Pooling (PgBouncer en puerto 6543).
* **Frontend:** Single Page Application (SPA) basada en Vanilla JavaScript modular, CSS3 moderno con variables dinámicas, Phosphor Icons e Inter font.
* **Despliegue / Servidor:** Preparado para ejecución local autónoma (servidor Flask unificado con estáticos) y despliegue en la nube (Render / Supabase / Vercel).

---

## 2. ESTRUCTURA DE DIRECTORIOS Y MÓDULOS

```
Sistema Jesmi/
├── .env.example                       # Plantilla de variables de entorno seguras
├── .gitignore                         # Exclusión de venv, cache y credenciales
├── ARQUITECTURA_Y_DOCUMENTACION_SISTEMA.md # Esta documentación maestra
│
├── backend/                           # BACKEND REST API (Modular)
│   ├── .env                           # Credenciales reales locales (DATABASE_URL)
│   ├── database.py                    # Configuración del Engine, Pool y ciclo de vida de sesiones
│   ├── main.py                        # Orquestador Flask, registro de Blueprints y servidor estático
│   ├── models.py                      # Modelos declarativos ORM (SQLAlchemy)
│   ├── Procfile                       # Comando de arranque para plataformas cloud (Render)
│   ├── requirements.txt               # Dependencias Python
│   └── routes/                        # Blueprints desacoplados por dominio de negocio
│       ├── __init__.py                # Exportación limpia de Blueprints
│       ├── auth.py                    # Autenticación y control de acceso
│       ├── users.py                   # CRUD de usuarios, perfiles y sedes
│       ├── almacen.py                 # Inventario, productos, stock, categorías y subcategorías
│       ├── ventas.py                  # Caja POS, transacciones, detalle y comprobantes
│       ├── proformas.py               # Cotizaciones y proformas
│       ├── promociones.py             # Reglas de descuento por sede y combos
│       ├── proveedores.py             # Directorio de proveedores y catálogos de precios
│       └── compras.py                 # Órdenes de compra y recepción de mercadería
│
└── frontend/                          # FRONTEND SPA MODULAR
    ├── index.html                     # Pantalla de Login y autenticación
    ├── dashboard.html                 # Cascarón SPA Shell ligero (141 líneas)
    ├── dashboard.css                  # Estilos globales de la interfaz y componentes
    ├── styles.css                     # Estilos complementarios de login
    ├── config.js                      # Configuración dinámica de API (Localhost vs Render)
    ├── router.js                      # Enrutador SPA dinámico con caché en memoria
    │
    ├── components/                    # Componentes estructurales
    │   ├── sidebar.html               # Barra de navegación lateral
    │   └── topbar.html                # Barra superior de usuario y sede
    │
    ├── views/                         # Vistas modulares cargadas bajo demanda (AJAX/Fetch)
    │   ├── usuarios.html              # Gestión de personal y accesos
    │   ├── perfil.html                # Perfil del usuario autenticado
    │   ├── almacen.html               # Catálogo de productos e inventario
    │   ├── caja.html                  # Punto de venta (POS) y carrito
    │   ├── historial_ventas.html      # Registro histórico y anulaciones
    │   ├── promociones.html           # Panel de descuentos y vigencias
    │   ├── proformas.html             # Emisión y conversión de cotizaciones
    │   ├── proveedores.html           # Gestión de empresas proveedoras
    │   ├── compras_emitir.html        # Emisión de órdenes de compra
    │   └── compras_historial.html     # Seguimiento y estado de órdenes
    │
    ├── modals/                        # Modales modulares inyectados dinámicamente
    │   ├── modals_usuarios.html       # Crear/editar usuarios y perfiles
    │   ├── modals_productos.html      # Crear/editar productos y categorías
    │   ├── modals_ventas.html         # Pago en caja, métodos de pago y ticket
    │   ├── modals_promociones.html    # Configurar descuentos y combos
    │   ├── modals_proveedores.html    # Registrar proveedores y catálogos
    │   └── modals_compras.html        # Detalle de orden y recepción
    │
    └── *.js                           # Controladores JS especializados por módulo
        ├── app.js                     # Controlador de login y redirección
        ├── dashboard.js               # Control del shell (menús, toggle, perfil)
        ├── almacen.js                 # Lógica de almacén y productos
        ├── caja.js                    # Lógica de POS, carrito y cobro
        ├── historial_ventas.js        # Filtros y anulación de ventas
        ├── proformas.js               # Cálculo y emisión de proformas
        ├── promociones.js             # Lógica de promociones
        ├── proveedores.js             # Lógica de proveedores
        └── compras.js                 # Lógica de órdenes de compra
```

---

## 3. ARQUITECTURA DEL BACKEND

### 3.1. Gestión del Pool de Conexiones (`backend/database.py`)
Para evitar cuellos de botella y desconexiones automáticas de Supabase (PgBouncer), el motor de base de datos implementa:
* `pool_pre_ping=True`: Verifica que la conexión TCP esté viva antes de ejecutar una consulta. Si se cerró por inactividad, la restablece silenciosamente sin fallar la petición.
* `pool_recycle=300`: Recicla las conexiones cada 5 minutos para adaptarse al límite de tiempo de espera del pooler.
* `get_db()` y `teardown_db()`: Vincula la sesión al ciclo de vida de la petición Flask (`g.db`), cerrándola automáticamente al responder el cliente para prevenir fugas de memoria y saturación de conexiones.

### 3.2. Blueprints y Rutas de la API REST

| Módulo | Blueprint | Prefijo / Rutas Clave | Responsabilidad |
| :--- | :--- | :--- | :--- |
| **Auth** | `auth_bp` | `/api/login` | Validación de credenciales y retorno de sesión. |
| **Usuarios** | `users_bp` | `/api/users`, `/api/sedes`, `/api/perfil` | Administración de usuarios, roles (Admin/Supervisor/Vendedor) y sedes. |
| **Almacén** | `almacen_bp` | `/api/productos`, `/api/categorias`, `/api/subcategorias`, `/api/productos/siguiente-codigo` | Catálogo de inventario, stock por sede, alertas de stock mínimo. |
| **Ventas** | `ventas_bp` | `/api/ventas`, `/api/ventas/historial`, `/api/ventas/anular` | Registro atómico de ventas, deducción de stock y comprobantes. |
| **Proformas** | `proformas_bp` | `/api/proformas`, `/api/proformas/emitir` | Cotizaciones con vigencia configurable. |
| **Promociones**| `promociones_bp`| `/api/promociones`, `/api/promociones/activas` | Descuentos porcentuales o fijos aplicables en caja. |
| **Proveedores**| `proveedores_bp`| `/api/proveedores`, `/api/proveedor-productos` | Directorio de proveedores y asociación con productos y costos. |
| **Compras** | `compras_bp` | `/api/compras`, `/api/compras/siguiente-correlativo`, `/api/compras/recepcionar` | Órdenes de compra y actualización de stock entrante. |

---

## 4. ARQUITECTURA DEL FRONTEND

### 4.1. El Enrutador Dinámico SPA (`frontend/router.js`)
El frontend ya no carga 1,700 líneas de HTML en un solo archivo. Utiliza un enrutador ligero en Vanilla JS que opera de la siguiente manera:
1. **Cascarón Inicial:** `dashboard.html` se carga en milisegundos conteniendo únicamente la barra lateral, la barra superior y dos contenedores vacíos: `#router-viewport` y `#modals-container`.
2. **Carga Asíncrona de Modales:** Al iniciar la aplicación, `router.js` inyecta todos los modales desde `modals/*.html` en segundo plano.
3. **Navegación Bajo Demanda:** Al hacer clic en una opción del menú (ej. `showSection('section-ventas')`):
   * Verifica la caché en memoria (`ViewRouter.cache`). Si ya se descargó previamente, no hace ninguna petición de red y la renderiza de inmediato.
   * Si es la primera vez que se visita, descarga el HTML específico desde `views/caja.html` y lo monta en `#router-viewport`.
   * Ejecuta la función controladora correspondiente (`cargarProductosCaja()`) para sincronizar datos con el backend.
4. **Preservación de IDs y Eventos:** Todos los identificadores originales del DOM (`#product-grid`, `#cart-total`, `#search-input`) se conservaron exactamente iguales, garantizando cero regresiones en los archivos JS existentes.

---

## 5. DIAGNÓSTICO: ¿EL PROGRAMA CORRE NORMAL?

**SÍ, la arquitectura y el código corren con total normalidad.**
No hay código duplicado en las vistas ni conflictos estructurales.

### ⚠️ Alerta de Base de Datos Externa (Supabase)
Si al levantar el backend recibes el error:
```text
FATAL: (ENOTFOUND) tenant/user postgres.ilkphmcbusmlwouourfa not found
```
**Causa:** No es un error de código. Supabase en su plan gratuito **pausa automáticamente** los proyectos que pasan más de 7 días sin recibir tráfico.  
**Solución (1 clic):**
1. Ingresa a tu panel en [https://supabase.com/dashboard](https://supabase.com/dashboard).
2. Selecciona el proyecto `ilkphmcbusmlwouourfa`.
3. Haz clic en el botón verde **"Restore Project"** o **"Resume"**. En 1 o 2 minutos estará activo y el backend se conectará automáticamente.

---

## 6. HOJA DE RUTA: QUÉ FALTA PARA ESCALAR CORRECTAMENTE

A continuación, la lista priorizada de mejoras recomendadas para llevar el sistema a un estándar de nivel empresarial:

### Nivel 1: Seguridad y Autenticación (Prioridad Crítica)
1. **Implementar Tokens JWT (JSON Web Tokens):**
   * *Situación actual:* El backend valida roles leyendo el encabezado `X-Role: Administrador` enviado por el cliente.
   * *Acción:* Generar un token JWT firmado criptográficamente al iniciar sesión en `/api/login`. Todos los endpoints deben verificar este token con un decorador `@token_required`, impidiendo que usuarios no autorizados falsifiquen su rol.
2. **Hasheo Seguro de Contraseñas:**
   * *Situación actual:* Las contraseñas están almacenadas y se comparan en texto plano.
   * *Acción:* Integrar `werkzeug.security.generate_password_hash` y `check_password_hash` (o `bcrypt`).

### Nivel 2: Arquitectura del Frontend JS (Prioridad Alta)
3. **Aislamiento de Controladores (Evitar Contaminación Global):**
   * *Situación actual:* Scripts como `caja.js`, `almacen.js`, `compras.js` declaran variables globales en el objeto `window` (ej. `var API_URL`, `let productosGlobal`).
   * *Acción:* Encapsular cada archivo en un objeto controlador o módulo ES (ej. `const CajaController = { ... }`) para prevenir colisiones accidentales de nombres entre pantallas.
4. **Sistema Unificado de Notificaciones (Toasts):**
   * *Situación actual:* Errores de red a veces solo se imprimen con `console.error()`.
   * *Acción:* Crear un componente global `Toast.success(msg)` y `Toast.error(msg)` para dar retroalimentación visual al usuario ante fallos de conexión.

### Nivel 3: Base de Datos y Concurrencia (Prioridad Media)
5. **Correlativos Atómicos por Secuencia de Base de Datos:**
   * *Situación actual:* Los códigos (`PROD-00098`, `OC-2026-0013`) se calculan buscando `MAX()` desde Python.
   * *Acción:* Utilizar secuencias nativas de PostgreSQL (`CREATE SEQUENCE`) o transacciones con bloqueo `SELECT FOR UPDATE` para evitar duplicidad de códigos si dos cajeros guardan al mismo milisegundo.
6. **Paginación en Backend (`LIMIT` / `OFFSET`):**
   * *Situación actual:* `/api/productos` y `/api/ventas` devuelven la totalidad de registros con `.all()`.
   * *Acción:* Añadir paginación de 50 en 50 registros. Cuando el inventario supere los 5,000 productos, esto reducirá el uso de ancho de banda y acelerará la carga a menos de 100 ms.

### Nivel 4: Mantenibilidad (Prioridad Baja)
7. **Capa de Servicios (Service Layer):**
   * *Situación actual:* Las rutas contienen la lógica de negocio y las consultas SQLAlchemy juntas.
   * *Acción:* Crear una carpeta `backend/services/` para desacoplar reglas de cálculo complejas de las rutas HTTP.

---

## 7. GUÍA RÁPIDA DE EJECUCIÓN LOCAL

### 1. Iniciar el Backend (Servidor Flask + Waitress)
```powershell
cd "c:\Users\luisa\OneDrive\Desktop\Sistema Jesmi\backend"
.\venv2\Scripts\python.exe main.py
```
El servidor arrancará en: **`http://localhost:8000`**

### 2. Abrir el Frontend
* **Opción A (Recomendada):** Acceder directamente desde el navegador a `http://localhost:8000/` o `http://localhost:8000/dashboard.html` (el backend ya sirve los archivos estáticos de forma nativa sin problemas de CORS).
* **Opción B:** Utilizar la extensión **Live Server** de VS Code abriendo `frontend/index.html`.

---
*Documento generado para el equipo de desarrollo de Sistema Jesmi.*

