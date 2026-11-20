// Enrutador para cargar las vistas y modales del dashboard segun el menu seleccionado

const ViewRouter = {
    // Cache de vistas ya visitadas para abrirlas mas rapido
    cache: {},
    currentSection: null,
    modalsLoaded: false,

    // Lista de rutas con su archivo HTML, titulo e inicializador
    routes: {
        'section-usuarios': {
            file: 'views/usuarios.html',
            title: 'GESTIÓN DE USUARIOS',
            init: () => {
                if (typeof loadUsers === 'function') {
                    loadUsers();
                } else if (typeof cargarUsuarios === 'function') {
                    cargarUsuarios();
                }
                const searchInput = document.getElementById('search-input');
                if (searchInput) {
                    searchInput.onkeyup = (e) => {
                        const term = e.target.value.toLowerCase();
                        document.querySelectorAll('#users-tbody tr').forEach(row => {
                            const text = row.textContent.toLowerCase();
                            row.style.display = text.includes(term) ? '' : 'none';
                        });
                    };
                }
            }
        },
        'section-perfil': {
            file: 'views/perfil.html',
            title: 'MI PERFIL',
            init: () => {
                const u = JSON.parse(localStorage.getItem('user')) || {};
                if (typeof loadUserProfile === 'function') {
                    loadUserProfile(u.id);
                } else if (typeof cargarDatosPerfil === 'function') {
                    cargarDatosPerfil();
                }

                // Enlazar tabs de perfil dinámicamente
                const tabPersonal = document.getElementById('tab-personal');
                const tabPassword = document.getElementById('tab-password');
                const panePersonal = document.getElementById('pane-personal');
                const panePassword = document.getElementById('pane-password');
                if (tabPersonal && tabPassword && panePersonal && panePassword) {
                    tabPersonal.onclick = () => {
                        tabPersonal.classList.add('active');
                        tabPassword.classList.remove('active');
                        panePersonal.classList.add('active');
                        panePassword.classList.remove('active');
                    };
                    tabPassword.onclick = () => {
                        tabPassword.classList.add('active');
                        tabPersonal.classList.remove('active');
                        panePassword.classList.add('active');
                        panePersonal.classList.remove('active');
                    };
                }
            }
        },
        'section-productos': {
            file: 'views/almacen.html',
            title: 'ALMACÉN E INVENTARIO',
            init: () => {
                if (typeof cargarCategorias === 'function') cargarCategorias();
                if (typeof cargarProductosAlmacen === 'function') {
                    cargarProductosAlmacen();
                } else if (typeof cargarProductos === 'function') {
                    cargarProductos();
                }
            }
        },
        'section-ventas': {
            file: 'views/caja.html',
            title: 'PUNTO DE VENTA (CAJA)',
            init: () => {
                if (typeof cargarProductosCaja === 'function') {
                    cargarProductosCaja();
                } else if (typeof cargarProductosPos === 'function') {
                    cargarProductosPos();
                }
            }
        },
        'section-historial-ventas': {
            file: 'views/historial_ventas.html',
            title: 'HISTORIAL DE VENTAS',
            init: () => {
                if (typeof cargarSedesFiltroHistorial === 'function') cargarSedesFiltroHistorial();
                if (typeof cargarHistorialVentas === 'function') cargarHistorialVentas();
            }
        },
        'section-promociones': {
            file: 'views/promociones.html',
            title: 'DESCUENTOS Y PROMOCIONES',
            init: () => {
                if (typeof cargarPromociones === 'function') cargarPromociones();
            }
        },
        'section-proformas': {
            file: 'views/proformas.html',
            title: 'EMISIÓN DE PROFORMAS / COTIZACIONES',
            init: () => {
                if (typeof cargarModuloProformas === 'function') cargarModuloProformas();
            }
        },
        'section-proveedores': {
            file: 'views/proveedores.html',
            title: 'GESTIÓN DE PROVEEDORES',
            init: () => {
                if (typeof cargarProveedores === 'function') cargarProveedores();
            }
        },
        'section-clientes': {
            file: 'views/clientes.html',
            title: 'GESTIÓN DE CLIENTES',
            init: () => {
                if (typeof cargarClientes === 'function') cargarClientes();
            }
        },
        'section-emitir-orden': {
            file: 'views/compras_emitir.html',
            title: 'EMITIR ORDEN',
            init: () => {
                if (typeof inicializarEmitirOrden === 'function') inicializarEmitirOrden();
            }
        },
        'section-historial-compras': {
            file: 'views/compras_historial.html',
            title: 'HISTORIAL COMPRAS',
            init: () => {
                if (typeof cargarHistorialCompras === 'function') cargarHistorialCompras();
            }
        }
    },

    // Carga los archivos HTML de modales en el contenedor principal
    async loadModals() {
        if (this.modalsLoaded) return;
        const container = document.getElementById('modals-container');
        if (!container) return;

        const modalFiles = [
            'modals/modals_productos.html',
            'modals/modals_usuarios.html',
            'modals/modals_ventas.html',
            'modals/modals_promociones.html',
            'modals/modals_proveedores.html',
            'modals/modals_clientes.html',
            'modals/modals_compras.html'
        ];

        try {
            const promises = modalFiles.map(async (file) => {
                const res = await fetch(file);
                if (!res.ok) throw new Error(`Error ${res.status} al cargar ${file}`);
                return res.text();
            });
            const contents = await Promise.all(promises);
            container.innerHTML = contents.join('\n');
            this.modalsLoaded = true;

            // Cerramos modal al hacer clic en el fondo oscuro
            document.querySelectorAll('.modal-overlay').forEach(overlay => {
                overlay.addEventListener('click', (e) => {
                    if (e.target === overlay) overlay.classList.remove('active');
                });
            });
        } catch (err) {
            console.error("Error al cargar modales modulares:", err);
        }
    },

    // Cambia de seccion, carga el HTML de la vista y ejecuta su inicializador
    async navigate(sectionId) {
        const u = JSON.parse(localStorage.getItem('user')) || {};
        const role = u.activeRole || u.role || 'Vendedor';

        // Redireccionamos si el rol no tiene permiso para ver esa seccion
        if (role === 'Vendedor' && (sectionId === 'section-usuarios' || sectionId === 'section-historial-ventas' || sectionId === 'section-emitir-orden' || sectionId === 'section-historial-compras' || sectionId === 'section-proveedores')) {
            sectionId = 'section-ventas';
        }
        if (role !== 'Vendedor' && sectionId === 'section-proformas') {
            sectionId = (role === 'Supervisor') ? 'section-productos' : 'section-usuarios';
        }

        const route = this.routes[sectionId];
        if (!route) {
            console.warn(`Ruta no configurada: ${sectionId}`);
            return;
        }

        const viewport = document.getElementById('router-viewport');
        if (!viewport) return;

        // Actualizamos el titulo del encabezado
        const titleEl = document.getElementById('global-page-title');
        if (titleEl) titleEl.textContent = route.title;

        // Marcamos la opcion activa en la barra lateral
        this.updateSidebarActive(sectionId);

        // Si ya esta en cache la reutilizamos
        if (!this.cache[sectionId]) {
            try {
                const res = await fetch(route.file);
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                this.cache[sectionId] = await res.text();
            } catch (err) {
                console.error(`Error al cargar vista ${route.file}:`, err);
                viewport.innerHTML = `<div style="padding: 40px; text-align: center; color: #ef4444;">
                    <h3>Error al cargar el módulo</h3>
                    <p>No se pudo cargar la vista <code>${route.file}</code>. Asegúrate de ejecutar la app mediante un servidor local (HTTP).</p>
                </div>`;
                return;
            }
        }

        // Insertamos el HTML de la vista
        viewport.innerHTML = this.cache[sectionId];

        const sectionEl = viewport.querySelector('.app-section');
        if (sectionEl) sectionEl.style.display = 'block';

        this.currentSection = sectionId;

        // Ejecutamos la funcion que inicializa la logica de esa pantalla
        try {
            if (typeof route.init === 'function') {
                route.init();
            }
        } catch (err) {
            console.error(`Error al inicializar lógica de ${sectionId}:`, err);
        }
    },

    // Marca activo el boton de la barra lateral segun la seccion abierta
    updateSidebarActive(sectionId) {
        document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.sidebar-nav .nav-subitem').forEach(el => el.classList.remove('active'));

        const clicked = Array.from(document.querySelectorAll('.sidebar-nav .nav-item')).find(
            el => el.getAttribute('onclick') === `showSection('${sectionId}')`
        );
        if (clicked) clicked.classList.add('active');

        const clickedSub = Array.from(document.querySelectorAll('.sidebar-nav .nav-subitem')).find(
            el => el.getAttribute('onclick') === `showSection('${sectionId}')`
        );
        if (clickedSub) {
            clickedSub.classList.add('active');
            const parentGroup = clickedSub.closest('.nav-subgroup');
            if (parentGroup && parentGroup.classList.contains('collapsed')) {
                parentGroup.classList.remove('collapsed');
                const parentToggle = parentGroup.previousElementSibling;
                const caret = parentToggle?.querySelector('.ph-caret-down');
                if (caret) caret.style.transform = 'rotate(0deg)';
            }
        }
    }
};

// Funcion global que ejecutan los botones del menu lateral
function showSection(sectionId) {
    ViewRouter.navigate(sectionId);
}

// Inicializamos la navegacion al cargar el documento
document.addEventListener('DOMContentLoaded', () => {
    // Cargamos los modales en segundo plano
    ViewRouter.loadModals();

    // Determinamos la seccion inicial segun el rol del usuario
    const role = typeof getUsuarioRolActual === 'function' 
        ? getUsuarioRolActual() 
        : ((JSON.parse(localStorage.getItem('user')) || {}).role || 'Vendedor');

    if (typeof aplicarReglasVisibilidadNavegacion === 'function') {
        aplicarReglasVisibilidadNavegacion(role);
    }

    if (role === 'Vendedor') {
        showSection('section-ventas');
    } else if (role === 'Supervisor') {
        showSection('section-productos');
    } else {
        showSection('section-usuarios');
    }
});

