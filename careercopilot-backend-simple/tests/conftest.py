import os
import tempfile
import uuid

# Debe ir antes de importar la app: BD temporal y límites conocidos.
_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db}"
os.environ["SUPABASE_URL"] = "http://localhost:9"
os.environ["ADMIN_EMAILS"] = '["admin@test.cl"]'
os.environ["FREE_INTERVIEW_LIMIT"] = "3"
os.environ["AI_RATE_LIMIT_PER_HOUR"] = "1000"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user_payload
from app.db.base import Base
from app.db.session import engine
from app.main import app
from app.shared import rate_limit

FAKE_CV = (
    "Ana Pérez ana@mail.cl +56 9 1234 5678. Experiencia: Desarrolladora backend en Acme "
    "(2023-2026) con Python, FastAPI y SQL. Educación: Ingeniería en Informática. Habilidades: Docker."
)


@pytest_asyncio.fixture(autouse=True)
async def _db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    rate_limit.reset()
    yield


@pytest.fixture(autouse=True)
def fake_ai(monkeypatch):
    """Reemplaza al proveedor de IA por respuestas fijas (sin red)."""
    calls = {"n": 0}

    async def _fake(system_prompt, user_prompt, model=None):
        calls["n"] += 1
        return {
            "score": 74, "summary": "ok", "sections": {"contactInfo": True, "experience": True, "education": True, "skills": True},
            "strengths": ["a"], "improvements": ["b"], "missingKeywords": ["Docker"],
            "score_compatibilidad": 80, "cumple": ["Python"], "no_cumple": ["Docker"], "resumen": "Buen match",
            "subject": "Postulación", "body": "Hola, me interesa el cargo.", "respuesta": "Cuéntame sobre un proyecto.",
        }

    monkeypatch.setattr("app.core.ai_router.generate_json", _fake)
    return calls


class Session:
    def __init__(self, client: AsyncClient):
        self.client = client
        self.user = None

    def login(self, email="user@test.cl", name="Usuario Test"):
        uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, email))
        payload = {"sub": uid, "email": email, "user_metadata": {"full_name": name}}
        app.dependency_overrides[get_current_user_payload] = lambda: payload
        self.user = payload
        return uid


@pytest_asyncio.fixture
async def api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as client:
        s = Session(client)
        s.login()
        yield s
    app.dependency_overrides.clear()
