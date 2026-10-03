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
            const response = await fetch('http://localhost:8000/api/login', {
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

            } else {
                alert(data.error || 'Credenciales incorrectas');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error de conexión con el servidor');
            btn.textContent = originalText;
            btn.disabled = false;
        }
    });
});
