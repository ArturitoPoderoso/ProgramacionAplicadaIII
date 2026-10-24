// ==============================================================================
// CONFIGURACIÓN DINÁMICA DE LA API (Localhost vs Render / Producción)
// ==============================================================================

const RENDER_BACKEND_URL = 'https://sistema-jesmi-api.onrender.com/api';

const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api'
    : RENDER_BACKEND_URL;

window.API_BASE_URL = API_BASE_URL;
