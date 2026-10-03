import re

with open('frontend/dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Fix showSection
old_func = "function showSection(sectionId) {"
new_func = """function showSection(sectionId) {
            if (sectionId === 'section-productos') {
                if (typeof cargarProductos === 'function') cargarProductos();
            }"""
html = html.replace(old_func, new_func)

# Fix script tag caching
html = html.replace('src="almacen.js"', 'src="almacen.js?v=4"')

with open('frontend/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
