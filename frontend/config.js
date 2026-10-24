// ==============================================================================
// CONFIGURACIÓN DINÁMICA DE LA API (Localhost vs Render / Producción)
// ==============================================================================

const RENDER_BACKEND_URL = 'https://sistema-jesmi.onrender.com/api'; // Reemplazar con la URL exacta que te dé Render

const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api'
    : RENDER_BACKEND_URL;

window.API_BASE_URL = API_BASE_URL;
