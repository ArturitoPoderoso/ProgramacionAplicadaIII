from database import engine, SessionLocal
import models
from sqlalchemy import text

def run_migration():
    print("Iniciando migración de tabla subcategorias...")
    
    # 1. Crear las tablas si no existen
    models.Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        # 2. Agregar columna id_subcategoria a la tabla productos si no existe
        conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS id_subcategoria INTEGER REFERENCES subcategorias(id_subcategoria);"))
        conn.commit()
        print("Columna 'id_subcategoria' verificada/creada en la tabla productos.")

    db = SessionLocal()
    try:
        # 3. Traspasar subcategorías que estaban guardadas en 'categorias' con id_padre
        old_subcats = db.query(models.Categoria).filter(models.Categoria.id_padre != None).all()
        migrated_count = 0

        for old_c in old_subcats:
            # Verificar si ya existe en la nueva tabla subcategorias
            existing = db.query(models.Subcategoria).filter(
                models.Subcategoria.nombre == old_c.nombre,
                models.Subcategoria.id_categoria == old_c.id_padre
            ).first()

            if not existing:
                new_sub = models.Subcategoria(
                    nombre=old_c.nombre,
                    descripcion=old_c.descripcion or f"Subcategoría de categoría {old_c.id_padre}",
                    id_categoria=old_c.id_padre,
                    estado_registro=1
                )
                db.add(new_sub)
                db.flush() # obtener id_subcategoria
                migrated_count += 1
                sub_id = new_sub.id_subcategoria
            else:
                sub_id = existing.id_subcategoria

            # Actualizar los productos que apuntaban al antiguo id_categoria de esa subcategoría
            prods = db.query(models.Producto).filter(models.Producto.id_categoria == old_c.id_categoria).all()
            for p in prods:
                p.id_categoria = old_c.id_padre
                p.id_subcategoria = sub_id

        db.commit()
        print(f"Migración completada. Se crearon {migrated_count} subcategorías en la nueva tabla.")

    except Exception as e:
        db.rollback()
        print(f"Error durante la migración: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
