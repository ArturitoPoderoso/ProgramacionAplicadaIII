// Modulo para la administracion de clientes del sistema

let listaClientesCache = [];

// Carga los clientes desde la API y actualiza la tabla y tarjetas de resumen
async function cargarClientes() {
    try {
        const baseUrl = window.API_BASE_URL || 'http://localhost:8000/api';
        const res = await fetch(`${baseUrl}/clientes`);
        if (!res.ok) throw new Error('Error al consultar clientes');

        listaClientesCache = await res.json();
        renderizarTablaClientes(listaClientesCache);
        actualizarEstadisticasClientes(listaClientesCache);
    } catch (err) {
        console.error('Error cargando clientes:', err);
        if (window.Toast) Toast.error('No se pudo cargar la lista de clientes.');
    }
}

// Dibuja las filas de la tabla de clientes en el DOM
function renderizarTablaClientes(clientes) {
    const tbody = document.getElementById('clientes-tbody');
    if (!tbody) return;

    if (!clientes || clientes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 40px; color: #94a3b8;">
                    <i class="ph-fill ph-users" style="font-size: 2.2rem; display: block; margin-bottom: 8px;"></i>
                    No se encontraron clientes registrados.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = clientes.map(c => {
        const badgeColor = c.tipo_documento === 'RUC' ? '#d97706' : '#0284c7';
        const badgeBg = c.tipo_documento === 'RUC' ? '#fef3c7' : '#e0f2fe';
        return `
            <tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.15s;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='white'">
                <td style="padding: 14px 16px;">
                    <span style="font-size: 0.72rem; font-weight: 700; padding: 2px 7px; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor}; margin-right: 6px;">
                        ${c.tipo_documento || 'DNI'}
                    </span>
                    <span style="font-family: monospace; font-weight: 700; color: #0f172a;">${c.numero_documento}</span>
                </td>
                <td style="padding: 14px 16px; font-weight: 600; color: #1e293b;">
                    ${c.nombres_razon_social}
                </td>
                <td style="padding: 14px 16px; color: #475569; font-size: 0.88rem;">
                    ${c.telefono ? `<i class="ph ph-phone" style="color: #64748b; margin-right: 4px;"></i>${c.telefono}` : '<span style="color:#cbd5e1;">---</span>'}
                </td>
                <td style="padding: 14px 16px; color: #475569; font-size: 0.88rem;">
                    ${c.correo ? `<i class="ph ph-envelope" style="color: #64748b; margin-right: 4px;"></i>${c.correo}` : '<span style="color:#cbd5e1;">---</span>'}
                </td>
                <td style="padding: 14px 16px; color: #64748b; font-size: 0.85rem; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    ${c.direccion || '<span style="color:#cbd5e1;">---</span>'}
                </td>
                <td style="padding: 14px 16px; text-align: center;">
                    <div style="display: inline-flex; gap: 6px;">
                        <button onclick="abrirModalEditarCliente(${c.id_cliente})" title="Editar Cliente" style="background: #f1f5f9; border: 1px solid #cbd5e1; color: #0284c7; width: 32px; height: 32px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                            <i class="ph-bold ph-pencil-simple"></i>
                        </button>
                        <button onclick="eliminarCliente(${c.id_cliente}, '${c.nombres_razon_social.replace(/'/g, "\\'")}')" title="Eliminar Cliente" style="background: #fef2f2; border: 1px solid #fecaca; color: #ef4444; width: 32px; height: 32px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                            <i class="ph-bold ph-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Calcula y muestra las tarjetas de total, personas y empresas
function actualizarEstadisticasClientes(clientes) {
    const elTotal = document.getElementById('cli-stat-total');
    const elDni = document.getElementById('cli-stat-dni');
    const elRuc = document.getElementById('cli-stat-ruc');

    if (elTotal) elTotal.innerText = clientes.length;
    if (elDni) elDni.innerText = clientes.filter(c => c.tipo_documento === 'DNI').length;
    if (elRuc) elRuc.innerText = clientes.filter(c => c.tipo_documento === 'RUC').length;
}

// Filtra la tabla localmente segun el texto ingresado en el buscador
function filtrarClientes() {
    const input = document.getElementById('clientes-search-input');
    if (!input) return;
    const term = input.value.trim().toLowerCase();

    if (!term) {
        renderizarTablaClientes(listaClientesCache);
        return;
    }

    const filtrados = listaClientesCache.filter(c => {
        return (c.numero_documento && c.numero_documento.toLowerCase().includes(term)) ||
               (c.nombres_razon_social && c.nombres_razon_social.toLowerCase().includes(term)) ||
               (c.telefono && c.telefono.toLowerCase().includes(term)) ||
               (c.correo && c.correo.toLowerCase().includes(term)) ||
               (c.direccion && c.direccion.toLowerCase().includes(term));
    });

    renderizarTablaClientes(filtrados);
}

// Ajusta los placeholders y limites segun el tipo de documento seleccionado
function onCambioTipoDocumentoCliente() {
    const tipo = document.getElementById('cli-tipo-doc').value;
    const inputDoc = document.getElementById('cli-numero-doc');
    if (!inputDoc) return;

    if (tipo === 'DNI') {
        inputDoc.maxLength = 8;
        inputDoc.placeholder = 'Ej: 71234567';
    } else if (tipo === 'RUC') {
        inputDoc.maxLength = 11;
        inputDoc.placeholder = 'Ej: 20601234567';
    } else {
        inputDoc.maxLength = 12;
        inputDoc.placeholder = 'N° de Carnet';
    }
}

// Abre el modal para crear un cliente nuevo con los campos vacios
function abrirModalCrearCliente() {
    document.getElementById('edit-cliente-id').value = '';
    document.getElementById('modal-cliente-title').innerHTML = '<i class="ph-fill ph-user-plus"></i> Registrar Nuevo Cliente';
    document.getElementById('cli-tipo-doc').value = 'DNI';
    document.getElementById('cli-numero-doc').value = '';
    document.getElementById('cli-nombre').value = '';
    document.getElementById('cli-telefono').value = '';
    document.getElementById('cli-correo').value = '';
    document.getElementById('cli-direccion').value = '';
    onCambioTipoDocumentoCliente();

    if (typeof openModal === 'function') {
        openModal('modal-cliente');
    } else {
        const m = document.getElementById('modal-cliente');
        if (m) m.classList.add('active');
    }
}

// Abre el modal cargando los datos del cliente para modificarlos
function abrirModalEditarCliente(idCliente) {
    const cliente = listaClientesCache.find(c => c.id_cliente === idCliente);
    if (!cliente) return;

    document.getElementById('edit-cliente-id').value = cliente.id_cliente;
    document.getElementById('modal-cliente-title').innerHTML = '<i class="ph-fill ph-pencil-simple"></i> Editar Información del Cliente';
    document.getElementById('cli-tipo-doc').value = cliente.tipo_documento || 'DNI';
    document.getElementById('cli-numero-doc').value = cliente.numero_documento || '';
    document.getElementById('cli-nombre').value = cliente.nombres_razon_social || '';
    document.getElementById('cli-telefono').value = cliente.telefono || '';
    document.getElementById('cli-correo').value = cliente.correo || '';
    document.getElementById('cli-direccion').value = cliente.direccion || '';
    onCambioTipoDocumentoCliente();

    if (typeof openModal === 'function') {
        openModal('modal-cliente');
    } else {
        const m = document.getElementById('modal-cliente');
        if (m) m.classList.add('active');
    }
}

// Valida el formulario y guarda los cambios en el servidor
async function guardarCliente() {
    const idCliente = document.getElementById('edit-cliente-id').value;
    const tipoDoc = document.getElementById('cli-tipo-doc').value;
    const numDoc = document.getElementById('cli-numero-doc').value.trim();
    const nombre = document.getElementById('cli-nombre').value.trim();
    const telefono = document.getElementById('cli-telefono').value.trim();
    const correo = document.getElementById('cli-correo').value.trim();
    const direccion = document.getElementById('cli-direccion').value.trim();

    if (!numDoc) {
        if (window.Toast) Toast.error('El número de documento es obligatorio.');
        return;
    }

    if (!nombre) {
        if (window.Toast) Toast.error('El nombre o razón social es obligatorio.');
        return;
    }

    if (tipoDoc === 'DNI' && (!/^\d{8}$/.test(numDoc))) {
        if (window.Toast) Toast.error('El DNI debe tener exactamente 8 dígitos numéricos.');
        return;
    }

    if (tipoDoc === 'RUC' && (!/^\d{11}$/.test(numDoc) || (!numDoc.startsWith('10') && !numDoc.startsWith('20')))) {
        if (window.Toast) Toast.error('El RUC debe tener 11 dígitos y empezar con 10 o 20.');
        return;
    }

    const payload = {
        tipo_documento: tipoDoc,
        numero_documento: numDoc,
        nombres_razon_social: nombre,
        telefono: telefono,
        correo: correo,
        direccion: direccion
    };

    const baseUrl = window.API_BASE_URL || 'http://localhost:8000/api';
    const isEdit = Boolean(idCliente);
    const url = isEdit ? `${baseUrl}/clientes/${idCliente}` : `${baseUrl}/clientes`;
    const method = isEdit ? 'PUT' : 'POST';

    const btn = document.getElementById('btn-guardar-cliente');
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error al guardar el cliente');

        if (window.Toast) Toast.success(isEdit ? 'Cliente actualizado con éxito' : 'Cliente registrado con éxito');

        if (typeof closeModal === 'function') {
            closeModal('modal-cliente');
        } else {
            const m = document.getElementById('modal-cliente');
            if (m) m.classList.remove('active');
        }

        await cargarClientes();
    } catch (err) {
        console.error('Error guardando cliente:', err);
        if (window.Toast) Toast.error(err.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Elimina el cliente tras confirmacion del usuario
async function eliminarCliente(idCliente, nombreCliente) {
    if (!confirm(`¿Estás seguro de eliminar a "${nombreCliente}" del directorio de clientes?`)) {
        return;
    }

    const baseUrl = window.API_BASE_URL || 'http://localhost:8000/api';
    try {
        const res = await fetch(`${baseUrl}/clientes/${idCliente}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error al eliminar cliente');

        if (window.Toast) Toast.success('Cliente eliminado correctamente');
        await cargarClientes();
    } catch (err) {
        console.error('Error eliminando cliente:', err);
        if (window.Toast) Toast.error(err.message);
    }
}

// Exponer funciones en window para que los botones onclick funcionen
window.cargarClientes = cargarClientes;
window.renderizarTablaClientes = renderizarTablaClientes;
window.filtrarClientes = filtrarClientes;
window.onCambioTipoDocumentoCliente = onCambioTipoDocumentoCliente;
window.abrirModalCrearCliente = abrirModalCrearCliente;
window.abrirModalEditarCliente = abrirModalEditarCliente;
window.guardarCliente = guardarCliente;
window.eliminarCliente = eliminarCliente;
