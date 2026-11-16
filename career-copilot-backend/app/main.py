from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.monitoring import configure_logging
from app.db.base import Base
from app.db.session import engine
from app.modules.ats.router import router as ats_router
from app.modules.auth.router import router as auth_router
from app.modules.interview.router import router as interview_router
from app.modules.job_match.router import router as job_match_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.email.router import router as email_router
from app.modules.historial.router import router as historial_router
from app.modules.profile.router import router as profile_router
from app.modules.ats.cv_documents_router import router as cv_documents_router

configure_logging()

@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        def add_email_tone_column(sync_connection):
            columns = {column["name"] for column in inspect(sync_connection).get_columns("emails_generados")}
            if "tone" not in columns:
                sync_connection.execute(text(
                    "ALTER TABLE emails_generados ADD COLUMN tone VARCHAR(30) NOT NULL DEFAULT 'professional'"
                ))

        def add_profile_fields(sync_connection):
            columns = {column["name"] for column in inspect(sync_connection).get_columns("perfiles")}
            if "headline" not in columns:
                sync_connection.execute(text("ALTER TABLE perfiles ADD COLUMN headline VARCHAR(200)"))
            if "additional_sections" not in columns:
                sync_connection.execute(text("ALTER TABLE perfiles ADD COLUMN additional_sections JSON"))

        await connection.run_sync(add_email_tone_column)
        await connection.run_sync(add_profile_fields)
    yield
    await engine.dispose()

app = FastAPI(title="CareerCopilot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Todas las rutas bajo /api/v1, igual que espera
# frontend/lib/constants.ts → API_BASE_URL = "http://localhost:8000/api/v1"
router_prefix = settings.API_PREFIX

app.include_router(auth_router, prefix=router_prefix)
app.include_router(ats_router, prefix=router_prefix)
app.include_router(job_match_router, prefix=router_prefix)
app.include_router(interview_router, prefix=router_prefix)
app.include_router(email_router, prefix=router_prefix)
app.include_router(historial_router, prefix=router_prefix)
app.include_router(dashboard_router, prefix=router_prefix)
app.include_router(profile_router, prefix=router_prefix)
app.include_router(cv_documents_router, prefix=router_prefix)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
