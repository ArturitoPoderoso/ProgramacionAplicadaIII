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
                // Save token or user data if needed, then redirect
                // Determine activeRole based on roles list
                if (data.roles && data.roles.length > 0) {
                    if (data.roles.includes('Administrador')) data.activeRole = 'Administrador';
                    else if (data.roles.includes('Supervisor')) data.activeRole = 'Supervisor';
                    else data.activeRole = 'Vendedor';
                } else {
                    data.activeRole = data.role || 'Vendedor';
                }
                
                localStorage.setItem('user', JSON.stringify(data));
                
                if (data.activeRole === 'Vendedor') {
                    window.location.href = 'perfil.html';
                } else {
                    window.location.href = 'dashboard.html';
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
