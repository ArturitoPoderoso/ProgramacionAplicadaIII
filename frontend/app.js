document.addEventListener('DOMContentLoaded', () => {
    const togglePasswordBtn = document.getElementById('toggle-password');
    const passwordInput = document.getElementById('password');
    const eyeIcon = document.getElementById('eye-icon');
    const loginForm = document.getElementById('login-form');

    // Toggle password visibility
    togglePasswordBtn.addEventListener('click', () => {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        
        // Cambiar icono
        if (type === 'text') {
            eyeIcon.classList.remove('ph-eye');
            eyeIcon.classList.add('ph-eye-slash');
        } else {
            eyeIcon.classList.remove('ph-eye-slash');
            eyeIcon.classList.add('ph-eye');
        }
    });

    const roleContainer = document.getElementById('role-select-container');
    const roleWelcome = document.getElementById('role-select-welcome');
    const roleWrapper = document.getElementById('role-buttons-wrapper');
    const btnCancelRole = document.getElementById('btn-cancel-role');

    if (btnCancelRole) {
        btnCancelRole.addEventListener('click', () => {
            if (roleContainer) roleContainer.style.display = 'none';
            if (loginForm) loginForm.style.display = 'flex';
            const btn = loginForm.querySelector('.btn-primary');
            if (btn) {
                btn.textContent = 'Iniciar Sesión';
                btn.disabled = false;
            }
        });
    }

    // Handle form submission
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const dni = document.getElementById('dni').value.trim();
        const password = passwordInput.value;
        
        const btn = loginForm.querySelector('.btn-primary');
        const originalText = btn.textContent;
        btn.textContent = 'Cargando...';
        btn.disabled = true;
        
        try {
            const baseUrl = window.API_BASE_URL || 'http://localhost:8000/api';
            const response = await fetch(`${baseUrl}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ dni, password })
            });

            const data = await response.json();

            if (response.ok) {
                const roles = data.roles || (data.role ? [data.role] : ['Vendedor']);

                const ingresarConRol = (selectedRole) => {
                    data.activeRole = selectedRole;
                    data.roles = roles;
                    localStorage.setItem('user', JSON.stringify(data));
                    window.location.href = 'dashboard.html';
                };

                // Si el usuario tiene 2 o más roles, mostramos el menú de selección
                if (roles.length > 1) {
                    loginForm.style.display = 'none';
                    roleContainer.style.display = 'flex';
                    roleWelcome.textContent = `¡Hola, ${data.first_name || data.username || 'Usuario'}!`;
                    roleWrapper.innerHTML = '';

                    const roleDetails = {
                        'Administrador': {
                            icon: 'ph-crown',
                            class: 'role-btn-admin',
                            desc: 'Gestión total, usuarios e inventario'
                        },
                        'Supervisor': {
                            icon: 'ph-shield-check',
                            class: 'role-btn-supervisor',
                            desc: 'Supervisión de almacén y reportes'
                        },
                        'Vendedor': {
                            icon: 'ph-storefront',
                            class: 'role-btn-vendedor',
                            desc: 'Punto de venta y emisión de boletas'
                        }
                    };

                    roles.forEach(r => {
                        const info = roleDetails[r] || { icon: 'ph-user', class: '', desc: 'Acceso al sistema' };
                        const b = document.createElement('button');
                        b.type = 'button';
                        b.className = `role-btn ${info.class}`;
                        b.innerHTML = `
                            <div class="role-icon-box">
                                <i class="ph-fill ${info.icon}"></i>
                            </div>
                            <div class="role-text-content">
                                <span class="role-title">Ingresar como ${r}</span>
                                <span class="role-desc">${info.desc}</span>
                            </div>
                            <i class="ph ph-caret-right role-arrow"></i>
                        `;
                        b.onclick = () => ingresarConRol(r);
                        roleWrapper.appendChild(b);
                    });

                } else {
                    // Si solo tiene 1 rol, entra directo
                    ingresarConRol(roles[0] || 'Vendedor');
                }

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

            } else {
                showNotification(data.error || 'Credenciales incorrectas', 'error');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('Error de conexión con el servidor', 'error');
            btn.textContent = originalText;
            btn.disabled = false;
        }
    });
});

