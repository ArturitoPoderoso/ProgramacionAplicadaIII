let proformaProductos = [];
let proformaCart = [];

async function cargarModuloProformas() {
    await cargarProductosParaProforma();
    renderCartProforma();
    await cargarProformasEmitidas();
}

async function cargarProductosParaProforma() {
    const user = JSON.parse(localStorage.getItem('user')) || {};
    const listaEl = document.getElementById('proforma-lista-productos');
    if (!listaEl) return;

    listaEl.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b;"><i class="ph ph-spinner ph-spin" style="font-size: 1.5rem;"></i> Cargando productos...</div>';

    try {
        const response = await fetch('http://localhost:8000/api/productos');
        const data = await response.json();

        if (response.ok) {
            proformaProductos = data.map(p => {
                let pv = p.precio_venta || 0;
                let stock = p.stock_total || 0;

                if (user.id_sede && p.inventario_sedes && p.inventario_sedes[user.id_sede]) {
                    pv = p.inventario_sedes[user.id_sede].precio_venta || pv;
                    stock = p.inventario_sedes[user.id_sede].stock_actual || 0;
                } else if (p.inventarios && p.inventarios.length > 0) {
                    pv = p.inventarios[0].precio_venta || pv;
                }

                return {
                    id_producto: p.id_producto,
                    codigo: p.codigo_producto,
                    nombre: p.nombre,
                    categoria: p.categoria || 'General',
                    precio_venta: pv,
                    stock_referencial: stock
                };
            });

            renderListaProductosProforma(proformaProductos);
        } else {
            listaEl.innerHTML = '<div style="text-align: center; padding: 15px; color: #ef4444;">Error al cargar catálogo de productos.</div>';
        }
    } catch (err) {
        console.error('Error fetching proforma products:', err);
        listaEl.innerHTML = '<div style="text-align: center; padding: 15px; color: #ef4444;">Error de conexión con el servidor.</div>';
    }
}

function renderListaProductosProforma(lista) {
    const container = document.getElementById('proforma-lista-productos');
    if (!container) return;

    if (lista.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 25px; color: #94a3b8; font-style: italic;">No se encontraron productos coincidentes.</div>';
        return;
    }

    container.innerHTML = lista.map(p => `
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; transition: all 0.15s ease;">
            <div>
                <div style="font-weight: 700; font-size: 0.88rem; color: #1e293b;">${p.nombre}</div>
                <div style="font-size: 0.78rem; color: #64748b; display: flex; gap: 10px; margin-top: 2px;">
                    <span><i class="ph ph-barcode"></i> ${p.codigo}</span>
                    <span><i class="ph ph-tag"></i> ${p.categoria}</span>
                    <span style="color: #059669; font-weight: 600;"><i class="ph ph-package"></i> Stock Ref: ${p.stock_referencial} un.</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-weight: 800; font-size: 0.95rem; color: #1d4ed8;">S/ ${parseFloat(p.precio_venta).toFixed(2)}</span>
                <button onclick="agregarACartProforma(${p.id_producto})" style="background: #2563eb; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-size: 0.8rem; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 4px; transition: background 0.2s;">
                    <i class="ph ph-plus-circle" style="font-size: 1rem;"></i> Agregar
                </button>
            </div>
        </div>
    `).join('');
}

function filtrarProductosProforma() {
    const q = document.getElementById('proforma-search-prod').value.toLowerCase().trim();
    if (!q) {
        renderListaProductosProforma(proformaProductos);
        return;
    }
    const filtrados = proformaProductos.filter(p => 
        p.nombre.toLowerCase().includes(q) || p.codigo.toLowerCase().includes(q)
    );
    renderListaProductosProforma(filtrados);
}

function agregarACartProforma(idProd) {
    const prod = proformaProductos.find(p => p.id_producto === idProd);
    if (!prod) return;

    const exist = proformaCart.find(item => item.id_producto === idProd);
    if (exist) {
        exist.cantidad += 1;
        exist.subtotal = exist.cantidad * exist.precio_unitario;
    } else {
        proformaCart.push({
            id_producto: prod.id_producto,
            codigo: prod.codigo,
            nombre: prod.nombre,
            cantidad: 1,
            precio_unitario: parseFloat(prod.precio_venta),
            subtotal: parseFloat(prod.precio_venta)
        });
    }

    renderCartProforma();
}

function cambiarCantidadProforma(idProd, nuevaCant) {
    const cant = parseInt(nuevaCant);
    if (isNaN(cant) || cant <= 0) {
        eliminarItemProforma(idProd);
        return;
    }
    const item = proformaCart.find(i => i.id_producto === idProd);
    if (item) {
        item.cantidad = cant;
        item.subtotal = item.cantidad * item.precio_unitario;
    }
    renderCartProforma();
}

function eliminarItemProforma(idProd) {
    proformaCart = proformaCart.filter(i => i.id_producto !== idProd);
    renderCartProforma();
}

function renderCartProforma() {
    const tbody = document.getElementById('proforma-cart-tbody');
    const totalEl = document.getElementById('proforma-cart-total');

    if (!tbody || !totalEl) return;

    if (proformaCart.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 25px; color: #94a3b8; font-style: italic;">
                    No hay productos en la cotización. Selecciona del panel izquierdo.
                </td>
            </tr>
        `;
        totalEl.textContent = 'S/ 0.00';
        return;
    }

    let total = 0;
    tbody.innerHTML = proformaCart.map(item => {
        total += item.subtotal;
        return `
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 8px 10px; font-weight: 600; color: #334155;">${item.nombre}</td>
                <td style="padding: 8px 6px; text-align: center;">
                    <input type="number" min="1" value="${item.cantidad}" onchange="cambiarCantidadProforma(${item.id_producto}, this.value)" style="width: 50px; text-align: center; padding: 3px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 0.82rem;">
                </td>
                <td style="padding: 8px 6px; text-align: right; color: #475569;">S/ ${item.precio_unitario.toFixed(2)}</td>
                <td style="padding: 8px 6px; text-align: right; font-weight: 700; color: #059669;">S/ ${item.subtotal.toFixed(2)}</td>
                <td style="padding: 8px 6px; text-align: center;">
                    <button onclick="eliminarItemProforma(${item.id_producto})" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 1rem;" title="Quitar">
                        <i class="ph ph-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    totalEl.textContent = `S/ ${total.toFixed(2)}`;
}

async function generarEImprimirProforma() {
    if (proformaCart.length === 0) {
        alert('Debe agregar al menos un producto a la cotización.');
        return;
    }

    const user = JSON.parse(localStorage.getItem('user')) || {};
    if (!user.id) {
        alert('Sesión no encontrada. Vuelva a iniciar sesión.');
        return;
    }

    const clienteNombre = document.getElementById('proforma-cliente-nombre').value.trim() || 'Cliente General';
    const clienteDoc = document.getElementById('proforma-cliente-doc').value.trim();
    const validezDias = parseInt(document.getElementById('proforma-validez').value) || 7;

    const payload = {
        id_usuario: user.id,
        id_sede: user.id_sede || 1,
        rol: user.activeRole || user.role || 'Vendedor',
        cliente_nombre: clienteNombre,
        cliente_doc: clienteDoc,
        validez_dias: validezDias,
        detalles: proformaCart.map(i => ({
            id_producto: i.id_producto,
            cantidad: i.cantidad,
            precio_unitario: i.precio_unitario
        }))
    };

    try {
        const response = await fetch('http://localhost:8000/api/proformas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            proformaCart = [];
            renderCartProforma();
            document.getElementById('proforma-cliente-nombre').value = '';
            document.getElementById('proforma-cliente-doc').value = '';

            await cargarProformasEmitidas();
            verDetalleProforma(data.id_proforma);
        } else {
            alert('Error al generar la proforma: ' + (data.error || 'Error en servidor'));
        }
    } catch (err) {
        console.error('Error al emitir proforma:', err);
        alert('Error de conexión con el servidor al emitir proforma.');
    }
}

async function cargarProformasEmitidas() {
    const user = JSON.parse(localStorage.getItem('user')) || {};
    const tbody = document.getElementById('proformas-historial-tbody');
    const q = document.getElementById('proformas-historial-search').value.trim();
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 15px; color: #64748b;"><i class="ph ph-spinner ph-spin"></i> Cargando cotizaciones...</td></tr>';

    try {
        let url = `http://localhost:8000/api/proformas?id_usuario=${user.id || ''}`;
        if (user.id_sede) url += `&sede_id=${user.id_sede}`;
        if (q) url += `&search=${encodeURIComponent(q)}`;

        const response = await fetch(url);
        const data = await response.json();

        if (response.ok) {
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 20px; color: #94a3b8; font-style: italic;">No hay proformas emitidas recientemente.</td></tr>';
                return;
            }

            tbody.innerHTML = data.map(p => `
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="font-weight: 700; color: #2563eb;">${p.correlativo}</td>
                    <td style="color: #475569; font-size: 0.82rem;">${p.fecha_emision}</td>
                    <td style="font-weight: 600; color: #1e293b;">${p.cliente_nombre} ${p.cliente_doc ? `<br><small style="color:#64748b; font-weight:normal;">DOC: ${p.cliente_doc}</small>` : ''}</td>
                    <td><span style="background: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.78rem;">${p.validez_dias} días</span></td>
                    <td style="color: #475569; font-weight: 500;">${p.sede_nombre}</td>
                    <td style="color: #475569;">${p.vendedor}</td>
                    <td style="font-weight: 800; color: #16a34a;">S/ ${parseFloat(p.total).toFixed(2)}</td>
                    <td style="text-align: center;">
                        <button onclick="verDetalleProforma(${p.id_proforma})" style="background: #0284c7; color: white; border: none; border-radius: 6px; padding: 5px 10px; font-size: 0.78rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;">
                            <i class="ph ph-file-text"></i> Ver / Imprimir
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 15px; color: #ef4444;">Error al cargar historial.</td></tr>';
        }
    } catch (err) {
        console.error('Error proformas historial:', err);
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 15px; color: #ef4444;">Error de conexión.</td></tr>';
    }
}

async function verDetalleProforma(idProforma) {
    try {
        const response = await fetch(`http://localhost:8000/api/proformas/${idProforma}`);
        const data = await response.json();

        if (response.ok) {
            const container = document.getElementById('proforma-document-content');
            if (!container) return;

            const itemsHtml = data.detalles.map(d => `
                <tr style="border-bottom: 1px dashed #e2e8f0; font-size: 0.85rem;">
                    <td style="padding: 8px 4px; text-align: center; font-weight: 700;">${d.cantidad}</td>
                    <td style="padding: 8px 4px;">
                        <div style="font-weight: 600; color: #0f172a;">${d.nombre}</div>
                        <div style="font-size: 0.75rem; color: #64748b;">CÓD: ${d.codigo}</div>
                    </td>
                    <td style="padding: 8px 4px; text-align: right;">S/ ${parseFloat(d.precio_unitario).toFixed(2)}</td>
                    <td style="padding: 8px 4px; text-align: right; font-weight: 700; color: #0f172a;">S/ ${parseFloat(d.subtotal).toFixed(2)}</td>
                </tr>
            `).join('');

            container.innerHTML = `
                <!-- Cabecera de la Proforma -->
                <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0f172a; padding-bottom: 15px; margin-bottom: 15px;">
                    <div>
                        <h2 style="font-size: 1.4rem; font-weight: 800; color: #0f172a; margin: 0; text-transform: uppercase;">FERRETERÍA JESSMI</h2>
                        <div style="font-size: 0.8rem; color: #475569; margin-top: 4px;">
                            <strong>Sede:</strong> ${data.sede_nombre}<br>
                            <strong>Dirección:</strong> ${data.sede_direccion}<br>
                            <strong>Teléfono:</strong> ${data.sede_telefono}
                        </div>
                    </div>
                    <div style="text-align: right; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 14px;">
                        <div style="font-size: 0.75rem; font-weight: 700; color: #64748b;">COTIZACIÓN / PROFORMA</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #2563eb; margin-top: 2px;">${data.correlativo}</div>
                        <div style="font-size: 0.75rem; color: #059669; font-weight: 600; margin-top: 4px;">VALIDEZ: ${data.validez_dias} DÍAS</div>
                    </div>
                </div>

                <!-- Datos Cliente y Vendedor -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: #f8fafc; border-radius: 6px; padding: 12px; font-size: 0.82rem; margin-bottom: 15px; border: 1px solid #f1f5f9;">
                    <div>
                        <strong>Cliente:</strong> ${data.cliente_nombre}<br>
                        <strong>DNI/RUC:</strong> ${data.cliente_doc || 'N/A'}
                    </div>
                    <div>
                        <strong>Fecha Emisión:</strong> ${data.fecha_emision}<br>
                        <strong>Vendedor Atendió:</strong> ${data.vendedor}
                    </div>
                </div>

                <!-- Tabla de Productos -->
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px;">
                    <thead>
                        <tr style="background: #0f172a; color: white; font-size: 0.78rem; text-transform: uppercase;">
                            <th style="padding: 6px; width: 45px; text-align: center;">CANT</th>
                            <th style="padding: 6px; text-align: left;">DESCRIPCIÓN DE MATERIALES</th>
                            <th style="padding: 6px; width: 75px; text-align: right;">P. UNIT</th>
                            <th style="padding: 6px; width: 85px; text-align: right;">TOTAL</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${itemsHtml}
                    </tbody>
                </table>

                <!-- Total -->
                <div style="display: flex; justify-content: flex-end; margin-bottom: 20px;">
                    <div style="background: #0f172a; color: white; padding: 8px 18px; border-radius: 6px; text-align: right;">
                        <span style="font-size: 0.85rem; font-weight: 500; display: block;">TOTAL COTIZADO</span>
                        <span style="font-size: 1.35rem; font-weight: 800; color: #4ade80;">S/ ${parseFloat(data.total).toFixed(2)}</span>
                    </div>
                </div>

                <!-- Leyenda Informativa de Stock -->
                <div style="background: #fffbe6; border: 1px solid #ffe58f; border-radius: 6px; padding: 10px; font-size: 0.75rem; color: #855900; text-align: center; font-style: italic;">
                    📌 <strong>Nota Importante:</strong> Esta proforma es únicamente un presupuesto informativo de precios vigentes durante el periodo de validez señalado. <strong>No constituye comprobante de pago ni garantiza reserva de stock en inventario.</strong>
                </div>
            `;

            if (typeof openModal === 'function') {
                openModal('modal-proforma-printable');
            } else {
                const modal = document.getElementById('modal-proforma-printable');
                if (modal) modal.classList.add('active');
            }
        } else {
            alert('No se pudo obtener el detalle de la proforma.');
        }
    } catch (err) {
        console.error('Error verDetalleProforma:', err);
        alert('Error de conexión.');
    }
}

function imprimirDocumentoProforma() {
    const content = document.getElementById('proforma-document-content').innerHTML;
    const printWindow = window.open('', '_blank', 'width=800,height=900');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Imprimir Proforma - Ferretería Jessmi</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
            <style>
                body { font-family: 'Inter', sans-serif; padding: 30px; color: #0f172a; }
                @media print {
                    body { padding: 0; }
                }
            </style>
        </head>
        <body>
            ${content}
            <script>
                window.onload = function() {
                    window.print();
                    setTimeout(() => window.close(), 500);
                }
            </script>
        </body>
        </html>
    `);
    printWindow.document.close();
}
