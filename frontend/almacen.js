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
    document.getElementById('new-prod-minimo').value = '0';
    document.getElementById('modal-crear-producto').classList.add('active');
}

async function cargarCategorias() {
    try {
        const response = await fetch(`${API_URL}/categorias`);
        const categorias = await response.json();
        const select = document.getElementById('new-prod-categoria');
        
        categorias.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id_categoria;
            option.textContent = cat.nombre;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error cargando categorias:', error);
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
        return codigo.includes(query) || nombre.includes(query) || cat.includes(query);
    });

    const totalPaginas = Math.ceil(filtrados.length / productosPorPaginaAlmacen) || 1;
    if (paginaActualAlmacen > totalPaginas) paginaActualAlmacen = totalPaginas;
    if (paginaActualAlmacen < 1) paginaActualAlmacen = 1;

    const inicio = (paginaActualAlmacen - 1) * productosPorPaginaAlmacen;
    const fin = inicio + productosPorPaginaAlmacen;
    const paginaProductos = filtrados.slice(inicio, fin);

    if (paginaProductos.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="7" style="text-align:center; padding: 20px; color: #666;">No se encontraron productos</td>`;
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
                <td>${p.categoria || 'Sin categoría'}</td>
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
    const data = {
        codigo_producto: document.getElementById('new-prod-codigo').value,
        nombre: document.getElementById('new-prod-nombre').value,
        id_categoria: document.getElementById('new-prod-categoria').value || null,
        descripcion: document.getElementById('new-prod-desc').value,
        precio_compra: parseFloat(document.getElementById('new-prod-pcompra').value),
        precio_venta: parseFloat(document.getElementById('new-prod-pventa').value),
        stock_actual: 0,
        stock_minimo: parseInt(document.getElementById('new-prod-minimo').value),
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
