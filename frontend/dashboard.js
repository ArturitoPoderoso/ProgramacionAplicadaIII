/**
 * dashboard.js
 * Maneja la interactividad del menú, modales y notificaciones del dashboard.
 */

// ------------------------------------
// Notificaciones Toast (Simulación de éxito)
// ------------------------------------
function showNotification(message, type = 'success') {
    // Si no existe el contenedor de notificaciones en el documento actual, lo creamos
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.bottom = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '10px';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.style.background = type === 'success' ? '#4CAF50' : '#E53935';
    toast.style.color = '#fff';
    toast.style.padding = '12px 24px';
    toast.style.borderRadius = '8px';
    toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    toast.style.fontFamily = "'Inter', sans-serif";
    toast.style.fontWeight = '600';
    toast.style.fontSize = '0.9rem';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(20px)';
    toast.style.transition = 'all 0.3s ease';
    toast.innerText = message;

    container.appendChild(toast);

    // Animación de entrada
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    // Remover después de 3 segundos
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// ------------------------------------
// Funcionalidad de Modales
// ------------------------------------
function openModal(modalId, contextText = '') {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        // Si es el modal de acción genérica, actualizamos el título
        if (modalId === 'modal-accion' && contextText) {
            const title = modal.querySelector('#modal-accion-title');
            if (title) title.innerText = contextText;
        }
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

// Cerrar modales haciendo clic en el fondo gris (overlay)
document.addEventListener('DOMContentLoaded', () => {
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });
});

// ------------------------------------
// Interacciones del Menú Lateral
// ------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    const btnSeguridad = document.getElementById('btn-seguridad');
    const subgroupSeguridad = document.getElementById('subgroup-seguridad');

    if (btnSeguridad && subgroupSeguridad) {
        btnSeguridad.addEventListener('click', (e) => {
            e.preventDefault(); // Evitar salto a arriba
            subgroupSeguridad.classList.toggle('collapsed');
            
            // Rotar el icono caret (opcional visual)
            const caret = btnSeguridad.querySelector('.ph-caret-down');
            if(caret) {
                if(subgroupSeguridad.classList.contains('collapsed')) {
                    caret.style.transform = 'rotate(-90deg)';
                } else {
                    caret.style.transform = 'rotate(0deg)';
                }
                caret.style.transition = 'transform 0.3s ease';
            }
        });
    }

    // Toggle de pestañas en Perfil (si existen)
    const tabPersonal = document.getElementById('tab-personal');
    const tabPassword = document.getElementById('tab-password');
    const panePersonal = document.getElementById('pane-personal');
    const panePassword = document.getElementById('pane-password');

    if (tabPersonal && tabPassword && panePersonal && panePassword) {
        tabPersonal.addEventListener('click', () => {
            tabPersonal.classList.add('active');
            tabPassword.classList.remove('active');
            panePersonal.classList.add('active');
            panePassword.classList.remove('active');
        });

        tabPassword.addEventListener('click', () => {
            tabPassword.classList.add('active');
            tabPersonal.classList.remove('active');
            panePassword.classList.add('active');
            panePersonal.classList.remove('active');
        });
    }
});

// ------------------------------------
// Lógica de Backend (API)
// ------------------------------------
var API_URL = 'http://localhost:8000/api';

async function loadUsers() {
    try {
        const currentUser = JSON.parse(localStorage.getItem('user')) || {};
        const currentRole = currentUser.activeRole || currentUser.role || 'Administrador';
        
        if (currentRole === 'Vendedor') {
            return; // Vendedores no gestionan usuarios
        }

        const currentId = currentUser.id || 1;

        const response = await fetch(`${API_URL}/users`, {
            headers: {
                'X-Role': currentRole,
                'X-User-Id': currentId
            }
        });

        if (!response.ok) {
            return;
        }

        const users = await response.json();
        
        const tbody = document.getElementById('users-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = ''; // Limpiar la tabla
        
        users.forEach(user => {
            const tr = document.createElement('tr');
            
            const isSupervisor = currentRole === 'Supervisor';
            const targetIsAdmin = user.role === 'Administrador';
            const canEdit = !(isSupervisor && targetIsAdmin);
            
            const editAction = canEdit ? `onclick="abrirModalEditar(${user.id})"` : `style="color: #ccc; cursor: not-allowed;"`;
            const toggleAction = canEdit ? `onclick="toggleEstadoUsuario(${user.id}, '${user.username}', ${user.is_active})"` : `style="color: #ccc; cursor: not-allowed;"`;
            const deleteAction = canEdit ? `onclick="abrirModalEliminar(${user.id})"` : `style="color: #ccc; cursor: not-allowed;"`;
            
            tr.innerHTML = `
                <td style="${user.is_active ? '' : 'color: #999; text-decoration: line-through;'}">${String(user.id).padStart(2, '0')}</td>
                <td style="${user.is_active ? '' : 'color: #999; text-decoration: line-through;'}">${user.username}</td>
                <td style="${user.is_active ? '' : 'color: #999; text-decoration: line-through;'}">${user.role}</td>
                <td style="${user.is_active ? '' : 'color: #999; text-decoration: line-through;'}">${user.location}</td>
                <td style="${user.is_active ? '' : 'color: #999; text-decoration: line-through;'}">${user.last_access}</td>
                <td class="actions-cell">
                    <i class="ph ph-pencil-simple icon-action" ${editAction} title="Editar Usuario"></i>
                    <i class="ph-fill ${user.is_active ? 'ph-lock-key-open' : 'ph-lock-key'} icon-action" ${toggleAction} title="${user.is_active ? 'Desactivar' : 'Activar'}"></i>
                    <i class="ph-fill ph-trash icon-action" ${deleteAction} title="Eliminar"></i>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error cargando usuarios:', error);
        showNotification('Error al cargar usuarios desde el servidor', 'error');
    }
}

function abrirModalCrear() {
    const currentUser = JSON.parse(localStorage.getItem('user')) || {};
    const currentRole = currentUser.activeRole || currentUser.role || 'Administrador';
    const currentLocation = currentUser.location || 'SJL';

    document.getElementById('edit-user-id').value = '';
    document.getElementById('modal-crear-usuario-title').innerText = 'Crear Nuevo Usuario';
    
    document.getElementById('new-user-first-name').value = '';
    document.getElementById('new-user-last-name').value = '';
    document.getElementById('new-user-name').value = '';
    document.getElementById('new-user-email').value = '';
    document.getElementById('new-user-phone').value = '';
    document.getElementById('new-user-dni').value = '';
    document.getElementById('new-user-location').value = currentLocation;
    
    // Restricciones para supervisor
    const checkboxes = document.querySelectorAll('input[name="user_roles"]');
    checkboxes.forEach(cb => { cb.checked = false; cb.disabled = false; cb.parentElement.style.display = ''; });
    
    const locationSelect = document.getElementById('new-user-location');
    
    if (currentRole === 'Supervisor') {
        checkboxes.forEach(cb => {
            if (cb.value === 'Administrador' || cb.value === 'Supervisor') {
                cb.parentElement.style.display = 'none';
                cb.disabled = true;
            }
        });
        document.querySelector('input[name="user_roles"][value="Vendedor"]').checked = true;
        locationSelect.value = currentLocation;
        locationSelect.disabled = true;
    } else {
        locationSelect.disabled = false;
    }
    
    openModal('modal-crear-usuario');
}

async function abrirModalEditar(id) {
    try {
        const currentUser = JSON.parse(localStorage.getItem('user')) || {};
        const currentRole = currentUser.activeRole || currentUser.role || 'Administrador';
        const currentLocation = currentUser.location || 'SJL';

        const response = await fetch(`${API_URL}/users`);
        const users = await response.json();
        const user = users.find(u => u.id === id);
        
        if(user) {
            document.getElementById('edit-user-id').value = user.id;
            document.getElementById('modal-crear-usuario-title').innerText = 'Editar Usuario';
            
            document.getElementById('new-user-first-name').value = user.first_name || '';
            document.getElementById('new-user-last-name').value = user.last_name || '';
            document.getElementById('new-user-name').value = user.username || '';
            document.getElementById('new-user-email').value = user.email || '';
            document.getElementById('new-user-phone').value = user.phone || '';
            document.getElementById('new-user-dni').value = user.dni || '';
            if(user.gender) document.getElementById('new-user-gender').value = user.gender;
            if(user.location) document.getElementById('new-user-location').value = user.location;
            
            const checkboxes = document.querySelectorAll('input[name="user_roles"]');
            checkboxes.forEach(cb => { cb.checked = false; cb.disabled = false; cb.parentElement.style.display = ''; });
            if (user.roles && user.roles.length > 0) {
                user.roles.forEach(r => {
                    const cb = document.querySelector(`input[name="user_roles"][value="${r}"]`);
                    if (cb) cb.checked = true;
                });
            } else if (user.role) {
                const cb = document.querySelector(`input[name="user_roles"][value="${user.role}"]`);
                if (cb) cb.checked = true;
            }
            
            const locationSelect = document.getElementById('new-user-location');
            
            if (currentRole === 'Supervisor') {
                checkboxes.forEach(cb => {
                    if (cb.value === 'Administrador' || cb.value === 'Supervisor') {
                        cb.parentElement.style.display = 'none';
                        cb.disabled = true;
                    }
                });
                locationSelect.disabled = true;
            } else {
                locationSelect.disabled = false;
            }

            openModal('modal-crear-usuario');
        }
    } catch(err) {
        showNotification('Error al cargar datos del usuario', 'error');
    }
}

async function toggleEstadoUsuario(id, username, isActive) {
    const newState = isActive ? 0 : 1;
    const currentUser = JSON.parse(localStorage.getItem('user')) || {};
    const currentRole = currentUser.activeRole || currentUser.role || 'Administrador';
    const currentId = currentUser.id || 1;

    try {
        const response = await fetch(`${API_URL}/users/${id}`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'X-Role': currentRole,
                'X-User-Id': currentId
            },
            body: JSON.stringify({ is_active: newState })
        });
        
        if (response.ok) {
            showNotification(`Usuario ${username} ${newState ? 'activado' : 'desactivado'}`, 'success');
            loadUsers();
        } else {
            showNotification('Error al cambiar estado', 'error');
        }
    } catch (error) {
        showNotification('Error de conexión', 'error');
    }
}

async function crearUsuario() {
    const first_name = document.getElementById('new-user-first-name').value;
    const last_name = document.getElementById('new-user-last-name').value;
    const username = document.getElementById('new-user-name').value;
    const email = document.getElementById('new-user-email').value;
    const phone = document.getElementById('new-user-phone').value;
    const dni = document.getElementById('new-user-dni').value.trim();
    const gender = document.getElementById('new-user-gender').value;
    const roles = Array.from(document.querySelectorAll('input[name="user_roles"]:checked')).map(cb => cb.value);
    const location = document.getElementById('new-user-location').value;

    if(!username || roles.length === 0 || !location || !first_name || !last_name || !dni) {
        showNotification('Por favor, completa al menos nombres, apellidos, usuario, DNI, rol y local', 'error');
        return;
    }

    const userId = document.getElementById('edit-user-id').value;
    const isEditing = !!userId;
    const method = isEditing ? 'PUT' : 'POST';
    const url = isEditing ? `${API_URL}/users/${userId}` : `${API_URL}/users`;

    const currentUser = JSON.parse(localStorage.getItem('user')) || {};
    const currentRole = currentUser.activeRole || currentUser.role || 'Administrador';
    const currentId = currentUser.id || 1;

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 
                'Content-Type': 'application/json',
                'X-Role': currentRole,
                'X-User-Id': currentId
            },
            body: JSON.stringify({ 
                first_name, last_name, username, email, phone, dni, gender, roles, location 
            })
        });

        if (response.ok) {
            showNotification(isEditing ? 'Usuario actualizado con éxito' : 'Usuario creado con éxito', 'success');
            closeModal('modal-crear-usuario');
            
            // Limpiar campos
            document.getElementById('new-user-first-name').value = '';
            document.getElementById('new-user-last-name').value = '';
            document.getElementById('new-user-name').value = '';
            document.getElementById('new-user-email').value = '';
            document.getElementById('new-user-phone').value = '';
            document.getElementById('new-user-dni').value = '';
            // document.getElementById('new-user-location').value = '';
            
            // Recargar tabla
            loadUsers();
        } else {
            showNotification('Error al crear usuario', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification('Error de conexión', 'error');
    }
}

function abrirModalEliminar(id) {
    document.getElementById('delete-user-id').value = id;
    openModal('modal-eliminar');
}

async function eliminarUsuarioConfirmado() {
    const id = document.getElementById('delete-user-id').value;
    
    const currentUser = JSON.parse(localStorage.getItem('user')) || {};
    const currentRole = currentUser.activeRole || currentUser.role || 'Administrador';
    const currentId = currentUser.id || 1;

    try {
        const response = await fetch(`${API_URL}/users/${id}`, {
            method: 'DELETE',
            headers: {
                'X-Role': currentRole,
                'X-User-Id': currentId
            }
        });

        if (response.ok) {
            showNotification('Usuario eliminado', 'success');
            closeModal('modal-eliminar');
            loadUsers();
        } else {
            showNotification('Error al eliminar usuario', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification('Error de conexión', 'error');
    }
}

// Cargar usuarios al iniciar la página
document.addEventListener('DOMContentLoaded', () => {
    updateTopBarUser();
    loadUsers();
});

function updateTopBarUser() {
    const currentUser = JSON.parse(localStorage.getItem('user'));
    if (currentUser && currentUser.first_name) {
        const nameElements = document.querySelectorAll('.user-name');
        const roleElements = document.querySelectorAll('.user-role');
        const avatarElements = document.querySelectorAll('.avatar img');
        
        const fullName = `${currentUser.first_name} ${currentUser.last_name}`;
        const currentRole = currentUser.activeRole || currentUser.role || 'Administrador';
        
        nameElements.forEach(el => el.textContent = fullName);
        roleElements.forEach(el => el.textContent = currentRole);
        avatarElements.forEach(el => el.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(fullName)}&background=random`);
        
        // Render Profile Switcher
        const switcherContainer = document.getElementById('profile-switcher-container');
        if (switcherContainer && currentUser.roles && currentUser.roles.length > 1) {
            switcherContainer.style.display = 'block';
            switcherContainer.innerHTML = '';
            currentUser.roles.forEach(r => {
                if (r !== currentRole) {
                    const btn = document.createElement('button');
                    btn.innerHTML = `<i class="ph ph-arrows-left-right"></i> Cambiar a ${r}`;
                    btn.style.color = '#111827';
                    btn.onclick = () => {
                        currentUser.activeRole = r;
                        localStorage.setItem('user', JSON.stringify(currentUser));
                        window.location.reload();
                    };
                    switcherContainer.appendChild(btn);
                }
            });
        }
    }
}

function cerrarSesion() {
    localStorage.removeItem('user');
    window.location.href = 'index.html';
}

// Cerrar el menú si se hace clic fuera de él
window.onclick = function(event) {
    if (!event.target.closest('.user-profile')) {
        const dropdowns = document.getElementsByClassName("user-dropdown");
        for (let i = 0; i < dropdowns.length; i++) {
            const openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}

async function guardarPerfil(btnElement) {
    const newPassword = document.getElementById('profile-new-password').value;
    const confirmPassword = document.getElementById('profile-confirm-password').value;
    
    if (!newPassword || !confirmPassword) {
        showNotification('Por favor ingrese y confirme la nueva contraseña', 'error');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showNotification('Las contraseñas no coinciden', 'error');
        return;
    }
    
    const currentUser = JSON.parse(localStorage.getItem('user'));
    if (!currentUser) {
        showNotification('No estás autenticado', 'error');
        return;
    }
    
    const originalText = btnElement.innerText;
    btnElement.innerText = 'Guardando...';
    btnElement.disabled = true;
    
    try {
        const response = await fetch(`${API_URL}/users/${currentUser.id}/password`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: newPassword })
        });
        
        if (response.ok) {
            showNotification('Contraseña actualizada exitosamente', 'success');
            document.getElementById('profile-new-password').value = '';
            document.getElementById('profile-confirm-password').value = '';
        } else {
            const data = await response.json();
            showNotification(data.error || 'Error al actualizar contraseña', 'error');
        }
    } catch (error) {
        showNotification('Error de conexión', 'error');
    }
    
    btnElement.innerText = originalText;
    btnElement.disabled = false;
}

function aplicarReglasVisibilidadNavegacion(role) {
    const elSeguridad = document.getElementById('nav-seguridad');
    const elPerfilVendedor = document.getElementById('nav-mi-perfil-vendedor');
    const elProductos = document.getElementById('nav-productos');
    const elVentas = document.getElementById('nav-ventas');
    const elHistorialVentas = document.getElementById('nav-historial-ventas');
    const elProformas = document.getElementById('nav-proformas');
    const elClientes = document.getElementById('nav-clientes');
    const elCompras = document.getElementById('nav-compras');
    const elProveedores = document.getElementById('nav-proveedores');
    const elGanancias = document.getElementById('nav-ganancias');
    const elBoletas = document.getElementById('nav-boletas');
    const elFacturas = document.getElementById('nav-facturas');
    const btnNuevoProd = document.getElementById('btn-nuevo-producto');

    if (role === 'Vendedor') {
        if (elSeguridad) elSeguridad.style.display = 'none';
        if (elPerfilVendedor) elPerfilVendedor.style.display = 'flex';
        if (elVentas) elVentas.style.display = 'flex';
        if (elProductos) elProductos.style.display = 'flex';
        if (elProformas) elProformas.style.display = 'flex';
        if (elClientes) elClientes.style.display = 'flex';
        if (elBoletas) elBoletas.style.display = 'flex';
        if (elFacturas) elFacturas.style.display = 'flex';

        if (elHistorialVentas) elHistorialVentas.style.display = 'none';
        if (elCompras) elCompras.style.display = 'none';
        if (elProveedores) elProveedores.style.display = 'none';
        if (elGanancias) elGanancias.style.display = 'none';
        if (btnNuevoProd) btnNuevoProd.style.display = 'none';

    } else if (role === 'Supervisor') {
        if (elSeguridad) elSeguridad.style.display = 'block';
        if (elPerfilVendedor) elPerfilVendedor.style.display = 'none';
        if (elProductos) elProductos.style.display = 'flex';
        if (elVentas) elVentas.style.display = 'flex';
        if (elHistorialVentas) elHistorialVentas.style.display = 'flex';
        if (elProformas) elProformas.style.display = 'none';
        if (elCompras) elCompras.style.display = 'flex';
        if (elProveedores) elProveedores.style.display = 'flex';
        if (elClientes) elClientes.style.display = 'flex';
        if (elBoletas) elBoletas.style.display = 'flex';
        if (elFacturas) elFacturas.style.display = 'flex';

        if (elGanancias) elGanancias.style.display = 'none';
        if (btnNuevoProd) btnNuevoProd.style.display = 'inline-flex';

    } else {
        // Administrador
        if (elSeguridad) elSeguridad.style.display = 'block';
        if (elPerfilVendedor) elPerfilVendedor.style.display = 'none';
        if (elProductos) elProductos.style.display = 'flex';
        if (elVentas) elVentas.style.display = 'flex';
        if (elHistorialVentas) elHistorialVentas.style.display = 'flex';
        if (elProformas) elProformas.style.display = 'none';
        if (elCompras) elCompras.style.display = 'flex';
        if (elProveedores) elProveedores.style.display = 'flex';
        if (elClientes) elClientes.style.display = 'flex';
        if (elGanancias) elGanancias.style.display = 'flex';
        if (elBoletas) elBoletas.style.display = 'flex';
        if (elFacturas) elFacturas.style.display = 'flex';

        if (btnNuevoProd) btnNuevoProd.style.display = 'inline-flex';
    }
}

// Check role on load
document.addEventListener('DOMContentLoaded', () => {
    const currentUser = JSON.parse(localStorage.getItem('user')) || {};
    const currentRole = currentUser.activeRole || currentUser.role || 'Administrador';

    // Aplicar reglas de visibilidad al menú lateral
    aplicarReglasVisibilidadNavegacion(currentRole);

    // Actualizar nombre y rol activo en el topbar
    const nameEl = document.getElementById('display-username');
    if (nameEl) {
        const fullName = `${currentUser.first_name || ''} ${currentUser.last_name || ''}`.trim() || currentUser.username || 'Usuario';
        nameEl.textContent = `${fullName} (${currentRole})`;
    }

    const avatarEl = document.getElementById('topbar-avatar');
    if (avatarEl) {
        const nameForAvatar = encodeURIComponent(currentUser.first_name || currentUser.username || 'User') + '+' + encodeURIComponent(currentUser.last_name || '');
        avatarEl.src = `https://ui-avatars.com/api/?name=${nameForAvatar}&background=random`;
    }

    // Funcionalidad de Búsqueda
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keyup', (e) => {
            const term = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#users-tbody tr');
            rows.forEach(row => {
                const idText = row.cells[0]?.textContent.toLowerCase() || '';
                const usernameText = row.cells[1]?.textContent.toLowerCase() || '';
                if (idText.includes(term) || usernameText.includes(term)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    // Si estamos en perfil.html, cargar datos del perfil
    if (document.getElementById('profile-email-lbl')) {
        loadUserProfile(currentUser.id);
    }
});

async function loadUserProfile(userId) {
    if (!userId) return;
    try {
        const response = await fetch(`${API_URL}/users/${userId}`);
        if (response.ok) {
            const user = await response.json();
            
            document.getElementById('profile-email-lbl').innerText = user.email || '---';
            document.getElementById('profile-phone-lbl').innerText = user.phone || '---';
            document.getElementById('profile-dni-lbl').innerText = user.dni || '---';
            document.getElementById('profile-role-lbl').innerText = user.role || '---';
            
            document.getElementById('profile-names-val').innerText = `${user.first_name} ${user.last_name}`;
            document.getElementById('profile-username-val').innerText = user.username || '---';
            document.getElementById('profile-dni-val').innerText = user.dni || '---';
            document.getElementById('profile-phone-val').innerText = user.phone || '---';
            document.getElementById('profile-gender-val').innerText = user.gender || '---';
            document.getElementById('profile-location-val').innerText = user.location || '---';
            
            const avatarImg = document.getElementById('profile-avatar');
            if (avatarImg) {
                avatarImg.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.first_name)}+${encodeURIComponent(user.last_name)}&background=random&size=200`;
            }
        }
    } catch (e) {
        console.error('Error loading profile', e);
    }
}
