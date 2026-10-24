import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
from models import Promocion

def main():
    print("[MIGRACION] Creando tabla 'promociones' en la base de datos...")
    Base.metadata.create_all(bind=engine, tables=[Promocion.__table__])
    print("[MIGRACION] ¡Tabla 'promociones' creada exitosamente!")

if __name__ == "__main__":
    main()
