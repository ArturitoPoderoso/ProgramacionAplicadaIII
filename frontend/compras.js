/**
 * compras.js
 * Módulo de Compras (HU 19, HU 20 & HU 21)
 * - HU 19: Emisión de Orden de Compra por Proveedor con precios pactados y generación de PDF/WhatsApp.
 * - HU 20: Recepción de Mercadería con Ingreso Automático a Almacén y registro en Kardex.
 * - HU 21: Historial de Compras, control por sede, estados y anulación segura con reversión de stock.
 */

const API_COMPRAS = 'http://localhost:8000/api';

// Estado en memoria para emisión de orden
let proveedorSeleccionadoOC = null;
let productosCatalogoProveedorOC = [];
let itemsOrdenCompraActual = []; // [{ id_producto, codigo, nombre, precio_compra, cantidad, subtotal }]

// Estado en memoria para historial de compras
let listaComprasCache = [];
let tabComprasActual = 'pendientes'; // 'pendientes' | 'todas'
let ordenSeleccionadaAccion = null;

// ==============================================================================
// 1. INICIALIZACIÓN Y HOOKS
// ==============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar listeners al cargar DOM si las secciones existen
    const inputBuscarHistorial = document.getElementById('compras-search-input');
    if (inputBuscarHistorial) {
        inputBuscarHistorial.addEventListener('keyup', filtrarHistorialCompras);
    }
});

/**
 * Inicializa la sección "Emitir Orden" (HU 19)
 */
async function inicializarEmitirOrden() {
    limpiarFormularioOrden();
    await cargarSiguienteCorrelativoOC();
    await cargarProveedoresParaOrden();

    // Establecer fecha esperada mínima (hoy) y sugerida (+3 días hábiles)
    const elFecha = document.getElementById('oc-fecha-esperada');
    if (elFecha) {
        const hoy = new Date();
        const hoyStr = hoy.toISOString().split('T')[0];
        elFecha.min = hoyStr;
        if (!elFecha.value || elFecha.value < hoyStr) {
            hoy.setDate(hoy.getDate() + 3);
            elFecha.value = hoy.toISOString().split('T')[0];
        }
    }
}

/**
 * Carga el siguiente correlativo estimado (ej: OC-2026-0001)
 */
async function cargarSiguienteCorrelativoOC() {
    const elCod = document.getElementById('oc-correlativo-display');
    if (!elCod) return;

    try {
        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';

        const res = await fetch(`${API_COMPRAS}/compras/siguiente-correlativo`, {
            headers: { 'X-Role': userRole }
        });
        if (res.ok) {
            const data = await res.json();
            elCod.innerText = data.correlativo || 'OC-XXXX';
        }
    } catch (e) {
        console.warn('No se pudo obtener correlativo preview:', e);
    }
}

/**
 * Carga los proveedores activos filtrados estrictamente por la sede del usuario
 */
async function cargarProveedoresParaOrden() {
    const selectProv = document.getElementById('oc-select-proveedor');
    if (!selectProv) return;

    selectProv.innerHTML = '<option value="">-- Selecciona un Proveedor --</option>';

    try {
        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';
        const idSede = u.id_sede || 1;

        const res = await fetch(`${API_COMPRAS}/proveedores?id_sede=${idSede}`, {
            headers: { 'X-Role': userRole }
        });

        if (!res.ok) throw new Error('Error al obtener proveedores de la sede.');

        const proveedores = await res.json();
        proveedores.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id_proveedor;
            opt.textContent = p.razon_social;
            opt.dataset.ruc = p.ruc;
            opt.dataset.contacto = p.nombre_contacto || 'Sin contacto';
            opt.dataset.telefono = p.telefono || 'Sin celular';
            opt.dataset.correo = p.correo || '';
            opt.dataset.totalProds = p.total_productos || 0;
            selectProv.appendChild(opt);
        });

    } catch (err) {
        if (typeof showNotification === 'function') {
            showNotification(err.message, 'error');
        }
    }
}

/**
 * Manejador al cambiar de proveedor en la emisión de orden
 * Restringe la orden estrictamente a un solo proveedor y carga su catálogo
 */
async function onProveedorOrdenChange() {
    const selectProv = document.getElementById('oc-select-proveedor');
    const idProv = selectProv ? selectProv.value : '';

    const cardInfo = document.getElementById('oc-proveedor-info-card');
    const selectProd = document.getElementById('oc-select-producto');

    if (!idProv) {
        proveedorSeleccionadoOC = null;
        productosCatalogoProveedorOC = [];
        itemsOrdenCompraActual = [];
        renderizarTablaOrdenItems();

        if (cardInfo) cardInfo.style.display = 'none';
        if (selectProd) selectProd.innerHTML = '<option value="">-- Primero selecciona un proveedor --</option>';
        return;
    }

    const opt = selectProv.options[selectProv.selectedIndex];
    proveedorSeleccionadoOC = {
        id_proveedor: parseInt(idProv),
        razon_social: opt.textContent.trim(),
        ruc: opt.dataset.ruc,
        contacto: opt.dataset.contacto,
        telefono: opt.dataset.telefono,
        correo: opt.dataset.correo
    };

    // Mostrar ficha rápida del proveedor
    if (cardInfo) {
        cardInfo.style.display = 'flex';
        document.getElementById('oc-card-ruc').innerText = proveedorSeleccionadoOC.ruc;
        document.getElementById('oc-card-contacto').innerText = proveedorSeleccionadoOC.contacto;
        document.getElementById('oc-card-telefono').innerText = proveedorSeleccionadoOC.telefono;
        document.getElementById('oc-card-correo').innerText = proveedorSeleccionadoOC.correo || '---';
    }

    // Cargar catálogo de este proveedor (HU 23)
    await cargarCatalogoDeProveedorParaOrden(idProv);

    // Reiniciar lista de ítems de la orden
    itemsOrdenCompraActual = [];
    renderizarTablaOrdenItems();
}

/**
 * Obtiene los productos asociados al catálogo de este proveedor con sus precios pactados
 */
async function cargarCatalogoDeProveedorParaOrden(idProveedor) {
    const selectProd = document.getElementById('oc-select-producto');
    if (!selectProd) return;

    selectProd.innerHTML = '<option value="">Cargando catálogo...</option>';
    selectProd.disabled = true;

    try {
        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';
        const idSede = u.id_sede || 1;

        const res = await fetch(`${API_COMPRAS}/proveedores/${idProveedor}/catalogo?id_sede=${idSede}`, {
            headers: { 'X-Role': userRole }
        });

        if (!res.ok) throw new Error('No se pudo cargar el catálogo del proveedor.');

        const resData = await res.json();
        const prods = Array.isArray(resData) ? resData : (resData.productos || []);
        productosCatalogoProveedorOC = prods;

        selectProd.innerHTML = '';
        if (prods.length === 0) {
            selectProd.innerHTML = '<option value="">Este proveedor no tiene productos en su catálogo aún</option>';
            selectProd.disabled = true;
            return;
        }

        selectProd.innerHTML = '<option value="">-- Selecciona producto a ordenar --</option>';
        prods.forEach(p => {
            const opt = document.createElement('option');
            const nom = p.nombre || p.nombre_producto || 'Producto';
            opt.value = p.id_producto;
            opt.textContent = `${p.codigo_producto} - ${nom}`;
            opt.dataset.codigo = p.codigo_producto;
            opt.dataset.nombre = nom;
            opt.dataset.precio = p.precio_compra;
            selectProd.appendChild(opt);
        });

        selectProd.disabled = false;

    } catch (err) {
        selectProd.innerHTML = '<option value="">Error al cargar catálogo</option>';
        selectProd.disabled = false;
        if (typeof showNotification === 'function') {
            showNotification(err.message, 'error');
        }
    }
}

/**
 * Evento al seleccionar un producto para autocompletar precio de compra pactado
 */
function onProductoOrdenChange() {
    const selectProd = document.getElementById('oc-select-producto');
    const inputPrecio = document.getElementById('oc-item-precio');
    const inputCant = document.getElementById('oc-item-cantidad');

    if (!selectProd || !selectProd.value) {
        if (inputPrecio) inputPrecio.value = '';
        return;
    }

    const opt = selectProd.options[selectProd.selectedIndex];
    const precio = parseFloat(opt.dataset.precio || 0);

    if (inputPrecio) inputPrecio.value = precio.toFixed(2);
    if (inputCant && (!inputCant.value || inputCant.value <= 0)) {
        inputCant.value = 1;
    }
}

/**
 * Agrega un producto a la lista de ítems de la orden de compra
 */
function agregarItemAOrden() {
    if (!proveedorSeleccionadoOC) {
        if (typeof showNotification === 'function') {
            showNotification('Error: Debes seleccionar un proveedor primero.', 'error');
        } else {
            alert('Error: Debes seleccionar un proveedor primero.');
        }
        return;
    }

    const selectProd = document.getElementById('oc-select-producto');
    const inputPrecio = document.getElementById('oc-item-precio');
    const inputCant = document.getElementById('oc-item-cantidad');

    const idProducto = parseInt(selectProd?.value);
    const precioU = parseFloat(inputPrecio?.value);
    const cantidad = parseInt(inputCant?.value);

    if (!idProducto || isNaN(idProducto)) {
        if (typeof showNotification === 'function') {
            showNotification('Por favor, selecciona un producto del catálogo.', 'error');
        }
        return;
    }

    if (isNaN(cantidad) || cantidad <= 0) {
        if (typeof showNotification === 'function') {
            showNotification('La cantidad a ordenar debe ser mayor a 0.', 'error');
        }
        inputCant?.focus();
        return;
    }

    if (isNaN(precioU) || precioU <= 0) {
        if (typeof showNotification === 'function') {
            showNotification('El precio de compra debe ser un número mayor a 0.', 'error');
        }
        inputPrecio?.focus();
        return;
    }

    const opt = selectProd.options[selectProd.selectedIndex];
    const codigo = opt.dataset.codigo;
    const nombre = opt.dataset.nombre;

    // Verificar si ya está en la lista
    const existente = itemsOrdenCompraActual.find(i => i.id_producto === idProducto);
    if (existente) {
        existente.cantidad += cantidad;
        existente.precio_compra = precioU;
        existente.subtotal = round2(existente.cantidad * existente.precio_compra);
        if (typeof showNotification === 'function') {
            showNotification(`Se sumaron ${cantidad} unidades a '${nombre}'.`, 'success');
        }
    } else {
        itemsOrdenCompraActual.push({
            id_producto: idProducto,
            codigo: codigo,
            nombre: nombre,
            precio_compra: precioU,
            cantidad: cantidad,
            subtotal: round2(cantidad * precioU)
        });
    }

    renderizarTablaOrdenItems();

    // Resetear selector de producto y cantidad
    selectProd.value = '';
    if (inputPrecio) inputPrecio.value = '';
    if (inputCant) inputCant.value = '1';
}

/**
 * Renderiza la tabla de productos de la orden en construcción
 */
function renderizarTablaOrdenItems() {
    const tbody = document.getElementById('oc-items-tbody');
    if (!tbody) return;

    if (itemsOrdenCompraActual.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 30px; color: #94a3b8; font-style: italic;">
                    No hay productos agregados a la orden aún. Selecciona un producto y haz clic en <strong>"+ Agregar Ítem"</strong>.
                </td>
            </tr>
        `;
        actualizarTotalesOrden();
        return;
    }

    tbody.innerHTML = '';
    itemsOrdenCompraActual.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="font-family: monospace; font-weight: 700; color: #1e293b;">${item.codigo}</td>
            <td style="font-weight: 600; color: #0f172a;">${item.nombre}</td>
            <td style="text-align: right; font-weight: 600; color: #334155;">S/. ${item.precio_compra.toFixed(2)}</td>
            <td style="text-align: center;">
                <input type="number" min="1" value="${item.cantidad}" onchange="modificarCantidadItemOrden(${index}, this.value)"
                       style="width: 75px; text-align: center; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 6px; font-weight: 700; color: #0f172a;">
            </td>
            <td style="text-align: right; font-weight: 800; color: #0284c7;">S/. ${item.subtotal.toFixed(2)}</td>
            <td style="text-align: center;">
                <button type="button" onclick="eliminarItemOrden(${index})" class="btn-table-action" title="Quitar ítem"
                        style="background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; padding: 6px 9px; border-radius: 6px; cursor: pointer;">
                    <i class="ph-bold ph-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    actualizarTotalesOrden();
}

function modificarCantidadItemOrden(index, nuevaCant) {
    const cant = parseInt(nuevaCant);
    if (isNaN(cant) || cant <= 0) {
        renderizarTablaOrdenItems();
        return;
    }
    itemsOrdenCompraActual[index].cantidad = cant;
    itemsOrdenCompraActual[index].subtotal = round2(cant * itemsOrdenCompraActual[index].precio_compra);
    renderizarTablaOrdenItems();
}

function eliminarItemOrden(index) {
    itemsOrdenCompraActual.splice(index, 1);
    renderizarTablaOrdenItems();
}

function actualizarTotalesOrden() {
    const total = itemsOrdenCompraActual.reduce((acc, item) => acc + item.subtotal, 0);
    const subtotalBase = round2(total / 1.18);
    const igv = round2(total - subtotalBase);

    const elSub = document.getElementById('oc-total-subtotal');
    const elIgv = document.getElementById('oc-total-igv');
    const elTot = document.getElementById('oc-total-general');

    if (elSub) elSub.innerText = `S/. ${subtotalBase.toFixed(2)}`;
    if (elIgv) elIgv.innerText = `S/. ${igv.toFixed(2)}`;
    if (elTot) elTot.innerText = `S/. ${total.toFixed(2)}`;
}

/**
 * Limpia el formulario completo de emisión de orden
 */
function limpiarFormularioOrden() {
    proveedorSeleccionadoOC = null;
    productosCatalogoProveedorOC = [];
    itemsOrdenCompraActual = [];

    const selectProv = document.getElementById('oc-select-proveedor');
    if (selectProv) selectProv.value = '';

    const selectProd = document.getElementById('oc-select-producto');
    if (selectProd) selectProd.innerHTML = '<option value="">-- Primero selecciona un proveedor --</option>';

    const cardInfo = document.getElementById('oc-proveedor-info-card');
    if (cardInfo) cardInfo.style.display = 'none';

    const elObs = document.getElementById('oc-observaciones');
    if (elObs) elObs.value = '';

    renderizarTablaOrdenItems();
}

/**
 * Envía la orden de compra al servidor (HU 19)
 */
async function emitirOrdenCompra() {
    if (!proveedorSeleccionadoOC) {
        if (typeof showNotification === 'function') {
            showNotification('Error: Debes seleccionar un proveedor obligatorio.', 'error');
        } else {
            alert('Error: Debes seleccionar un proveedor obligatorio.');
        }
        return;
    }

    if (itemsOrdenCompraActual.length === 0) {
        if (typeof showNotification === 'function') {
            showNotification('Error: Debes agregar al menos un producto a la orden de compra.', 'error');
        } else {
            alert('Error: Debes agregar al menos un producto a la orden de compra.');
        }
        return;
    }

    const u = JSON.parse(localStorage.getItem('user')) || {};
    const userRole = u.activeRole || u.role || 'Administrador';
    const idSede = u.id_sede || 1;
    const idUsuario = u.id || u.id_usuario || 1;

    const fechaEsperada = document.getElementById('oc-fecha-esperada')?.value || '';
    const observacion = document.getElementById('oc-observaciones')?.value.trim() || '';

    // Validar que la fecha esperada no sea anterior a hoy
    if (fechaEsperada) {
        const hoyStr = new Date().toISOString().split('T')[0];
        if (fechaEsperada < hoyStr) {
            const msg = `Error: La fecha de entrega programada (${fechaEsperada}) no puede ser anterior a la fecha de hoy (${hoyStr}).`;
            if (typeof showNotification === 'function') {
                showNotification(msg, 'error');
            } else {
                alert(msg);
            }
            return;
        }
    }

    const payload = {
        id_proveedor: proveedorSeleccionadoOC.id_proveedor,
        id_sede: idSede,
        id_usuario: idUsuario,
        fecha_esperada: fechaEsperada,
        observacion: observacion,
        items: itemsOrdenCompraActual.map(i => ({
            id_producto: i.id_producto,
            cantidad: i.cantidad,
            precio_unitario: i.precio_compra
        }))
    };

    const btnEmitir = document.getElementById('btn-emitir-orden-submit');
    if (btnEmitir) {
        btnEmitir.disabled = true;
        btnEmitir.innerHTML = `<i class="ph ph-spinner spinner"></i> Emitiendo...`;
    }

    try {
        const res = await fetch(`${API_COMPRAS}/compras`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Role': userRole
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error al emitir orden de compra.');

        if (typeof showNotification === 'function') {
            showNotification(`¡${data.message}!`, 'success');
        } else {
            alert(data.message);
        }

        const idCreada = data.id_orden_compra;
        limpiarFormularioOrden();
        await cargarSiguienteCorrelativoOC();

        // Abrir inmediatamente la vista previa formal / PDF de la orden generada
        if (idCreada) {
            await abrirModalDetalleCompra(idCreada);
        }

    } catch (err) {
        if (typeof showNotification === 'function') {
            showNotification(err.message, 'error');
        } else {
            alert(err.message);
        }
    } finally {
        if (btnEmitir) {
            btnEmitir.disabled = false;
            btnEmitir.innerHTML = `<i class="ph-bold ph-paper-plane-tilt"></i> Emitir Orden de Compra`;
        }
    }
}


// ==============================================================================
// 2. HISTORIAL DE COMPRAS & RECEPCIÓN (HU 20 & HU 21)
// ==============================================================================

/**
 * Carga el historial de compras desde el backend
 */
async function cargarHistorialCompras() {
    const tbody = document.getElementById('compras-historial-tbody');
    if (!tbody) return;

    tbody.innerHTML = `
        <tr>
            <td colspan="7" style="text-align: center; padding: 30px; color: #94a3b8;">
                <i class="ph ph-spinner spinner" style="font-size: 1.5rem;"></i> Cargando historial de compras...
            </td>
        </tr>
    `;

    try {
        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';
        const idSede = u.id_sede || 1;

        const res = await fetch(`${API_COMPRAS}/compras?id_sede=${idSede}`, {
            headers: { 'X-Role': userRole }
        });

        if (!res.ok) throw new Error('Error al consultar historial de compras.');

        const ordenes = await res.json();
        listaComprasCache = ordenes;

        actualizarResumenHistorialCompras(ordenes);
        filtrarYRenderizarCompras();

    } catch (err) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 25px; color: #ef4444;">
                    <i class="ph ph-warning-circle" style="font-size: 1.3rem;"></i> ${err.message}
                </td>
            </tr>
        `;
    }
}

/**
 * Cambia la pestaña activa: 'pendientes' o 'todas'
 */
function cambiarTabCompras(tab) {
    tabComprasActual = tab;

    const btnPend = document.getElementById('tab-compras-pendientes');
    const btnTodas = document.getElementById('tab-compras-todas');

    if (btnPend && btnTodas) {
        if (tab === 'pendientes') {
            btnPend.style.background = '#0284c7';
            btnPend.style.color = '#ffffff';
            btnPend.style.borderColor = '#0284c7';

            btnTodas.style.background = '#f8fafc';
            btnTodas.style.color = '#64748b';
            btnTodas.style.borderColor = '#e2e8f0';
        } else {
            btnTodas.style.background = '#0284c7';
            btnTodas.style.color = '#ffffff';
            btnTodas.style.borderColor = '#0284c7';

            btnPend.style.background = '#f8fafc';
            btnPend.style.color = '#64748b';
            btnPend.style.borderColor = '#e2e8f0';
        }
    }

    filtrarYRenderizarCompras();
}

/**
 * Filtra por tab y por texto de búsqueda
 */
function filtrarHistorialCompras() {
    filtrarYRenderizarCompras();
}

function filtrarYRenderizarCompras() {
    const searchVal = (document.getElementById('compras-search-input')?.value || '').toLowerCase().trim();

    let filtradas = listaComprasCache;

    // Filtro por pestaña
    if (tabComprasActual === 'pendientes') {
        filtradas = filtradas.filter(o => o.estado === 'PENDIENTE');
    }

    // Filtro por texto
    if (searchVal) {
        filtradas = filtradas.filter(o =>
            (o.correlativo || '').toLowerCase().includes(searchVal) ||
            (o.proveedor_nombre || '').toLowerCase().includes(searchVal) ||
            (o.proveedor_ruc || '').toLowerCase().includes(searchVal) ||
            (o.usuario_nombre || '').toLowerCase().includes(searchVal)
        );
    }

    renderizarTablaHistorialCompras(filtradas);
}

/**
 * Actualiza tarjetas de métricas superiores
 */
function actualizarResumenHistorialCompras(ordenes) {
    const elTot = document.getElementById('kpi-compras-total');
    const elPend = document.getElementById('kpi-compras-pendientes');
    const elInversion = document.getElementById('kpi-compras-monto');
    const badgePendTab = document.getElementById('badge-count-pendientes');

    const totalCount = ordenes.length;
    const pendCount = ordenes.filter(o => o.estado === 'PENDIENTE').length;
    const montoRecibido = ordenes
        .filter(o => o.estado === 'RECIBIDA')
        .reduce((acc, o) => acc + (o.total || 0), 0);

    if (elTot) elTot.innerText = totalCount;
    if (elPend) elPend.innerText = pendCount;
    if (badgePendTab) badgePendTab.innerText = pendCount;
    if (elInversion) elInversion.innerText = `S/. ${montoRecibido.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Renderiza filas en la tabla de historial de compras
 */
function renderizarTablaHistorialCompras(ordenes) {
    const tbody = document.getElementById('compras-historial-tbody');
    if (!tbody) return;

    if (!ordenes || ordenes.length === 0) {
        const msg = tabComprasActual === 'pendientes'
            ? '¡Excelente! No tienes órdenes de compra pendientes por recibir en tu sede.'
            : 'No se encontraron registros de órdenes de compra para los criterios especificados.';

        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px; color: #94a3b8; font-style: italic;">
                    <i class="ph-bold ph-check-circle" style="font-size: 1.8rem; color: #10b981; display: block; margin-bottom: 8px;"></i>
                    ${msg}
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = '';
    ordenes.forEach(o => {
        const tr = document.createElement('tr');
        tr.style.transition = 'background-color 0.15s ease';

        // Estilos de badge de estado
        let badgeBg = '#fef3c7', badgeColor = '#b45309', badgeBorder = '#fde68a', icon = 'ph-clock';
        if (o.estado === 'RECIBIDA') {
            badgeBg = '#dcfce7'; badgeColor = '#15803d'; badgeBorder = '#bbf7d0'; icon = 'ph-check-circle';
        } else if (o.estado === 'ANULADA') {
            badgeBg = '#fee2e2'; badgeColor = '#b91c1c'; badgeBorder = '#fecaca'; icon = 'ph-x-circle';
        }

        const esPendiente = o.estado === 'PENDIENTE';

        tr.innerHTML = `
            <td>
                <div style="font-weight: 800; color: #0284c7; font-family: monospace; font-size: 0.95rem;">
                    ${o.correlativo}
                </div>
                <div style="font-size: 0.75rem; color: #64748b;">${o.total_items} ítems (${o.total_unidades} uds)</div>
            </td>
            <td>
                <div style="font-weight: 700; color: #0f172a; font-size: 0.92rem;">${o.proveedor_nombre}</div>
                <div style="font-size: 0.78rem; color: #64748b; font-family: monospace;">RUC: ${o.proveedor_ruc}</div>
            </td>
            <td>
                <div style="font-size: 0.85rem; color: #334155; font-weight: 600;">${o.fecha_emision}</div>
                <div style="font-size: 0.75rem; color: #64748b;">Por: ${o.usuario_nombre}</div>
            </td>
            <td>
                <div style="font-size: 0.85rem; color: #334155;">
                    ${o.estado === 'RECIBIDA' ? `✔ Recibido: ${o.fecha_recepcion}` : `📅 Esperado: ${o.fecha_esperada || 'Inmediato'}`}
                </div>
            </td>
            <td style="text-align: right; font-weight: 800; color: #0f172a; font-size: 0.95rem;">
                S/. ${o.total.toFixed(2)}
            </td>
            <td style="text-align: center;">
                <span style="background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBorder}; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; display: inline-flex; align-items: center; gap: 4px;">
                    <i class="ph-bold ${icon}"></i> ${o.estado}
                </span>
            </td>
            <td style="text-align: center;">
                <div style="display: inline-flex; gap: 6px; align-items: center;">
                    ${esPendiente ? `
                        <button onclick="abrirModalRecibirCompra(${o.id_orden_compra})" class="btn-recibir-oc"
                                style="background: #16a34a; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 4px rgba(22, 163, 74, 0.25);"
                                title="Recibir Mercadería e Ingresar Stock a Almacén">
                            <i class="ph-bold ph-package"></i>
                            <span>Recibir</span>
                        </button>
                    ` : ''}

                    <button onclick="abrirModalDetalleCompra(${o.id_orden_compra})" title="Ver Detalle y Descargar PDF"
                            style="background: #f0f9ff; border: 1px solid #bae6fd; color: #0284c7; padding: 6px 9px; border-radius: 6px; cursor: pointer;">
                        <i class="ph-bold ph-file-text" style="font-size: 1rem;"></i>
                    </button>

                    ${o.proveedor_telefono ? `
                        <button onclick="enviarOrdenPorWhatsApp(${o.id_orden_compra})" title="Enviar resumen por WhatsApp"
                                style="background: #f0fdf4; border: 1px solid #bbf7d0; color: #16a34a; padding: 6px 9px; border-radius: 6px; cursor: pointer;">
                            <i class="ph-bold ph-whatsapp-logo" style="font-size: 1rem;"></i>
                        </button>
                    ` : ''}

                    ${o.estado !== 'ANULADA' ? `
                        <button onclick="abrirModalAnularCompra(${o.id_orden_compra}, '${o.correlativo}')" title="Anular Orden"
                                style="background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; padding: 6px 9px; border-radius: 6px; cursor: pointer;">
                            <i class="ph-bold ph-x-circle" style="font-size: 1rem;"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}


// ==============================================================================
// 3. RECEPCIÓN DE MERCADERÍA AL ALMACÉN (HU 20)
// ==============================================================================

/**
 * Abre modal para confirmar recepción de mercadería (HU 20)
 */
async function abrirModalRecibirCompra(idOrden) {
    try {
        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';

        const res = await fetch(`${API_COMPRAS}/compras/${idOrden}`, {
            headers: { 'X-Role': userRole }
        });

        if (!res.ok) throw new Error('No se pudo cargar la orden.');

        const orden = await res.json();
        ordenSeleccionadaAccion = orden;

        document.getElementById('modal-recibir-oc-correlativo').innerText = orden.correlativo;
        document.getElementById('modal-recibir-oc-proveedor').innerText = orden.proveedor_nombre;

        const tbody = document.getElementById('modal-recibir-oc-items-tbody');
        tbody.innerHTML = '';

        orden.items.forEach(it => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-family: monospace; font-weight: 700; color: #334155;">${it.codigo_producto}</td>
                <td style="font-weight: 600; color: #0f172a;">${it.nombre_producto}</td>
                <td style="text-align: center; font-weight: 800; color: #16a34a; font-size: 1rem;">+${it.cantidad_solicitada} uds</td>
                <td style="text-align: right; color: #64748b;">S/. ${it.precio_unitario.toFixed(2)}</td>
                <td style="text-align: right; font-weight: 700; color: #0284c7;">S/. ${it.subtotal.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });

        const modal = document.getElementById('modal-recibir-compra');
        if (modal) modal.classList.add('active');

    } catch (err) {
        if (typeof showNotification === 'function') {
            showNotification(err.message, 'error');
        }
    }
}

/**
 * Confirma el ingreso oficial a Almacén e incrementa stock_actual en base de datos
 */
async function confirmarRecepcionCompra() {
    if (!ordenSeleccionadaAccion) return;

    const u = JSON.parse(localStorage.getItem('user')) || {};
    const userRole = u.activeRole || u.role || 'Administrador';
    const idUsuario = u.id || u.id_usuario || 1;

    const btn = document.getElementById('btn-confirmar-recepcion-submit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="ph ph-spinner spinner"></i> Ingresando a Almacén...`;
    }

    try {
        const res = await fetch(`${API_COMPRAS}/compras/${ordenSeleccionadaAccion.id_orden_compra}/recibir`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Role': userRole
            },
            body: JSON.stringify({ id_usuario: idUsuario })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error al recepcionar mercadería.');

        if (typeof showNotification === 'function') {
            showNotification(data.message, 'success');
        } else {
            alert(data.message);
        }

        if (typeof closeModal === 'function') {
            closeModal('modal-recibir-compra');
        }

        // Recargar historial y productos si están cargados
        await cargarHistorialCompras();
        if (typeof cargarProductosAlmacen === 'function') {
            cargarProductosAlmacen();
        }

    } catch (err) {
        if (typeof showNotification === 'function') {
            showNotification(err.message, 'error');
        } else {
            alert(err.message);
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="ph-bold ph-check"></i> Confirmar e Ingresar a Almacén`;
        }
    }
}


// ==============================================================================
// 4. ANULACIÓN SEGURA DE ÓRDENES (HU 21)
// ==============================================================================

function abrirModalAnularCompra(idOrden, correlativo) {
    const orden = listaComprasCache.find(o => o.id_orden_compra === idOrden);
    if (!orden) return;

    ordenSeleccionadaAccion = orden;

    const modal = document.getElementById('modal-confirmacion-custom');
    if (!modal) {
        if (confirm(`¿Estás seguro de anular la orden ${correlativo}?`)) {
            ejecutarAnulacionCompra(idOrden);
        }
        return;
    }

    const iconWrapper = document.getElementById('modal-confirm-icon-wrapper');
    const icon = document.getElementById('modal-confirm-icon');
    if (iconWrapper) iconWrapper.style.background = '#fee2e2';
    if (icon) {
        icon.className = 'ph-bold ph-x-circle';
        icon.style.color = '#dc2626';
    }

    document.getElementById('modal-confirm-titulo').innerText = `Anular Orden ${correlativo}`;
    document.getElementById('modal-confirm-mensaje').innerText =
        `¿Deseas anular esta orden de compra del proveedor ${orden.proveedor_nombre}?`;

    const notaWrapper = document.getElementById('modal-confirm-nota-wrapper');
    const notaTexto = document.getElementById('modal-confirm-nota');

    if (orden.estado === 'RECIBIDA') {
        if (notaWrapper) notaWrapper.style.display = 'block';
        if (notaTexto) notaTexto.innerText =
            'ADVERTENCIA: Esta orden ya fue recibida en almacén. Al anularla, el sistema descontará automáticamente el stock ingresado y registrará la salida por anulación.';
    } else {
        if (notaWrapper) notaWrapper.style.display = 'none';
    }

    const btnAceptar = document.getElementById('modal-confirm-btn-aceptar');
    btnAceptar.onclick = () => {
        if (typeof closeModal === 'function') closeModal('modal-confirmacion-custom');
        ejecutarAnulacionCompra(idOrden);
    };

    modal.classList.add('active');
}

async function ejecutarAnulacionCompra(idOrden) {
    const u = JSON.parse(localStorage.getItem('user')) || {};
    const userRole = u.activeRole || u.role || 'Administrador';

    try {
        const res = await fetch(`${API_COMPRAS}/compras/${idOrden}/anular`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Role': userRole
            },
            body: JSON.stringify({ motivo: 'Anulado por usuario en panel de Compras' })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error al anular orden de compra.');

        if (typeof showNotification === 'function') {
            showNotification(data.message, 'success');
        } else {
            alert(data.message);
        }

        await cargarHistorialCompras();
        if (typeof cargarProductosAlmacen === 'function') {
            cargarProductosAlmacen();
        }

    } catch (err) {
        if (typeof showNotification === 'function') {
            showNotification(err.message, 'error');
        } else {
            alert(err.message);
        }
    }
}


// ==============================================================================
// 5. MODAL FORMAL DE ORDEN DE COMPRA, IMPRESIÓN PDF Y WHATSAPP (HU 19 & 21)
// ==============================================================================

/**
 * Abre el documento formal de la orden de compra en pantalla
 */
async function abrirModalDetalleCompra(idOrden) {
    try {
        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';

        const res = await fetch(`${API_COMPRAS}/compras/${idOrden}`, {
            headers: { 'X-Role': userRole }
        });

        if (!res.ok) throw new Error('No se pudo cargar la orden.');

        const orden = await res.json();
        ordenSeleccionadaAccion = orden;

        document.getElementById('doc-oc-correlativo').innerText = orden.correlativo;
        document.getElementById('doc-oc-fecha-emision').innerText = orden.fecha_emision;
        document.getElementById('doc-oc-fecha-esperada').innerText = orden.fecha_esperada || 'Inmediata';
        document.getElementById('doc-oc-estado').innerText = orden.estado;

        // Datos del proveedor
        document.getElementById('doc-oc-prov-nombre').innerText = orden.proveedor_nombre;
        document.getElementById('doc-oc-prov-ruc').innerText = orden.proveedor_ruc;
        document.getElementById('doc-oc-prov-contacto').innerText = orden.proveedor_contacto || '---';
        document.getElementById('doc-oc-prov-telefono').innerText = orden.proveedor_telefono || '---';
        document.getElementById('doc-oc-prov-correo').innerText = orden.proveedor_correo || '---';

        // Datos de la sede de entrega
        document.getElementById('doc-oc-sede-nombre').innerText = orden.sede_nombre;
        document.getElementById('doc-oc-sede-direccion').innerText = orden.sede_direccion || 'Av. Principal S/N';

        // Tabla de ítems
        const tbody = document.getElementById('doc-oc-items-tbody');
        tbody.innerHTML = '';
        orden.items.forEach((it, idx) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="text-align: center; color: #64748b;">${idx + 1}</td>
                <td style="font-family: monospace; font-weight: 700; color: #1e293b;">${it.codigo_producto}</td>
                <td style="font-weight: 600; color: #0f172a;">${it.nombre_producto}</td>
                <td style="text-align: center; font-weight: 700; color: #0f172a;">${it.cantidad_solicitada}</td>
                <td style="text-align: right; color: #334155;">S/. ${it.precio_unitario.toFixed(2)}</td>
                <td style="text-align: right; font-weight: 800; color: #0284c7;">S/. ${it.subtotal.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });

        // Totales
        const total = orden.total || 0;
        const subtotal = round2(total / 1.18);
        const igv = round2(total - subtotal);

        document.getElementById('doc-oc-subtotal').innerText = `S/. ${subtotal.toFixed(2)}`;
        document.getElementById('doc-oc-igv').innerText = `S/. ${igv.toFixed(2)}`;
        document.getElementById('doc-oc-total').innerText = `S/. ${total.toFixed(2)}`;

        // Observaciones
        const elObs = document.getElementById('doc-oc-observaciones');
        if (elObs) elObs.innerText = orden.observacion ? `Observaciones: ${orden.observacion}` : '';

        const modal = document.getElementById('modal-documento-orden-compra');
        if (modal) modal.classList.add('active');

    } catch (err) {
        if (typeof showNotification === 'function') {
            showNotification(err.message, 'error');
        }
    }
}

/**
 * Imprimir orden de compra con ventana del navegador / Guardar como PDF
 */
function imprimirOrdenCompraActual() {
    const contenedor = document.getElementById('doc-oc-printable-area');
    if (!contenedor) return;

    const ventanaImpresion = window.open('', '_blank');
    ventanaImpresion.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Orden de Compra - Ferretería Jesmi</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 25px; color: #1e293b; }
                table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 15px; }
                th, td { border: 1px solid #cbd5e1; padding: 8px 10px; font-size: 13px; }
                th { background-color: #f1f5f9; color: #334155; text-align: left; }
                .text-right { text-align: right; }
                .text-center { text-align: center; }
                .header-table td { border: none; padding: 4px; }
            </style>
        </head>
        <body>
            ${contenedor.innerHTML}
            <script>
                window.onload = function() { window.print(); window.close(); }
            </script>
        </body>
        </html>
    `);
    ventanaImpresion.document.close();
}

/**
 * Genera enlace formal para enviar la orden por WhatsApp al proveedor
 */
function enviarOrdenPorWhatsApp(idOrden) {
    const orden = listaComprasCache.find(o => o.id_orden_compra === idOrden) || ordenSeleccionadaAccion;
    if (!orden || !orden.proveedor_telefono) {
        if (typeof showNotification === 'function') {
            showNotification('El proveedor no tiene número celular registrado.', 'error');
        }
        return;
    }

    const telLimpio = orden.proveedor_telefono.replace(/[^0-9]/g, '');
    const telefonoWhatsApp = telLimpio.startsWith('51') ? telLimpio : `51${telLimpio}`;

    const mensaje = encodeURIComponent(
        `*FERRETERÍA JESMI - ORDEN DE COMPRA ${orden.correlativo}*\n\n` +
        `Estimados señores de *${orden.proveedor_nombre}*,\n` +
        `Les enviamos la presente Orden de Compra para entrega en nuestra sede *${orden.sede_nombre}*.\n\n` +
        `📋 *Correlativo:* ${orden.correlativo}\n` +
        `📅 *Fecha:* ${orden.fecha_emision}\n` +
        `💰 *Monto Total:* S/. ${orden.total.toFixed(2)}\n\n` +
        `Por favor confirmar recepción y fecha estimada de entrega. Muchas gracias.`
    );

    window.open(`https://wa.me/${telefonoWhatsApp}?text=${mensaje}`, '_blank');
}

/**
 * Utilidad de redondeo seguro
 */
function round2(num) {
    return Math.round((num + Number.EPSILON) * 100) / 100;
}
