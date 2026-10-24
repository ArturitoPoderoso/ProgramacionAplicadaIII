import sys
from database import SessionLocal
import models

def sincronizar_precios_reales():
    db = SessionLocal()
    try:
        # Obtener todas las asociaciones de proveedor_productos activas
        asociaciones = db.query(models.ProveedorProducto).filter(
            models.ProveedorProducto.estado_registro == 1
        ).all()

        total_actualizados = 0
        detalles = []

        for asoc in asociaciones:
            # Buscar el proveedor para conocer su sede si la tiene
            prov = db.query(models.Proveedor).filter(models.Proveedor.id_proveedor == asoc.id_proveedor).first()
            id_sede = prov.id_sede if prov and prov.id_sede else None

            # Buscar el precio_compra registrado en inventario_sedes para ese producto
            query_inv = db.query(models.InventarioSede).filter(
                models.InventarioSede.id_producto == asoc.id_producto,
                models.InventarioSede.estado_registro == 1
            )

            # Si el proveedor pertenece a una sede específica, priorizamos el precio de esa sede
            inv = None
            if id_sede:
                inv = query_inv.filter(models.InventarioSede.id_sede == id_sede).first()
            if not inv:
                inv = query_inv.first()

            if inv and inv.precio_compra is not None:
                precio_real = round(float(inv.precio_compra), 2)
                precio_anterior = asoc.precio_compra

                asoc.precio_compra = precio_real
                total_actualizados += 1

                prod = db.query(models.Producto).filter(models.Producto.id_producto == asoc.id_producto).first()
                nombre_prod = prod.nombre if prod else f"ID {asoc.id_producto}"
                detalles.append(f"Prov {asoc.id_proveedor} | Prod {asoc.id_producto} ({nombre_prod}): S/. {precio_anterior} -> S/. {precio_real}")

        db.commit()
        print(f"Sincronizacion completada con exito! Total registros actualizados: {total_actualizados}\n")
        print("Muestra de productos sincronizados:")
        for d in detalles[:15]:
            print(f"  * {d}")

    except Exception as e:
        db.rollback()
        print(f"Error durante la sincronizacion: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == '__main__':
    sincronizar_precios_reales()
