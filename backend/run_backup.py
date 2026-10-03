import os
from sqlalchemy import text
from database import engine

sql_file_path = "respaldo_supabase.sql"

print("Conectando a la nueva base de datos en Supabase...")
try:
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        # Leemos todo el archivo y separamos por punto y coma (;)
        sql_commands = f.read().split(';')

    with engine.begin() as conn: # begin() asegura auto-commit
        for cmd in sql_commands:
            if cmd.strip():
                conn.execute(text(cmd))
                
    print("¡Base de datos y datos iniciales creados exitosamente!")
except Exception as e:
    print(f"Ocurrió un error: {e}")
