"""
Motor de base de datos. SQLite por defecto (un solo archivo, cero
configuración) — suficiente para lo que el frontend actual necesita.
Si más adelante el equipo decide usar Postgres/Supabase, solo se cambia
DATABASE_URL; el resto del código no depende del motor específico.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency de FastAPI: entrega una sesión por request y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
