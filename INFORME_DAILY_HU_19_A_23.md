# INFORME TÉCNICO Y DE AVANCE PARA DAILY SCRUM
## Proyecto: Sistema Jesmi - Ferretería
**Fecha:** 24 de Octubre de 2026  
**Módulos:** Proveedores, Catálogos Pactados, Emisión de Órdenes de Compra, Recepción en Almacén e Historial de Compras  
**Historias de Usuario (HU):** **HU 19, HU 20, HU 21, HU 22 y HU 23**  
**Estado:** **100% Implementado, Integrado en Base de Datos (Supabase) y Validado sin Errores**

---

## 1. Guion Rápido para la Reunión de Daily Scrum (Para leer al equipo)

> **¿Qué se hizo ayer / en esta sesión?**  
> *"Completamos de punta a punta todo el ciclo comercial y logístico de compras y proveedores correspondiente a las Historias de Usuario 19, 20, 21, 22 y 23.  
> 1. En la **HU 22**, implementamos la gestión de proveedores con validaciones de RUC y teléfono y aislamiento estricto por sede.  
> 2. En la **HU 23**, vinculamos los catálogos de productos a cada proveedor con sus precios de compra pactados.  
> 3. En la **HU 19**, construimos la emisión de órdenes de compra con la regla comercial de 1 solo proveedor por orden, carga automática de sus productos pactados, desglose de IGV y correlativo único `OC-2026-XXXX`.  
> 4. En la **HU 20**, creamos la recepción de mercadería que, al confirmarse, suma automáticamente el stock al inventario de la sede y registra el movimiento de ENTRADA en el Kardex.  
> 5. En la **HU 21**, desarrollamos el historial de compras con filtros, pestañas rápidas ('Pendientes' e 'Historial'), visor documental imprimible en PDF, envío por WhatsApp y anulación segura con reversión de inventario en almacén."*

> **¿Qué se hará hoy?**  
> *"Revisar con el equipo los siguientes módulos del backlog (Reportes de ganancias consolidadas o facturación electrónica) e iniciar sus respectivas pruebas de aceptación."*

> **¿Hay algún impedimento o bloqueo?**  
> *"Ninguno. Se corrieron pruebas unitarias y de integración end-to-end contra Supabase PostgreSQL y los endpoints responden con código 200/201. Toda la interfaz sigue la regla de nombres cortos de máximo 2 a 3 palabras sin romper ninguna funcionalidad existente."*

---

## 2. Diagrama de Flujo del Ciclo Logístico Completo

```
  [ HU 22: Proveedor por Sede ]
                 │
                 ▼
  [ HU 23: Catálogo Pactado ] ──> Define Productos y Precios Acordados (S/.)
                 │
                 ▼
  [ HU 19: Emitir Orden ] ────> 1 Solo Proveedor por OC | Correlativo Único | Subtotal + IGV
                 │
                 ▼
          (Estado: PENDIENTE)
                 │
                 ├─────────────────────────────────────────────────┐
                 ▼ (Llega la mercadería física)                    ▼ (Cancelación)
  [ HU 20: Recibir Mercadería ]                      [ HU 21: Anular Orden ]
                 │                                                 │
                 ├─> Suma Stock en InventarioSede                  ├─> Si era PENDIENTE: Cambia estado
                 ├─> Actualiza Precio Compra en Sede               └─> Si era RECIBIDA:
                 └─> Registra ENTRADA en Kardex                         ├─> Valida stock disponible
                                                                        ├─> Resta Stock en InventarioSede
                                                                        └─> Registra SALIDA en Kardex
```

---

## 3. Detalle Técnico y Funcional por Historia de Usuario

### 🚚 HU 22: Gestión de Proveedores por Sede
* **Necesidad del Negocio:** La ferretería trabaja con múltiples proveedores (distribuidores de cemento, herramientas, pinturas, etc.) asignados a sedes específicas (SJL, Los Olivos). Los usuarios de una sede no deben alterar ni ver la lista de proveedores de otra sede.
* **Criterios de Aceptación Cumplidos:**
  1. **Aislamiento Multisede:** Las consultas filtran estrictamente por `id_sede` del usuario logueado en sesión.
  2. **Validación de RUC:** Solo admite exactamente 11 dígitos numéricos con sanitización en tiempo real (`validarInputRucEnTiempoReal`).
  3. **Validación de Celular:** Restricción a 9 dígitos numéricos obligatorios para posterior integración con WhatsApp.
  4. **Eliminación Lógica:** No se borra físicamente el registro; se marca `estado_registro = 0` para preservar la integridad de auditoría y compras históricas.
* **Especificación Backend:**
  * `GET /api/proveedores?id_sede={id}`: Retorna la lista activa de proveedores de la sede.
  * `POST /api/proveedores`: Registra nuevo proveedor validando duplicidad de RUC en la misma sede.
  * `PUT /api/proveedores/{id}`: Actualiza datos de contacto, dirección y condiciones de pago.
  * `DELETE /api/proveedores/{id}`: Inactiva el proveedor.
* **Archivos Afectados:**
  * [`frontend/proveedores.js`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/frontend/proveedores.js)
  * [`backend/main.py`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/backend/main.py)
  * [`backend/models.py`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/backend/models.py) (Entidad `Proveedor`)

---

### 📦 HU 23: Catálogo de Productos y Precios Pactados por Proveedor
* **Necesidad del Negocio:** Un mismo producto de ferretería puede ser ofrecido por varios proveedores a costos distintos. El sistema debe recordar qué productos vende cada proveedor y a qué precio de costo mayorista fue negociado.
* **Criterios de Aceptación Cumplidos:**
  1. **Catálogo Exclusivo:** Un proveedor solo tiene asociados productos que efectivamente suministra.
  2. **Precios Pactados en Soles:** Cada producto asociado almacena un `precio_compra` pactado que servirá como base fija al momento de generar órdenes de compra.
  3. **Actualización Ágil:** Modal específico para modificar precios pactados en cualquier momento.
  4. **Desvinculación:** Opción de retirar productos del catálogo sin afectar el inventario general de la ferretería.
* **Especificación Backend:**
  * `GET /api/proveedores/{id}/catalogo`: Retorna los productos asociados al proveedor junto con sus precios pactados y código de inventario.
  * `POST /api/proveedores/{id}/catalogo`: Vincula un producto del maestro al catálogo del proveedor.
  * `PUT /api/proveedores/{id}/catalogo/{id_producto}`: Actualiza el precio acordado.
  * `DELETE /api/proveedores/{id}/catalogo/{id_producto}`: Retira el ítem del catálogo.
* **Archivos Afectados:**
  * [`frontend/proveedores.js`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/frontend/proveedores.js) (`modal-catalogo-proveedor`, `modal-editar-precio`)
  * [`backend/models.py`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/backend/models.py) (Entidad `ProveedorProducto`)

---

### 📝 HU 19: Emisión de Orden de Compra por Proveedor
* **Necesidad del Negocio:** Formalizar los pedidos de mercadería hacia los proveedores sin errores humanos, garantizando precios negociados y orden correlativo único.
* **Criterios de Aceptación Cumplidos:**
  1. **Regla de 1 Proveedor por Orden:** Al iniciar la orden, se debe seleccionar obligatoriamente un único proveedor. No se permite mezclar proveedores en una misma orden.
  2. **Catálogo Filtrado Automático:** El selector de productos se bloquea hasta elegir el proveedor; una vez seleccionado, solo despliega los productos de su catálogo (HU 23) precargando su costo pactado.
  3. **Cálculos en Vivo:**
     $$\text{Subtotal Base} = \frac{\text{Total}}{1.18}, \quad \text{IGV (18\%)} = \text{Total} - \text{Subtotal Base}$$
  4. **Correlativo Consecutivo:** Generación automática basada en el año fiscal: `OC-2026-0001`, `OC-2026-0002`, etc.
  5. **Nombres Cortos:** Botón `Emitir Orden`, cabecera `Emitir Orden`, selector `Proveedor`, botón `Agregar Ítem`.
* **Especificación Backend:**
  * `GET /api/compras/siguiente-correlativo`: Genera el código correlativo para previsualización.
  * `POST /api/compras`: Valida proveedor, sede, detalle de productos e inserta la cabecera en `ordenes_compra` y los ítems en `detalle_ordenes_compra` con estado `PENDIENTE`.
* **Archivos Afectados:**
  * [`frontend/compras.js`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/frontend/compras.js)
  * [`frontend/dashboard.html`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/frontend/dashboard.html) (`section-emitir-orden`)
  * [`backend/models.py`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/backend/models.py) (`OrdenCompra`, `DetalleOrdenCompra`)

---

### 📥 HU 20: Recepción de Mercadería e Ingreso Automático a Almacén
* **Necesidad del Negocio:** Eliminar el doble registro manual de inventario. Cuando el camión del proveedor entrega los materiales, el sistema debe sincronizar el stock del almacén con un solo clic.
* **Criterios de Aceptación Cumplidos:**
  1. **Validación Visual de Llegada:** Modal que detalla productos y cantidades que están ingresando físicamente.
  2. **Actualización Automática de Stock:** Suma directamente `stock_actual += cantidad` en la tabla `inventario_sedes` de la sede correspondiente.
  3. **Actualización del Costo:** Modifica `precio_compra` en almacén para reflejar el costo más reciente.
  4. **Kardex Oficial:** Inserta un movimiento en la tabla `movimientos_almacen` con `tipo = 'ENTRADA'`, asociando usuario responsable, sede, fecha y correlativo de la orden.
  5. **Transaccionalidad Atómica:** Si alguna actualización falla, se ejecuta `rollback()`, evitando stock corrupto o descuadrado.
* **Especificación Backend:**
  * `POST /api/compras/{id_orden}/recibir`:
    * Cambia estado a `RECIBIDA`.
    * Actualiza `inventario_sedes`.
    * Registra `MovimientoAlmacen`.
* **Archivos Afectados:**
  * [`frontend/compras.js`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/frontend/compras.js) (`abrirModalRecibirCompra`, `confirmarRecepcionCompra`)
  * [`frontend/dashboard.html`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/frontend/dashboard.html) (`modal-recibir-compra`)
  * [`backend/main.py`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/backend/main.py)

---

### 📊 HU 21: Historial de Compras, Visor Documental y Anulación Segura
* **Necesidad del Negocio:** Trazabilidad histórica completa, control de compras pendientes por recibir, capacidad de generar comprobantes en PDF y enviar al proveedor por WhatsApp, y anulación sin descuadre de inventario.
* **Criterios de Aceptación Cumplidos:**
  1. **Navegación Eficiente con Nombres Cortos:**
     * Pestaña `Pendientes`: Filtra órdenes por recibir con badge indicador en tiempo real.
     * Pestaña `Historial`: Muestra el consolidado de todas las órdenes (Pendientes, Recibidas y Anuladas).
  2. **Tarjetas KPI:** `Total Órdenes`, `Pendientes`, `Total Recibido (S/)`.
  3. **Buscador Dinámico:** Búsqueda en tiempo real por número de OC, razón social o RUC.
  4. **Visor de Documento Formal ("Orden de Compra"):**
     * Membrete corporativo Ferretería Jesmi, datos de la sede de recepción, datos fiscales del proveedor y tabla de ítems.
     * Botón **"Imprimir PDF"**: Formato limpio para impresión física o PDF del navegador.
     * Botón **"Enviar WhatsApp"**: Abre directamente el API de WhatsApp con mensaje formateado listo para enviar al proveedor.
  5. **Anulación Segura con Reversión de Stock:**
     * Si la orden está `PENDIENTE`, se cancela directamente sin alterar el inventario.
     * Si la orden ya estaba `RECIBIDA`, el backend valida que Almacén tenga stock suficiente disponible; si es así, descuenta las unidades e inserta un movimiento de `SALIDA` en el Kardex para mantener el balance exacto.
* **Especificación Backend:**
  * `GET /api/compras?id_sede={id}&estado={estado}&search={query}`: Listado con filtros.
  * `GET /api/compras/{id}`: Consulta profunda con ítems y proveedor.
  * `POST /api/compras/{id}/anular`: Ejecución de anulación y reversión de Kardex.
* **Archivos Afectados:**
  * [`frontend/compras.js`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/frontend/compras.js)
  * [`frontend/dashboard.html`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/frontend/dashboard.html) (`section-historial-compras`, `modal-documento-orden-compra`)
  * [`backend/main.py`](file:///c:/Users/luisa/OneDrive/Desktop/Sistema%20Jesmi/backend/main.py)

---

## 4. Matriz de Nombres Cortos de la Interfaz (Máximo 2 a 3 palabras)

| Elemento de Interfaz | Nombre Asignado | Conteo de palabras |
| :--- | :--- | :---: |
| **Menú Lateral** | `Compras` | 1 |
| **Submenú 1** | `Emitir Orden` | 2 |
| **Submenú 2** | `Historial Compras` | 2 |
| **Título Superior 1** | `EMITIR ORDEN` | 2 |
| **Título Superior 2** | `HISTORIAL COMPRAS` | 2 |
| **Pestañas (Tabs)** | `Pendientes` / `Historial` | 1 c/u |
| **Tarjetas KPI** | `Total Órdenes`, `Pendientes`, `Total Recibido` | 1 - 2 |
| **Botón de Emisión** | `Emitir Orden` | 2 |
| **Botón de Limpieza** | `Limpiar Orden` | 2 |
| **Botón en Tabla** | `Recibir` | 1 |
| **Modal Recepción** | `Recibir Mercadería` / `Confirmar Recepción` | 2 |
| **Modal Documento** | `Orden de Compra` | 3 |
| **Botón Imprimir** | `Imprimir PDF` | 2 |
| **Botón WhatsApp** | `Enviar WhatsApp` | 2 |

---

## 5. Matriz de Roles y Permisos (RBAC)

| Módulo / Acción | Vendedor | Supervisor | Administrador |
| :--- | :---: | :---: | :---: |
| **Ver Menú Compras en Sidebar** | ❌ Oculto | ✅ Visible | ✅ Visible |
| **Gestionar Proveedores (HU 22)** | ❌ Denegado | ✅ Permitido (Sede) | ✅ Permitido (Sede) |
| **Catálogo de Precios (HU 23)** | ❌ Denegado | ✅ Permitido (Sede) | ✅ Permitido (Sede) |
| **Emitir Orden de Compra (HU 19)** | ❌ 403 Forbidden | ✅ Permitido | ✅ Permitido |
| **Recibir Mercadería en Almacén (HU 20)**| ❌ 403 Forbidden | ✅ Permitido | ✅ Permitido |
| **Consultar Historial de Compras (HU 21)**| ❌ 403 Forbidden | ✅ Permitido | ✅ Permitido |
| **Anular Orden de Compra (HU 21)** | ❌ 403 Forbidden | ✅ Permitido | ✅ Permitido |

---

## 6. Evidencia de Pruebas Automatizadas de Integración (QA Log)

Se ejecutó un script automatizado de ciclo completo en el entorno local conectado a la base de datos PostgreSQL en Supabase:

```
[TEST 1] Consulta de proveedor activo en sede 1:
         -> Proveedor ID: 9 (DISTRIBUIDORA FERRETERA DEL NORTE S.A.C.) - OK
[TEST 2] Catálogo de productos pactados:
         -> Producto ID: 18 | Precio Pactado: S/. 15.50 - OK
[TEST 3] Emisión de Orden de Compra (HU 19):
         -> Generada: OC-2026-0005 | Total: S/. 155.00 | Estado: PENDIENTE - OK
[TEST 4] Stock en Almacén antes de recibir:
         -> Stock actual en InventarioSede: 99 unidades
[TEST 5] Confirmación de Recepción (HU 20):
         -> Respuesta 200: Mercadería recibida e ingresada al almacén.
         -> Stock posterior en InventarioSede: 109 unidades (+10 uds)
         -> Registro generado en movimientos_almacen: ENTRADA (Kardex) - OK
[TEST 6] Anulación de Orden Recibida (HU 21):
         -> Respuesta 200: Orden de compra OC-2026-0005 anulada correctamente.
         -> Stock revertido en InventarioSede: 99 unidades (-10 uds)
         -> Registro generado en movimientos_almacen: SALIDA (Reversión Kardex) - OK

RESULTADO FINAL: 100% de pruebas aprobadas con código de salida 0.
```

---

## 7. Archivos del Repositorio Actualizados y Listos para Commit

* `frontend/compras.js`: Controlador principal de compras, cálculo de totales, integración con Almacén y visor PDF/WhatsApp.
* `frontend/proveedores.js`: Controlador de proveedores y catálogo de precios pactados por sede.
* `frontend/dashboard.html`: Estructura SPA con submenú desplegable, secciones `section-emitir-orden`, `section-historial-compras` y modales.
* `frontend/dashboard.js`: Navegación dinámica, toggle de subgrupos y control de permisos por rol.
* `backend/main.py`: Endpoints REST con validaciones transaccionales y soporte multisede.
* `backend/models.py`: Modelos SQLAlchemy para `Proveedor`, `ProveedorProducto`, `OrdenCompra`, `DetalleOrdenCompra` y `MovimientoAlmacen`.
* `backend/schemas.py`: Esquemas Pydantic para validación de datos.
* `INFORME_DAILY_HU_19_A_23.md`: Informe técnico de avance.
* `.gitignore`: Configuración limpia para omitir temporales y entornos virtuales.
