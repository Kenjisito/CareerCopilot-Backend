from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import Base, engine
from app.modules.ats.router import router as ats_router
from app.modules.auth.router import router as auth_router
from app.modules.interview.router import router as interview_router
from app.modules.job_match.router import router as job_match_router

# Crea las tablas si no existen (SQLite: basta con esto, sin migraciones
# formales por ahora — suficiente para el alcance actual del frontend).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CareerCopilot API", version="0.1.0")

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


@app.get("/health")
def health():
    return {"status": "ok"}
