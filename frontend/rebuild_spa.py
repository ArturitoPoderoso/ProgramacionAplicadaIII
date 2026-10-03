import os, re
base_dir = r'c:\Users\luisa\OneDrive\Desktop\Sistema Jesmi\frontend'

def read_file(name, enc='utf-8'):
    try:
        with open(os.path.join(base_dir, name), 'r', encoding=enc) as f:
            return f.read()
    except Exception as e:
        print(f"Fallback to utf-16 for {name}")
        with open(os.path.join(base_dir, name), 'r', encoding='utf-16') as f:
            return f.read()

# First we must recover the original dashboard.html before PowerShell corrupted it
os.system(f'cd "{base_dir}" && git checkout dashboard.html')

dashboard_html = read_file('dashboard.html')
perfil_html = read_file('perfil.html')
almacen_html = read_file('almacen.html')
caja_html = read_file('caja.html')

def extract_main_content(html_content):
    match = re.search(r'<main class="main-content">(.*?)</main>', html_content, re.DOTALL)
    if match:
        return match.group(1)
    return ''

dashboard_main = extract_main_content(dashboard_html)
perfil_main = extract_main_content(perfil_html)
almacen_main = extract_main_content(almacen_html)
caja_main = extract_main_content(caja_html)

dashboard_section = f'<div id="section-usuarios" class="app-section" style="display:block;">{dashboard_main}</div>'
perfil_section = f'<div id="section-perfil" class="app-section" style="display:none;">{perfil_main}</div>'
almacen_section = f'<div id="section-productos" class="app-section" style="display:none;">{almacen_main}</div>'
caja_section = f'<div id="section-ventas" class="app-section" style="display:none;">{caja_main}</div>'

all_sections = dashboard_section + '\n' + perfil_section + '\n' + almacen_section + '\n' + caja_section

new_dashboard = re.sub(r'<main class="main-content">.*?</main>', f'<main class="main-content" id="main-app-content">\n{all_sections}\n</main>', dashboard_html, flags=re.DOTALL)

scripts = """
    <script src="dashboard.js?v=9"></script>
    <script src="almacen.js"></script>
    <script src="caja.js"></script>
    <script>
        function showSection(sectionId) {
            document.querySelectorAll('.app-section').forEach(el => el.style.display = 'none');
            document.getElementById(sectionId).style.display = 'block';
            
            const titles = {
                'section-usuarios': 'GESTIÓN DE USUARIOS',
                'section-perfil': 'MI PERFIL',
                'section-productos': 'ALMACÉN E INVENTARIO',
                'section-ventas': 'PUNTO DE VENTA (CAJA)'
            };
            const titleEl = document.getElementById('global-page-title');
            if (titleEl) {
                titleEl.textContent = titles[sectionId] || 'SISTEMA JESMI';
            }

            document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => el.classList.remove('active'));
            const clicked = Array.from(document.querySelectorAll('.sidebar-nav .nav-item')).find(el => el.getAttribute('onclick') === `showSection('${sectionId}')`);
            if (clicked) clicked.classList.add('active');
            
            const u = JSON.parse(localStorage.getItem('user')) || {};
            const role = u.activeRole || u.role;
            if (role === 'Vendedor' && sectionId === 'section-usuarios') {
                showSection('section-perfil');
            }
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            const u = JSON.parse(localStorage.getItem('user')) || {};
            const role = u.activeRole || u.role;
            if (role === 'Vendedor') {
                showSection('section-perfil');
            } else {
                showSection('section-usuarios');
            }
        });
    </script>
"""

new_dashboard = re.sub(r'<script src="dashboard.js.*?></script>', scripts, new_dashboard)

new_dashboard = new_dashboard.replace('href="dashboard.html"', 'href="#" onclick="showSection(\'section-usuarios\')"')
new_dashboard = new_dashboard.replace('href="perfil.html"', 'href="#" onclick="showSection(\'section-perfil\')"')
new_dashboard = new_dashboard.replace('href="almacen.html"', 'href="#" onclick="showSection(\'section-productos\')"')
new_dashboard = new_dashboard.replace('href="caja.html"', 'href="#" onclick="showSection(\'section-ventas\')"')
new_dashboard = new_dashboard.replace('href="almacen.html?v=2"', 'href="#" onclick="showSection(\'section-productos\')"')
new_dashboard = new_dashboard.replace('href="caja.html?v=2"', 'href="#" onclick="showSection(\'section-ventas\')"')

almacen_modals = re.search(r'<!-- Modal Crear Producto -->.*?</div>\s*</div>', almacen_html, re.DOTALL)
if almacen_modals:
    new_dashboard = new_dashboard.replace('<!-- Modals -->', '<!-- Modals -->\n' + almacen_modals.group(0))

# Remove the Stock Inicial input dynamically before saving
stock_regex = r'<div class="form-group">\s*<label>Stock Inicial</label>\s*<input type="number" id="new-prod-stock" value="0">\s*</div>'
new_dashboard = re.sub(stock_regex, '', new_dashboard)

# Fix nav item links for Productos and Ventas
new_dashboard = re.sub(
    r'<a href="#" class="nav-item">\s*<i class="ph-fill ph-cube"></i>\s*<span>Productos</span>\s*</a>',
    r'<a href="#" onclick="showSection(\'section-productos\')" class="nav-item">\n                    <i class="ph-fill ph-cube"></i>\n                    <span>Productos</span>\n                </a>'.replace("\\'", "'"),
    new_dashboard
)

new_dashboard = re.sub(
    r'<a href="#" class="nav-item">\s*<i class="ph-fill ph-chart-line-up"></i>\s*<span>Ventas</span>\s*<i class="ph ph-caret-right ml-auto"></i>\s*</a>',
    r'<a href="#" onclick="showSection(\'section-ventas\')" class="nav-item">\n                    <i class="ph-fill ph-chart-line-up"></i>\n                    <span>Ventas</span>\n                    <i class="ph ph-caret-right ml-auto"></i>\n                </a>'.replace("\\'", "'"),
    new_dashboard
)

with open(os.path.join(base_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
    f.write(new_dashboard)
print('SPA generated successfully')
