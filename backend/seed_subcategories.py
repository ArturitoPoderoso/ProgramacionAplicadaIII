import sys
import os
from database import SessionLocal
import models

def seed():
    print("Iniciando seed de subcategorías...")
    db = SessionLocal()
    try:
        subcats_map = {
            1: ["Martillos y Combas", "Alicates y Tenazas", "Destornilladores y Llaves"],
            2: ["Taladros y Rotomartillos", "Amoladoras y Esmeriles", "Sierras y Cortadoras"],
            3: ["Cemento y Agregados", "Ladrillos y Bloques", "Fierros y Varillas"],
            4: ["Pinturas Látex", "Esmaltes Sintéticos", "Brochas y Rodillos", "Thinner y Disolventes"],
            5: ["Tubos y Conexiones PVC", "Grifería y Llaves", "Accesorios para Gas"],
            6: ["Cables y Conductores", "Tomacorrientes e Llaves Térmicas", "Focos y Luminarias LED"],
            7: ["Tornillos y Pijas", "Pernos y Tuercas", "Tarugos y Anclajes"],
            8: ["Cascos y Guantes", "Calzado y Lentes de Seguridad"],
            9: ["Siliconas y Masillas", "Pegamentos y Colas"],
            10: ["Mangueras y Aspersores", "Herramientas de Jardín"]
        }

        created_count = 0
        for parent_id, sub_names in subcats_map.items():
            parent = db.query(models.Categoria).filter(models.Categoria.id_categoria == parent_id).first()
            if not parent:
                continue
            for name in sub_names:
                existing = db.query(models.Categoria).filter(
                    models.Categoria.nombre == name,
                    models.Categoria.id_padre == parent_id
                ).first()
                if not existing:
                    new_sub = models.Categoria(
                        nombre=name,
                        descripcion=f"Subcategoría de {parent.nombre}",
                        id_padre=parent_id,
                        estado_registro=1
                    )
                    db.add(new_sub)
                    created_count += 1
        
        db.commit()
        print(f"Se crearon {created_count} subcategorías predeterminadas con éxito.")

        productos = db.query(models.Producto).all()
        reassigned = 0
        for prod in productos:
            if prod.id_categoria and prod.id_categoria in subcats_map:
                first_sub = db.query(models.Categoria).filter(
                    models.Categoria.id_padre == prod.id_categoria
                ).first()
                if first_sub:
                    prod.id_categoria = first_sub.id_categoria
                    reassigned += 1
        
        db.commit()
        print(f"Se reasignaron {reassigned} productos a su subcategoría predeterminada.")

    except Exception as e:
        db.rollback()
        print(f"Error al poblar subcategorías: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
