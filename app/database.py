# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path
import os

# Usar ruta absoluta desde variable de entorno o por defecto
DB_DIR = os.getenv("DB_DIR", "/app/data")
DB_PATH = Path(DB_DIR) / "wp_scrap.db"

# Crear directorio si no existe
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Engine con configuración optimizada para SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30  # timeout en segundos para locks
    },
    pool_pre_ping=True,  # verifica conexiones antes de usar
    echo=False  # cambiar a True para debug SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency para FastAPI
def get_db():
    """
    Dependency que proporciona una sesión de base de datos.
    Se cierra automáticamente al finalizar el request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    Se debe llamar al inicio de la aplicación.
    """
    Base.metadata.create_all(bind=engine)
