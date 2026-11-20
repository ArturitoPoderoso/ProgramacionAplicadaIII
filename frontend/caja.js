// Modulo de Caja y Punto de Venta (POS)
// Administra el catalogo de productos, el carrito de compras, descuentos y emision de tickets

const CajaModule = {
    apiUrl: window.API_BASE_URL || 'http://localhost:8000/api',
    productosGlobal: [],
    carrito: [],
    promocionesActivas: [],
    supervisorAutorizadoInfo: null,
    _filterTimeout: null,

    notify(message, type = 'success') {
        if (window.Toast && typeof window.Toast[type] === 'function') {
            window.Toast[type](message);
        } else if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            alert(message);
        }
    },

    round2(val) {
        return Math.round((val + Number.EPSILON) * 100) / 100;
    },

    async cargarProductosCaja() {
        try {
            const user = JSON.parse(localStorage.getItem('user'));
            const sedeId = (user && user.id_sede) ? user.id_sede : 1;
            const [resProd, resPromo] = await Promise.all([
                fetch(`${this.apiUrl}/productos?sede_id=${sedeId}`),
                fetch(`${this.apiUrl}/promociones/activas`)
            ]);
            this.productosGlobal = await resProd.json();
            if (resPromo.ok) {
                this.promocionesActivas = await resPromo.json();
            }
            this.renderProductos(this.productosGlobal);
            this.renderCarrito();
        } catch (error) {
            console.error('Error cargando productos para caja:', error);
        }
    },

    renderProductos(productos) {
        const grid = document.getElementById('product-grid');
        if (!grid) return;
        grid.innerHTML = '';

        if (!productos || productos.length === 0) {
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
                card.onclick = () => this.agregarAlCarrito(p);
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
    },

    filtrarProductos() {
        clearTimeout(this._filterTimeout);
        this._filterTimeout = setTimeout(() => {
            const input = document.getElementById('search-pos');
            if (!input) return;
            const texto = input.value.toLowerCase().trim();
            const filtrados = this.productosGlobal.filter(p =>
                (p.nombre || '').toLowerCase().includes(texto) ||
                (p.codigo_producto || '').toLowerCase().includes(texto) ||
                (p.categoria || '').toLowerCase().includes(texto)
            );
            this.renderProductos(filtrados);
        }, 200);
    },

    agregarAlCarrito(producto) {
        if (producto.stock_actual <= 0) {
            this.notify('El producto está agotado', 'error');
            return;
        }

        const item = this.carrito.find(i => i.id_producto === producto.id_producto);
        if (item) {
            if (item.cantidad < producto.stock_actual) {
                item.cantidad++;
            } else {
                this.notify(`Stock máximo alcanzado (${producto.stock_actual} unidades)`, 'error');
                return;
            }
        } else {
            this.carrito.push({
                id_producto: producto.id_producto,
                id_categoria: producto.id_categoria,
                nombre: producto.nombre,
                codigo: producto.codigo_producto,
                precio_unitario: parseFloat(producto.precio_venta) || 0,
                precio_compra: parseFloat(producto.precio_compra) || 0,
                descuento_unitario: 0,
                cantidad: 1,
                stock_max: producto.stock_actual
            });
        }
        this.renderCarrito();
    },

    actualizarCantidad(id_producto, delta) {
        const item = this.carrito.find(i => i.id_producto === id_producto);
        if (!item) return;

        if (delta === -999) {
            this.carrito = this.carrito.filter(i => i.id_producto !== id_producto);
        } else {
            const nuevaCantidad = item.cantidad + delta;
            if (nuevaCantidad <= 0) {
                this.carrito = this.carrito.filter(i => i.id_producto !== id_producto);
            } else if (nuevaCantidad > item.stock_max) {
                this.notify(`No puedes superar el stock disponible (${item.stock_max})`, 'error');
                return;
            } else {
                item.cantidad = nuevaCantidad;
            }
        }
        this.renderCarrito();
    },

    vaciarCarrito() {
        this.carrito = [];
        this.renderCarrito();
    },

    renderCarrito() {
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

        if (this.carrito.length === 0) {
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

        this.carrito.forEach(item => {
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

        // Aplica promociones activas si coinciden con productos o categorias
        let descuentoTemporada = 0;
        let nombreCampañaActiva = '';

        if (this.promocionesActivas && this.promocionesActivas.length > 0) {
            this.promocionesActivas.forEach(promo => {
                this.carrito.forEach(item => {
                    const itemSubtotal = item.cantidad * item.precio_unitario;
                    let aplica = false;
                    if (promo.aplica_a === 'TODOS') aplica = true;
                    else if (promo.aplica_a === 'CATEGORIA' && promo.id_categoria && parseInt(promo.id_categoria) === parseInt(item.id_categoria)) aplica = true;
                    else if (promo.aplica_a === 'PRODUCTO' && promo.id_producto && parseInt(promo.id_producto) === parseInt(item.id_producto)) aplica = true;

                    if (aplica) {
                        nombreCampañaActiva = promo.nombre;
                        if (promo.tipo_descuento === 'PORCENTAJE') {
                            descuentoTemporada += (itemSubtotal * promo.valor) / 100;
                        } else {
                            descuentoTemporada += Math.min(itemSubtotal, promo.valor * item.cantidad);
                        }
                    }
                });
            });
        }

        const bannerPromo = document.getElementById('pos-promo-banner');
        const lblPromoNom = document.getElementById('pos-promo-nombre');
        const lblPromoMonto = document.getElementById('pos-promo-monto');

        if (descuentoTemporada > 0 && bannerPromo) {
            bannerPromo.style.display = 'block';
            if (lblPromoNom) lblPromoNom.textContent = `🔥 ${nombreCampañaActiva}`;
            if (lblPromoMonto) lblPromoMonto.textContent = `-S/ ${descuentoTemporada.toFixed(2)}`;
        } else if (bannerPromo) {
            bannerPromo.style.display = 'none';
        }

        // Aplica el descuento manual si el supervisor ya autorizo
        let descuentoSupervisor = 0;
        if (this.supervisorAutorizadoInfo) {
            let rawVal = inputDesc ? String(inputDesc.value || '0').replace(',', '.') : '0';
            let descInputVal = parseFloat(rawVal);
            if (isNaN(descInputVal) || descInputVal < 0) descInputVal = 0;

            if (tipoDesc === '%') {
                descuentoSupervisor = (subtotalBruto * descInputVal) / 100;
            } else {
                descuentoSupervisor = descInputVal;
            }
        }

        const descuentoGlobal = descuentoTemporada + descuentoSupervisor;

        // Validacion de precio: ningun producto puede salir por debajo de su costo de compra
        let tieneError = false;
        let mensajeError = '';

        this.carrito.forEach(item => {
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
    },

    async procesarVenta() {
        if (this.carrito.length === 0) {
            this.notify('El carrito está vacío. Agrega productos primero.', 'error');
            return;
        }

        const user = JSON.parse(localStorage.getItem('user'));
        if (!user || !user.id) {
            this.notify('Sesión no encontrada. Por favor inicia sesión de nuevo.', 'error');
            return;
        }

        const metodoPagoEl = document.getElementById('metodo-pago');
        const metodoPago = metodoPagoEl ? metodoPagoEl.value : 'Efectivo';

        const clienteNomInput = document.getElementById('pos-cliente-nombre');
        const clienteDocInput = document.getElementById('pos-cliente-doc');
        const inputDesc = document.getElementById('pos-descuento-val');
        const tipoDescEl = document.getElementById('pos-tipo-descuento');
        const tipoDesc = tipoDescEl ? tipoDescEl.value : 'S/';

        const clienteNombre = clienteNomInput ? clienteNomInput.value.trim() : '';
        const clienteDoc = clienteDocInput ? clienteDocInput.value.trim() : '';

        if (clienteNomInput) clienteNomInput.style.border = '1px solid #cbd5e1';
        if (clienteDocInput) clienteDocInput.style.border = '1px solid #cbd5e1';

        // Validación obligatoria: Nombre de Cliente
        if (!clienteNombre) {
            if (clienteNomInput) {
                clienteNomInput.style.border = '2px solid #ef4444';
                clienteNomInput.focus();
            }
            this.notify('El Nombre del Cliente es obligatorio para procesar la venta.', 'error');
            return;
        }

        // Validación obligatoria: DNI / RUC
        if (!clienteDoc) {
            if (clienteDocInput) {
                clienteDocInput.style.border = '2px solid #ef4444';
                clienteDocInput.focus();
            }
            this.notify('El DNI o RUC del Cliente es obligatorio para procesar la venta.', 'error');
            return;
        }

        if (clienteDoc.length < 8) {
            if (clienteDocInput) {
                clienteDocInput.style.border = '2px solid #ef4444';
                clienteDocInput.focus();
            }
            this.notify('El documento debe tener al menos 8 caracteres (DNI: 8 dígitos / RUC: 11 dígitos).', 'error');
            return;
        }

        let subtotalBruto = this.carrito.reduce((acc, i) => acc + (i.cantidad * i.precio_unitario), 0);

        // 1. Descuento por Temporada Activa
        let descuentoTemporada = 0;
        if (this.promocionesActivas && this.promocionesActivas.length > 0) {
            this.promocionesActivas.forEach(promo => {
                this.carrito.forEach(item => {
                    const itemSub = item.cantidad * item.precio_unitario;
                    let aplica = false;
                    if (promo.aplica_a === 'TODOS') aplica = true;
                    else if (promo.aplica_a === 'CATEGORIA' && promo.id_categoria && parseInt(promo.id_categoria) === parseInt(item.id_categoria)) aplica = true;
                    else if (promo.aplica_a === 'PRODUCTO' && promo.id_producto && parseInt(promo.id_producto) === parseInt(item.id_producto)) aplica = true;

                    if (aplica) {
                        if (promo.tipo_descuento === 'PORCENTAJE') {
                            descuentoTemporada += (itemSub * promo.valor) / 100;
                        } else {
                            descuentoTemporada += Math.min(itemSub, promo.valor * item.cantidad);
                        }
                    }
                });
            });
        }

        // 2. Descuento Autorizado por Supervisor
        let descuentoSupervisor = 0;
        if (this.supervisorAutorizadoInfo) {
            let rawVal = inputDesc ? String(inputDesc.value || '0').replace(',', '.') : '0';
            let descInputVal = parseFloat(rawVal);
            if (isNaN(descInputVal) || descInputVal < 0) descInputVal = 0;

            if (tipoDesc === '%') {
                descuentoSupervisor = (subtotalBruto * descInputVal) / 100;
            } else {
                descuentoSupervisor = descInputVal;
            }
        }

        let descuentoTotal = descuentoTemporada + descuentoSupervisor;

        // Validación cliente antes de enviar
        for (let item of this.carrito) {
            const propGlobalItem = subtotalBruto > 0 ? (descuentoTotal * (item.cantidad * item.precio_unitario) / subtotalBruto) : 0;
            const descUnitItem = propGlobalItem / item.cantidad;
            const precioEfectivoUnit = item.precio_unitario - descUnitItem;
            const precioCompra = item.precio_compra || 0;

            if (precioEfectivoUnit < precioCompra) {
                this.notify(`No se puede procesar la venta: El descuento aplicado deja a "${item.nombre}" por debajo del costo de compra.`, 'error');
                return;
            }
        }

        const clienteIdInput = document.getElementById('pos-cliente-id');
        const idClienteVal = clienteIdInput && clienteIdInput.value ? parseInt(clienteIdInput.value) : null;
        const clienteTelInput = document.getElementById('pos-cliente-telefono');
        const clienteTel = clienteTelInput ? clienteTelInput.value.trim() : '';

        const payload = {
            metodo_pago: metodoPago,
            id_usuario: user.id,
            id_cliente: idClienteVal,
            cliente_nombre: clienteNombre,
            cliente_doc: clienteDoc,
            cliente_telefono: clienteTel,
            descuento_total: this.round2(descuentoTotal),
            detalles: this.carrito.map(item => {
                const propGlobalItem = subtotalBruto > 0 ? (descuentoTotal * (item.cantidad * item.precio_unitario) / subtotalBruto) : 0;
                const descUnitItem = propGlobalItem / item.cantidad;
                return {
                    id_producto: item.id_producto,
                    cantidad: item.cantidad,
                    precio_unitario: item.precio_unitario,
                    descuento_unitario: this.round2(descUnitItem)
                };
            })
        };

        try {
            const response = await fetch(`${this.apiUrl}/ventas`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok) {
                const copiaCarrito = [...this.carrito];
                const totalCobrado = Math.max(0, subtotalBruto - descuentoTotal);

                this.mostrarBoletaVenta({
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

                this.notify('¡Venta registrada exitosamente!', 'success');

                this.carrito = [];
                if (clienteNomInput) clienteNomInput.value = '';
                if (clienteDocInput) clienteDocInput.value = '';
                if (clienteTelInput) clienteTelInput.value = '';
                if (clienteIdInput) clienteIdInput.value = '';
                if (inputDesc) inputDesc.value = '';
                this.cancelarDescuentoSupervisor();
                this.renderCarrito();

                await this.cargarProductosCaja();

                // Avisamos a las demas pantallas que cambio el stock y se registro la venta
                if (window.EventBus) {
                    window.EventBus.emit('stock:updated', { source: 'caja' });
                    window.EventBus.emit('venta:registrada', { correlativo: result.correlativo });
                    window.EventBus.emit('cliente:registrado', { id_cliente: result.id_cliente });
                }
            } else {
                this.notify(result.error || 'Error al procesar la venta', 'error');
            }
        } catch (error) {
            console.error('Error procesando venta:', error);
            this.notify('Error de conexión con el servidor backend', 'error');
        }
    },

    mostrarBoletaVenta(data) {
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
        } else {
            const modal = document.getElementById('modal-ticket-venta');
            if (modal) modal.classList.add('active');
        }
    },

    imprimirBoleta() {
        window.print();
    },

    abrirModalAutorizacionSupervisor() {
        const user = JSON.parse(localStorage.getItem('user')) || {};
        const role = user.activeRole || user.role || 'Vendedor';

        if (role === 'Supervisor' || role === 'Administrador') {
            const nombreSup = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username || role;
            this.supervisorAutorizadoInfo = { supervisor: nombreSup, id: user.id };
            this.activarCajaDescuentoSupervisor(nombreSup);
            this.notify(`Descuento habilitado con tu rol de ${role}`, 'success');
            return;
        }

        const form = document.getElementById('form-autorizacion-supervisor');
        if (form) form.reset();
        const modal = document.getElementById('modal-autorizacion-supervisor');
        if (modal) modal.classList.add('active');
    },

    async validarAutorizacionSupervisor(e) {
        if (e && e.preventDefault) e.preventDefault();
        const username = document.getElementById('sup-auth-user')?.value.trim();
        const password = document.getElementById('sup-auth-pass')?.value.trim();

        try {
            const response = await fetch(`${this.apiUrl}/supervisor/autorizar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok && data.autorizado) {
                this.supervisorAutorizadoInfo = data;
                this.activarCajaDescuentoSupervisor(data.supervisor);
                const modal = document.getElementById('modal-autorizacion-supervisor');
                if (modal) modal.classList.remove('active');

                this.notify(`¡Autorizado por ${data.supervisor}! Descuento habilitado.`, 'success');
            } else {
                this.notify(data.error || 'Credenciales de supervisor incorrectas', 'error');
            }
        } catch (err) {
            this.notify('Error de conexión al verificar supervisor', 'error');
        }
    },

    activarCajaDescuentoSupervisor(supervisorNombre) {
        const box = document.getElementById('pos-supervisor-discount-box');
        const btn = document.getElementById('btn-solicitar-autorizacion-sup');
        const lbl = document.getElementById('pos-sup-autorizado-lbl');

        if (box) box.style.display = 'block';
        if (btn) btn.style.display = 'none';
        if (lbl) lbl.textContent = `Autorizado por: ${supervisorNombre}`;
    },

    cancelarDescuentoSupervisor() {
        this.supervisorAutorizadoInfo = null;
        const box = document.getElementById('pos-supervisor-discount-box');
        const btn = document.getElementById('btn-solicitar-autorizacion-sup');
        const inputDesc = document.getElementById('pos-descuento-val');

        if (box) box.style.display = 'none';
        if (btn) btn.style.display = 'flex';
        if (inputDesc) inputDesc.value = '';

        this.renderCarrito();
    },

    init() {
        // Suscribirse a eventos de stock actualizados en toda la SPA
        if (window.EventBus) {
            window.EventBus.on('stock:updated', (data) => {
                if (data && data.source === 'caja') return; // Evitar loop si la venta se originó en esta misma caja
                this.cargarProductosCaja();
            });
        }
    }
};

// Autocompleta el nombre del cliente en caja al ingresar DNI o RUC
async function autocompletarClienteCaja(doc) {
    const val = String(doc || '').trim();
    const idInput = document.getElementById('pos-cliente-id');
    if (idInput && val.length < 8) idInput.value = '';

    if (val.length === 8 || val.length === 11) {
        try {
            const loadingEl = document.getElementById('pos-cliente-loading');
            if (loadingEl) loadingEl.style.display = 'inline';
            const baseUrl = window.API_BASE_URL || 'http://localhost:8000/api';
            const res = await fetch(`${baseUrl}/clientes/buscar/${val}`);
            if (res.ok) {
                const cliente = await res.json();
                const nomInput = document.getElementById('pos-cliente-nombre');
                if (nomInput && cliente.nombres_razon_social) {
                    nomInput.value = cliente.nombres_razon_social;
                }
                const telInput = document.getElementById('pos-cliente-telefono');
                if (telInput && cliente.telefono) {
                    telInput.value = cliente.telefono;
                }
                if (idInput) {
                    idInput.value = cliente.id_cliente;
                }
                if (window.Toast) Toast.info(`Cliente encontrado: ${cliente.nombres_razon_social}`);
            }
        } catch (e) {
            // No interrumpe si el cliente no existe todavia
        } finally {
            const loadingEl = document.getElementById('pos-cliente-loading');
            if (loadingEl) loadingEl.style.display = 'none';
        }
    }
}
window.autocompletarClienteCaja = autocompletarClienteCaja;

// Exportamos las funciones al objeto window para que funcionen con los onclick del HTML
window.CajaModule = CajaModule;
window.cargarProductosCaja = () => CajaModule.cargarProductosCaja();
window.cargarProductosPos = () => CajaModule.cargarProductosCaja();
window.renderProductos = (p) => CajaModule.renderProductos(p);
window.filtrarProductos = () => CajaModule.filtrarProductos();
window.agregarAlCarrito = (p) => CajaModule.agregarAlCarrito(p);
window.actualizarCantidad = (id, delta) => CajaModule.actualizarCantidad(id, delta);
window.vaciarCarrito = () => CajaModule.vaciarCarrito();
window.renderCarrito = () => CajaModule.renderCarrito();
window.procesarVenta = () => CajaModule.procesarVenta();
window.cobrarVenta = () => CajaModule.procesarVenta(); // Alias
window.mostrarBoletaVenta = (d) => CajaModule.mostrarBoletaVenta(d);
window.imprimirBoleta = () => CajaModule.imprimirBoleta();
window.abrirModalAutorizacionSupervisor = () => CajaModule.abrirModalAutorizacionSupervisor();
window.validarAutorizacionSupervisor = (e) => CajaModule.validarAutorizacionSupervisor(e);
window.activarCajaDescuentoSupervisor = (nom) => CajaModule.activarCajaDescuentoSupervisor(nom);
window.cancelarDescuentoSupervisor = () => CajaModule.cancelarDescuentoSupervisor();
window.round2 = (v) => CajaModule.round2(v);

// Inicializar al cargar el script o DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => CajaModule.init());
} else {
    CajaModule.init();
}
