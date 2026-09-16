"""
Configuración centralizada. Todo el resto del código importa `settings`
desde aquí — nunca lee os.environ directamente.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"

    # El frontend llama a http://localhost:8000/api/v1 por defecto
    # (ver frontend/lib/constants.ts → API_BASE_URL). Debe coincidir.
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Base de datos simple (archivo SQLite) — no se requiere Postgres/Supabase
    # porque el frontend no tiene ningún código que dependa de eso.
    DATABASE_URL: str = "sqlite:///./careercopilot.db"

    # Auth propia (JWT), acorde a que el frontend ya guarda un Bearer token
    # en localStorage bajo la clave "career_copilot_token".
    JWT_SECRET: str = "cambia-esto-en-produccion"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 60 * 24 * 7  # 7 días

    # IA — el integrarbackend.txt del repo sugiere que el proveedor sea
    # intercambiable; por defecto usamos OpenAI.
    AI_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
