// Modulo de Almacen e Inventario
// Administra productos, categorias, subcategorias y el stock por cada sede

const AlmacenModule = {
    apiUrl: window.API_BASE_URL || 'http://localhost:8000/api',
    listaCategoriasGlobal: [],
    listaSubcategoriasGlobal: [],
    productosAlmacenGlobal: [],
    paginaActualAlmacen: 1,
    productosPorPaginaAlmacen: 10,
    busquedaAlmacenQuery: '',

    notify(message, type = 'success') {
        if (window.Toast && typeof window.Toast[type] === 'function') {
            window.Toast[type](message);
        } else if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            alert(message);
        }
    },

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('active');
    },

    async abrirModalCrearProducto() {
        const inputCodigo = document.getElementById('new-prod-codigo');
        if (inputCodigo) {
            inputCodigo.value = 'Cargando...';
            inputCodigo.readOnly = true;
        }

        const elNom = document.getElementById('new-prod-nombre');
        const elDesc = document.getElementById('new-prod-desc');
        const elPcompra = document.getElementById('new-prod-pcompra');
        const elPventa = document.getElementById('new-prod-pventa');
        const elStock = document.getElementById('new-prod-stock');
        const elMinimo = document.getElementById('new-prod-minimo');

        if (elNom) elNom.value = '';
        if (elDesc) elDesc.value = '';
        if (elPcompra) elPcompra.value = '0';
        if (elPventa) elPventa.value = '0';
        if (elStock) elStock.value = '10';
        if (elMinimo) elMinimo.value = '5';

        const modal = document.getElementById('modal-crear-producto');
        if (modal) modal.classList.add('active');

        try {
            const response = await fetch(`${this.apiUrl}/productos/siguiente-codigo`);
            const data = await response.json();
            if (data && data.codigo && inputCodigo) {
                inputCodigo.value = data.codigo;
            }
        } catch (e) {
            console.error('Error obteniendo siguiente codigo:', e);
            if (inputCodigo) inputCodigo.value = 'PROD-00001';
        }
    },

    async cargarCategorias() {
        try {
            const [resCat, resSub] = await Promise.all([
                fetch(`${this.apiUrl}/categorias`),
                fetch(`${this.apiUrl}/subcategorias`)
            ]);

            this.listaCategoriasGlobal = await resCat.json();
            this.listaSubcategoriasGlobal = await resSub.json();

            const selectPadreProd = document.getElementById('new-prod-categoria-padre');
            const selectSubcatPadre = document.getElementById('new-subcat-categoria-padre');

            if (selectPadreProd) {
                selectPadreProd.innerHTML = '<option value="">Seleccione Categoría Principal...</option>';
                this.listaCategoriasGlobal.forEach(cat => {
                    const option = document.createElement('option');
                    option.value = cat.id_categoria;
                    option.textContent = cat.nombre;
                    selectPadreProd.appendChild(option);
                });
                this.onCategoriaPadreChange();
            }

            if (selectSubcatPadre) {
                selectSubcatPadre.innerHTML = '<option value="">Seleccione Categoría Padre...</option>';
                this.listaCategoriasGlobal.forEach(cat => {
                    const option = document.createElement('option');
                    option.value = cat.id_categoria;
                    option.textContent = cat.nombre;
                    selectSubcatPadre.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error cargando categorias y subcategorias:', error);
        }
    },

    async onCategoriaPadreChange() {
        const selectPadre = document.getElementById('new-prod-categoria-padre');
        const selectSub = document.getElementById('new-prod-subcategoria');
        if (!selectPadre || !selectSub) return;

        const padreId = parseInt(selectPadre.value);
        selectSub.innerHTML = '<option value="">Seleccione Subcategoría...</option>';

        if (!padreId) {
            selectSub.disabled = true;
            return;
        }

        selectSub.disabled = false;

        try {
            const res = await fetch(`${this.apiUrl}/subcategorias?id_categoria=${padreId}`);
            const subcats = await res.json();

            if (!Array.isArray(subcats) || subcats.length === 0) {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = '(Sin subcategorías específicas)';
                selectSub.appendChild(option);
            } else {
                subcats.forEach(sub => {
                    const option = document.createElement('option');
                    option.value = sub.id_subcategoria;
                    option.textContent = sub.nombre;
                    selectSub.appendChild(option);
                });
            }
        } catch (e) {
            console.error('Error filtrando subcategorias:', e);
        }
    },

    async cargarProductosAlmacen() {
        try {
            const user = JSON.parse(localStorage.getItem('user'));
            const sedeParam = user && user.id_sede ? `?sede_id=${user.id_sede}` : '';
            const response = await fetch(`${this.apiUrl}/productos${sedeParam}`);
            this.productosAlmacenGlobal = await response.json();
            this.paginaActualAlmacen = 1;
            this.renderTablaProductosAlmacen();
        } catch (error) {
            console.error('Error cargando productos:', error);
        }
    },

    renderTablaProductosAlmacen() {
        const tbody = document.getElementById('productos-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        const query = this.busquedaAlmacenQuery.toLowerCase().trim();
        const filtrados = this.productosAlmacenGlobal.filter(p => {
            const codigo = (p.codigo_producto || '').toLowerCase();
            const nombre = (p.nombre || '').toLowerCase();
            const cat = (p.categoria || '').toLowerCase();
            const subcat = (p.subcategoria || '').toLowerCase();
            return codigo.includes(query) || nombre.includes(query) || cat.includes(query) || subcat.includes(query);
        });

        const totalPaginas = Math.ceil(filtrados.length / this.productosPorPaginaAlmacen) || 1;
        if (this.paginaActualAlmacen > totalPaginas) this.paginaActualAlmacen = totalPaginas;
        if (this.paginaActualAlmacen < 1) this.paginaActualAlmacen = 1;

        const inicio = (this.paginaActualAlmacen - 1) * this.productosPorPaginaAlmacen;
        const fin = inicio + this.productosPorPaginaAlmacen;
        const paginaProductos = filtrados.slice(inicio, fin);

        if (paginaProductos.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="8" style="text-align:center; padding: 20px; color: #666;">No se encontraron productos</td>`;
            tbody.appendChild(tr);
        } else {
            paginaProductos.forEach(p => {
                const estaBajo = p.stock_actual <= p.stock_minimo;
                const stockColor = estaBajo ? '#ef4444' : '#10b981';
                const stockPeso = estaBajo ? 'bold' : 'normal';
                const emojiAlerta = estaBajo ? ' ⚠️' : '';

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${p.codigo_producto}</td>
                    <td>${p.nombre}${emojiAlerta}</td>
                    <td><span style="font-weight: 500;">${p.categoria || 'Sin categoría'}</span></td>
                    <td><span style="color: #6b7280; font-size: 0.88rem;">${p.subcategoria || 'General'}</span></td>
                    <td style="color: ${stockColor}; font-weight: ${stockPeso};">${p.stock_actual}</td>
                    <td>${p.stock_minimo}</td>
                    <td>S/ ${(p.precio_compra || 0).toFixed(2)}</td>
                    <td>S/ ${(p.precio_venta || 0).toFixed(2)}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        const pagInfo = document.getElementById('paginacion-info');
        if (pagInfo) {
            pagInfo.textContent = `Página ${this.paginaActualAlmacen} de ${totalPaginas} (${filtrados.length} productos)`;
        }

        const btnPrev = document.getElementById('btn-pag-prev');
        if (btnPrev) btnPrev.disabled = (this.paginaActualAlmacen <= 1);

        const btnNext = document.getElementById('btn-pag-next');
        if (btnNext) btnNext.disabled = (this.paginaActualAlmacen >= totalPaginas);
    },

    filtrarProductosAlmacen(query) {
        this.busquedaAlmacenQuery = query;
        this.paginaActualAlmacen = 1;
        this.renderTablaProductosAlmacen();
    },

    cambiarPaginaAlmacen(delta) {
        this.paginaActualAlmacen += delta;
        this.renderTablaProductosAlmacen();
    },

    async crearProducto() {
        const user = JSON.parse(localStorage.getItem('user'));
        const padreVal = document.getElementById('new-prod-categoria-padre')?.value;
        const subcatVal = document.getElementById('new-prod-subcategoria')?.value;
        const codigoInput = document.getElementById('new-prod-codigo')?.value.trim() || '';

        if (!codigoInput || codigoInput.length < 3) {
            this.notify('El código de producto debe tener al menos 3 caracteres (Ej: PROD-00001).', 'error');
            return;
        }

        const data = {
            codigo_producto: codigoInput,
            nombre: document.getElementById('new-prod-nombre')?.value || '',
            id_categoria: padreVal ? parseInt(padreVal) : null,
            id_subcategoria: subcatVal ? parseInt(subcatVal) : null,
            descripcion: document.getElementById('new-prod-desc')?.value || '',
            precio_compra: parseFloat(document.getElementById('new-prod-pcompra')?.value) || 0,
            precio_venta: parseFloat(document.getElementById('new-prod-pventa')?.value) || 0,
            stock_actual: parseInt(document.getElementById('new-prod-stock')?.value) || 0,
            stock_minimo: parseInt(document.getElementById('new-prod-minimo')?.value) || 0,
            id_usuario: user ? user.id : 1
        };

        try {
            const response = await fetch(`${this.apiUrl}/productos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                this.notify('Producto creado con éxito', 'success');
                this.closeModal('modal-crear-producto');
                await this.cargarProductosAlmacen();

                // Notificar a toda la SPA que el stock/catálogo cambió
                if (window.EventBus) {
                    window.EventBus.emit('stock:updated', { source: 'almacen' });
                }
            } else {
                this.notify(result.error || 'Error creando producto', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.notify('Error de conexión al crear producto', 'error');
        }
    },

    abrirModalCrearCategoria(id = null) {
        const editIdInput = document.getElementById('edit-cat-id');
        const nameInput = document.getElementById('new-cat-nombre');
        const descInput = document.getElementById('new-cat-desc');
        const padreSelect = document.getElementById('new-cat-padre');
        const titleEl = document.getElementById('modal-crear-categoria-title');

        if (editIdInput) editIdInput.value = id || '';
        if (nameInput) nameInput.value = '';
        if (descInput) descInput.value = '';
        if (padreSelect) padreSelect.value = '';

        if (titleEl) {
            titleEl.textContent = id ? 'Editar Categoría' : 'Nueva Categoría Principal';
        }

        const modal = document.getElementById('modal-crear-categoria');
        if (modal) modal.classList.add('active');
    },

    async guardarCategoria() {
        const editId = document.getElementById('edit-cat-id')?.value;
        const nombre = document.getElementById('new-cat-nombre')?.value.trim();
        const id_padre = document.getElementById('new-cat-padre')?.value || null;
        const descripcion = document.getElementById('new-cat-desc')?.value.trim();

        if (!nombre) {
            this.notify('El nombre de la categoría principal es obligatorio', 'error');
            return;
        }

        const isEdit = !!editId;
        const url = isEdit ? `${this.apiUrl}/categorias/${editId}` : `${this.apiUrl}/categorias`;
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nombre, id_padre, descripcion })
            });

            const data = await response.json();

            if (response.ok) {
                this.notify(isEdit ? 'Categoría actualizada con éxito' : 'Categoría creada con éxito', 'success');
                this.closeModal('modal-crear-categoria');
                await this.cargarCategorias();
            } else {
                this.notify(data.error || 'Error al guardar categoría', 'error');
            }
        } catch (err) {
            console.error('Error guardando categoría:', err);
            this.notify('Error de conexión con el servidor', 'error');
        }
    },

    abrirModalCrearSubcategoria() {
        const elNombre = document.getElementById('new-subcat-nombre');
        const elDesc = document.getElementById('new-subcat-desc');
        const elPadre = document.getElementById('new-subcat-categoria-padre');
        if (elNombre) elNombre.value = '';
        if (elDesc) elDesc.value = '';
        if (elPadre) elPadre.value = '';

        const modal = document.getElementById('modal-crear-subcategoria');
        if (modal) modal.classList.add('active');
    },

    async guardarSubcategoria() {
        const id_categoria = document.getElementById('new-subcat-categoria-padre')?.value;
        const nombre = document.getElementById('new-subcat-nombre')?.value.trim();
        const descripcion = document.getElementById('new-subcat-desc')?.value.trim();

        if (!id_categoria) {
            this.notify('Debes seleccionar una Categoría Padre obligatoriamente.', 'error');
            return;
        }
        if (!nombre) {
            this.notify('El nombre de la subcategoría es obligatorio.', 'error');
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/subcategorias`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nombre: nombre,
                    descripcion: descripcion,
                    id_categoria: parseInt(id_categoria)
                })
            });

            const res = await response.json();
            if (response.ok) {
                this.notify('Subcategoría creada con éxito', 'success');
                this.closeModal('modal-crear-subcategoria');
                await this.cargarCategorias();
            } else {
                this.notify(res.error || 'Error al crear la subcategoría', 'error');
            }
        } catch (e) {
            console.error(e);
            this.notify('Error de conexión al guardar subcategoría', 'error');
        }
    },

    init() {
        // Cierra el modal si se hace clic afuera
        const overlays = document.querySelectorAll('.modal-overlay');
        overlays.forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    overlay.classList.remove('active');
                }
            });
        });

        // Busqueda en tiempo real con un pequeno retraso
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            let almacenSearchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(almacenSearchTimeout);
                almacenSearchTimeout = setTimeout(() => {
                    this.filtrarProductosAlmacen(e.target.value);
                }, 200);
            });
        }

        // Recarga el inventario si otra pantalla notifica cambios de stock
        if (window.EventBus) {
            window.EventBus.on('stock:updated', () => {
                this.cargarProductosAlmacen();
            });
        }
    }
};

// Funciones accesibles desde los eventos onclick del HTML
window.AlmacenModule = AlmacenModule;
window.cargarCategorias = () => AlmacenModule.cargarCategorias();
window.onCategoriaPadreChange = () => AlmacenModule.onCategoriaPadreChange();
window.cargarProductosAlmacen = () => AlmacenModule.cargarProductosAlmacen();
window.cargarProductos = () => AlmacenModule.cargarProductosAlmacen(); // Alias para router o vistas legacy
window.renderTablaProductosAlmacen = () => AlmacenModule.renderTablaProductosAlmacen();
window.filtrarProductosAlmacen = (q) => AlmacenModule.filtrarProductosAlmacen(q);
window.cambiarPaginaAlmacen = (d) => AlmacenModule.cambiarPaginaAlmacen(d);
window.abrirModalCrearProducto = () => AlmacenModule.abrirModalCrearProducto();
window.crearProducto = () => AlmacenModule.crearProducto();
window.abrirModalCrearCategoria = (id) => AlmacenModule.abrirModalCrearCategoria(id);
window.guardarCategoria = () => AlmacenModule.guardarCategoria();
window.abrirModalCrearSubcategoria = () => AlmacenModule.abrirModalCrearSubcategoria();
window.guardarSubcategoria = () => AlmacenModule.guardarSubcategoria();
if (!window.closeModal) window.closeModal = (id) => AlmacenModule.closeModal(id);

// Inicializar al cargar el script o DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AlmacenModule.init());
} else {
    AlmacenModule.init();
}
