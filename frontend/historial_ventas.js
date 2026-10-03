/**
 * historial_ventas.js
 * Lógica para la Historia de Usuario HU13: Historial de Ventas.
 * Exclusivo para Administradores y Supervisores.
 */

let ventasHistorialGlobal = [];

document.addEventListener('DOMContentLoaded', () => {
    cargarSedesFiltroHistorial();
});

async function cargarSedesFiltroHistorial() {
    const user = JSON.parse(localStorage.getItem('user')) || {};
    const role = (user.activeRole || user.role || '').toLowerCase();
    const select = document.getElementById('historial-sede-select');

    if (!select) return;

    try {
        const response = await fetch(`${API_URL}/sedes`);
        const sedes = await response.json();

        if (Array.isArray(sedes)) {
            select.innerHTML = '<option value="">Todas las Sedes</option>';
            sedes.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id_sede;
                opt.textContent = s.nombre;
                select.appendChild(opt);
            });

            // Si es supervisor, forzar y bloquear a su sede asignada
            if (role.includes('supervisor') && !role.includes('admin')) {
                if (user.id_sede) {
                    select.value = user.id_sede;
                    select.disabled = true;
                    select.title = "Los supervisores solo ven las ventas de su sede asignada";
                }
            } else {
                select.disabled = false;
            }
        }
    } catch (e) {
        console.error('Error cargando sedes para filtro de historial:', e);
    }
}

async function cargarHistorialVentas() {
    const user = JSON.parse(localStorage.getItem('user')) || {};
    const userRole = (user.activeRole || user.role || '').toLowerCase();

    // Bloqueo estricto para vendedores
    if (userRole.includes('vendedor') && !userRole.includes('admin') && !userRole.includes('supervisor')) {
        if (typeof showNotification === 'function') {
            showNotification('Acceso denegado al historial de ventas', 'error');
        } else {
            alert('Acceso denegado al historial de ventas');
        }
        return;
    }

    const fechaInicio = document.getElementById('historial-fecha-inicio')?.value || '';
    const fechaFin = document.getElementById('historial-fecha-fin')?.value || '';
    const selectSede = document.getElementById('historial-sede-select');
    let sedeId = selectSede?.value || '';

    // Si es supervisor, forzar su sede asignada
    if (userRole.includes('supervisor') && !userRole.includes('admin') && user.id_sede) {
        sedeId = user.id_sede;
    }

    const userId = user.id || 1;

    let queryParams = `?user_id=${userId}`;
    if (fechaInicio) queryParams += `&fecha_inicio=${fechaInicio}`;
    if (fechaFin) queryParams += `&fecha_fin=${fechaFin}`;
    if (sedeId) queryParams += `&sede_id=${sedeId}`;

    try {
        const response = await fetch(`${API_URL}/ventas${queryParams}`);
        const data = await response.json();

        if (response.ok) {
            ventasHistorialGlobal = data.ventas || [];
            actualizarKpisHistorial(data.kpis || {});
            renderTablaHistorialVentas(ventasHistorialGlobal);
        } else {
            console.error('Error del servidor:', data.error);
            if (typeof showNotification === 'function') {
                showNotification(data.error || 'Error al cargar historial', 'error');
            }
        }
    } catch (err) {
        console.error('Error de conexión cargando historial de ventas:', err);
    }
}

function actualizarKpisHistorial(kpis) {
    const elMonto = document.getElementById('kpi-historial-monto');
    const elComprobantes = document.getElementById('kpi-historial-comprobantes');

    if (elMonto) elMonto.textContent = `S/ ${(kpis.monto_total || 0).toFixed(2)}`;
    if (elComprobantes) elComprobantes.textContent = (kpis.total_comprobantes || 0).toString();
}

function renderTablaHistorialVentas(lista) {
    const tbody = document.getElementById('historial-ventas-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (lista.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 25px; color: #6b7280;">No se encontraron registros de ventas para esta sede</td></tr>`;
        return;
    }

    lista.forEach(v => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong style="color: #1e40af; font-family: monospace;">${v.correlativo}</strong></td>
            <td>${v.fecha}</td>
            <td><span style="font-weight: 500;">${v.vendedor}</span></td>
            <td><span class="badge" style="background: #f3f4f6; color: #374151; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">${v.sede}</span></td>
            <td>${v.metodo_pago}</td>
            <td>${v.unidades_totales} unid.</td>
            <td style="font-weight: 700; color: #10b981;">S/ ${(v.total || 0).toFixed(2)}</td>
            <td style="text-align: center;">
                <button class="btn-action" style="background: #2563eb; border-color: #1d4ed8; padding: 5px 12px; font-size: 0.8rem; border-radius: 6px;" onclick="verDetalleBoletaHistorial(${v.id_venta})">
                    <i class="ph ph-receipt"></i> Ver Boleta
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filtrarHistorialVentasLocal() {
    const query = (document.getElementById('historial-search-input')?.value || '').toLowerCase().trim();
    if (!query) {
        renderTablaHistorialVentas(ventasHistorialGlobal);
        return;
    }

    const filtrados = ventasHistorialGlobal.filter(v => {
        const corr = (v.correlativo || '').toLowerCase();
        const vend = (v.vendedor || '').toLowerCase();
        const sede = (v.sede || '').toLowerCase();
        return corr.includes(query) || vend.includes(query) || sede.includes(query);
    });

    renderTablaHistorialVentas(filtrados);
}

function limpiarFiltrosHistorial() {
    const fIni = document.getElementById('historial-fecha-inicio');
    const fFin = document.getElementById('historial-fecha-fin');
    const fSede = document.getElementById('historial-sede-select');
    const fSearch = document.getElementById('historial-search-input');

    if (fIni) fIni.value = '';
    if (fFin) fFin.value = '';
    if (fSearch) fSearch.value = '';
    
    if (fSede && !fSede.disabled) fSede.value = '';

    cargarHistorialVentas();
}

async function verDetalleBoletaHistorial(idVenta) {
    try {
        const response = await fetch(`${API_URL}/ventas/${idVenta}`);
        const data = await response.json();

        if (!response.ok) {
            alert(data.error || 'Error al obtener detalle de la venta');
            return;
        }

        // Usar la función oficial de boleta de caja (caja.js) si está disponible para garantía del 100% de coincidencia visual
        const boletaData = {
            correlativo: data.correlativo,
            fecha: data.fecha,
            cliente: data.cliente || 'Público General',
            dni: data.dni || '----------------',
            vendedor: data.vendedor,
            sede_nombre: data.sede_nombre,
            metodo_pago: data.metodo_pago,
            total: parseFloat(data.total),
            detalles: (data.detalles || []).map(d => ({
                cantidad: d.cantidad,
                nombre: d.nombre,
                precio_unitario: parseFloat(d.precio_unitario),
                subtotal: parseFloat(d.subtotal)
            }))
        };

        if (typeof mostrarBoletaModal === 'function') {
            mostrarBoletaModal(boletaData);
        } else {
            renderBoletaModalFallback(data);
            const modal = document.getElementById('modal-detalle-venta');
            if (modal) modal.classList.add('active');
        }

    } catch (err) {
        console.error('Error obteniendo comprobante:', err);
        alert('Error de conexión con el servidor');
    }
}

function renderBoletaModalFallback(data) {
    const body = document.getElementById('modal-detalle-venta-body');
    if (!body) return;

    let itemsHtml = '';
    (data.detalles || []).forEach(d => {
        itemsHtml += `
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 0.85rem;">
                <span>${d.cantidad}x ${d.nombre}</span>
                <span>S/ ${parseFloat(d.subtotal).toFixed(2)}</span>
            </div>
            <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 6px;">P.Unit: S/ ${parseFloat(d.precio_unitario).toFixed(2)}</div>
        `;
    });

    body.innerHTML = `
        <div style="text-align: center; border-bottom: 1px dashed #ccc; padding-bottom: 10px; margin-bottom: 10px;">
            <h4 style="margin: 0; font-size: 1.1rem; color: #111827;">FERRETERÍA JESSMI</h4>
            <p style="margin: 2px 0; font-size: 0.8rem; color: #4b5563;">${data.sede_nombre}</p>
            <p style="margin: 2px 0; font-size: 0.75rem; color: #6b7280;">${data.sede_direccion}</p>
            <p style="margin: 2px 0; font-size: 0.75rem; color: #6b7280;">Teléf: ${data.sede_telefono}</p>
            <div style="margin-top: 8px; font-weight: bold; color: #1d4ed8; font-size: 0.95rem;">BOLETA DE VENTA: ${data.correlativo}</div>
            <div style="font-size: 0.75rem; color: #6b7280;">Fecha: ${data.fecha}</div>
            <div style="font-size: 0.75rem; color: #6b7280;">Vendedor: ${data.vendedor}</div>
        </div>

        <div style="margin-bottom: 10px;">
            <div style="font-size: 0.8rem; font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 4px;">DESGLOSE DE PRODUCTOS:</div>
            ${itemsHtml}
        </div>

        <div style="border-top: 1px dashed #ccc; padding-top: 10px; font-size: 0.88rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span>Método de Pago:</span>
                <strong>${data.metodo_pago}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 1.1rem; font-weight: bold; color: #111827; margin-top: 6px;">
                <span>TOTAL CANCELADO:</span>
                <span style="color: #10b981;">S/ ${parseFloat(data.total).toFixed(2)}</span>
            </div>
        </div>
    `;
}
