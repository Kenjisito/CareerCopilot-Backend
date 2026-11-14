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
os.environ["OPENAI_API_KEY"] = "test-key"  # nunca se usa: la IA se reemplaza por fake_ai
os.environ["INTERVIEW_QUESTIONS"] = "6"

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


def fake_response(system_prompt: str) -> dict:
    """Respuesta con la forma exacta que pide cada prompt (así un prompt que
    pida claves distintas a las que valida el servicio hace fallar los tests)."""
    if '"rubrica"' in system_prompt:  # ATS
        return {
            "rubrica": {"estructura": 16, "contacto": 8, "experiencia": 20, "habilidades": 14, "legibilidad": 16},
            "detectedRole": "Desarrolladora Backend", "summary": "CV sólido; faltan métricas.",
            "sections": {"contactInfo": True, "workExperience": True, "education": True, "skills": False},
            "strengths": ["Experiencia relevante"], "improvements": ["Cuantifica tus logros"],
            "missingKeywords": ["Docker", "Kubernetes", "CI/CD"],
        }
    if '"es_oferta"' in system_prompt:  # extracción de oferta desde una página
        return {"es_oferta": True, "nombre": "Analista de Datos", "empresa": "DataCorp",
                "oferta_texto": "Buscamos Analista de Datos con SQL, Python y Power BI. Requisitos: 2 años de experiencia. Modalidad híbrida."}
    if '"score_compatibilidad"' in system_prompt:  # Job Match
        return {"score_compatibilidad": 80, "cumple": ["Python"], "no_cumple": ["Kubernetes"],
                "resumen": "Buen match", "recomendaciones": ["Destaca tu experiencia con FastAPI"]}
    if '"puntaje_general"' in system_prompt:  # evaluación de entrevista
        return {"puntaje_general": 70, "resumen": "Buen desempeño general.",
                "preguntas": [{"puntaje": 60 + 10 * i, "comentario": f"c{i}", "sugerencia": f"s{i}"} for i in range(6)],
                "competencias": [{"nombre": n, "puntaje": 70} for n in ("Comunicación", "Conocimiento del puesto", "Ejemplos concretos (STAR)", "Motivación y encaje")],
                "fortalezas": ["Claridad"], "recomendaciones": ["Usa el método STAR", "Agrega cifras"]}
    if '"reaccion"' in system_prompt:  # turno del entrevistador
        return {"reaccion": "Gracias por tu respuesta.", "pregunta": "Cuéntame sobre un proyecto donde usaste FastAPI."}
    return {"subject": "Postulación", "body": "Hola, me interesa el cargo."}  # email


@pytest.fixture(autouse=True)
def fake_ai(monkeypatch):
    """Reemplaza al proveedor de IA por respuestas fijas (sin red)."""
    calls = {"n": 0, "prompts": []}

    async def _fake(system_prompt, user_prompt, model=None, **kwargs):
        calls["n"] += 1
        calls["prompts"].append((system_prompt, user_prompt))
        return fake_response(system_prompt)

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
