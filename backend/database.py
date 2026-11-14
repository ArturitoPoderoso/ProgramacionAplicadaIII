import os
from flask import g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Cargar variables de entorno desde .env si existe
def _load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = val

_load_env_file()

# Obtener URL de conexión de la base de datos
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "")

if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
elif SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada. Crea el archivo .env o define la variable de entorno.")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Elimina congelamientos al verificar la conexión antes de cada query
    pool_size=10,        # Mantiene conexiones listas en el pool
    max_overflow=20,     # Maneja picos de peticiones
    pool_recycle=300     # Recicla conexiones cada 5 minutos para evitar cierres de Supabase
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Obtiene una sesión de base de datos vinculada al ciclo de vida de la petición Flask"""
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db

def teardown_db(exception=None):
    """Cierra la sesión de base de datos al finalizar la petición"""
    db = g.pop('db', None)
    if db is not None:
        db.close()
