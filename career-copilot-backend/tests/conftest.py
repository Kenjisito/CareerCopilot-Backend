import os
import uuid
from copy import deepcopy

# Debe ir antes de importar la app: Supabase y límites conocidos.
os.environ["SUPABASE_URL"] = "http://localhost:9"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["ADMIN_EMAILS"] = '["admin@test.cl"]'
os.environ["FREE_INTERVIEW_LIMIT"] = "3"
os.environ["AI_RATE_LIMIT_PER_HOUR"] = "1000"
os.environ["OPENAI_API_KEY"] = "test-key"  # nunca se usa: la IA se reemplaza por fake_ai
os.environ["INTERVIEW_QUESTIONS"] = "6"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user_payload
from app.main import app
from app.shared.dependencies import get_supabase
from app.shared import rate_limit

FAKE_CV = (
    "Ana Pérez ana@mail.cl +56 9 1234 5678. Experiencia: Desarrolladora backend en Acme "
    "(2023-2026) con Python, FastAPI y SQL. Educación: Ingeniería en Informática. Habilidades: Docker."
)


class FakeResponse:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self.action = "select"
        self.columns = "*"
        self.count_mode = None
        self.payload = None
        self.conflict = None
        self.ignore_duplicates = False
        self.filters = []
        self.orders = []
        self.row_limit = None

    def select(self, columns="*", count=None, **kwargs):
        self.columns = columns
        self.count_mode = count
        return self

    def insert(self, payload, **kwargs):
        self.action = "insert"
        self.payload = payload
        return self

    def upsert(self, payload, on_conflict=None, ignore_duplicates=False, **kwargs):
        self.action = "upsert"
        self.payload = payload
        self.conflict = on_conflict
        self.ignore_duplicates = ignore_duplicates
        return self

    def update(self, payload, **kwargs):
        self.action = "update"
        self.payload = payload
        return self

    def delete(self, **kwargs):
        self.action = "delete"
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def in_(self, column, values):
        self.filters.append(("in", column, values))
        return self

    def ilike(self, column, value):
        self.filters.append(("ilike", column, value))
        return self

    def gte(self, column, value):
        self.filters.append(("gte", column, value))
        return self

    def order(self, column, desc=False, **kwargs):
        self.orders.append((column, desc))
        return self

    def limit(self, value):
        self.row_limit = value
        return self

    def _matches(self, row):
        for operation, column, value in self.filters:
            current = row.get(column)
            if operation == "eq" and current != value:
                return False
            if operation == "in" and current not in value:
                return False
            if operation == "ilike" and str(current).casefold() != str(value).casefold():
                return False
            if operation == "gte" and (current is None or current < value):
                return False
        return True

    def _project(self, row):
        if self.columns == "*":
            return deepcopy(row)
        return {key: deepcopy(row[key]) for key in self.columns.split(",") if key in row}

    async def execute(self):
        failure_key = (self.table_name, self.action)
        if self.client.fail_next.get(failure_key, 0):
            self.client.fail_next[failure_key] -= 1
            raise RuntimeError(f"simulated {self.action} failure")
        rows = self.client.tables.setdefault(self.table_name, [])
        if self.action == "insert":
            inserted = self.payload if isinstance(self.payload, list) else [self.payload]
            rows.extend(deepcopy(inserted))
            return FakeResponse([self._project(row) for row in inserted])
        if self.action == "upsert":
            inserted = self.payload if isinstance(self.payload, list) else [self.payload]
            result = []
            for incoming in inserted:
                existing = next(
                    (row for row in rows if self.conflict and row.get(self.conflict) == incoming.get(self.conflict)),
                    None,
                )
                if existing is None:
                    rows.append(deepcopy(incoming))
                    result.append(incoming)
                elif not self.ignore_duplicates:
                    existing.update(deepcopy(incoming))
                    result.append(existing)
            return FakeResponse([self._project(row) for row in result])

        matched = [row for row in rows if self._matches(row)]
        if self.action == "update":
            for row in matched:
                row.update(deepcopy(self.payload))
        if self.action == "delete":
            self.client.tables[self.table_name] = [row for row in rows if not self._matches(row)]
        count = len(matched) if self.count_mode == "exact" else None
        if self.orders:
            for column, descending in reversed(self.orders):
                matched.sort(key=lambda row: row.get(column) or "", reverse=descending)
        if self.row_limit is not None:
            matched = matched[:self.row_limit]
        return FakeResponse([self._project(row) for row in matched], count)


class FakeAdmin:
    async def delete_user(self, user_id):
        return None


class FakeAuth:
    def __init__(self):
        self.admin = FakeAdmin()


class FakeSupabase:
    def __init__(self):
        self.tables = {}
        self.fail_next = {}
        self.auth = FakeAuth()

    def table(self, name):
        return FakeQuery(self, name)


@pytest_asyncio.fixture(autouse=True)
async def _supabase():
    client = FakeSupabase()
    app.dependency_overrides[get_supabase] = lambda: client
    rate_limit.reset()
    yield client
    app.dependency_overrides.clear()


def fake_response(system_prompt: str) -> dict:
    """Respuesta con la forma exacta que pide cada prompt (así un prompt que
    pida claves distintas a las que valida el servicio hace fallar los tests)."""
    if "Eres un editor de CV experto" in system_prompt:
        return {
            "summary": "Astro encontró mejoras de claridad y enfoque ATS.",
            "changes": [
                {
                    "field": "professionalSummary",
                    "experienceIndex": None,
                    "suggestedValue": "Desarrolladora backend especializada en Python.",
                    "reason": "Resume el perfil y destaca una especialidad presente.",
                },
                {
                    "field": "experienceDescription",
                    "experienceIndex": 0,
                    "suggestedValue": "Desarrolló servicios con FastAPI.",
                    "reason": "Expresa la responsabilidad con mayor claridad.",
                },
            ],
        }
    if "Extrae información profesional explícita" in system_prompt:  # perfil desde CV
        return {
            "fullName": "Ana Pérez",
            "headline": "Desarrolladora Backend",
            "email": "ana@mail.cl",
            "phone": "+56 9 1234 5678",
            "professionalSummary": "Desarrolladora backend con experiencia en Python.",
            "skills": ["Python", "FastAPI"],
            "additionalSections": {
                "education": ["Ingeniería en Informática · Universidad de Chile"],
                "certifications": ["AWS Certified Solutions Architect"],
                "projects": ["API de pagos · Python, FastAPI"],
                "languages": ["Español: nativo", "Inglés: avanzado"],
            },
            "experiences": [{
                "role": "Desarrolladora backend",
                "company": "Acme",
                "startDate": "2023-01",
                "endDate": None,
                "isCurrent": True,
                "description": "Servicios con FastAPI.",
                "achievements": ["Redujo la latencia en 35%."],
                "experienceType": "professional",
                "rawText": "Desarrolladora backend en Acme (2023-2026). Servicios con FastAPI.",
            }],
        }
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
    def __init__(self, client: AsyncClient, supabase: FakeSupabase):
        self.client = client
        self.supabase = supabase
        self.user = None

    def login(self, email="user@test.cl", name="Usuario Test"):
        uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, email))
        payload = {"sub": uid, "email": email, "user_metadata": {"full_name": name}}
        app.dependency_overrides[get_current_user_payload] = lambda: payload
        self.user = payload
        return uid


@pytest_asyncio.fixture
async def api(_supabase):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as client:
        s = Session(client, _supabase)
        s.login()
        yield s
    app.dependency_overrides.clear()
