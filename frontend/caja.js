var API_URL = 'http://localhost:8000/api';
let productosGlobal = [];
let carrito = [];

async function cargarProductosCaja() {
    try {
        const user = JSON.parse(localStorage.getItem('user'));
        const sedeId = (user && user.id_sede) ? user.id_sede : 1;
        const response = await fetch(`${API_URL}/productos?sede_id=${sedeId}`);
        productosGlobal = await response.json();
        renderProductos(productosGlobal);
    } catch (error) {
        console.error('Error cargando productos para caja:', error);
    }
}

function renderProductos(productos) {
    const grid = document.getElementById('product-grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (productos.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 40px; color:#94a3b8;">No hay productos disponibles</div>';
        return;
    }

    productos.forEach(p => {
        const sinStock = (p.stock_actual <= 0);
        const estaBajo = (p.stock_actual <= p.stock_minimo);
        
        let stockClass = 'prod-stock';
        if (sinStock) stockClass += ' stock-zero';
        else if (estaBajo) stockClass += ' stock-bajo';

        const card = document.createElement('div');
        card.className = `product-card ${sinStock ? 'no-stock' : ''}`;
        
        if (!sinStock) {
            card.onclick = () => agregarAlCarrito(p);
        }

        card.innerHTML = `
            <div>
                <div class="prod-code">${p.codigo_producto || 'PROD'}</div>
                <div class="prod-title">${p.nombre}</div>
                <div class="prod-category">${p.categoria || 'General'}</div>
            </div>
            <div class="prod-bottom">
                <div class="prod-price">S/ ${(p.precio_venta || 0).toFixed(2)}</div>
                <div class="${stockClass}">${sinStock ? 'Agotado' : `Stock: ${p.stock_actual}`}</div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function filtrarProductos() {
    const input = document.getElementById('search-pos');
    if (!input) return;
    const texto = input.value.toLowerCase().trim();
    const filtrados = productosGlobal.filter(p => 
        (p.nombre || '').toLowerCase().includes(texto) || 
        (p.codigo_producto || '').toLowerCase().includes(texto) ||
        (p.categoria || '').toLowerCase().includes(texto)
    );
    renderProductos(filtrados);
}

function agregarAlCarrito(producto) {
    if (producto.stock_actual <= 0) {
        if (typeof showNotification === 'function') {
            showNotification('El producto está agotado', 'error');
        } else {
            alert('El producto está agotado');
        }
        return;
    }

    const item = carrito.find(i => i.id_producto === producto.id_producto);
    if (item) {
        if (item.cantidad < producto.stock_actual) {
            item.cantidad++;
        } else {
            if (typeof showNotification === 'function') {
                showNotification(`Stock máximo alcanzado (${producto.stock_actual} unidades)`, 'error');
            } else {
                alert(`No puedes agregar más. Stock disponible: ${producto.stock_actual}`);
            }
            return;
        }
    } else {
        carrito.push({
            id_producto: producto.id_producto,
            nombre: producto.nombre,
            codigo: producto.codigo_producto,
            precio_unitario: parseFloat(producto.precio_venta) || 0,
            precio_compra: parseFloat(producto.precio_compra) || 0,
            descuento_unitario: 0,
            cantidad: 1,
            stock_max: producto.stock_actual
        });
    }
    renderCarrito();
}

function actualizarCantidad(id_producto, delta) {
    const item = carrito.find(i => i.id_producto === id_producto);
    if (!item) return;

    if (delta === -999) {
        carrito = carrito.filter(i => i.id_producto !== id_producto);
    } else {
        const nuevaCantidad = item.cantidad + delta;
        if (nuevaCantidad <= 0) {
            carrito = carrito.filter(i => i.id_producto !== id_producto);
        } else if (nuevaCantidad > item.stock_max) {
            if (typeof showNotification === 'function') {
                showNotification(`No puedes superar el stock disponible (${item.stock_max})`, 'error');
            } else {
                alert(`Stock máximo alcanzado: ${item.stock_max}`);
            }
            return;
        } else {
            item.cantidad = nuevaCantidad;
        }
    }
    renderCarrito();
}

function vaciarCarrito() {
    carrito = [];
    renderCarrito();
}

function renderCarrito() {
    const container = document.getElementById('cart-items');
    const totalEl = document.getElementById('cart-total');
    const subtotalEl = document.getElementById('cart-subtotal');
    const descuentoRow = document.getElementById('cart-descuento-row');
    const descuentoLbl = document.getElementById('cart-descuento-lbl');
    const descMontoLbl = document.getElementById('pos-descuento-monto-lbl');
    const errorMsgEl = document.getElementById('pos-descuento-error-msg');
    const inputDesc = document.getElementById('pos-descuento-val');
    const tipoDescEl = document.getElementById('pos-tipo-descuento');
    const btnProcesar = document.getElementById('btn-procesar-venta');
    const tipoDesc = tipoDescEl ? tipoDescEl.value : 'S/';

    if (!container || !totalEl) return;

    if (carrito.length === 0) {
        container.innerHTML = `
            <div style="text-align:center; color:#94a3b8; margin-top:60px;">
                <i class="ph ph-shopping-cart-simple" style="font-size: 3rem; opacity: 0.4; display:block; margin-bottom: 10px;"></i>
                El carrito está vacío
            </div>`;
        totalEl.textContent = 'S/ 0.00';
        if (subtotalEl) subtotalEl.textContent = 'S/ 0.00';
        if (descuentoRow) descuentoRow.style.display = 'none';
        if (descMontoLbl) descMontoLbl.textContent = '-S/ 0.00';
        if (errorMsgEl) errorMsgEl.style.display = 'none';
        if (btnProcesar) {
            btnProcesar.disabled = true;
            btnProcesar.style.opacity = '0.5';
            btnProcesar.style.cursor = 'not-allowed';
        }
        return;
    }

    container.innerHTML = '';
    let subtotalBruto = 0;

    carrito.forEach(item => {
        const itemSubtotal = item.cantidad * item.precio_unitario;
        subtotalBruto += itemSubtotal;

        const div = document.createElement('div');
        div.className = 'cart-item';
        div.innerHTML = `
            <div style="flex: 1;">
                <div class="cart-item-name">${item.nombre}</div>
                <div class="cart-item-price-unit" style="display:flex; gap:10px; align-items:center; font-size:0.78rem; color:#64748b;">
                    <span>S/ ${item.precio_unitario.toFixed(2)} c/u</span>
                </div>
                <div class="cart-item-qty">
                    <button class="qty-btn" onclick="actualizarCantidad(${item.id_producto}, -1)">-</button>
                    <span style="font-weight:700; min-width: 20px; text-align:center;">${item.cantidad}</span>
                    <button class="qty-btn" onclick="actualizarCantidad(${item.id_producto}, 1)">+</button>
                    <span style="margin-left:auto; font-weight:800; color: #1e293b;">S/ ${itemSubtotal.toFixed(2)}</span>
                </div>
            </div>
            <button style="border:none; background:none; color:#ef4444; cursor:pointer; padding: 6px 4px 6px 10px; font-size: 1.1rem;" onclick="actualizarCantidad(${item.id_producto}, -999)" title="Eliminar">
                <i class="ph-fill ph-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });

    // Calcular Descuento Global
    let rawVal = inputDesc ? String(inputDesc.value || '0').replace(',', '.') : '0';
    let descInputVal = parseFloat(rawVal);
    if (isNaN(descInputVal) || descInputVal < 0) descInputVal = 0;

    let descuentoGlobal = 0;
    if (tipoDesc === '%') {
        descuentoGlobal = (subtotalBruto * descInputVal) / 100;
    } else {
        descuentoGlobal = descInputVal;
    }

    // REGLA DE ORO DE DESCUENTOS: Verificar que ningún producto se venda por debajo de su precio_compra
    let tieneError = false;
    let mensajeError = '';

    carrito.forEach(item => {
        const itemSubtotal = item.cantidad * item.precio_unitario;
        const propGlobalItem = subtotalBruto > 0 ? (descuentoGlobal * itemSubtotal / subtotalBruto) : 0;
        const descUnitItem = propGlobalItem / item.cantidad;
        const precioEfectivoUnit = item.precio_unitario - descUnitItem;
        const precioCompra = item.precio_compra || 0;

        if (precioEfectivoUnit < precioCompra) {
            tieneError = true;
            mensajeError = `⚠️ ¡Bloqueado! El precio final (S/ ${precioEfectivoUnit.toFixed(2)}) de "${item.nombre}" no puede ser menor al costo de compra (S/ ${precioCompra.toFixed(2)}).`;
        }
    });

    const totalFinal = Math.max(0, subtotalBruto - descuentoGlobal);

    if (subtotalEl) subtotalEl.textContent = `S/ ${subtotalBruto.toFixed(2)}`;

    if (descuentoGlobal > 0) {
        if (descuentoRow) descuentoRow.style.display = 'flex';
        if (descuentoLbl) descuentoLbl.textContent = `-S/ ${descuentoGlobal.toFixed(2)}`;
        if (descMontoLbl) descMontoLbl.textContent = `-S/ ${descuentoGlobal.toFixed(2)}`;
    } else {
        if (descuentoRow) descuentoRow.style.display = 'none';
        if (descMontoLbl) descMontoLbl.textContent = `-S/ 0.00`;
    }

    if (tieneError) {
        if (errorMsgEl) {
            errorMsgEl.style.display = 'block';
            errorMsgEl.textContent = mensajeError;
        }
        if (inputDesc) inputDesc.style.border = '2px solid #ef4444';
        totalEl.style.color = '#ef4444';
        if (btnProcesar) {
            btnProcesar.disabled = true;
            btnProcesar.style.opacity = '0.5';
            btnProcesar.style.cursor = 'not-allowed';
        }
    } else {
        if (errorMsgEl) errorMsgEl.style.display = 'none';
        if (inputDesc) inputDesc.style.border = '1px solid #cbd5e1';
        totalEl.style.color = '#16a34a';
        if (btnProcesar) {
            btnProcesar.disabled = false;
            btnProcesar.style.opacity = '1';
            btnProcesar.style.cursor = 'pointer';
        }
    }

    totalEl.textContent = `S/ ${totalFinal.toFixed(2)}`;
}

async function procesarVenta() {
    if (carrito.length === 0) {
        if (typeof showNotification === 'function') {
            showNotification('El carrito está vacío. Agrega productos primero.', 'error');
        } else {
            alert('El carrito está vacío');
        }
        return;
    }

    const user = JSON.parse(localStorage.getItem('user'));
    if (!user || !user.id) {
        alert('Sesión no encontrada. Por favor inicia sesión de nuevo.');
        return;
    }

    const metodoPagoEl = document.getElementById('metodo-pago');
    const metodoPago = metodoPagoEl ? metodoPagoEl.value : 'Efectivo';

    const clienteNomInput = document.getElementById('pos-cliente-nombre');
    const clienteDocInput = document.getElementById('pos-cliente-doc');
    const inputDesc = document.getElementById('pos-descuento-val');
    const tipoDescEl = document.getElementById('pos-tipo-descuento');
    const tipoDesc = tipoDescEl ? tipoDescEl.value : 'S/';

    const clienteNombre = clienteNomInput && clienteNomInput.value.trim() ? clienteNomInput.value.trim() : 'Público General';
    const clienteDoc = clienteDocInput && clienteDocInput.value.trim() ? clienteDocInput.value.trim() : '----------------';

    let rawVal = inputDesc ? String(inputDesc.value || '0').replace(',', '.') : '0';
    let descInputVal = parseFloat(rawVal);
    if (isNaN(descInputVal) || descInputVal < 0) descInputVal = 0;

    let subtotalBruto = carrito.reduce((acc, i) => acc + (i.cantidad * i.precio_unitario), 0);
    let descuentoTotal = (tipoDesc === '%') ? (subtotalBruto * descInputVal) / 100 : descInputVal;

    // Validación cliente antes de enviar
    for (let item of carrito) {
        const propGlobalItem = subtotalBruto > 0 ? (descuentoTotal * (item.cantidad * item.precio_unitario) / subtotalBruto) : 0;
        const descUnitItem = propGlobalItem / item.cantidad;
        const precioEfectivoUnit = item.precio_unitario - descUnitItem;
        const precioCompra = item.precio_compra || 0;

        if (precioEfectivoUnit < precioCompra) {
            alert(`No se puede procesar la venta: El descuento aplicado deja a "${item.nombre}" en S/ ${precioEfectivoUnit.toFixed(2)}, por debajo del costo de compra S/ ${precioCompra.toFixed(2)}.`);
            return;
        }
    }

    const payload = {
        metodo_pago: metodoPago,
        id_usuario: user.id,
        descuento_total: round2(descuentoTotal),
        detalles: carrito.map(item => {
            const propGlobalItem = subtotalBruto > 0 ? (descuentoTotal * (item.cantidad * item.precio_unitario) / subtotalBruto) : 0;
            const descUnitItem = propGlobalItem / item.cantidad;
            return {
                id_producto: item.id_producto,
                cantidad: item.cantidad,
                precio_unitario: item.precio_unitario,
                descuento_unitario: round2(descUnitItem)
            };
        })
    };

    try {
        const response = await fetch(`${API_URL}/ventas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (response.ok) {
            const copiaCarrito = [...carrito];
            const totalCobrado = Math.max(0, subtotalBruto - descuentoTotal);

            mostrarBoletaVenta({
                correlativo: result.correlativo,
                fecha: result.fecha || new Date().toLocaleString(),
                metodo_pago: result.metodo_pago,
                subtotal: subtotalBruto,
                descuento_total: descuentoTotal,
                total: totalCobrado,
                detalles: copiaCarrito,
                sede_nombre: result.sede_nombre || 'Sede Principal',
                sede_direccion: result.sede_direccion || 'Av. Central 123, Los Olivos',
                sede_telefono: result.sede_telefono || '01-1234567',
                vendedor: result.vendedor || user.first_name || 'Vendedor',
                cliente: clienteNombre,
                dni: clienteDoc
            });

            if (typeof showNotification === 'function') {
                showNotification(`¡Venta registrada exitosamente!`, 'success');
            }

            carrito = [];
            if (clienteNomInput) clienteNomInput.value = '';
            if (clienteDocInput) clienteDocInput.value = '';
            if (inputDesc) inputDesc.value = '';
            renderCarrito();

            cargarProductosCaja();
            if (typeof cargarProductosAlmacen === 'function') {
                cargarProductosAlmacen();
            }
        } else {
            if (typeof showNotification === 'function') {
                showNotification(result.error || 'Error al procesar la venta', 'error');
            } else {
                alert(result.error || 'Error procesando la venta');
            }
        }
    } catch (error) {
        console.error('Error procesando venta:', error);
        alert('Error de conexión con el servidor backend');
    }
}

function round2(val) {
    return Math.round((val + Number.EPSILON) * 100) / 100;
}

function mostrarBoletaVenta(data) {
    const paper = document.getElementById('boleta-printable');
    if (!paper) return;

    let itemsRowsHtml = '';
    data.detalles.forEach(item => {
        const sub = (item.cantidad * item.precio_unitario).toFixed(2);
        itemsRowsHtml += `
            <tr>
                <td style="text-align: center; font-weight: 700;">${item.cantidad}</td>
                <td>${item.nombre}</td>
                <td style="text-align: right;">S/ ${item.precio_unitario.toFixed(2)}</td>
                <td style="text-align: right; font-weight: 700;">S/ ${sub}</td>
            </tr>
        `;
    });

    const descTotal = data.descuento_total || 0;
    const subtotal = data.subtotal || (data.total + descTotal);

    let totalRowsHtml = '';
    if (descTotal > 0) {
        totalRowsHtml = `
            <tr>
                <td style="background: #f8fafc; font-size: 0.8rem; color:#64748b;">SUBTOTAL</td>
                <td style="background: #ffffff; color: #475569; font-size: 0.85rem; text-align:right;">S/ ${subtotal.toFixed(2)}</td>
            </tr>
            <tr>
                <td style="background: #f8fafc; font-size: 0.8rem; color:#dc2626;">DESCUENTO</td>
                <td style="background: #ffffff; color: #dc2626; font-size: 0.85rem; font-weight:700; text-align:right;">-S/ ${descTotal.toFixed(2)}</td>
            </tr>
        `;
    }
    totalRowsHtml += `
        <tr>
            <td style="background: #0f172a; color:white; font-size: 0.85rem; font-weight:700;">TOTAL</td>
            <td style="background: #0f172a; color: #4ade80; font-size: 1.1rem; font-weight:800; text-align:right;">S/ ${data.total.toFixed(2)}</td>
        </tr>
    `;

    paper.innerHTML = `
        <div class="boleta-header">
            <div class="boleta-brand-box">
                <div class="boleta-brand-title">FERRETERÍA JESSMI</div>
                <div class="boleta-brand-tagline">Todo para tu proyecto</div>
                <div class="boleta-brand-info">
                    📍 ${data.sede_direccion}<br>
                    📞 Tel: ${data.sede_telefono}
                </div>
            </div>
            <div class="boleta-ruc-box">
                <div class="boleta-ruc-title">BOLETA DE VENTA</div>
                <div class="boleta-ruc-num">N° ${data.correlativo}</div>
                <div class="boleta-ruc-sub">R.U.C. 20601234567</div>
                <div style="font-size: 0.72rem; color: #64748b; margin-top:2px;">Serie 001</div>
            </div>
        </div>

        <div class="boleta-client-grid">
            <div class="boleta-client-field">
                <span class="boleta-client-label">Cliente:</span>
                <span class="boleta-client-val">${data.cliente}</span>
            </div>
            <div class="boleta-client-field" style="justify-content: flex-end;">
                <span class="boleta-client-label">Fecha:</span>
                <span class="boleta-client-val">${data.fecha}</span>
            </div>
            <div class="boleta-client-field">
                <span class="boleta-client-label">DNI/RUC:</span>
                <span class="boleta-client-val">${data.dni}</span>
            </div>
            <div class="boleta-client-field" style="justify-content: flex-end;">
                <span class="boleta-client-label">Atendido por:</span>
                <span class="boleta-client-val">${data.vendedor}</span>
            </div>
        </div>

        <table class="boleta-table">
            <thead>
                <tr>
                    <th style="width: 10%;">CANT.</th>
                    <th>DESCRIPCIÓN</th>
                    <th style="width: 22%; text-align: right;">P. UNIT.</th>
                    <th style="width: 22%; text-align: right;">IMPORTE</th>
                </tr>
            </thead>
            <tbody>
                ${itemsRowsHtml}
            </tbody>
        </table>

        <div class="boleta-total-box">
            <div style="font-size: 0.78rem; color: #64748b; line-height: 1.4;">
                Forma de Pago: <strong>${data.metodo_pago}</strong><br>
                Sede: <strong>${data.sede_nombre}</strong>
            </div>
            <table class="boleta-total-table">
                ${totalRowsHtml}
            </table>
        </div>

        <div class="boleta-footer">
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="ph ph-qr-code" style="font-size: 2.2rem; color: #334155;"></i>
                <div>
                    <strong style="font-style: italic; font-size: 0.85rem;">¡Gracias por su compra!</strong><br>
                    <span style="font-size: 0.72rem; color: #94a3b8;">Comprobante de Pago Electrónico</span>
                </div>
            </div>
            <div style="font-size: 0.72rem; color: #94a3b8; font-style: italic;">
                * No se aceptan cambios ni devoluciones *
            </div>
        </div>
    `;

    if (typeof openModal === 'function') {
        openModal('modal-ticket-venta');
    }
}

function imprimirBoleta() {
    window.print();
}
