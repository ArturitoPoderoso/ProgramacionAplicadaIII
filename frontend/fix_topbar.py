import os
import re

base_dir = r"c:\Users\luisa\OneDrive\Desktop\Sistema Jesmi\frontend"
file_path = os.path.join(base_dir, 'dashboard.html')

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove all inner topbars from the sections
content = re.sub(r'<header class="topbar">.*?</header>', '', content, flags=re.DOTALL)

# Now we need to re-insert exactly ONE topbar at the top of <main class="main-content" id="main-app-content">
topbar_html = """
            <header class="topbar">
                <h1 class="page-title" id="global-page-title">SISTEMA JESMI</h1>
                <div class="user-profile" onclick="document.getElementById('user-dropdown').classList.toggle('show')">
                    <div class="avatar">
                        <img src="https://ui-avatars.com/api/?name=User&background=random" alt="Avatar" id="topbar-avatar">
                    </div>
                    <div class="user-info">
                        <span class="user-name" id="display-username">Cargando...</span>
                    </div>
                    
                    <div class="user-dropdown" id="user-dropdown">
                        <div id="profile-switcher-container" style="display: none; border-bottom: 1px solid #eee; margin-bottom: 5px; padding-bottom: 5px;">
                            <!-- Botones de cambio de perfil generados dinamicamente -->
                        </div>
                        <button onclick="cerrarSesion()">
                            <i class="ph ph-sign-out"></i> Cerrar Sesion
                        </button>
                    </div>
                </div>
            </header>
"""

content = content.replace('<main class="main-content" id="main-app-content">', f'<main class="main-content" id="main-app-content">\n{topbar_html}')

# Add logic to change the page title dynamically in showSection
script_match = re.search(r'function showSection\(sectionId\) \{.*?(?=</script>)', content, re.DOTALL)
if script_match:
    old_script = script_match.group(0)
    new_script = old_script.replace("document.getElementById(sectionId).style.display = 'block';", """document.getElementById(sectionId).style.display = 'block';
            const titles = {
                'section-usuarios': 'GESTIÓN DE USUARIOS',
                'section-perfil': 'MI PERFIL',
                'section-productos': 'ALMACÉN E INVENTARIO',
                'section-ventas': 'PUNTO DE VENTA (CAJA)'
            };
            document.getElementById('global-page-title').textContent = titles[sectionId] || 'SISTEMA JESMI';
""")
    content = content.replace(old_script, new_script)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed topbar successfully")
