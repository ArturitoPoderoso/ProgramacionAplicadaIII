# DOCUMENTACIÓN NUEVA - SISTEMA JESMI
## Registro de Mejoras, Correcciones Críticas, Auditoría Integral y Guía de Mantenimiento

---

### 📌 Información General del Documento
* **Proyecto:** Sistema Jesmi - ERP Comercial, Almacén, Ventas y Facturación Electrónica.
* **Versión del Sistema:** v2.5 Enterprise (100% Procedimientos Almacenados en PostgreSQL).
* **Fecha de Actualización:** Noviembre 2026.
* **Propósito:** Registrar las modificaciones recientes en el código fuente, la resolución de incidencias en producción/desarrollo, los resultados de la auditoría preventiva de Frontend y Base de Datos, y la guía operativa para mantener la estabilidad del sistema.

---

## 1. Resumen de Cambios Recientes (Changelog de Ingeniería)

### 1.1 Estandarización de Llamadas en Backend (`backend/routes/`)
* **Eliminación Total de Modelos ORM:** Se removieron todas las dependencias de clases mapeadas (`models.py`) en las 9 rutas del sistema (`ventas.py`, `almacen.py`, `clientes.py`, `compras.py`, `proveedores.py`, `auth.py`, `users.py`, `proformas.py`, `promociones.py`).
* **Sintaxis Canónica de Funciones:** Se reemplazaron todas las consultas que listaban columnas de forma manual en Python (`SELECT col1, col2, ... FROM fn_...`) por la sintaxis limpia y estandarizada:
  ```python
  rows = db.execute(text("SELECT * FROM fn_nombre_funcion(:param)"), {"param": valor}).mappings().all()
  return jsonify([dict(r) for r in rows]), 200
  ```
* **Transacciones de Escritura:** Todas las mutaciones de datos se ejecutan estrictamente mediante llamadas a procedimientos almacenados:
  ```python
  db.execute(text("CALL sp_nombre_procedimiento(:param1, ..., :res)"), params)
  db.commit()
  ```

---

## 2. Incidencias Críticas Detectadas y Soluciones Aplicadas

A continuación se detallan los tres problemas reales que fueron diagnosticados y resueltos en el sistema:

### 2.1 Caso: Bloqueo en "Emitir Orden de Compra" (Catálogo de Proveedor Congelado)
* **Síntoma:** Al seleccionar un proveedor en el módulo de compras (por ejemplo, *CEMENTOS Y AGREGADOS SAN JUAN S.A.C.*), el desplegable de **Producto** no cargaba y se quedaba bloqueado en `-- Primero selecciona un proveedor --`.
* **Diagnóstico Técnico:**
  1. *Error de Frontend (DOM):* En el archivo HTML `frontend/views/compras_emitir.html` faltaba la etiqueta `<span id="oc-card-razon">`. Cuando el controlador `frontend/compras.js` ejecutaba `document.getElementById('oc-card-razon').innerText = ...`, el navegador lanzaba una excepción silenciosa `TypeError: Cannot set properties of null`, interrumpiendo la ejecución antes de llamar a `cargarCatalogoDeProveedorParaOrden()`.
  2. *Error de Base de Datos (Column Mismatch):* En la rutina `fn_catalogo_proveedor`, la consulta interna intentaba leer la columna `pp.precio_pactado` y `p.precio_compra`, pero en la tabla `proveedor_productos` de Supabase la columna real se llama `precio_compra`.
* **Solución Implementada:**
  1. Se agregó el elemento `oc-card-razon` en `frontend/views/compras_emitir.html`.
  2. Se protegieron todas las asignaciones en `frontend/compras.js` con validaciones previas (`if (el) ...`).
  3. Se corrigió la función `fn_catalogo_proveedor` en Supabase usando `COALESCE(pp.precio_compra, 0.0)::DOUBLE PRECISION AS precio_pactado`.
  4. **Fallback Inteligente:** Si un proveedor nuevo no tiene productos registrados en su catálogo exclusivo, el sistema ahora carga automáticamente los productos generales del almacén, permitiendo que el usuario emita la orden de compra sin bloqueos.

---

### 2.2 Caso: Aislamiento de la Tabla `clientes` en el Diagrama ER de Supabase
* **Síntoma:** En el visualizador gráfico de esquemas de Supabase, la tabla `clientes` aparecía flotando en la parte inferior sin líneas relacionales con ninguna otra tabla.
* **Diagnóstico Técnico:**
  * El visualizador de Supabase dibuja líneas conectoras **únicamente si existe una restricción explícita de `FOREIGN KEY` en PostgreSQL**.
  * Aunque las tablas `ventas` y `proformas` tenían la columna `id_cliente` y el código hacía los `JOIN` correspondientes, no se había declarado la restricción formal en la base de datos.
* **Solución Implementada:**
  * Se validó previamente que no existieran registros huérfanos (ventas con clientes inexistentes).
  * Se crearon formalmente las llaves foráneas con eliminación segura (`ON DELETE SET NULL`):
    ```sql
    ALTER TABLE ventas 
    ADD CONSTRAINT fk_ventas_cliente 
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE SET NULL;

    ALTER TABLE proformas 
    ADD CONSTRAINT fk_proformas_cliente 
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE SET NULL;
    ```
  * Ahora el diagrama entidad-relación refleja la integridad referencial real entre Clientes, Ventas y Cotizaciones.

---

### 2.3 Caso: Potencial Fallo en Modal de Nuevo Cliente (`clientes.js`)
* **Síntoma:** Riesgo de bloqueo silencioso al hacer clic en el botón "+ Registrar Nuevo Cliente".
* **Diagnóstico Técnico:**
  * La función `abrirModalCrearCliente()` en `frontend/clientes.js` intentaba asignar valores a campos de correo y dirección (`cli-correo`, `cli-direccion`) que no existen en el modal `frontend/modals/modals_clientes.html`.
* **Solución Implementada:**
  * Se protegieron ambas instrucciones con condicionales `if (elCorreo)` y `if (elDir)`, evitando que un elemento inexistente corte la apertura del modal.

---

## 3. Resultados de la Auditoría Preventiva Integral

Para garantizar que no existan más fallos ocultos similares, se ejecutaron pruebas automáticas de punta a punta:

### 3.1 Auditoría de Frontend (Cruce de IDs DOM vs Scripts JS)
* **Alcance:** 20 archivos HTML (vistas y modales) con **254 IDs únicos** analizados contra todos los archivos JavaScript del frontend.
* **Resultado:** **0 llamadas desprotegidas restantes**. Todos los accesos al DOM cuentan con condicionales `if` o encadenamiento opcional `?.`.

### 3.2 Auditoría de Base de Datos (Ejecución de 25 Funciones en Supabase)
Se probaron en vivo las 25 rutinas de lectura de PostgreSQL conectadas a la API:

| Módulo | Función Evaluada | Estado de Prueba |
| :--- | :--- | :--- |
| **Sedes** | `fn_listar_sedes` | ✅ Retorna registros correctamente |
| **Usuarios** | `fn_listar_usuarios`, `fn_autenticar_usuario` | ✅ Verificado y seguro |
| **Almacén** | `fn_listar_productos_sede`, `fn_siguiente_codigo_producto`, `fn_listar_categorias`, `fn_listar_subcategorias` | ✅ 106 productos y 16 categorías operativas |
| **Clientes** | `fn_listar_clientes`, `fn_buscar_cliente`, `fn_obtener_cliente` | ✅ Búsqueda por DNI y catálogo activos |
| **Compras** | `fn_listar_compras`, `fn_obtener_compra_cabecera`, `fn_obtener_compra_detalle`, `fn_siguiente_correlativo_oc` | ✅ Órdenes de compra verificadas |
| **Proveedores** | `fn_listar_proveedores`, `fn_obtener_proveedor`, `fn_catalogo_proveedor` | ✅ Catálogo de insumos probado |
| **Ventas** | `fn_listar_ventas`, `fn_obtener_venta_cabecera`, `fn_obtener_venta_detalle` | ✅ Reportes y KPIs de caja operativos |
| **Proformas** | `fn_listar_proformas`, `fn_obtener_proforma_cabecera`, `fn_obtener_proforma_detalle` | ✅ Cotizaciones operativas |
| **Promociones** | `fn_listar_promociones`, `fn_listar_promociones_activas` | ✅ Reglas de descuento vigentes |

---

## 4. Guía de Mantenimiento y Buenas Prácticas para Desarrolladores

Para mantener la estabilidad del sistema en futuros desarrollos, se deben seguir estas reglas:

### 4.1 Al Crear o Modificar Vistas en el Frontend
1. **Verificar IDs de Formularios:** Cada vez que en un archivo `.js` se utilice `document.getElementById('mi-id')`, asegurarse de que el elemento exista en la vista HTML correspondiente o usar protección:
   ```javascript
   const el = document.getElementById('mi-id');
   if (el) el.value = 'nuevo valor';
   ```
2. **Uso de Opciones de Respaldo (*Fallback*):** Cuando un selector dependa de un servicio externo o una tabla secundaria (como catálogos de proveedores), prever siempre qué mostrar si el arreglo viene vacío (`prods.length === 0`).

### 4.2 Al Crear Nuevas Rutas en el Backend
1. **Regla Cero ORM:** Jamás importar `models.py` ni usar `db.session.add()` o `db.session.query()`.
2. **Toda lógica transaccional pertenece a PostgreSQL:**
   * Si la operación altera tablas (INSERT / UPDATE / DELETE), crear un `PROCEDURE` con `sp_...` en [backend/stored_procedures.sql](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/backend/stored_procedures.sql).
   * Si la operación lee datos tabulares con joins, crear una `FUNCTION` con `fn_...` que retorne `TABLE (...)`.
3. **Parameter Binding Obligatorio:** Pasar siempre los parámetros como diccionarios vinculados (`:nombre_param`), nunca concatenando cadenas de texto (`f"SELECT ... {variable}"`).

---

## 5. Control de Versiones y Despliegue

Todos los cambios descritos en esta documentación se encuentran integrados y respaldados en el repositorio oficial del proyecto:
* **Repositorio:** `https://github.com/ArturitoPoderoso/ProgramacionAplicadaIII.git`
* **Rama Principal:** `main`
* **Commits Clave:**
  * `109b304`: Documentación técnica de arquitectura backend y base de datos.
  * `f9a80c5`: Estandarización a `SELECT * FROM fn_...` en los 9 módulos de backend.
  * `908db2a`: Corrección de columnas en `fn_catalogo_proveedor`.
  * `7fe5e4d`: Corrección de eventos DOM y catálogo en emisión de compras.
  * `76bc028`: Implementación de claves foráneas para tabla `clientes`.
  * `9225568`: Blindaje contra excepciones en modal de clientes.

---
*Fin del documento técnico.*
