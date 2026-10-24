var API_URL = 'http://localhost:8000/api';

function showNotification(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.bottom = '24px';
        container.style.right = '24px';
        container.style.zIndex = '999999';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '10px';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const isSuccess = type === 'success';
    toast.style.background = isSuccess ? '#10b981' : '#ef4444';
    toast.style.color = '#ffffff';
    toast.style.padding = '14px 22px';
    toast.style.borderRadius = '10px';
    toast.style.boxShadow = '0 10px 25px rgba(0,0,0,0.18)';
    toast.style.fontFamily = "'Inter', sans-serif";
    toast.style.fontWeight = '600';
    toast.style.fontSize = '0.92rem';
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.style.gap = '10px';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(20px)';
    toast.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
    
    const iconClass = isSuccess ? 'ph-check-circle' : 'ph-warning-circle';
    toast.innerHTML = `<i class="ph-fill ${iconClass}" style="font-size: 1.3rem;"></i><span>${message}</span>`;

    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}


document.addEventListener('DOMContentLoaded', () => {
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });

    cargarCategorias();
    cargarProductos();

    
    // Configurar buscador con debounce
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let almacenSearchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(almacenSearchTimeout);
            almacenSearchTimeout = setTimeout(() => {
                const term = e.target.value.toLowerCase();
                const rows = document.querySelectorAll('#productos-tbody tr');
                rows.forEach(row => {
                    const codigo = row.cells[0]?.textContent.toLowerCase() || '';
                    const nombre = row.cells[1]?.textContent.toLowerCase() || '';
                    const categoria = row.cells[2]?.textContent.toLowerCase() || '';
                    if (codigo.includes(term) || nombre.includes(term) || categoria.includes(term)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            }, 200);
        });
    }

    
    // Obtener usuario del localstorage
    const user = JSON.parse(localStorage.getItem('user'));
    if (user) {
        document.getElementById('display-username').textContent = user.first_name + ' ' + user.last_name;
    }
});



async function abrirModalCrearProducto() {
    const inputCodigo = document.getElementById('new-prod-codigo');
    if (inputCodigo) {
        inputCodigo.value = 'Cargando...';
        inputCodigo.readOnly = true;
    }

    document.getElementById('new-prod-nombre').value = '';
    document.getElementById('new-prod-desc').value = '';
    document.getElementById('new-prod-pcompra').value = '0';
    document.getElementById('new-prod-pventa').value = '0';
    document.getElementById('new-prod-stock').value = '10';
    document.getElementById('new-prod-minimo').value = '5';
    document.getElementById('modal-crear-producto').classList.add('active');

    try {
        const response = await fetch(`${API_URL}/productos/siguiente-codigo`);
        const data = await response.json();
        if (data && data.codigo && inputCodigo) {
            inputCodigo.value = data.codigo;
        }
    } catch (e) {
        console.error('Error obteniendo siguiente codigo:', e);
        if (inputCodigo) inputCodigo.value = 'PROD-00001';
    }
}


let listaCategoriasGlobal = [];
let listaSubcategoriasGlobal = [];

async function cargarCategorias() {
    try {
        const [resCat, resSub] = await Promise.all([
            fetch(`${API_URL}/categorias`),
            fetch(`${API_URL}/subcategorias`)
        ]);

        listaCategoriasGlobal = await resCat.json();
        listaSubcategoriasGlobal = await resSub.json();
        
        const selectPadreProd = document.getElementById('new-prod-categoria-padre');
        const selectSubcatPadre = document.getElementById('new-subcat-categoria-padre');
        
        if (selectPadreProd) {
            selectPadreProd.innerHTML = '<option value="">Seleccione Categoría Principal...</option>';
            listaCategoriasGlobal.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id_categoria;
                option.textContent = cat.nombre;
                selectPadreProd.appendChild(option);
            });
            onCategoriaPadreChange();
        }

        if (selectSubcatPadre) {
            selectSubcatPadre.innerHTML = '<option value="">Seleccione Categoría Padre...</option>';
            listaCategoriasGlobal.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id_categoria;
                option.textContent = cat.nombre;
                selectSubcatPadre.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error cargando categorias y subcategorias:', error);
    }
}

async function onCategoriaPadreChange() {
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
    
    // Filtrar subcategorías pertenecientes a este id_categoria de la API dedicada
    try {
        const res = await fetch(`${API_URL}/subcategorias?id_categoria=${padreId}`);
        const subcats = await res.json();

        if (!Array.isArray(subcats) || subcats.length === 0) {
            const option = document.createElement('option');
            option.value = "";
            option.textContent = "(Sin subcategorías específicas)";
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
}


function abrirModalCrearCategoria(id = null) {
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
        titleEl.textContent = id ? 'Editar Categoría' : 'Nueva Categoría / Subcategoría';
    }

    const modal = document.getElementById('modal-crear-categoria');
    if (modal) modal.classList.add('active');
}

async function guardarCategoria() {
    const editId = document.getElementById('edit-cat-id')?.value;
    const nombre = document.getElementById('new-cat-nombre')?.value.trim();
    const id_padre = document.getElementById('new-cat-padre')?.value || null;
    const descripcion = document.getElementById('new-cat-desc')?.value.trim();

    if (!nombre) {
        if (typeof showNotification === 'function') {
            showNotification('El nombre de la categoría es obligatorio', 'error');
        } else {
            alert('El nombre de la categoría es obligatorio');
        }
        return;
    }

    const isEdit = !!editId;
    const url = isEdit ? `${API_URL}/categorias/${editId}` : `${API_URL}/categorias`;
    const method = isEdit ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre, id_padre, descripcion })
        });

        const data = await response.json();

        if (response.ok) {
            if (typeof showNotification === 'function') {
                showNotification(isEdit ? 'Categoría actualizada con éxito' : 'Categoría creada con éxito', 'success');
            } else {
                alert(isEdit ? 'Categoría actualizada con éxito' : 'Categoría creada con éxito');
            }
            closeModal('modal-crear-categoria');
            await cargarCategorias();
        } else {
            if (typeof showNotification === 'function') {
                showNotification(data.error || 'Error al guardar categoría', 'error');
            } else {
                alert(data.error || 'Error al guardar categoría');
            }
        }
    } catch (err) {
        console.error('Error guardando categoría:', err);
        alert('Error de conexión con el servidor');
    }
}

let productosAlmacenGlobal = [];
let paginaActualAlmacen = 1;
const productosPorPaginaAlmacen = 10;
let busquedaAlmacenQuery = '';

async function cargarProductosAlmacen() {
    try {
        const user = JSON.parse(localStorage.getItem('user'));
        const sedeParam = user && user.id_sede ? `?sede_id=${user.id_sede}` : '';
        const response = await fetch(`${API_URL}/productos${sedeParam}`);
        productosAlmacenGlobal = await response.json();
        paginaActualAlmacen = 1;
        renderTablaProductosAlmacen();
    } catch (error) {
        console.error('Error cargando productos:', error);
    }
}

function renderTablaProductosAlmacen() {
    const tbody = document.getElementById('productos-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const query = busquedaAlmacenQuery.toLowerCase().trim();
    const filtrados = productosAlmacenGlobal.filter(p => {
        const codigo = (p.codigo_producto || '').toLowerCase();
        const nombre = (p.nombre || '').toLowerCase();
        const cat = (p.categoria || '').toLowerCase();
        const subcat = (p.subcategoria || '').toLowerCase();
        return codigo.includes(query) || nombre.includes(query) || cat.includes(query) || subcat.includes(query);
    });

    const totalPaginas = Math.ceil(filtrados.length / productosPorPaginaAlmacen) || 1;
    if (paginaActualAlmacen > totalPaginas) paginaActualAlmacen = totalPaginas;
    if (paginaActualAlmacen < 1) paginaActualAlmacen = 1;

    const inicio = (paginaActualAlmacen - 1) * productosPorPaginaAlmacen;
    const fin = inicio + productosPorPaginaAlmacen;
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
        pagInfo.textContent = `Página ${paginaActualAlmacen} de ${totalPaginas} (${filtrados.length} productos)`;
    }

    const btnPrev = document.getElementById('btn-pag-prev');
    if (btnPrev) btnPrev.disabled = (paginaActualAlmacen <= 1);

    const btnNext = document.getElementById('btn-pag-next');
    if (btnNext) btnNext.disabled = (paginaActualAlmacen >= totalPaginas);
}

function filtrarProductosAlmacen(query) {
    busquedaAlmacenQuery = query;
    paginaActualAlmacen = 1;
    renderTablaProductosAlmacen();
}

function cambiarPaginaAlmacen(delta) {
    paginaActualAlmacen += delta;
    renderTablaProductosAlmacen();
}

async function crearProducto() {
    const user = JSON.parse(localStorage.getItem('user'));
    const padreVal = document.getElementById('new-prod-categoria-padre')?.value;
    const subcatVal = document.getElementById('new-prod-subcategoria')?.value;
    const codigoInput = document.getElementById('new-prod-codigo')?.value.trim() || '';

    if (!codigoInput || codigoInput.length < 3) {
        showNotification('El código de producto debe tener al menos 3 caracteres (Ej: PROD-00001).', 'error');
        return;
    }

    const data = {
        codigo_producto: codigoInput,
        nombre: document.getElementById('new-prod-nombre').value,
        id_categoria: padreVal ? parseInt(padreVal) : null,
        id_subcategoria: subcatVal ? parseInt(subcatVal) : null,
        descripcion: document.getElementById('new-prod-desc').value,
        precio_compra: parseFloat(document.getElementById('new-prod-pcompra').value) || 0,
        precio_venta: parseFloat(document.getElementById('new-prod-pventa').value) || 0,
        stock_actual: parseInt(document.getElementById('new-prod-stock').value) || 0,
        stock_minimo: parseInt(document.getElementById('new-prod-minimo').value) || 0,
        id_usuario: user ? user.id : 1
    };


    try {
        const response = await fetch(`${API_URL}/productos`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Producto creado con éxito', 'success');
            closeModal('modal-crear-producto');
            cargarProductosAlmacen();
        } else {
            showNotification(result.error || 'Error creando producto', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error de conexión', 'error');
    }
}

function abrirModalCrearCategoria() {
    const elNombre = document.getElementById('new-cat-nombre');
    const elDesc = document.getElementById('new-cat-desc');
    if (elNombre) elNombre.value = '';
    if (elDesc) elDesc.value = '';
    
    const modal = document.getElementById('modal-crear-categoria');
    if (modal) modal.classList.add('active');
}

async function guardarCategoria() {
    const nombre = document.getElementById('new-cat-nombre')?.value.trim();
    const descripcion = document.getElementById('new-cat-desc')?.value.trim();

    if (!nombre) {
        showNotification('El nombre de la categoría principal es obligatorio.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/categorias`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nombre: nombre,
                descripcion: descripcion
            })
        });

        const res = await response.json();
        if (response.ok) {
            showNotification('Categoría Principal creada con éxito', 'success');
            closeModal('modal-crear-categoria');
            await cargarCategorias();
        } else {
            showNotification(res.error || 'Error al crear la categoría', 'error');
        }
    } catch (e) {
        console.error(e);
        showNotification('Error de conexión al guardar categoría', 'error');
    }
}

function abrirModalCrearSubcategoria() {
    const elNombre = document.getElementById('new-subcat-nombre');
    const elDesc = document.getElementById('new-subcat-desc');
    const elPadre = document.getElementById('new-subcat-categoria-padre');
    if (elNombre) elNombre.value = '';
    if (elDesc) elDesc.value = '';
    if (elPadre) elPadre.value = '';

    const modal = document.getElementById('modal-crear-subcategoria');
    if (modal) modal.classList.add('active');
}

async function guardarSubcategoria() {
    const id_categoria = document.getElementById('new-subcat-categoria-padre')?.value;
    const nombre = document.getElementById('new-subcat-nombre')?.value.trim();
    const descripcion = document.getElementById('new-subcat-desc')?.value.trim();

    if (!id_categoria) {
        showNotification('Debes seleccionar una Categoría Padre obligatoriamente.', 'error');
        return;
    }
    if (!nombre) {
        showNotification('El nombre de la subcategoría es obligatorio.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/subcategorias`, {
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
            showNotification('Subcategoría creada con éxito', 'success');
            closeModal('modal-crear-subcategoria');
            await cargarCategorias();
        } else {
            showNotification(res.error || 'Error al crear la subcategoría', 'error');
        }
    } catch (e) {
        console.error(e);
        showNotification('Error de conexión al guardar subcategoría', 'error');
    }
}



