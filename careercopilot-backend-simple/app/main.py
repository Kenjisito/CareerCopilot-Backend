from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

configure_logging()

@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
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


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
