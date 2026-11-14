// Modulo de Proveedores y Precios Pactados
// Registro de proveedores, validacion de RUC y catalogo de productos pactados

const ProveedoresModule = {
    apiUrl: window.API_BASE_URL || 'http://localhost:8000/api',
    listaProveedoresCache: [],
    proveedorActualCatalogo: null,
    productosGeneralesCache: [],

    notify(message, type = 'success') {
        if (window.Toast && typeof window.Toast[type] === 'function') {
            window.Toast[type](message);
        } else if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            alert(message);
        }
    },

    cambiarSedeProveedores() {
        this.cargarProveedores();
    },

    async cargarProveedores() {
        const tbody = document.getElementById('proveedores-tbody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 25px; color: #94a3b8;">
                    <i class="ph ph-spinner spinner" style="font-size: 1.5rem;"></i> Cargando proveedores...
                </td>
            </tr>
        `;

        try {
            const u = JSON.parse(localStorage.getItem('user')) || {};
            const userRole = u.activeRole || u.role || 'Administrador';
            const idSede = u.id_sede || 1;

            const url = `${this.apiUrl}/proveedores?id_sede=${idSede}`;
            const res = await fetch(url, {
                headers: { 'X-Role': userRole }
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || 'Error al obtener la lista de proveedores.');
            }

            const data = await res.json();
            this.listaProveedoresCache = data;

            this.actualizarCardsResumen(data);
            this.renderizarTablaProveedores(data);
        } catch (err) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 25px; color: #ef4444;">
                        <i class="ph ph-warning-circle" style="font-size: 1.3rem;"></i> ${err.message}
                    </td>
                </tr>
            `;
            this.notify(err.message, 'error');
        }
    },

    actualizarCardsResumen(data) {
        const elTotal = document.getElementById('prov-stat-total');
        const elProds = document.getElementById('prov-stat-prods');

        if (elTotal) elTotal.innerText = data.length;

        if (elProds) {
            const sumaProds = data.reduce((acc, p) => acc + (p.total_productos || 0), 0);
            elProds.innerText = sumaProds;
        }
    },

    renderizarTablaProveedores(proveedores) {
        const tbody = document.getElementById('proveedores-tbody');
        if (!tbody) return;

        if (!proveedores || proveedores.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 35px; color: #94a3b8; font-style: italic;">
                        No se encontraron proveedores registrados para tu sede. Haz clic en <strong>"+ Nuevo Proveedor"</strong> para registrar uno.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = '';
        proveedores.forEach(p => {
            const tr = document.createElement('tr');
            tr.style.transition = 'background-color 0.15s ease';

            tr.innerHTML = `
                <td>
                    <div style="font-weight: 700; color: #1e293b; font-family: monospace; font-size: 0.95rem;">
                        ${p.ruc}
                    </div>
                </td>
                <td>
                    <div style="font-weight: 600; color: #0f172a; font-size: 0.95rem;">${p.razon_social}</div>
                    <div style="font-size: 0.78rem; color: #64748b;">${p.direccion || 'Sin dirección registrada'}</div>
                </td>
                <td>
                    <div style="font-weight: 600; color: #334155;">${p.nombre_contacto || '---'}</div>
                    <div style="font-size: 0.82rem; color: #059669; font-weight: 700; display: flex; align-items: center; gap: 4px; margin-top: 2px;">
                        <i class="ph-bold ph-device-mobile" style="font-size: 0.9rem;"></i> ${p.telefono || 'Sin celular'}
                    </div>
                </td>
                <td>
                    <div style="font-size: 0.85rem; color: #334155;">
                        <i class="ph ph-envelope-simple" style="font-size: 0.8rem; color: #94a3b8;"></i> ${p.correo || '---'}
                    </div>
                </td>
                <td style="text-align: center;">
                    <button onclick="abrirModalCatalogo(${p.id_proveedor})" 
                            style="background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; padding: 5px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s;"
                            title="Ver y Gestionar Catálogo de Productos">
                        <i class="ph-bold ph-package"></i>
                        <span>${p.total_productos} Ítems</span>
                    </button>
                </td>
                <td style="text-align: center;">
                    <div style="display: inline-flex; gap: 6px;">
                        <button class="btn-table-action" onclick="abrirModalEditarProveedor(${p.id_proveedor})" title="Editar Proveedor" style="background: #f8fafc; border: 1px solid #cbd5e1; color: #475569; padding: 6px 9px; border-radius: 6px; cursor: pointer;">
                            <i class="ph-bold ph-pencil-simple" style="font-size: 0.95rem;"></i>
                        </button>
                        <button class="btn-table-action" onclick="eliminarProveedor(${p.id_proveedor}, '${p.razon_social.replace(/'/g, "\\'")}')" title="Eliminar Proveedor" style="background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; padding: 6px 9px; border-radius: 6px; cursor: pointer;">
                            <i class="ph-bold ph-trash" style="font-size: 0.95rem;"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    filtrarProveedores() {
        const searchVal = (document.getElementById('proveedor-search-input')?.value || '').toLowerCase().trim();

        const filtrados = this.listaProveedoresCache.filter(p => {
            return (
                (p.ruc || '').toLowerCase().includes(searchVal) ||
                (p.razon_social || '').toLowerCase().includes(searchVal) ||
                (p.nombre_contacto || '').toLowerCase().includes(searchVal) ||
                (p.telefono || '').toLowerCase().includes(searchVal) ||
                (p.correo || '').toLowerCase().includes(searchVal)
            );
        });

        this.renderizarTablaProveedores(filtrados);
    },

    validarInputRucEnTiempoReal(input) {
        if (!input) return;

        input.value = input.value.replace(/[^0-9]/g, '').slice(0, 11);

        const val = input.value;
        const helper = document.getElementById('prov-ruc-helper');
        if (!helper) return;

        if (val.length === 0) {
            helper.innerText = 'Debe tener exactamente 11 dígitos e iniciar con 10 o 20.';
            helper.style.color = '#64748b';
            input.style.borderColor = '#cbd5e1';
            return;
        }

        if (val.length === 1) {
            if (val !== '1' && val !== '2') {
                helper.innerText = '❌ Error: El RUC solo puede iniciar con 10 o 20.';
                helper.style.color = '#ef4444';
                input.style.borderColor = '#ef4444';
            } else {
                helper.innerText = `⏳ Iniciando con ${val}... (falta completar)`;
                helper.style.color = '#f59e0b';
                input.style.borderColor = '#cbd5e1';
            }
            return;
        }

        const prefijo = val.slice(0, 2);
        if (prefijo !== '10' && prefijo !== '20') {
            helper.innerText = `❌ Error: Inicia con "${prefijo}". Solo se permite iniciar con "10" o "20".`;
            helper.style.color = '#ef4444';
            input.style.borderColor = '#ef4444';
            return;
        }

        if (val.length < 11) {
            const tipo = prefijo === '10' ? 'Persona Natural' : 'Empresa / Jurídica';
            helper.innerText = `⏳ Prefijo ${prefijo} (${tipo}) correcto: ${val.length}/11 dígitos (faltan ${11 - val.length}).`;
            helper.style.color = '#0284c7';
            input.style.borderColor = '#38bdf8';
        } else if (val.length === 11) {
            const tipo = prefijo === '10' ? 'Persona Natural con Negocio' : 'Empresa / Persona Jurídica';
            helper.innerText = `✔ RUC Válido: 11 dígitos (${prefijo} - ${tipo}).`;
            helper.style.color = '#059669';
            input.style.borderColor = '#10b981';
        }
    },

    abrirModalCrearProveedor() {
        document.getElementById('modal-proveedor-title').innerText = 'Registrar Nuevo Proveedor';
        document.getElementById('edit-proveedor-id').value = '';
        const rucInput = document.getElementById('prov-ruc');
        rucInput.value = '';
        rucInput.disabled = false;
        document.getElementById('prov-razon-social').value = '';
        document.getElementById('prov-contacto').value = '';
        document.getElementById('prov-telefono').value = '';
        document.getElementById('prov-correo').value = '';
        document.getElementById('prov-direccion').value = '';

        this.validarInputRucEnTiempoReal(rucInput);

        const modal = document.getElementById('modal-proveedor');
        if (modal) modal.classList.add('active');
    },

    abrirModalEditarProveedor(idProveedor) {
        const prov = this.listaProveedoresCache.find(p => p.id_proveedor === idProveedor);
        if (!prov) return;

        document.getElementById('modal-proveedor-title').innerText = 'Editar Datos de Proveedor';
        document.getElementById('edit-proveedor-id').value = prov.id_proveedor;
        const rucInput = document.getElementById('prov-ruc');
        rucInput.value = prov.ruc;
        rucInput.disabled = false;
        document.getElementById('prov-razon-social').value = prov.razon_social;
        document.getElementById('prov-contacto').value = prov.nombre_contacto || '';
        document.getElementById('prov-telefono').value = prov.telefono || '';
        document.getElementById('prov-correo').value = prov.correo || '';
        document.getElementById('prov-direccion').value = prov.direccion || '';

        this.validarInputRucEnTiempoReal(rucInput);

        const modal = document.getElementById('modal-proveedor');
        if (modal) modal.classList.add('active');
    },

    async guardarProveedor() {
        const idProv = document.getElementById('edit-proveedor-id')?.value;
        const ruc = document.getElementById('prov-ruc')?.value.trim();
        const razonSocial = document.getElementById('prov-razon-social')?.value.trim();
        const contacto = document.getElementById('prov-contacto')?.value.trim();
        const telefono = document.getElementById('prov-telefono')?.value.trim();
        const correo = document.getElementById('prov-correo')?.value.trim();
        const direccion = document.getElementById('prov-direccion')?.value.trim();

        const u = JSON.parse(localStorage.getItem('user')) || {};
        const idSede = u.id_sede || 1;

        if (!ruc) {
            this.notify('Error: Por favor, ingresa el número de RUC.', 'error');
            document.getElementById('prov-ruc')?.focus();
            return;
        }

        if (!/^\d+$/.test(ruc)) {
            this.notify('Error en RUC: Debe contener únicamente dígitos numéricos.', 'error');
            document.getElementById('prov-ruc')?.focus();
            return;
        }

        if (ruc.length !== 11) {
            this.notify(`Error en RUC: Debe tener obligatoriamente 11 dígitos (${ruc.length} ingresados).`, 'error');
            document.getElementById('prov-ruc')?.focus();
            return;
        }

        if (!ruc.startsWith('10') && !ruc.startsWith('20')) {
            this.notify('Error en RUC: Solo se permite iniciar con "10" o "20".', 'error');
            document.getElementById('prov-ruc')?.focus();
            return;
        }

        if (!razonSocial) {
            this.notify('Por favor, ingresa la Razón Social o nombre del proveedor.', 'error');
            document.getElementById('prov-razon-social')?.focus();
            return;
        }

        if (!telefono) {
            this.notify('Error: El Celular es obligatorio.', 'error');
            document.getElementById('prov-telefono')?.focus();
            return;
        }

        if (!/^\d+$/.test(telefono)) {
            this.notify('Error en Celular: Debe contener únicamente dígitos numéricos.', 'error');
            document.getElementById('prov-telefono')?.focus();
            return;
        }

        if (telefono.length !== 9 || !telefono.startsWith('9')) {
            this.notify('Error en Celular: Debe tener 9 dígitos y comenzar obligatoriamente con "9".', 'error');
            document.getElementById('prov-telefono')?.focus();
            return;
        }

        const payload = {
            ruc: ruc,
            id_sede: idSede,
            razon_social: razonSocial,
            nombre_contacto: contacto,
            telefono: telefono,
            correo: correo,
            direccion: direccion
        };

        const userRole = u.activeRole || u.role || 'Administrador';
        const url = idProv ? `${this.apiUrl}/proveedores/${idProv}` : `${this.apiUrl}/proveedores`;
        const method = idProv ? 'PUT' : 'POST';

        const btnSave = document.getElementById('btn-guardar-proveedor');
        if (btnSave) {
            btnSave.disabled = true;
            btnSave.innerHTML = `<i class="ph ph-spinner spinner"></i> Guardando...`;
        }

        try {
            const res = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Role': userRole
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se pudo guardar el proveedor.');

            this.notify(data.message || 'Proveedor guardado exitosamente.', 'success');

            if (typeof closeModal === 'function') {
                closeModal('modal-proveedor');
            } else {
                document.getElementById('modal-proveedor')?.classList.remove('active');
            }

            await this.cargarProveedores();
        } catch (err) {
            this.notify(err.message, 'error');
        } finally {
            if (btnSave) {
                btnSave.disabled = false;
                btnSave.innerHTML = 'Guardar Proveedor';
            }
        }
    },

    confirmarAccionModal({ titulo, mensaje, nota = null, tipo = 'danger', textoBoton = 'Eliminar', iconoBoton = 'ph-trash', onConfirm }) {
        const modal = document.getElementById('modal-confirmacion-custom');
        if (!modal) {
            if (confirm(mensaje.replace(/<[^>]*>?/gm, ''))) {
                if (typeof onConfirm === 'function') onConfirm();
            }
            return;
        }

        const elTitulo = document.getElementById('modal-confirm-titulo');
        const elMensaje = document.getElementById('modal-confirm-mensaje');
        const elNotaWrapper = document.getElementById('modal-confirm-nota-wrapper');
        const elNota = document.getElementById('modal-confirm-nota');
        const elBtnAceptar = document.getElementById('modal-confirm-btn-aceptar');
        const elBtnCancelar = document.getElementById('modal-confirm-btn-cancelar');
        const elIcon = document.getElementById('modal-confirm-icon');
        const elIconWrapper = document.getElementById('modal-confirm-icon-wrapper');

        if (elTitulo) elTitulo.textContent = titulo || '¿Estás seguro?';
        if (elMensaje) elMensaje.innerHTML = mensaje;

        if (nota && elNotaWrapper && elNota) {
            elNota.textContent = nota;
            elNotaWrapper.style.display = 'block';
        } else if (elNotaWrapper) {
            elNotaWrapper.style.display = 'none';
        }

        if (elBtnAceptar) {
            elBtnAceptar.innerHTML = `<i class="ph-bold ${iconoBoton}"></i> ${textoBoton}`;
            elBtnAceptar.style.background = tipo === 'danger' ? '#dc2626' : '#0284c7';
        }

        if (elIconWrapper && elIcon) {
            elIcon.className = `ph-bold ${iconoBoton}`;
            elIconWrapper.style.background = tipo === 'danger' ? '#fee2e2' : '#e0f2fe';
            elIconWrapper.style.color = tipo === 'danger' ? '#dc2626' : '#0284c7';
        }

        const cerrar = () => {
            modal.classList.remove('active');
            if (elBtnAceptar) elBtnAceptar.onclick = null;
            if (elBtnCancelar) elBtnCancelar.onclick = null;
        };

        if (elBtnCancelar) elBtnCancelar.onclick = cerrar;

        if (elBtnAceptar) {
            elBtnAceptar.onclick = async () => {
                cerrar();
                if (typeof onConfirm === 'function') {
                    await onConfirm();
                }
            };
        }

        modal.classList.add('active');
    },

    eliminarProveedor(idProveedor, razonSocial) {
        this.confirmarAccionModal({
            titulo: '¿Eliminar Proveedor?',
            mensaje: `¿Estás seguro de que deseas eliminar al proveedor <strong>"${razonSocial}"</strong>?`,
            nota: 'Si tiene compras u órdenes registradas en el sistema, la eliminación será bloqueada automáticamente para resguardar la integridad contable.',
            tipo: 'danger',
            textoBoton: 'Sí, eliminar',
            iconoBoton: 'ph-trash',
            onConfirm: async () => {
                const u = JSON.parse(localStorage.getItem('user')) || {};
                const userRole = u.activeRole || u.role || 'Administrador';

                try {
                    const res = await fetch(`${this.apiUrl}/proveedores/${idProveedor}`, {
                        method: 'DELETE',
                        headers: { 'X-Role': userRole }
                    });

                    const data = await res.json();
                    if (!res.ok) throw new Error(data.error || 'No se pudo eliminar el proveedor.');

                    this.notify(data.message || 'Proveedor eliminado con éxito.', 'success');
                    await this.cargarProveedores();
                } catch (err) {
                    this.notify(err.message, 'error');
                }
            }
        });
    },

    // Catalogo de productos asociados al proveedor
    async abrirModalCatalogo(idProveedor) {
        this.proveedorActualCatalogo = idProveedor;
        const modal = document.getElementById('modal-catalogo-proveedor');
        if (modal) modal.classList.add('active');

        await this.cargarDetalleCatalogo(idProveedor);
        await this.asegurarProductosGenerales();
    },

    async cargarDetalleCatalogo(idProveedor) {
        const tbody = document.getElementById('catalogo-tbody');
        const headerInfo = document.getElementById('catalogo-proveedor-info');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 20px; color: #94a3b8;">
                    <i class="ph ph-spinner spinner" style="font-size: 1.3rem;"></i> Cargando catálogo...
                </td>
            </tr>
        `;

        try {
            const u = JSON.parse(localStorage.getItem('user')) || {};
            const userRole = u.activeRole || u.role || 'Administrador';
            const idSede = u.id_sede || 1;

            const res = await fetch(`${this.apiUrl}/proveedores/${idProveedor}/catalogo?id_sede=${idSede}`, {
                headers: { 'X-Role': userRole }
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || 'Error al obtener catálogo.');
            }

            const data = await res.json();

            if (headerInfo && data.proveedor) {
                headerInfo.innerHTML = `
                    <div style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">${data.proveedor.razon_social}</div>
                    <div style="font-size: 0.85rem; color: #64748b; display: flex; gap: 14px; margin-top: 4px; align-items: center;">
                        <span><strong>RUC:</strong> ${data.proveedor.ruc}</span>
                        <span><strong>Contacto:</strong> ${data.proveedor.nombre_contacto || '---'}</span>
                        <span style="background: #e0f2fe; color: #0369a1; padding: 2px 10px; border-radius: 6px; font-weight: 700; font-size: 0.8rem;">
                            <i class="ph ph-map-pin"></i> Sede: ${data.proveedor.sede_nombre || 'General'}
                        </span>
                    </div>
                `;
            }

            const badgeTotal = document.getElementById('catalogo-badge-total');
            const footerContador = document.getElementById('catalogo-contador-footer');
            const cantProds = (data.productos || []).length;
            if (badgeTotal) badgeTotal.textContent = `${cantProds} producto${cantProds !== 1 ? 's' : ''}`;
            if (footerContador) footerContador.textContent = `${cantProds} producto${cantProds !== 1 ? 's' : ''}`;

            if (!data.productos || data.productos.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" style="text-align: center; padding: 30px; color: #94a3b8; font-style: italic;">
                            Este proveedor aún no tiene productos asociados en su catálogo.<br>
                            Usa el formulario superior para incorporar productos y sus precios de compra pactados.
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = '';
            data.productos.forEach(it => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>
                        <span style="font-family: monospace; font-weight: 700; color: #1e293b;">${it.codigo_producto}</span>
                    </td>
                    <td>
                        <div style="font-weight: 600; color: #1e293b;">${it.nombre}</div>
                        <div style="font-size: 0.76rem; color: #64748b;">${it.categoria} ${it.subcategoria ? '• ' + it.subcategoria : ''}</div>
                    </td>
                    <td style="text-align: right;">
                        <span style="font-weight: 700; color: #059669; font-size: 0.95rem;">
                            S/. ${parseFloat(it.precio_compra).toFixed(2)}
                        </span>
                    </td>
                    <td style="text-align: center;">
                        <div style="display: inline-flex; gap: 6px;">
                            <button onclick="cambiarPrecioItemCatalogo(${it.id_producto}, '${it.nombre.replace(/'/g, "\\'")}', ${it.precio_compra})" 
                                    title="Actualizar Precio de Compra" 
                                    style="background: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; padding: 5px 9px; border-radius: 6px; cursor: pointer;">
                                <i class="ph-bold ph-pencil-simple"></i>
                            </button>
                            <button onclick="desvincularProductoCatalogo(${it.id_producto}, '${it.nombre.replace(/'/g, "\\'")}')" 
                                    title="Desvincular del Proveedor" 
                                    style="background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; padding: 5px 9px; border-radius: 6px; cursor: pointer;">
                                <i class="ph-bold ph-trash"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (err) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; padding: 20px; color: #ef4444;">
                        ${err.message}
                    </td>
                </tr>
            `;
        }
    },

    async asegurarProductosGenerales() {
        const select = document.getElementById('catalogo-select-producto');
        if (!select) return;

        if (this.productosGeneralesCache.length > 0) {
            this.poblarSelectProductos(this.productosGeneralesCache);
            return;
        }

        try {
            const u = JSON.parse(localStorage.getItem('user')) || {};
            const idSede = u.id_sede || 1;

            const res = await fetch(`${this.apiUrl}/productos?id_sede=${idSede}`);
            if (!res.ok) throw new Error('Error al cargar productos generales.');

            const prods = await res.json();
            this.productosGeneralesCache = prods;
            this.poblarSelectProductos(prods);
        } catch (e) {
            console.error('Error al cargar selector de productos:', e);
        }
    },

    poblarSelectProductos(prods) {
        const select = document.getElementById('catalogo-select-producto');
        if (!select) return;

        select.innerHTML = '<option value="">-- Selecciona un producto para asociar --</option>';
        prods.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id_producto;
            opt.textContent = `[${p.codigo_producto}] ${p.nombre} (${p.categoria || 'General'})`;
            opt.dataset.pcompra = p.precio_compra || 0;
            select.appendChild(opt);
        });
    },

    onSelectProductoCatalogo() {
        const select = document.getElementById('catalogo-select-producto');
        const inputPrecio = document.getElementById('catalogo-precio-compra');
        if (!select || !inputPrecio) return;

        const opt = select.options[select.selectedIndex];
        if (opt && opt.dataset.pcompra) {
            inputPrecio.value = parseFloat(opt.dataset.pcompra).toFixed(2);
        }
    },

    async asociarProductoACatalogo() {
        if (!this.proveedorActualCatalogo) return;

        const select = document.getElementById('catalogo-select-producto');
        const inputPrecio = document.getElementById('catalogo-precio-compra');

        const idProducto = parseInt(select.value);
        const precioCompra = parseFloat(inputPrecio.value);

        if (!idProducto) {
            this.notify('Por favor, selecciona un producto del catálogo general.', 'error');
            select.focus();
            return;
        }

        if (isNaN(precioCompra) || precioCompra <= 0) {
            this.notify('Ingresa un precio de compra válido mayor a 0.', 'error');
            inputPrecio.focus();
            return;
        }

        const u = JSON.parse(localStorage.getItem('user')) || {};
        const userRole = u.activeRole || u.role || 'Administrador';

        const payload = {
            id_producto: idProducto,
            precio_compra: precioCompra,
            codigo_proveedor: ''
        };

        try {
            const res = await fetch(`${this.apiUrl}/proveedores/${this.proveedorActualCatalogo}/catalogo`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Role': userRole
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se pudo asociar el producto.');

            this.notify(data.message, 'success');

            select.value = '';
            inputPrecio.value = '';

            await this.cargarDetalleCatalogo(this.proveedorActualCatalogo);
            this.cargarProveedores();
        } catch (err) {
            this.notify(err.message, 'error');
        }
    },

    cambiarPrecioItemCatalogo(idProducto, nombreProd, precioActual) {
        const modal = document.getElementById('modal-editar-precio');
        const elNombre = document.getElementById('modal-precio-producto-nombre');
        const inputPrecio = document.getElementById('modal-nuevo-precio-input');
        const btnGuardar = document.getElementById('modal-precio-btn-guardar');

        if (!modal || !inputPrecio || !btnGuardar) return;

        if (elNombre) elNombre.textContent = nombreProd;
        inputPrecio.value = parseFloat(precioActual).toFixed(2);

        btnGuardar.onclick = async () => {
            const nuevoPrecio = parseFloat(inputPrecio.value);
            if (isNaN(nuevoPrecio) || nuevoPrecio <= 0) {
                this.notify('Ingresa un precio de compra válido mayor a 0.', 'error');
                inputPrecio.focus();
                return;
            }

            const u = JSON.parse(localStorage.getItem('user')) || {};
            const userRole = u.activeRole || u.role || 'Administrador';

            try {
                btnGuardar.disabled = true;
                btnGuardar.textContent = 'Guardando...';

                const res = await fetch(`${this.apiUrl}/proveedores/${this.proveedorActualCatalogo}/catalogo`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Role': userRole
                    },
                    body: JSON.stringify({
                        id_producto: idProducto,
                        precio_compra: nuevoPrecio
                    })
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Error al actualizar precio.');

                this.notify(data.message, 'success');
                modal.classList.remove('active');
                await this.cargarDetalleCatalogo(this.proveedorActualCatalogo);
            } catch (err) {
                this.notify(err.message, 'error');
            } finally {
                btnGuardar.disabled = false;
                btnGuardar.textContent = 'Guardar Precio';
            }
        };

        modal.classList.add('active');
        setTimeout(() => {
            inputPrecio.focus();
            inputPrecio.select();
        }, 120);
    },

    desvincularProductoCatalogo(idProducto, nombreProd) {
        this.confirmarAccionModal({
            titulo: '¿Desvincular Producto?',
            mensaje: `¿Deseas desvincular el producto <strong>"${nombreProd}"</strong> del catálogo de este proveedor?`,
            tipo: 'danger',
            textoBoton: 'Sí, desvincular',
            iconoBoton: 'ph-trash',
            onConfirm: async () => {
                const u = JSON.parse(localStorage.getItem('user')) || {};
                const userRole = u.activeRole || u.role || 'Administrador';

                try {
                    const res = await fetch(`${this.apiUrl}/proveedores/${this.proveedorActualCatalogo}/catalogo/${idProducto}`, {
                        method: 'DELETE',
                        headers: { 'X-Role': userRole }
                    });

                    const data = await res.json();
                    if (!res.ok) throw new Error(data.error || 'Error al desvincular producto.');

                    this.notify(data.message, 'success');

                    await this.cargarDetalleCatalogo(this.proveedorActualCatalogo);
                    this.cargarProveedores();
                } catch (err) {
                    this.notify(err.message, 'error');
                }
            }
        });
    }
};

// Funciones globales expuestas para los onclick del HTML
window.ProveedoresModule = ProveedoresModule;
window.cambiarSedeProveedores = () => ProveedoresModule.cambiarSedeProveedores();
window.cargarProveedores = () => ProveedoresModule.cargarProveedores();
window.actualizarCardsResumen = (data) => ProveedoresModule.actualizarCardsResumen(data);
window.renderizarTablaProveedores = (provs) => ProveedoresModule.renderizarTablaProveedores(provs);
window.filtrarProveedores = () => ProveedoresModule.filtrarProveedores();
window.validarInputRucEnTiempoReal = (input) => ProveedoresModule.validarInputRucEnTiempoReal(input);
window.abrirModalCrearProveedor = () => ProveedoresModule.abrirModalCrearProveedor();
window.abrirModalEditarProveedor = (id) => ProveedoresModule.abrirModalEditarProveedor(id);
window.guardarProveedor = () => ProveedoresModule.guardarProveedor();
window.confirmarAccionModal = (cfg) => ProveedoresModule.confirmarAccionModal(cfg);
window.eliminarProveedor = (id, nom) => ProveedoresModule.eliminarProveedor(id, nom);
window.abrirModalCatalogo = (id) => ProveedoresModule.abrirModalCatalogo(id);
window.cargarDetalleCatalogo = (id) => ProveedoresModule.cargarDetalleCatalogo(id);
window.asegurarProductosGenerales = () => ProveedoresModule.asegurarProductosGenerales();
window.poblarSelectProductos = (p) => ProveedoresModule.poblarSelectProductos(p);
window.onSelectProductoCatalogo = () => ProveedoresModule.onSelectProductoCatalogo();
window.asociarProductoACatalogo = () => ProveedoresModule.asociarProductoACatalogo();
window.cambiarPrecioItemCatalogo = (id, n, p) => ProveedoresModule.cambiarPrecioItemCatalogo(id, n, p);
window.desvincularProductoCatalogo = (id, n) => ProveedoresModule.desvincularProductoCatalogo(id, n);
