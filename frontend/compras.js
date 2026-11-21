// Modulo de Compras
// Emision de ordenes a proveedores, recepcion de mercaderia e historial

const ComprasModule = {
    apiUrl: window.API_BASE_URL || 'http://localhost:8000/api',

    // Estado en memoria para emisión de orden
    proveedorSeleccionadoOC: null,
    productosCatalogoProveedorOC: [],
    itemsOrdenCompraActual: [],

    // Estado en memoria para historial de compras
    listaComprasCache: [],
    ordenesFiltradasCache: [],
    tabComprasActual: 'pendientes',
    ordenSeleccionadaAccion: null,
    paginaActualCompras: 1,
    comprasPorPagina: 10,

    notify(message, type = 'success') {
        if (window.Toast && typeof window.Toast[type] === 'function') {
            window.Toast[type](message);
        } else if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            alert(message);
        }
    },

    round2(num) {
        return Math.round((num + Number.EPSILON) * 100) / 100;
    },

    // Emision de nuevas ordenes de compra
    getHoyLocalStr() {
        const hoy = new Date();
        const y = hoy.getFullYear();
        const m = String(hoy.getMonth() + 1).padStart(2, '0');
        const d = String(hoy.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    },

    async inicializarEmitirOrden() {
        this.limpiarFormularioOrden();
        await this.cargarSiguienteCorrelativoOC();
        await this.cargarProveedoresParaOrden();

        const elFecha = document.getElementById('oc-fecha-esperada');
        if (elFecha) {
            const hoyStr = this.getHoyLocalStr();
            elFecha.min = hoyStr;
            if (!elFecha.value || elFecha.value < hoyStr) {
                const hoy = new Date();
                const en3dias = new Date(hoy.getTime() + 3 * 24 * 60 * 60 * 1000);
                const y3 = en3dias.getFullYear();
                const m3 = String(en3dias.getMonth() + 1).padStart(2, '0');
                const d3 = String(en3dias.getDate()).padStart(2, '0');
                elFecha.value = `${y3}-${m3}-${d3}`;
            }
        }
    },

    async cargarSiguienteCorrelativoOC() {
        const elCod = document.getElementById('oc-correlativo-display');
        if (!elCod) return;

        try {
            const u = JSON.parse(localStorage.getItem('user')) || {};
            const userRole = u.activeRole || u.role || 'Administrador';

            const res = await fetch(`${this.apiUrl}/compras/siguiente-correlativo`, {
                headers: { 'X-Role': userRole }
            });
            if (res.ok) {
                const data = await res.json();
                elCod.innerText = data.correlativo || 'OC-XXXX';
            }
        } catch (e) {
            console.warn('No se pudo obtener correlativo preview:', e);
        }
    },

    async cargarProveedoresParaOrden() {
        const selectProv = document.getElementById('oc-select-proveedor');
        if (!selectProv) return;

        selectProv.innerHTML = '<option value="">-- Selecciona un Proveedor --</option>';

        try {
            const u = JSON.parse(localStorage.getItem('user')) || {};
            const userRole = u.activeRole || u.role || 'Administrador';
            const idSede = u.id_sede || 1;

            const res = await fetch(`${this.apiUrl}/proveedores?id_sede=${idSede}`, {
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
            this.notify(err.message, 'error');
        }
    },

    async onProveedorOrdenChange() {
        const selectProv = document.getElementById('oc-select-proveedor');
        const idProv = selectProv ? selectProv.value : '';

        const cardInfo = document.getElementById('oc-proveedor-info-card');
        const selectProd = document.getElementById('oc-select-producto');

        if (!idProv) {
            this.proveedorSeleccionadoOC = null;
            this.productosCatalogoProveedorOC = [];
            this.itemsOrdenCompraActual = [];
            this.renderizarTablaOrdenItems();

            if (cardInfo) cardInfo.style.display = 'none';
            if (selectProd) selectProd.innerHTML = '<option value="">-- Primero selecciona un proveedor --</option>';
            return;
        }

        const opt = selectProv.options[selectProv.selectedIndex];
        this.proveedorSeleccionadoOC = {
            id_proveedor: parseInt(idProv),
            razon_social: opt ? opt.textContent.trim() : '',
            ruc: opt ? (opt.dataset.ruc || '---') : '---',
            contacto: opt ? (opt.dataset.contacto || '---') : '---',
            telefono: opt ? (opt.dataset.telefono || '---') : '---',
            correo: opt ? (opt.dataset.correo || '---') : '---'
        };

        if (cardInfo) {
            const elRazon = document.getElementById('oc-card-razon');
            if (elRazon) elRazon.innerText = this.proveedorSeleccionadoOC.razon_social;
            const elRuc = document.getElementById('oc-card-ruc');
            if (elRuc) elRuc.innerText = `RUC: ${this.proveedorSeleccionadoOC.ruc}`;
            const elContacto = document.getElementById('oc-card-contacto');
            if (elContacto) elContacto.innerText = `Contacto: ${this.proveedorSeleccionadoOC.contacto}`;
            const elTel = document.getElementById('oc-card-telefono');
            if (elTel) elTel.innerText = `Teléfono: ${this.proveedorSeleccionadoOC.telefono}`;
            const elCorreo = document.getElementById('oc-card-correo');
            if (elCorreo) elCorreo.innerText = `Correo: ${this.proveedorSeleccionadoOC.correo}`;
            cardInfo.style.display = 'flex';
        }

        this.itemsOrdenCompraActual = [];
        this.renderizarTablaOrdenItems();

        await this.cargarCatalogoDeProveedorParaOrden(this.proveedorSeleccionadoOC.id_proveedor);
    },

    async cargarCatalogoDeProveedorParaOrden(idProveedor) {
        const selectProd = document.getElementById('oc-select-producto');
        if (!selectProd) return;

        selectProd.innerHTML = '<option value="">Cargando catálogo pactado...</option>';

        try {
            const u = JSON.parse(localStorage.getItem('user')) || {};
            const userRole = u.activeRole || u.role || 'Administrador';

            const res = await fetch(`${this.apiUrl}/proveedores/${idProveedor}/catalogo`, {
                headers: { 'X-Role': userRole }
            });

            if (!res.ok) throw new Error('Error al cargar catálogo del proveedor.');

            const prods = await res.json();
            this.productosCatalogoProveedorOC = prods || [];

            if (this.productosCatalogoProveedorOC.length === 0) {
                // Fallback amigable: cargar productos generales de almacén para que el usuario pueda abastecerse
                try {
                    const fallbackRes = await fetch(`${this.apiUrl}/productos?sede_id=1`, {
                        headers: { 'X-Role': userRole }
                    });
                    if (fallbackRes.ok) {
                        const allProds = await fallbackRes.json();
                        if (allProds && allProds.length > 0) {
                            selectProd.innerHTML = '<option value="">-- Selecciona producto de almacén --</option>';
                            allProds.forEach(p => {
                                const opt = document.createElement('option');
                                opt.value = p.id_producto;
                                const pr = parseFloat(p.precio_compra || 0);
                                opt.textContent = `${p.codigo_producto} - ${p.nombre} (Ref. S/. ${pr.toFixed(2)})`;
                                opt.dataset.codigo = p.codigo_producto;
                                opt.dataset.nombre = p.nombre;
                                opt.dataset.precio = pr;
                                selectProd.appendChild(opt);
                            });
                            this.notify('Proveedor sin catálogo exclusivo: mostrando productos generales de almacén.', 'info');
                            return;
                        }
                    }
                } catch (e) {
                    console.warn("Fallback productos error:", e);
                }
                selectProd.innerHTML = '<option value="">(Este proveedor aún no tiene productos vinculados)</option>';
                this.notify('El proveedor seleccionado no tiene productos en su catálogo.', 'warning');
                return;
            }

            selectProd.innerHTML = '<option value="">-- Selecciona un producto pactado --</option>';
            this.productosCatalogoProveedorOC.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id_producto;
                const prec = parseFloat(p.precio_pactado || 0);
                opt.textContent = `${p.codigo_producto} - ${p.nombre_producto} (Pactado: S/. ${prec.toFixed(2)})`;
                opt.dataset.codigo = p.codigo_producto;
                opt.dataset.nombre = p.nombre_producto;
                opt.dataset.precio = prec;
                selectProd.appendChild(opt);
            });
        } catch (err) {
            console.error("Error catálogo proveedor:", err);
            selectProd.innerHTML = '<option value="">Error al cargar catálogo</option>';
            this.notify(err.message, 'error');
        }
    },

    onProductoOrdenChange() {
        const selectProd = document.getElementById('oc-select-producto');
        const inputPrecio = document.getElementById('oc-item-precio') || document.getElementById('oc-input-precio');
        const inputCant = document.getElementById('oc-item-cantidad') || document.getElementById('oc-input-cantidad');

        if (!selectProd || !selectProd.value) {
            if (inputPrecio) inputPrecio.value = '';
            return;
        }

        const opt = selectProd.options[selectProd.selectedIndex];
        const precioPactado = parseFloat(opt.dataset.precio) || 0;

        if (inputPrecio) inputPrecio.value = precioPactado.toFixed(2);
        if (inputCant && !inputCant.value) inputCant.value = '10';
    },

    agregarItemAOrden() {
        if (!this.proveedorSeleccionadoOC) {
            this.notify('Debes seleccionar un proveedor antes de agregar ítems.', 'error');
            return;
        }

        const selectProd = document.getElementById('oc-select-producto');
        const inputCant = document.getElementById('oc-item-cantidad') || document.getElementById('oc-input-cantidad');
        const inputPrecio = document.getElementById('oc-item-precio') || document.getElementById('oc-input-precio');

        if (!selectProd || !selectProd.value) {
            this.notify('Por favor selecciona un producto del catálogo pactado.', 'error');
            return;
        }

        const opt = selectProd.options[selectProd.selectedIndex];
        const idProd = parseInt(selectProd.value);
        const cant = parseInt(inputCant?.value) || 0;
        const precio = parseFloat(inputPrecio?.value) || 0;

        if (cant <= 0) {
            this.notify('La cantidad debe ser mayor a 0 unidades.', 'error');
            if (inputCant) inputCant.focus();
            return;
        }

        if (precio <= 0) {
            this.notify('El precio de compra debe ser mayor a S/. 0.00.', 'error');
            return;
        }

        const itemExistente = this.itemsOrdenCompraActual.find(i => i.id_producto === idProd);
        if (itemExistente) {
            itemExistente.cantidad += cant;
            itemExistente.subtotal = this.round2(itemExistente.cantidad * itemExistente.precio_compra);
        } else {
            this.itemsOrdenCompraActual.push({
                id_producto: idProd,
                codigo: opt.dataset.codigo,
                nombre: opt.dataset.nombre,
                precio_compra: precio,
                cantidad: cant,
                subtotal: this.round2(cant * precio)
            });
        }

        if (inputCant) inputCant.value = '1';
        selectProd.selectedIndex = 0;
        if (inputPrecio) inputPrecio.value = '';

        this.renderizarTablaOrdenItems();
    },

    renderizarTablaOrdenItems() {
        const tbody = document.getElementById('oc-items-tbody') || document.getElementById('oc-items-table-tbody');
        if (!tbody) return;

        if (this.itemsOrdenCompraActual.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 25px; color: #94a3b8; font-style: italic;">
                        No hay productos agregados a esta orden de compra.
                    </td>
                </tr>
            `;
            this.actualizarTotalesOrden();
            return;
        }

        tbody.innerHTML = '';
        this.itemsOrdenCompraActual.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight: 700; color: #0284c7; font-family: monospace;">${item.codigo}</td>
                <td style="font-weight: 600; color: #1e293b;">${item.nombre}</td>
                <td style="text-align: right; color: #334155;">S/. ${item.precio_compra.toFixed(2)}</td>
                <td style="text-align: center;">
                    <input type="number" min="1" value="${item.cantidad}"
                           onchange="modificarCantidadItemOrden(${index}, this.value)"
                           style="width: 75px; text-align: center; padding: 4px; border: 1px solid #cbd5e1; border-radius: 6px; font-weight: 700;">
                </td>
                <td style="text-align: right; font-weight: 800; color: #0f172a;">S/. ${item.subtotal.toFixed(2)}</td>
                <td style="text-align: center;">
                    <button type="button" onclick="eliminarItemOrden(${index})" class="btn-table-action" title="Quitar ítem"
                            style="background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; padding: 6px 9px; border-radius: 6px; cursor: pointer;">
                        <i class="ph-bold ph-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        this.actualizarTotalesOrden();
    },

    modificarCantidadItemOrden(index, nuevaCant) {
        const cant = parseInt(nuevaCant);
        if (isNaN(cant) || cant <= 0) {
            this.renderizarTablaOrdenItems();
            return;
        }
        this.itemsOrdenCompraActual[index].cantidad = cant;
        this.itemsOrdenCompraActual[index].subtotal = this.round2(cant * this.itemsOrdenCompraActual[index].precio_compra);
        this.renderizarTablaOrdenItems();
    },

    eliminarItemOrden(index) {
        this.itemsOrdenCompraActual.splice(index, 1);
        this.renderizarTablaOrdenItems();
    },

    actualizarTotalesOrden() {
        const total = this.itemsOrdenCompraActual.reduce((acc, item) => acc + item.subtotal, 0);
        const subtotalBase = this.round2(total / 1.18);
        const igv = this.round2(total - subtotalBase);

        const elSub = document.getElementById('oc-total-subtotal');
        const elIgv = document.getElementById('oc-total-igv');
        const elTot = document.getElementById('oc-total-general');

        if (elSub) elSub.innerText = `S/. ${subtotalBase.toFixed(2)}`;
        if (elIgv) elIgv.innerText = `S/. ${igv.toFixed(2)}`;
        if (elTot) elTot.innerText = `S/. ${total.toFixed(2)}`;
    },

    limpiarFormularioOrden() {
        this.proveedorSeleccionadoOC = null;
        this.productosCatalogoProveedorOC = [];
        this.itemsOrdenCompraActual = [];

        const selectProv = document.getElementById('oc-select-proveedor');
        if (selectProv) selectProv.value = '';

        const selectProd = document.getElementById('oc-select-producto');
        if (selectProd) selectProd.innerHTML = '<option value="">-- Primero selecciona un proveedor --</option>';

        const cardInfo = document.getElementById('oc-proveedor-info-card');
        if (cardInfo) cardInfo.style.display = 'none';

        const elObs = document.getElementById('oc-observaciones');
        if (elObs) elObs.value = '';

        const inpPrecio = document.getElementById('oc-item-precio') || document.getElementById('oc-input-precio');
        if (inpPrecio) inpPrecio.value = '';
        const inpCant = document.getElementById('oc-item-cantidad') || document.getElementById('oc-input-cantidad');
        if (inpCant) inpCant.value = '1';

        this.renderizarTablaOrdenItems();
    },

    async emitirOrdenCompra() {
        if (!this.proveedorSeleccionadoOC) {
            this.notify('Error: Debes seleccionar un proveedor obligatorio.', 'error');
            return;
        }

        if (this.itemsOrdenCompraActual.length === 0) {
            this.notify('Error: Debes agregar al menos un producto a la orden de compra.', 'error');
            return;
        }

        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';
        const idSede = u.id_sede || 1;
        const idUsuario = u.id || u.id_usuario || 1;

        const fechaEsperada = document.getElementById('oc-fecha-esperada')?.value || '';
        const observacion = document.getElementById('oc-observaciones')?.value.trim() || '';

        if (fechaEsperada) {
            const hoyStr = this.getHoyLocalStr();
            if (fechaEsperada < hoyStr) {
                this.notify(`Error: La fecha de entrega (${fechaEsperada}) no puede ser anterior a hoy (${hoyStr}).`, 'error');
                return;
            }
        }

        const payload = {
            id_proveedor: this.proveedorSeleccionadoOC.id_proveedor,
            id_sede: idSede,
            id_usuario: idUsuario,
            fecha_esperada: fechaEsperada,
            observacion: observacion,
            items: this.itemsOrdenCompraActual.map(i => ({
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
            const res = await fetch(`${this.apiUrl}/compras`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Role': userRole
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Error al emitir orden de compra.');

            this.notify(`¡${data.message}!`, 'success');

            const idCreada = data.id_orden_compra;
            this.limpiarFormularioOrden();
            await this.cargarSiguienteCorrelativoOC();

            if (idCreada) {
                await this.abrirModalDetalleCompra(idCreada);
            }
        } catch (err) {
            this.notify(err.message, 'error');
        } finally {
            if (btnEmitir) {
                btnEmitir.disabled = false;
                btnEmitir.innerHTML = `<i class="ph-bold ph-paper-plane-tilt"></i> Emitir Orden de Compra`;
            }
        }
    },

    // Historial de compras y recepcion de mercaderia
    async cargarHistorialCompras() {
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

            const res = await fetch(`${this.apiUrl}/compras?id_sede=${idSede}`, {
                headers: { 'X-Role': userRole }
            });

            if (!res.ok) throw new Error('Error al consultar historial de compras.');

            const ordenes = await res.json();
            this.listaComprasCache = ordenes;

            this.actualizarResumenHistorialCompras(ordenes);
            this.paginaActualCompras = 1;
            this.filtrarYRenderizarCompras();
        } catch (err) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 25px; color: #ef4444;">
                        <i class="ph ph-warning-circle" style="font-size: 1.3rem;"></i> ${err.message}
                    </td>
                </tr>
            `;
        }
    },

    cambiarTabCompras(tab) {
        this.tabComprasActual = tab;

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

        this.paginaActualCompras = 1;
        this.filtrarYRenderizarCompras();
    },

    filtrarHistorialCompras() {
        this.paginaActualCompras = 1;
        this.filtrarYRenderizarCompras();
    },

    filtrarYRenderizarCompras() {
        const searchVal = (document.getElementById('compras-search-input')?.value || '').toLowerCase().trim();

        let filtradas = this.listaComprasCache;

        if (this.tabComprasActual === 'pendientes') {
            filtradas = filtradas.filter(o => o.estado === 'PENDIENTE');
        }

        if (searchVal) {
            filtradas = filtradas.filter(o =>
                (o.correlativo || '').toLowerCase().includes(searchVal) ||
                (o.proveedor_nombre || '').toLowerCase().includes(searchVal) ||
                (o.proveedor_ruc || '').toLowerCase().includes(searchVal) ||
                (o.usuario_nombre || '').toLowerCase().includes(searchVal)
            );
        }

        this.renderizarTablaHistorialCompras(filtradas);
    },

    actualizarResumenHistorialCompras(ordenes) {
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
    },

    renderizarTablaHistorialCompras(ordenes) {
        const tbody = document.getElementById('compras-historial-tbody');
        if (!tbody) return;

        this.ordenesFiltradasCache = ordenes || [];

        if (this.ordenesFiltradasCache.length === 0) {
            const msg = this.tabComprasActual === 'pendientes'
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
            this.actualizarPaginacionUI(0, 1);
            return;
        }

        const totalItems = this.ordenesFiltradasCache.length;
        const totalPaginas = Math.ceil(totalItems / this.comprasPorPagina) || 1;
        if (this.paginaActualCompras > totalPaginas) this.paginaActualCompras = totalPaginas;
        if (this.paginaActualCompras < 1) this.paginaActualCompras = 1;

        const inicio = (this.paginaActualCompras - 1) * this.comprasPorPagina;
        const fin = inicio + this.comprasPorPagina;
        const paginaItems = this.ordenesFiltradasCache.slice(inicio, fin);

        tbody.innerHTML = '';
        paginaItems.forEach(o => {
            const tr = document.createElement('tr');
            tr.style.transition = 'background-color 0.15s ease';

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

        this.actualizarPaginacionUI(totalItems, totalPaginas);
    },

    actualizarPaginacionUI(totalItems, totalPaginas) {
        const pagInfo = document.getElementById('compras-paginacion-info');
        if (pagInfo) {
            pagInfo.textContent = `Página ${this.paginaActualCompras} de ${totalPaginas} (${totalItems} órdenes)`;
        }

        const btnPrev = document.getElementById('btn-compras-pag-prev');
        if (btnPrev) btnPrev.disabled = (this.paginaActualCompras <= 1);

        const btnNext = document.getElementById('btn-compras-pag-next');
        if (btnNext) btnNext.disabled = (this.paginaActualCompras >= totalPaginas);
    },

    cambiarPaginaCompras(delta) {
        this.paginaActualCompras += delta;
        this.renderizarTablaHistorialCompras(this.ordenesFiltradasCache);
    },

    // Recepcion de mercaderia e ingreso al almacen
    async abrirModalRecibirCompra(idOrden) {
        const orden = this.listaComprasCache.find(o => o.id_orden_compra === idOrden);
        if (!orden) return;

        this.ordenSeleccionadaAccion = orden;

        document.getElementById('modal-recibir-oc-correlativo').innerText = orden.correlativo;
        document.getElementById('modal-recibir-oc-proveedor').innerText = orden.proveedor_nombre;

        const tbody = document.getElementById('modal-recibir-oc-items-tbody');
        tbody.innerHTML = '';
        orden.items.forEach(it => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-family: monospace; font-weight: 700; color: #0284c7;">${it.codigo_producto}</td>
                <td style="font-weight: 600; color: #1e293b;">${it.nombre_producto}</td>
                <td style="text-align: center; font-weight: 800; color: #16a34a; font-size: 1rem;">+${it.cantidad_solicitada}</td>
                <td style="text-align: right; color: #334155;">S/. ${it.precio_unitario.toFixed(2)}</td>
                <td style="text-align: right; font-weight: 700; color: #0f172a;">S/. ${it.subtotal.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });

        const modal = document.getElementById('modal-recibir-compra');
        if (modal) modal.classList.add('active');
    },

    async confirmarRecepcionCompra() {
        if (!this.ordenSeleccionadaAccion) return;

        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';
        const idUsuario = u.id || u.id_usuario || 1;

        const btn = document.getElementById('btn-confirmar-recepcion-submit');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i class="ph ph-spinner spinner"></i> Ingresando a Almacén...`;
        }

        try {
            const res = await fetch(`${this.apiUrl}/compras/${this.ordenSeleccionadaAccion.id_orden_compra}/recibir`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Role': userRole
                },
                body: JSON.stringify({ id_usuario: idUsuario })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Error al recepcionar mercadería.');

            this.notify(data.message, 'success');

            if (typeof closeModal === 'function') {
                closeModal('modal-recibir-compra');
            }

            await this.cargarHistorialCompras();

            // Emitir evento reactivo para refrescar stock en Almacén y Caja
            if (window.EventBus) {
                window.EventBus.emit('stock:updated', { source: 'compras' });
            }
        } catch (err) {
            this.notify(err.message, 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<i class="ph-bold ph-check"></i> Confirmar e Ingresar a Almacén`;
            }
        }
    },

    // Anulacion de ordenes de compra
    abrirModalAnularCompra(idOrden, correlativo) {
        const orden = this.listaComprasCache.find(o => o.id_orden_compra === idOrden);
        if (!orden) return;

        this.ordenSeleccionadaAccion = orden;

        const modal = document.getElementById('modal-confirmacion-custom');
        if (!modal) {
            if (confirm(`¿Estás seguro de anular la orden ${correlativo}?`)) {
                this.ejecutarAnulacionCompra(idOrden);
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
            this.ejecutarAnulacionCompra(idOrden);
        };

        modal.classList.add('active');
    },

    async ejecutarAnulacionCompra(idOrden) {
        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';

        try {
            const res = await fetch(`${this.apiUrl}/compras/${idOrden}/anular`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Role': userRole
                },
                body: JSON.stringify({ motivo: 'Anulado por usuario en panel de Compras' })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Error al anular orden de compra.');

            this.notify(data.message, 'success');

            await this.cargarHistorialCompras();

            // Emitir evento reactivo para refrescar stock si la anulación revirtió inventario
            if (window.EventBus) {
                window.EventBus.emit('stock:updated', { source: 'compras' });
            }
        } catch (err) {
            this.notify(err.message, 'error');
        }
    },

    // Detalle de la orden, impresion en PDF y envio por WhatsApp
    async abrirModalDetalleCompra(idOrden) {
        try {
            const u = JSON.parse(localStorage.getItem('user')) || {};
            const userRole = u.activeRole || u.role || 'Administrador';

            const res = await fetch(`${this.apiUrl}/compras/${idOrden}`, {
                headers: { 'X-Role': userRole }
            });

            if (!res.ok) throw new Error('No se pudo cargar la orden.');

            const orden = await res.json();
            this.ordenSeleccionadaAccion = orden;

            document.getElementById('doc-oc-correlativo').innerText = orden.correlativo;
            document.getElementById('doc-oc-fecha-emision').innerText = orden.fecha_emision;
            document.getElementById('doc-oc-fecha-esperada').innerText = orden.fecha_esperada || 'Inmediata';
            document.getElementById('doc-oc-estado').innerText = orden.estado;

            document.getElementById('doc-oc-prov-nombre').innerText = orden.proveedor_nombre;
            document.getElementById('doc-oc-prov-ruc').innerText = orden.proveedor_ruc;
            document.getElementById('doc-oc-prov-contacto').innerText = orden.proveedor_contacto || '---';
            document.getElementById('doc-oc-prov-telefono').innerText = orden.proveedor_telefono || '---';
            document.getElementById('doc-oc-prov-correo').innerText = orden.proveedor_correo || '---';

            document.getElementById('doc-oc-sede-nombre').innerText = orden.sede_nombre;
            document.getElementById('doc-oc-sede-direccion').innerText = orden.sede_direccion || 'Av. Principal S/N';

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

            const total = orden.total || 0;
            const subtotal = this.round2(total / 1.18);
            const igv = this.round2(total - subtotal);

            document.getElementById('doc-oc-subtotal').innerText = `S/. ${subtotal.toFixed(2)}`;
            document.getElementById('doc-oc-igv').innerText = `S/. ${igv.toFixed(2)}`;
            document.getElementById('doc-oc-total').innerText = `S/. ${total.toFixed(2)}`;

            const elObs = document.getElementById('doc-oc-observaciones');
            if (elObs) elObs.innerText = orden.observacion ? `Observaciones: ${orden.observacion}` : '';

            const modal = document.getElementById('modal-documento-orden-compra');
            if (modal) modal.classList.add('active');
        } catch (err) {
            this.notify(err.message, 'error');
        }
    },

    imprimirOrdenCompraActual() {
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
    },

    enviarOrdenPorWhatsApp(idOrden) {
        const orden = this.listaComprasCache.find(o => o.id_orden_compra === idOrden) || this.ordenSeleccionadaAccion;
        if (!orden || !orden.proveedor_telefono) {
            this.notify('El proveedor no tiene número celular registrado.', 'error');
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
    },

    init() {
        const inputBuscarHistorial = document.getElementById('compras-search-input');
        if (inputBuscarHistorial) {
            inputBuscarHistorial.addEventListener('keyup', () => this.filtrarHistorialCompras());
        }
    }
};

// Funciones globales expuestas para los eventos de los botones y modales
window.ComprasModule = ComprasModule;
window.inicializarEmitirOrden = () => ComprasModule.inicializarEmitirOrden();
window.cargarSiguienteCorrelativoOC = () => ComprasModule.cargarSiguienteCorrelativoOC();
window.cargarProveedoresParaOrden = () => ComprasModule.cargarProveedoresParaOrden();
window.onProveedorOrdenChange = () => ComprasModule.onProveedorOrdenChange();
window.cargarCatalogoDeProveedorParaOrden = (id) => ComprasModule.cargarCatalogoDeProveedorParaOrden(id);
window.onProductoOrdenChange = () => ComprasModule.onProductoOrdenChange();
window.agregarItemAOrden = () => ComprasModule.agregarItemAOrden();
window.renderizarTablaOrdenItems = () => ComprasModule.renderizarTablaOrdenItems();
window.modificarCantidadItemOrden = (idx, c) => ComprasModule.modificarCantidadItemOrden(idx, c);
window.eliminarItemOrden = (idx) => ComprasModule.eliminarItemOrden(idx);
window.actualizarTotalesOrden = () => ComprasModule.actualizarTotalesOrden();
window.limpiarFormularioOrden = () => ComprasModule.limpiarFormularioOrden();
window.emitirOrdenCompra = () => ComprasModule.emitirOrdenCompra();
window.cargarHistorialCompras = () => ComprasModule.cargarHistorialCompras();
window.cambiarTabCompras = (tab) => ComprasModule.cambiarTabCompras(tab);
window.filtrarHistorialCompras = () => ComprasModule.filtrarHistorialCompras();
window.filtrarYRenderizarCompras = () => ComprasModule.filtrarYRenderizarCompras();
window.actualizarResumenHistorialCompras = (ord) => ComprasModule.actualizarResumenHistorialCompras(ord);
window.renderizarTablaHistorialCompras = (ord) => ComprasModule.renderizarTablaHistorialCompras(ord);
window.cambiarPaginaCompras = (delta) => ComprasModule.cambiarPaginaCompras(delta);
window.abrirModalRecibirCompra = (id) => ComprasModule.abrirModalRecibirCompra(id);
window.confirmarRecepcionCompra = () => ComprasModule.confirmarRecepcionCompra();
window.abrirModalAnularCompra = (id, corr) => ComprasModule.abrirModalAnularCompra(id, corr);
window.ejecutarAnulacionCompra = (id) => ComprasModule.ejecutarAnulacionCompra(id);
window.abrirModalDetalleCompra = (id) => ComprasModule.abrirModalDetalleCompra(id);
window.imprimirOrdenCompraActual = () => ComprasModule.imprimirOrdenCompraActual();
window.enviarOrdenPorWhatsApp = (id) => ComprasModule.enviarOrdenPorWhatsApp(id);
window.round2 = (num) => ComprasModule.round2(num);

// Inicializar al cargar el script o DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ComprasModule.init());
} else {
    ComprasModule.init();
}
