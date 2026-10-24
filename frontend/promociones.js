// Módulo de Gestión de Descuentos y Promociones por Temporada
// Acceso exclusivo: Administrador y Supervisor

let categoriasPromosCache = [];
let productosPromosCache = [];

document.addEventListener('DOMContentLoaded', () => {
    // Si la sección activa es promociones al cargar, cargar automáticamente
    const secPromos = document.getElementById('section-promociones');
    if (secPromos && secPromos.style.display !== 'none') {
        cargarPromociones();
    }
});

// Hook para cargar promociones al cambiar de sección
const origShowSectionPromos = window.showSection;
if (typeof origShowSectionPromos === 'function') {
    window.showSection = function(sectionId) {
        origShowSectionPromos(sectionId);
        if (sectionId === 'section-promociones') {
            cargarPromociones();
        }
    };
}

async function cargarPromociones() {
    const tbody = document.getElementById('promociones-tbody');
    if (!tbody) return;

    tbody.innerHTML = `
        <tr>
            <td colspan="7" style="text-align: center; padding: 25px; color: #94a3b8;">
                <i class="ph ph-spinner spinner" style="font-size: 1.5rem;"></i> Cargando campañas...
            </td>
        </tr>
    `;

    try {
        const response = await fetch(`${API_URL}/promociones`);
        const data = await response.json();

        if (!response.ok) throw new Error(data.error || 'Error al cargar promociones');

        if (data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 35px; color: #94a3b8; font-style: italic;">
                        No hay campañas de promoción registradas. Da clic en "+ Nueva Promoción" para crear una.
                    </td>
                </tr>
            `;
            return;
        }

        const todayStr = new Date().toISOString().split('T')[0];

        tbody.innerHTML = '';
        data.forEach(p => {
            const tr = document.createElement('tr');

            // Determinar estado de la campaña
            let badgeHtml = '';
            if (p.estado_registro === 0) {
                badgeHtml = '<span style="background: #fee2e2; color: #ef4444; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 0.75rem;">Inactiva</span>';
            } else if (todayStr >= p.fecha_inicio && todayStr <= p.fecha_fin) {
                badgeHtml = '<span style="background: #dcfce7; color: #15803d; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 0.75rem;">🔥 Activa Ahora</span>';
            } else if (todayStr < p.fecha_inicio) {
                badgeHtml = '<span style="background: #fef3c7; color: #b45309; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 0.75rem;">🗓️ Programada</span>';
            } else {
                badgeHtml = '<span style="background: #f1f5f9; color: #64748b; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 0.75rem;">Vencida</span>';
            }

            // Formato de valor
            const descTxt = p.tipo_descuento === 'PORCENTAJE' ? `${p.valor}% de Descuento` : `S/ ${p.valor.toFixed(2)} de Descuento`;

            // Aplica a text
            let aplicaTxt = 'Todos los Productos';
            if (p.aplica_a === 'CATEGORIA') {
                aplicaTxt = `Categoría: ${p.categoria_nombre || 'N/A'}`;
            } else if (p.aplica_a === 'PRODUCTO') {
                aplicaTxt = `Producto: ${p.producto_nombre || 'N/A'}`;
            }

            tr.innerHTML = `
                <td style="padding: 12px; font-weight: 700; color: #1e293b;">${p.nombre}</td>
                <td style="padding: 12px; font-weight: 800; color: #6366f1;">${descTxt}</td>
                <td style="padding: 12px; font-size: 0.82rem; color: #475569;">${aplicaTxt}</td>
                <td style="padding: 12px; font-size: 0.85rem;">${p.fecha_inicio}</td>
                <td style="padding: 12px; font-size: 0.85rem;">${p.fecha_fin}</td>
                <td style="padding: 12px;">${badgeHtml}</td>
                <td style="padding: 12px; text-align: center;">
                    <button onclick="eliminarPromocion(${p.id_promocion})" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 1.1rem;" title="Eliminar Campaña">
                        <i class="ph-bold ph-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 20px; color: #ef4444;">
                    ⚠️ Error al cargar promociones: ${err.message}
                </td>
            </tr>
        `;
    }
}

async function abrirModalPromocion() {
    document.getElementById('form-promocion').reset();
    
    // Fechas por defecto: hoy -> en 7 días
    const today = new Date();
    const nextWeek = new Date();
    nextWeek.setDate(today.getDate() + 7);

    document.getElementById('promo-fecha-inicio').value = today.toISOString().split('T')[0];
    document.getElementById('promo-fecha-fin').value = nextWeek.toISOString().split('T')[0];

    togglePromoFiltros();
    await cargarCategoriasYProductosCache();

    document.getElementById('modal-promocion').classList.add('active');
}

function togglePromoFiltros() {
    const val = document.getElementById('promo-aplica').value;
    const groupCat = document.getElementById('group-promo-categoria');
    const groupProd = document.getElementById('group-promo-producto');

    if (groupCat) groupCat.style.display = (val === 'CATEGORIA') ? 'block' : 'none';
    if (groupProd) groupProd.style.display = (val === 'PRODUCTO') ? 'block' : 'none';
}

async function cargarCategoriasYProductosCache() {
    try {
        const [resCat, resProd] = await Promise.all([
            fetch(`${API_URL}/categorias`),
            fetch(`${API_URL}/productos`)
        ]);

        if (resCat.ok) {
            categoriasPromosCache = await resCat.json();
            const selectCat = document.getElementById('promo-categoria');
            if (selectCat) {
                selectCat.innerHTML = '<option value="">-- Seleccionar Categoría --</option>';
                categoriasPromosCache.forEach(c => {
                    selectCat.innerHTML += `<option value="${c.id_categoria}">${c.nombre}</option>`;
                });
            }
        }

        if (resProd.ok) {
            productosPromosCache = await resProd.json();
            const selectProd = document.getElementById('promo-producto');
            if (selectProd) {
                selectProd.innerHTML = '<option value="">-- Seleccionar Producto --</option>';
                productosPromosCache.forEach(p => {
                    selectProd.innerHTML += `<option value="${p.id_producto}">[${p.codigo_producto}] ${p.nombre} - S/ ${p.precio_venta.toFixed(2)}</option>`;
                });
            }
        }
    } catch (err) {
        console.error('Error cargando combos para promociones:', err);
    }
}

async function guardarPromocion(e) {
    e.preventDefault();

    const u = JSON.parse(localStorage.getItem('user')) || {};
    const nombre = document.getElementById('promo-nombre').value.trim();
    const tipo = document.getElementById('promo-tipo').value;
    const valor = parseFloat(document.getElementById('promo-valor').value);
    const aplica_a = document.getElementById('promo-aplica').value;
    const fecha_inicio = document.getElementById('promo-fecha-inicio').value;
    const fecha_fin = document.getElementById('promo-fecha-fin').value;

    let id_categoria = null;
    let id_producto = null;

    if (aplica_a === 'CATEGORIA') {
        id_categoria = parseInt(document.getElementById('promo-categoria').value);
        if (!id_categoria) {
            if (typeof showNotification === 'function') showNotification('Por favor selecciona una categoría.', 'error');
            return;
        }
    } else if (aplica_a === 'PRODUCTO') {
        id_producto = parseInt(document.getElementById('promo-producto').value);
        if (!id_producto) {
            if (typeof showNotification === 'function') showNotification('Por favor selecciona un producto.', 'error');
            return;
        }
    }

    if (fecha_fin < fecha_inicio) {
        if (typeof showNotification === 'function') showNotification('La fecha fin no puede ser anterior a la fecha inicio.', 'error');
        return;
    }

    const payload = {
        nombre,
        tipo_descuento: tipo,
        valor,
        aplica_a,
        id_categoria,
        id_producto,
        fecha_inicio,
        fecha_fin,
        user_id: u.id
    };

    try {
        const response = await fetch(`${API_URL}/promociones`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const res = await response.json();

        if (response.ok) {
            if (typeof showNotification === 'function') {
                showNotification('¡Campaña de Promoción registrada exitosamente!', 'success');
            }
            closeModal('modal-promocion');
            cargarPromociones();
        } else {
            if (typeof showNotification === 'function') {
                showNotification(res.error || 'Error al guardar promoción', 'error');
            }
        }
    } catch (err) {
        if (typeof showNotification === 'function') {
            showNotification('Error de conexión con el servidor', 'error');
        }
    }
}

async function eliminarPromocion(id_promocion) {
    if (!confirm('¿Estás seguro de eliminar esta campaña de descuento?')) return;

    try {
        const response = await fetch(`${API_URL}/promociones/${id_promocion}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            if (typeof showNotification === 'function') {
                showNotification('Campaña eliminada correctamente', 'success');
            }
            cargarPromociones();
        } else {
            const data = await response.json();
            if (typeof showNotification === 'function') {
                showNotification(data.error || 'Error al eliminar', 'error');
            }
        }
    } catch (err) {
        if (typeof showNotification === 'function') {
            showNotification('Error de conexión', 'error');
        }
    }
}
