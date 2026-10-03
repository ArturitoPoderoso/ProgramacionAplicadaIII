import sys, os, random
from database import SessionLocal, engine
from models import Categoria, Producto, InventarioSede, Sede

db = SessionLocal()

categorias_data = [
    {"nombre": "Herramientas Manuales", "desc": "Martillos, destornilladores, alicates, etc."},
    {"nombre": "Herramientas Eléctricas", "desc": "Taladros, sierras, esmeriladoras."},
    {"nombre": "Materiales de Construcción", "desc": "Cemento, arena, ladrillos."},
    {"nombre": "Pinturas y Acabados", "desc": "Pinturas, brochas, rodillos, solventes."},
    {"nombre": "Fontanería y Gas", "desc": "Tubos, conexiones, grifería."},
    {"nombre": "Electricidad e Iluminación", "desc": "Cables, focos, interruptores."},
    {"nombre": "Tornillería y Fijaciones", "desc": "Clavos, tornillos, tuercas, tacos."},
    {"nombre": "Seguridad y Protección", "desc": "Cascos, guantes, lentes, botas."},
    {"nombre": "Adhesivos y Selladores", "desc": "Pegamentos, siliconas, cintas."},
    {"nombre": "Jardinería", "desc": "Mangueras, palas, abonos."}
]

# Create Categorias
cats = {}
for cd in categorias_data:
    cat = db.query(Categoria).filter(Categoria.nombre == cd["nombre"]).first()
    if not cat:
        cat = Categoria(nombre=cd["nombre"], descripcion=cd["desc"])
        db.add(cat)
        db.commit()
        db.refresh(cat)
    cats[cd["nombre"]] = cat.id_categoria

productos_por_cat = {
    "Herramientas Manuales": ["Martillo de uña 16oz", "Destornillador Phillips", "Destornillador Plano", "Alicate Universal", "Alicate de corte", "Llave Inglesa 10 pulgadas", "Cinta Métrica 5m", "Nivel de burbuja", "Serrucho para madera", "Juego de llaves Allen"],
    "Herramientas Eléctricas": ["Taladro Percutor 700W", "Amoladora Angular 4 1/2", "Sierra Circular 1500W", "Taladro Inalámbrico 20V", "Lijadora Orbital", "Pistola de Calor", "Sierra Caladora", "Rotomartillo", "Sopladora", "Atornillador Eléctrico"],
    "Materiales de Construcción": ["Bolsa de Cemento 42.5kg", "Varilla de Fierro 1/2", "Ladrillo King Kong 18 huecos", "Arena Fina x saco", "Arena Gruesa x saco", "Piedra Chancada 1/2", "Yeso en bolsa 25kg", "Alambre cocido #16", "Pegamento para cerámicos", "Fragua gris"],
    "Pinturas y Acabados": ["Pintura Látex Blanco 1gl", "Pintura Esmalte Sintético Negro 1gl", "Brocha 2 pulgadas", "Brocha 4 pulgadas", "Rodillo de espuma 9 pulgadas", "Thinner Acrílico 1gl", "Aguarrás 1gl", "Lija al agua #180", "Lija al agua #220", "Pasta mural 1gl"],
    "Fontanería y Gas": ["Tubo PVC Agua 1/2", "Codo PVC 1/2", "Tee PVC 1/2", "Pegamento PVC 1/4gl", "Cinta Teflón", "Llave de paso 1/2", "Tubo CPVC 1/2", "Caño para lavadero", "Válvula Check", "Manguera de abasto 1/2"],
    "Electricidad e Iluminación": ["Cable THW 14 AWG x metro", "Cable THW 12 AWG x metro", "Interruptor Simple", "Tomacorriente Doble", "Foco LED 12W", "Foco LED 18W", "Cinta Aislante Negra", "Llave Termomagnética 2x16A", "Caja Octogonal", "Tubo Corrugado 20mm"],
    "Tornillería y Fijaciones": ["Clavo para madera 2 pulgadas (kg)", "Clavo para calamina", "Tornillo Drywall 1 1/4 (ciento)", "Tarugo plástico 1/4", "Tirafón 1/4 x 2", "Arandela plana 1/4", "Tuerca hexagonal 1/4", "Clavo de acero 2 pulgadas", "Remache pop 1/8", "Gancho J para calamina"],
    "Seguridad y Protección": ["Casco de seguridad Amarillo", "Guantes de cuero", "Guantes de nitrilo", "Lentes de seguridad transparentes", "Mascarilla N95", "Tapones de oído", "Chaleco reflectivo", "Botas de jebe talla 40", "Botas punta de acero talla 42", "Cinta de peligro 200m"],
    "Adhesivos y Selladores": ["Silicona Transparente tubo", "Pegamento Soldimix", "Triz", "Cinta Masking 1 pulgada", "Cinta de embalaje transparente", "Espuma de Poliuretano", "Pegamento de contacto africano", "Silicona acética blanca", "Cinta doble faz", "Adhesivo de montaje"],
    "Jardinería": ["Manguera reforzada 15m", "Pistola de riego", "Pico con mango", "Pala cuadrada", "Tijera de podar", "Tierra de chacra x saco", "Abono Urea 1kg", "Insecticida para plantas", "Maceta plástica nro 20", "Rastrillo de acero"]
}

sedes = db.query(Sede).all()

count = 0
for cat_name, prod_list in productos_por_cat.items():
    id_cat = cats[cat_name]
    for i, prod_name in enumerate(prod_list):
        codigo = f"PR-{cat_name[:3].upper()}-{i+1:03d}"
        
        prod = db.query(Producto).filter(Producto.codigo_producto == codigo).first()
        if not prod:
            prod = Producto(
                codigo_producto=codigo,
                nombre=prod_name,
                descripcion=f"{prod_name} de alta calidad.",
                id_categoria=id_cat,
                estado_registro=1
            )
            db.add(prod)
            db.commit()
            db.refresh(prod)
        
        # Generar inventario por cada sede
        for s in sedes:
            inv = db.query(InventarioSede).filter(InventarioSede.id_producto == prod.id_producto, InventarioSede.id_sede == s.id_sede).first()
            if not inv:
                # Precios coherentes: entre 5 y 100 soles
                pc = round(random.uniform(5.0, 100.0), 1)
                pv = round(pc * random.uniform(1.2, 1.5), 1) # 20% a 50% de ganancia
                
                min_stock = random.randint(10, 30)
                
                # Hacer que el ~30% de los productos estén en stock bajo o 0
                r = random.random()
                if r < 0.1:
                    stock_actual = 0
                elif r < 0.3:
                    stock_actual = min_stock - random.randint(1, 5) # Stock bajo
                else:
                    stock_actual = min_stock + random.randint(10, 50) # Stock ok
                
                inv = InventarioSede(
                    id_producto=prod.id_producto,
                    id_sede=s.id_sede,
                    precio_compra=pc,
                    precio_venta=pv,
                    stock_minimo=min_stock,
                    stock_actual=stock_actual,
                    estado_registro=1
                )
                db.add(inv)
                db.commit()
                count += 1

print(f"Insertados/Actualizados {count} registros de inventario en total.")
