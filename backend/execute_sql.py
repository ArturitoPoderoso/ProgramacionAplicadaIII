import sqlalchemy
from sqlalchemy import create_engine, text
import os

# Cadena de conexion
SQLALCHEMY_DATABASE_URL = "postgresql+pg8000://postgres.ilkphmcbusmlwouourfa:ARTURO4321%40luis@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

sql_file_path = os.path.join(os.path.dirname(__file__), "respaldo_supabase.sql")

with open(sql_file_path, 'r', encoding='utf-8') as file:
    sql_script = file.read()

# Dividir por sentencias (aproximado, usando el delimitador natural de Supabase/SQL)
# Ejecutar todo el script
try:
    with engine.connect() as connection:
        # Iniciamos transaccion
        trans = connection.begin()
        try:
            # Ejecutamos todo el script crudo
            for statement in sql_script.split(';'):
                if statement.strip():
                    connection.execute(text(statement))
            trans.commit()
            print("Script SQL ejecutado con EXITO.")
        except Exception as e:
            trans.rollback()
            print(f"Error ejecutando SQL: {e}")
            raise e
except Exception as e:
    print(f"Error de conexion: {e}")
