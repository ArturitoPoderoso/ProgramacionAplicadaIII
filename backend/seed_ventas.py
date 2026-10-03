import random
from datetime import datetime, timedelta
from database import SessionLocal
import models

def seed_ventas():
    db = SessionLocal()
    try:
        # Check if sales already seeded
        cant_ventas = db.query(models.Venta).count()
        if cant_ventas > 5:
            print(f"Ya existen {cant_ventas} ventas en la base de datos.")
            return

        productos = db.query(models.Producto).all()
        if not productos:
            print("No hay productos para generar ventas.")
            return

        # Users per Sede
        sedes_usuarios = {
            1: [1, 3], # Sede 1: Lenin, Denzel
            2: [2, 5]  # Sede 2: Juan David, Luis Arturo
        }

        metodos = ["Efectivo", "Tarjeta", "Yape"]
        
        # Generate 15 sample sales across the last 7 days
        for i in range(15):
            fecha = datetime.now() - timedelta(days=random.randint(0, 6), hours=random.randint(1, 10), minutes=random.randint(0, 59))
            sede_id = random.choice([1, 2])
            user_id = random.choice(sedes_usuarios[sede_id])
            metodo = random.choice(metodos)
            correlativo = f"V-{fecha.strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"

            # Pick 1-4 random products
            prod_sample = random.sample(productos, min(len(productos), random.randint(1, 4)))
            
            detalles_data = []
            total_venta = 0.0

            for p in prod_sample:
                # get price
                inv = db.query(models.InventarioSede).filter(
                    models.InventarioSede.id_producto == p.id_producto,
                    models.InventarioSede.id_sede == sede_id
                ).first()
                p_venta = inv.precio_venta if (inv and inv.precio_venta > 0) else 25.0
                cant = random.randint(1, 5)
                subt = cant * p_venta
                total_venta += subt
                detalles_data.append({
                    "id_producto": p.id_producto,
                    "cantidad": cant,
                    "precio_unitario": p_venta,
                    "subtotal": subt
                })

            nueva_venta = models.Venta(
                correlativo=correlativo,
                fecha_venta=fecha,
                total=round(total_venta, 2),
                metodo_pago=metodo,
                id_usuario=user_id,
                id_sede=sede_id,
                estado_registro=1
            )
            db.add(nueva_venta)
            db.flush()

            for d in detalles_data:
                det = models.DetalleVenta(
                    id_venta=nueva_venta.id_venta,
                    id_producto=d["id_producto"],
                    cantidad=d["cantidad"],
                    precio_unitario=d["precio_unitario"],
                    subtotal=round(d["subtotal"], 2)
                )
                db.add(det)

        db.commit()
        print("15 ventas de prueba sembradas exitosamente entre Sede 1 y Sede 2.")

    except Exception as e:
        db.rollback()
        print(f"Error sembrando ventas: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_ventas()
