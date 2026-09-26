"""
Configuración centralizada. Todo el resto del código importa `settings`
desde aquí — nunca lee os.environ directamente.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    ENVIRONMENT: str = "development"

    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    DATABASE_URL: str = "sqlite+aiosqlite:///./careercopilot.db"

    AI_PROVIDER: str = "openai"  # "openai" | "groq" — ver app/shared/ai_client.py
    AI_BASE_URL: str = ""  # override manual; si está vacío se deriva de AI_PROVIDER
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    AI_PREMIUM_MODEL: str = "gpt-4o"
    LOG_LEVEL: str = "INFO"
    FREE_MATCH_LIMIT: int = 5
    FREE_INTERVIEW_LIMIT: int = 1
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
