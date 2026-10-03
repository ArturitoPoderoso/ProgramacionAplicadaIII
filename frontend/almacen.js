var API_URL = 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', () => {
    cargarCategorias();
    cargarProductos();
    
    // Configurar buscador
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
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
        });
    }
    
    // Obtener usuario del localstorage
    const user = JSON.parse(localStorage.getItem('user'));
    if (user) {
        document.getElementById('display-username').textContent = user.first_name + ' ' + user.last_name;
    }
});



function abrirModalCrearProducto() {
    document.getElementById('new-prod-codigo').value = '';
    document.getElementById('new-prod-nombre').value = '';
    document.getElementById('new-prod-desc').value = '';
    document.getElementById('new-prod-pcompra').value = '0';
    document.getElementById('new-prod-pventa').value = '0';
    document.getElementById('new-prod-stock').value = '10';
    document.getElementById('new-prod-minimo').value = '5';
    document.getElementById('modal-crear-producto').classList.add('active');
}

let listaCategoriasGlobal = [];

async function cargarCategorias() {
    try {
        const response = await fetch(`${API_URL}/categorias`);
        listaCategoriasGlobal = await response.json();
        
        const selectPadreProd = document.getElementById('new-prod-categoria-padre');
        const selectPadreCat = document.getElementById('new-cat-padre');
        
        if (selectPadreProd) {
            selectPadreProd.innerHTML = '<option value="">Seleccione Categoría...</option>';
            listaCategoriasGlobal.filter(cat => !cat.id_padre).forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id_categoria;
                option.textContent = cat.nombre;
                selectPadreProd.appendChild(option);
            });
            onCategoriaPadreChange();
        }

        if (selectPadreCat) {
            selectPadreCat.innerHTML = '<option value="">Ninguna (Categoría Principal)</option>';
            listaCategoriasGlobal.filter(c => !c.id_padre).forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id_categoria;
                option.textContent = cat.nombre;
                selectPadreCat.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error cargando categorias:', error);
    }
}

function onCategoriaPadreChange() {
    const selectPadre = document.getElementById('new-prod-categoria-padre');
    const selectSub = document.getElementById('new-prod-subcategoria');
    if (!selectPadre || !selectSub) return;

    const padreId = parseInt(selectPadre.value);
    selectSub.innerHTML = '<option value="">Ninguna / General</option>';

    if (!padreId) {
        selectSub.disabled = true;
        return;
    }

    selectSub.disabled = false;
    const subcats = listaCategoriasGlobal.filter(c => c.id_padre === padreId);

    if (subcats.length === 0) {
        const option = document.createElement('option');
        option.value = "";
        option.textContent = "(Sin subcategorías específicas)";
        selectSub.appendChild(option);
    } else {
        subcats.forEach(sub => {
            const option = document.createElement('option');
            option.value = sub.id_categoria;
            option.textContent = sub.nombre;
            selectSub.appendChild(option);
        });
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
    const subcatVal = document.getElementById('new-prod-subcategoria')?.value;
    const padreVal = document.getElementById('new-prod-categoria-padre')?.value;
    const catId = subcatVal || padreVal || null;

    const data = {
        codigo_producto: document.getElementById('new-prod-codigo').value,
        nombre: document.getElementById('new-prod-nombre').value,
        id_categoria: catId ? parseInt(catId) : null,
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
            alert('Producto creado con éxito');
            closeModal('modal-crear-producto');
            cargarProductosAlmacen();
        } else {
            alert(result.error || 'Error creando producto');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión');
    }
}
