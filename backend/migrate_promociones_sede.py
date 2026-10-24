import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

def main():
    print("[MIGRACION] Agregando columna 'id_sede' a la tabla 'promociones'...")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE promociones ADD COLUMN IF NOT EXISTS id_sede INTEGER REFERENCES sedes(id_sede);"))
        conn.commit()
    print("[MIGRACION] ¡Columna 'id_sede' agregada correctamente!")

if __name__ == "__main__":
    main()
