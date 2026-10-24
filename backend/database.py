from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Usar psycopg2 para mayor velocidad y soporte nativo C
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres.ilkphmcbusmlwouourfa:ARTURO4321%40luis@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Elimina congelamientos al verificar la conexión antes de cada query
    pool_size=10,        # Mantiene conexiones listas en el pool
    max_overflow=20,     # Maneja picos de peticiones
    pool_recycle=300     # Recicla conexiones cada 5 minutos para evitar cierres de Supabase
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

