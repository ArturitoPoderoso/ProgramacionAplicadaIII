import sys
from database import SessionLocal
import models

def vincular_proveedores_productos():
    db = SessionLocal()
    try:
        # Diccionario de precios de compra de referencia basados en inventario o estándar
        precios_ref = {}
        for inv in db.query(models.InventarioSede).all():
            if inv.id_producto not in precios_ref:
                precios_ref[inv.id_producto] = round(inv.precio_compra, 2)

        # Mapeo de proveedores a sus productos correspondientes
        # Aseguramos un catálogo amplio (entre 5 y 10 productos por proveedor)
        catalogo = {
            # 1 & 2: ACEROS AREQUIPA (Fierros, alambres, clavos)
            1: [
                (12, 42.50, "AA-VAR-12"),   # Varilla Fierro 1/2
                (18, 15.50, "AA-ALAM-16"),  # Alambre cocido #16
                (51, 6.50,  "AA-CLAV-MAD"), # Clavo para madera 2"
                (52, 7.80,  "AA-CLAV-CAL"), # Clavo para calamina
                (58, 8.20,  "AA-CLAV-ACE"), # Clavo de acero 2"
                (60, 1.20,  "AA-GAN-J"),    # Gancho J calamina
            ],
            2: [
                (12, 41.80, "CORP-VAR-12"),
                (18, 14.90, "CORP-ALAM-16"),
                (51, 6.20,  "CORP-CLAV-MAD"),
                (52, 7.50,  "CORP-CLAV-CAL"),
                (58, 8.00,  "CORP-CLAV-ACE"),
                (60, 1.10,  "CORP-GAN-J"),
                (57, 0.40,  "CORP-TUERCA-14"),
            ],
            # 3: SIDERPERU (Fierros, mallas, alambres, pernos)
            3: [
                (12, 41.50, "SID-VAR-12"),
                (18, 14.80, "SID-ALAM-16"),
                (19, 18.50, "SID-PEG-CER"),
                (51, 6.30,  "SID-CLAV-MAD"),
                (52, 7.60,  "SID-CLAV-CAL"),
                (58, 8.10,  "SID-CLAV-ACE"),
                (56, 0.25,  "SID-ARAN-14"),
                (57, 0.45,  "SID-TUERCA-14"),
            ],
            # 4: PAVCO TUBERIAS & SANITARIOS (Fontanería, PVC, válvulas)
            4: [
                (31, 14.50, "PAV-TUB-12"),   # Tubo PVC Agua 1/2
                (32, 2.20,  "PAV-COD-12"),   # Codo PVC 1/2
                (33, 2.80,  "PAV-TEE-12"),   # Tee PVC 1/2
                (34, 18.50, "PAV-PEG-14"),   # Pegamento PVC 1/4gl
                (35, 1.50,  "PAV-TEF-01"),   # Cinta Teflón
                (36, 12.00, "PAV-PASO-12"),  # Llave de paso 1/2
                (37, 18.00, "PAV-CPVC-12"),  # Tubo CPVC 1/2
                (38, 24.50, "PAV-CANO-LAV"), # Caño lavadero
                (39, 22.00, "PAV-VALV-CHK"), # Válvula check
                (40, 9.50,  "PAV-MANG-ABS"), # Manguera abasto
                (26, 32.00, "PAV-THIN-ACR"), # Thinner Acrílico
                (30, 28.00, "PAV-PAS-MUR"),  # Pasta mural
            ],
            # 9: DISTRIBUIDORA FERRETERA DEL NORTE (Herramientas, pegamentos, tornillería)
            9: [
                (1,  18.50, "DFN-MART-16"),  # Martillo de uña 16oz
                (2,  6.50,  "DFN-DEST-PH"),  # Destornillador Phillips
                (3,  6.50,  "DFN-DEST-PL"),  # Destornillador Plano
                (4,  16.00, "DFN-ALIC-UNI"), # Alicate Universal
                (6,  26.00, "DFN-LLAV-ING"), # Llave Inglesa 10"
                (7,  9.00,  "DFN-WIN-5M"),   # Cinta Métrica 5m
                (8,  14.00, "DFN-NIV-BUR"),  # Nivel de burbuja
                (18, 15.00, "DFN-ALAM-16"),  # Alambre cocido
                (53, 11.50, "DFN-TORN-DRY"), # Tornillo Drywall
                (71, 10.50, "DFN-SIL-TRP"),  # Silicona transparente
                (72, 8.50,  "DFN-SOLDIMIX"), # Soldimix
                (73, 4.00,  "DFN-TRIZ"),     # Triz
            ],
            # 10: PINTURAS Y RECUBRIMIENTOS OLIVOS (Pinturas, brochas, rodillos, lijas)
            10: [
                (21, 38.00, "PIN-LAT-BLA"),  # Pintura Látex Blanco 1gl
                (22, 44.00, "PIN-ESM-NEG"),  # Pintura Esmalte Negro 1gl
                (23, 4.50,  "PIN-BRO-2"),    # Brocha 2"
                (24, 8.50,  "PIN-BRO-4"),    # Brocha 4"
                (25, 12.00, "PIN-ROD-ESP"),  # Rodillo de espuma 9"
                (26, 26.50, "PIN-THI-ACR"),  # Thinner Acrílico
                (27, 19.50, "PIN-AGU-1GL"),  # Aguarrás 1gl
                (28, 1.20,  "PIN-LIJ-180"),  # Lija al agua #180
                (29, 1.20,  "PIN-LIJ-220"),  # Lija al agua #220
                (30, 24.00, "PIN-PAS-MUR"),  # Pasta mural
                (74, 5.00,  "PIN-MASK-1P"),  # Cinta masking
            ],
            # 11: TUBOPLAST & VALVULAS NORTE (Tuberías, conexiones, grifería)
            11: [
                (31, 13.80, "TUB-AGU-12"),
                (32, 1.90,  "TUB-COD-12"),
                (33, 2.50,  "TUB-TEE-12"),
                (34, 17.00, "TUB-PEG-14"),
                (35, 1.30,  "TUB-TEF-01"),
                (36, 11.00, "TUB-PAS-12"),
                (37, 17.00, "TUB-CPVC-12"),
                (38, 22.00, "TUB-CAN-LAV"),
                (39, 20.50, "TUB-VAL-CHK"),
                (40, 8.80,  "TUB-MAN-ABS"),
            ],
            # 12: HERRAMIENTAS Y PERNOS OLIVOS (Herramientas manuales, pernos, fijaciones)
            12: [
                (1,  17.50, "HPO-MART-16"),
                (2,  6.00,  "HPO-DEST-PH"),
                (3,  6.00,  "HPO-DEST-PL"),
                (4,  15.50, "HPO-ALIC-UNI"),
                (5,  14.00, "HPO-ALIC-COR"),
                (9,  22.00, "HPO-SERR-MAD"),
                (10, 16.50, "HPO-LLAV-ALL"),
                (53, 10.80, "HPO-TORN-DRY"),
                (54, 4.50,  "HPO-TAR-14"),
                (55, 7.50,  "HPO-TIR-14X2"),
                (56, 0.20,  "HPO-ARA-14"),
                (57, 0.35,  "HPO-TUE-14"),
                (59, 6.00,  "HPO-REM-POP"),
            ],
            # 13: CEMENTOS Y AGREGADOS SAN JUAN (Cemento, ladrillos, agregados)
            13: [
                (11, 26.50, "CSJ-CEM-SOL"),  # Cemento 42.5kg
                (13, 0.95,  "CSJ-LAD-KK"),   # Ladrillo King Kong
                (14, 38.00, "CSJ-ARE-FIN"),  # Arena fina
                (15, 34.00, "CSJ-ARE-GRU"),  # Arena gruesa
                (16, 42.00, "CSJ-PIE-CHA"),  # Piedra chancada
                (17, 14.50, "CSJ-YESO-25"),  # Yeso 25kg
                (19, 17.50, "CSJ-PEG-CER"),  # Pegamento cerámicos
                (20, 7.50,  "CSJ-FRAG-GR"),  # Fragua gris
                (91, 25.50, "CSJ-CEM-GEN"),  # Cemento
                (95, 2.20,  "CSJ-LAD-TEC"),  # Ladrillo techo
                (97, 27.00, "CSJ-CEM-AND"),  # Cemento Andino
            ],
            # 14: DISTRIBUCIONES ELECTRICAS & CABLES SJL (Electricidad e iluminación)
            14: [
                (41, 1.80,  "DEC-THW-14"),   # Cable THW 14 AWG x metro
                (42, 2.60,  "DEC-THW-12"),   # Cable THW 12 AWG x metro
                (43, 5.50,  "DEC-INT-SIM"),  # Interruptor Simple
                (44, 7.80,  "DEC-TOM-DOB"),  # Tomacorriente Doble
                (45, 6.50,  "DEC-FOC-12W"),  # Foco LED 12W
                (46, 9.80,  "DEC-FOC-18W"),  # Foco LED 18W
                (47, 3.20,  "DEC-CIN-AIS"),  # Cinta Aislante
                (48, 28.50, "DEC-LLAV-TM"),  # Llave termomagnética
                (49, 2.50,  "DEC-CAJ-OCT"),  # Caja octogonal
                (50, 1.20,  "DEC-TUB-COR"),  # Tubo corrugado
            ],
            # 15: MATERIALES Y FIERROS EL CHINO (Materiales pesados y fierros)
            15: [
                (11, 26.80, "MFC-CEM-42"),
                (12, 42.00, "MFC-VAR-12"),
                (13, 0.98,  "MFC-LAD-KK"),
                (14, 39.00, "MFC-ARE-FIN"),
                (15, 35.00, "MFC-ARE-GRU"),
                (18, 15.20, "MFC-ALAM-16"),
                (51, 6.40,  "MFC-CLAV-MAD"),
                (83, 34.00, "MFC-PICO-MAN"), # Pico con mango
                (84, 28.00, "MFC-PALA-CUA"), # Pala cuadrada
            ]
        }

        total_creados = 0
        total_actualizados = 0

        for id_prov, lista_prods in catalogo.items():
            # Verificar si existe el proveedor
            prov = db.query(models.Proveedor).filter(models.Proveedor.id_proveedor == id_prov).first()
            if not prov:
                continue

            for (id_prod, precio, cod_prov) in lista_prods:
                # Verificar si el producto existe
                prod = db.query(models.Producto).filter(models.Producto.id_producto == id_prod).first()
                if not prod:
                    continue

                existente = db.query(models.ProveedorProducto).filter(
                    models.ProveedorProducto.id_proveedor == id_prov,
                    models.ProveedorProducto.id_producto == id_prod
                ).first()

                if existente:
                    existente.precio_compra = precio
                    existente.codigo_proveedor = cod_prov
                    existente.estado_registro = 1
                    total_actualizados += 1
                else:
                    nuevo = models.ProveedorProducto(
                        id_proveedor=id_prov,
                        id_producto=id_prod,
                        precio_compra=precio,
                        codigo_proveedor=cod_prov,
                        estado_registro=1
                    )
                    db.add(nuevo)
                    total_creados += 1

        db.commit()
        print(f"Vinculacion completada exitosamente! Creados: {total_creados}, Actualizados: {total_actualizados}")

        # Resumen de verificacion
        print("\n--- RESUMEN DE PRODUCTOS POR PROVEEDOR ---")
        for prov in db.query(models.Proveedor).filter(models.Proveedor.estado_registro == 1).all():
            cant = db.query(models.ProveedorProducto).filter(
                models.ProveedorProducto.id_proveedor == prov.id_proveedor,
                models.ProveedorProducto.estado_registro == 1
            ).count()
            print(f"ID {prov.id_proveedor} | {prov.razon_social} -> {cant} productos vinculados")

    except Exception as e:
        db.rollback()
        print(f"Error vinculando productos: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == '__main__':
    vincular_proveedores_productos()
