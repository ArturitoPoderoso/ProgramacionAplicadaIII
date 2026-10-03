import re

with open('../frontend/almacen.js', 'r', encoding='utf-8', errors='ignore') as f:
    js = f.read()

# Fix the emoji line
js = re.sub(r"const emojiAlerta = estaBajo \? '.*?' : '';", "const emojiAlerta = estaBajo ? ' ⚠️' : '';", js)

# Fix the alerts that were corrupted
js = js.replace('Ǹxito', 'éxito')
js = js.replace('conexin', 'conexión')

with open('../frontend/almacen.js', 'w', encoding='utf-8') as f:
    f.write(js)
