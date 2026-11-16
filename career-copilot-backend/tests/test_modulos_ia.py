"""Tests de los módulos con IA: Diagnóstico ATS, Job Match (incluida la
extracción de ofertas desde una URL) y el simulador de entrevistas."""
import io
import json

import httpx
import pytest
from docx import Document
from openai import BadRequestError, RateLimitError

from tests.conftest import fake_response
from tests.test_api import make_docx, upload

CV_MULTILINEA = """Ana Pérez
ana.perez@mail.cl | +56 9 1234 5678 | Santiago
Experiencia
Desarrolladora Backend — Acme (2023-2026)
Construí APIs con Python, FastAPI y PostgreSQL para 20 mil usuarios.
Educación
Ingeniería en Informática — Universidad de Chile
Habilidades
Python, FastAPI, SQL, Docker, Git"""

OFERTA = "Buscamos Desarrollador Backend con Python, FastAPI, Docker y Kubernetes. Deseable AWS."


def docx_lines(text: str) -> bytes:
    buf = io.BytesIO()
    d = Document()
    for line in text.splitlines():
        d.add_paragraph(line)
    d.save(buf)
    return buf.getvalue()


async def crear_match(api) -> str:
    assert (await upload(api, docx_lines(CV_MULTILINEA))).status_code == 201
    r = await api.client.post("/job-match/analyze", json={"nombre": "Backend Dev", "ofertaTexto": OFERTA})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --- Diagnóstico ATS -----------------------------------------------------------

async def test_ats_puntaje_es_suma_de_rubrica_con_desglose(api):
    r = await upload(api, docx_lines(CV_MULTILINEA))
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["score"] == 74
    assert [i["max"] for i in d["scoreBreakdown"]] == [20, 10, 30, 20, 20]
    assert sum(i["score"] for i in d["scoreBreakdown"]) == d["score"]
    assert d["detectedRole"] == "Desarrolladora Backend"


async def test_ats_secciones_se_complementan_con_deteccion_determinista(api):
    # La IA dice skills=false, pero el CV tiene un título "Habilidades".
    d = (await upload(api, docx_lines(CV_MULTILINEA))).json()
    assert d["sections"] == {"contactInfo": True, "workExperience": True, "education": True, "skills": True}


async def test_ats_no_reporta_como_faltante_una_keyword_que_esta_en_el_cv(api):
    d = (await upload(api, docx_lines(CV_MULTILINEA))).json()
    assert "Docker" not in d["missingKeywords"]  # está en el CV
    assert "Kubernetes" in d["missingKeywords"]


async def test_ats_extrae_texto_de_tablas_docx(api, fake_ai):
    buf = io.BytesIO()
    d = Document()
    d.add_paragraph("Ana Pérez — ana@mail.cl")
    table = d.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Experiencia"
    table.rows[0].cells[1].text = "Backend en Acme con Kubernetes y Terraform"
    d.save(buf)
    assert (await upload(api, buf.getvalue())).status_code == 201
    _, user_prompt = fake_ai["prompts"][-1]
    assert "Terraform" in user_prompt


@pytest.mark.parametrize(
    ("heading", "category"),
    [
        ("Professional Experience", "experience"),
        ("Formación académica", "education"),
        ("Technical Skills", "skills"),
        ("Experiencia Académica", "experience"),
        ("Perfil Académico", "summary"),
        ("SKILL", "skills"),
        ("Employment History: Backend Engineer at Acme", "experience"),
        ("Professional Experience at Acme", "experience"),
        ("RESEARCH GRANTS", "other"),
    ],
)
def test_catalogo_reconoce_sinonimos_y_titulos_con_contenido(heading, category):
    from app.modules.ats.section_catalog import identify_heading

    match = identify_heading(heading)
    assert match is not None and match[0] == category
    if ":" in heading:
        assert match[1] == "Backend Engineer at Acme"
    if heading == "Professional Experience at Acme":
        assert match[1] == "at Acme"


def test_diagnostico_detecta_secciones_con_sinonimos():
    from app.modules.ats.service import _detect_sections

    sections = _detect_sections(
        "Contact Details\nProfessional Experience\nAcademic Background\nCore Competencies"
    )
    assert sections.model_dump() == {
        "contactInfo": True,
        "workExperience": True,
        "education": True,
        "skills": True,
    }


def test_secciones_organizadas_y_bloques_conservan_contenido_y_contexto():
    from app.modules.ats.section_catalog import organize_cv_sections, split_text_chunks

    source = (
        "Professional Experience: Backend Engineer\n"
        + "Built reliable services with Python and FastAPI. " * 12
        + "\nAcademic Background\nComputer Science, Example University"
    )
    organized = organize_cv_sections(source)
    assert "## EXPERIENCIA LABORAL" in organized
    assert "## EDUCACION Y FORMACION" in organized

    chunks = split_text_chunks(organized, 110)
    assert all(len(chunk) <= 110 for chunk in chunks)
    joined = "\n".join(chunks)
    assert "Backend Engineer" in joined and "Computer Science, Example University" in joined
    assert all("## EXPERIENCIA LABORAL" in chunk for chunk in chunks if "Built reliable" in chunk)


def test_seccion_no_catalogada_se_conserva_en_otra_informacion():
    from app.modules.ats.section_catalog import organize_cv_sections

    organized = organize_cv_sections(
        "Ana Pérez\nRESEARCH GRANTS\nFunded a research project on public health.\nSkills: Python"
    )
    assert "## OTRA INFORMACION" in organized
    assert "### RESEARCH GRANTS" in organized
    assert "Funded a research project on public health." in organized
    assert "## HABILIDADES Y COMPETENCIAS" in organized
    assert "### Skills" in organized


def test_docx_extrae_tablas_de_encabezado_y_pie():
    from docx.shared import Inches
    from app.modules.ats.extract import extract_text

    buf = io.BytesIO()
    document = Document()
    header_table = document.sections[0].header.add_table(rows=1, cols=1, width=Inches(6))
    header_table.cell(0, 0).text = "Ana Pérez | ana@mail.cl"
    footer_table = document.sections[0].footer.add_table(rows=1, cols=1, width=Inches(6))
    footer_table.cell(0, 0).text = "Portfolio: ana.example.com"
    document.add_paragraph("Professional Experience")
    document.add_paragraph("Backend Engineer at Acme, building APIs.")
    document.save(buf)

    text = extract_text(buf.getvalue(), "cv.docx")
    assert "Ana Pérez" in text and "Portfolio: ana.example.com" in text
    assert "Backend Engineer" in text


def test_pdf_sin_texto_seleccionable_usa_ocr(monkeypatch):
    from app.modules.ats import extract

    class ScannedPage:
        @staticmethod
        def extract_text(**kwargs):
            return ""

    class ScannedPdf:
        pages = [ScannedPage()]

        def __enter__(self):
            return self

        @staticmethod
        def __exit__(*args):
            return None

    calls = {}

    def fake_ocr(file_bytes, filename, page_numbers):
        calls["args"] = (file_bytes, filename, page_numbers)
        return {0: "Texto reconocido por OCR"}

    monkeypatch.setattr(extract.pdfplumber, "open", lambda *_args, **_kwargs: ScannedPdf())
    monkeypatch.setattr(extract, "extract_text_with_ocr", fake_ocr)
    assert extract._extract_pdf(b"pdf") == "Texto reconocido por OCR"
    assert calls["args"] == (b"pdf", "PDF", [0])


async def test_parse_cv_procesa_fragmentos_largos_sin_omitir_el_final(api, fake_ai):
    content = "Professional Experience\n" + (
        "Built reliable services with Python, FastAPI, and PostgreSQL. " * 180
    ) + "\nEND_OF_CV_MARKER"
    response = await api.client.post(
        "/cv-documents/parse",
        files={"file": ("cv.docx", docx_lines(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200, response.text
    profile_prompts = [
        prompt for system, prompt in fake_ai["prompts"]
        if "Extrae información profesional explícita" in system
    ]
    assert len(profile_prompts) > 1
    assert any("END_OF_CV_MARKER" in prompt for prompt in profile_prompts)
    profile_system = next(
        system for system, _prompt in fake_ai["prompts"]
        if "Extrae información profesional explícita" in system
    )
    assert "additionalSections.education" in profile_system
    assert "additionalSections.certifications" in profile_system
    assert "experiences.company" in profile_system and "employer" in profile_system
    assert "experiences.startDate" in profile_system
    assert "experiences.description" in profile_system
    assert "experiences.achievements" in profile_system


async def test_parse_cv_no_descarta_experiencias_academicas_incompletas(api, monkeypatch):
    async def categorized_ai(system_prompt, user_prompt, model=None, **kwargs):
        if "Extrae información profesional explícita" in system_prompt:
            return {
                "fullName": "Ana Pérez",
                "headline": "Docente e investigadora",
                "experiences": [{
                    "role": "Docente de Informática",
                    "company": "",
                    "startDate": "",
                    "description": "Dictó cursos de programación.",
                    "experienceType": "academic",
                    "rawText": "Docente de Informática — dictó cursos de programación en la universidad.",
                }],
            }
        return fake_response(system_prompt)

    monkeypatch.setattr("app.core.ai_router.generate_json", categorized_ai)
    response = await api.client.post(
        "/cv-documents/parse",
        files={"file": (
            "cv.docx",
            docx_lines("Experiencia académica\nDocente de Informática — dictó cursos de programación."),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )},
    )
    assert response.status_code == 200, response.text
    experience = response.json()["experiences"][0]
    assert experience["experienceType"] == "academic"
    assert experience["company"] == "" and experience["startDate"] == ""
    assert "dictó cursos" in experience["rawText"]


async def test_ats_reintenta_si_la_ia_devuelve_otra_forma(api, monkeypatch):
    calls = {"n": 0}

    async def flaky(system_prompt, user_prompt, model=None, **kwargs):
        calls["n"] += 1
        return {"score": 50} if calls["n"] == 1 else fake_response(system_prompt)

    monkeypatch.setattr("app.core.ai_router.generate_json", flaky)
    r = await upload(api, make_docx())
    assert r.status_code == 201 and calls["n"] == 2


async def test_ats_diagnostico_antiguo_sin_desglose_sigue_abriendo(api):
    """Los diagnósticos guardados antes de esta versión no tienen scoreBreakdown."""
    from datetime import datetime, timezone
    import uuid

    await api.client.get("/auth/me")
    cv_id = str(uuid.uuid4())
    await api.supabase.table("cvs").insert({
        "id": cv_id,
        "usuario_id": api.user["sub"],
        "file_name": "viejo.pdf",
        "parsed_text": "x",
        "score": 60,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis": {
            "score": 60, "parsedText": "x", "summary": "s",
            "sections": {"contactInfo": True, "workExperience": True, "education": True, "skills": True},
            "strengths": [], "improvements": [], "missingKeywords": [],
        },
    }).execute()
    r = await api.client.get(f"/ats/{cv_id}")
    assert r.status_code == 200 and r.json()["scoreBreakdown"] is None


# --- Cliente de Groq: manejo de errores ------------------------------------------

def _req():
    return httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


class _FakeClient:
    def __init__(self, behaviours):
        self.behaviours = list(behaviours)
        self.calls = 0
        client = self

        class completions:
            @staticmethod
            async def create(**kw):
                client.calls += 1
                b = client.behaviours.pop(0)
                if isinstance(b, Exception):
                    raise b
                msg = type("M", (), {"content": b})
                return type("R", (), {"choices": [type("C", (), {"message": msg})]})

        self.chat = type("Chat", (), {"completions": completions})


@pytest.fixture
def real_ai_client(monkeypatch):
    from app.shared import ai_client

    monkeypatch.setattr("app.core.ai_router.generate_json", ai_client.generate_json)

    def install(*behaviours):
        fake = _FakeClient(behaviours)
        monkeypatch.setattr(ai_client, "_get_client", lambda: fake)
        return fake

    return install


async def test_groq_limite_de_uso_es_503_con_mensaje_claro(api, real_ai_client):
    real_ai_client(RateLimitError("rate limit", response=httpx.Response(429, request=_req()), body=None))
    r = await upload(api, make_docx())
    assert r.status_code == 503 and "límite" in r.json()["detail"]


async def test_groq_json_validate_failed_se_reintenta(api, real_ai_client):
    ok = json.dumps(fake_response('"rubrica"'))
    err = BadRequestError("json_validate_failed", response=httpx.Response(400, request=_req()), body={"error": {"code": "json_validate_failed"}})
    fake = real_ai_client(err, ok)
    r = await upload(api, make_docx())
    assert r.status_code == 201 and fake.calls == 2


async def test_groq_respuesta_con_bloque_markdown_se_parsea(api, real_ai_client):
    real_ai_client("```json\n" + json.dumps(fake_response('"rubrica"')) + "\n```")
    assert (await upload(api, make_docx())).status_code == 201


async def test_sin_api_key_es_503(api, real_ai_client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    real_ai_client()
    r = await upload(api, make_docx())
    assert r.status_code == 503 and "configurado" in r.json()["detail"]


# --- Job Match -------------------------------------------------------------------

async def test_job_match_devuelve_recomendaciones_y_envia_cv_y_oferta(api, fake_ai):
    await upload(api, docx_lines(CV_MULTILINEA))
    r = await api.client.post("/job-match/analyze", json={"nombre": "Backend Dev", "ofertaTexto": OFERTA})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["scoreCompatibilidad"] == 80 and body["recomendaciones"] == ["Destaca tu experiencia con FastAPI"]
    system, user = fake_ai["prompts"][-1]
    assert '"score_compatibilidad"' in system and '"no_cumple"' in system
    assert "Kubernetes" in user and "FastAPI y PostgreSQL" in user and "Backend Dev" in user


async def test_job_match_sin_cv_es_400(api):
    r = await api.client.post("/job-match/analyze", json={"nombre": "X", "ofertaTexto": OFERTA})
    assert r.status_code == 400 and "CV" in r.json()["detail"]


async def test_job_match_oferta_demasiado_larga_es_422(api):
    await upload(api, make_docx())
    r = await api.client.post("/job-match/analyze", json={"nombre": "X", "ofertaTexto": "a " * 20000})
    assert r.status_code == 422


# --- Extracción de ofertas desde URL ----------------------------------------------

JSONLD_HTML = """<html><head><title>Oferta</title>
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"X"},
{"@type":"JobPosting","title":"Desarrollador Frontend","hiringOrganization":{"@type":"Organization","name":"Acme SpA"},
"jobLocation":{"@type":"Place","address":{"addressLocality":"Santiago","addressCountry":"CL"}},
"employmentType":"FULL_TIME",
"description":"<p>Buscamos desarrollador <b>React</b> con experiencia.</p><ul><li>3 años con TypeScript</li><li>Next.js deseable</li></ul>"}]}
</script></head><body>menú</body></html>"""

PLAIN_HTML = """<html><head><title>Analista de Datos | Portal</title></head><body>
<nav>Inicio Empleos Empresas</nav><main><h1>Analista de Datos</h1><p>DataCorp busca Analista de Datos.</p>
<p>Requisitos: SQL avanzado, Python, Power BI, 2 años de experiencia en análisis de datos.</p>
<p>Ofrecemos modalidad híbrida y seguro complementario.</p></main><footer>© Portal</footer></body></html>"""


def test_parseo_jsonld_jobposting():
    from app.modules.job_match.extractor import extract_job_posting

    posting = extract_job_posting(JSONLD_HTML)
    assert posting["nombre"] == "Desarrollador Frontend"
    assert posting["empresa"] == "Acme SpA"
    text = posting["ofertaTexto"]
    assert "React" in text and "3 años con TypeScript" in text and "Santiago" in text and "<p>" not in text


def test_normaliza_urls_de_linkedin():
    from app.modules.job_match.extractor import normalize_job_url

    assert normalize_job_url("https://www.linkedin.com/jobs/search/?currentJobId=4012345678&keywords=python") == "https://www.linkedin.com/jobs/view/4012345678/"
    assert normalize_job_url("https://cl.linkedin.com/jobs/view/desarrollador-backend-at-acme-4012345678?trk=x") == "https://www.linkedin.com/jobs/view/4012345678/"
    assert normalize_job_url("https://www.getonbrd.com/jobs/x") == "https://www.getonbrd.com/jobs/x"


@pytest.mark.parametrize("url", ["http://127.0.0.1/admin", "http://localhost:8000/docs", "http://10.0.0.5/", "http://169.254.169.254/latest/meta-data", "ftp://example.com/x"])
async def test_extraccion_bloquea_urls_internas(api, url):
    r = await api.client.post("/job-match/extract", json={"url": url})
    assert r.status_code == 422


async def test_extraccion_con_datos_estructurados_no_usa_ia(api, fake_ai, monkeypatch):
    async def fake_fetch(url):
        return url, JSONLD_HTML

    monkeypatch.setattr("app.modules.job_match.extractor.fetch_html", fake_fetch)
    r = await api.client.post("/job-match/extract", json={"url": "https://www.getonbrd.com/jobs/frontend"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fuente"] == "datos-estructurados" and body["nombre"] == "Desarrollador Frontend"
    assert fake_ai["n"] == 0


async def test_extraccion_sin_datos_estructurados_usa_ia(api, fake_ai, monkeypatch):
    async def fake_fetch(url):
        return url, PLAIN_HTML

    monkeypatch.setattr("app.modules.job_match.extractor.fetch_html", fake_fetch)
    r = await api.client.post("/job-match/extract", json={"url": "https://portal.example.com/oferta/1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fuente"] == "ia" and body["nombre"] == "Analista de Datos" and body["empresa"] == "DataCorp"
    _, user_prompt = fake_ai["prompts"][-1]
    assert "Power BI" in user_prompt and "Inicio Empleos" not in user_prompt  # <nav> se descarta


async def test_extraccion_pagina_sin_oferta_es_422(api, monkeypatch):
    async def fake_fetch(url):
        return url, PLAIN_HTML

    async def no_offer(system_prompt, user_prompt, model=None, **kwargs):
        return {"es_oferta": False, "nombre": "", "empresa": None, "oferta_texto": ""}

    monkeypatch.setattr("app.modules.job_match.extractor.fetch_html", fake_fetch)
    monkeypatch.setattr("app.core.ai_router.generate_json", no_offer)
    r = await api.client.post("/job-match/extract", json={"url": "https://portal.example.com/"})
    assert r.status_code == 422 and "pégalo" in r.json()["detail"]


async def test_extraccion_pagina_vacia_es_422(api, monkeypatch):
    async def fake_fetch(url):
        return url, "<html><body><div id='root'></div></body></html>"

    monkeypatch.setattr("app.modules.job_match.extractor.fetch_html", fake_fetch)
    r = await api.client.post("/job-match/extract", json={"url": "https://spa.example.com/job/1"})
    assert r.status_code == 422 and "JavaScript" in r.json()["detail"]


async def test_extraccion_url_invalida_es_422(api):
    assert (await api.client.post("/job-match/extract", json={"url": "no es una url"})).status_code == 422


# --- Simulador de entrevistas -------------------------------------------------------

async def test_entrevista_completa_con_evaluacion(api, fake_ai):
    jm = await crear_match(api)
    start = await api.client.post(f"/interview/start/{jm}", json={"tipo": "tecnica", "seniority": "Senior"})
    assert start.status_code == 201, start.text
    s = start.json()
    assert s["preguntaActual"] == 1 and s["totalPreguntas"] == 6
    iid = s["entrevistaId"]

    # El entrevistador recibe la oferta, el CV y las brechas del Job Match.
    system, user = fake_ai["prompts"][-1]
    assert "TÉCNICA" in system and "Senior" in system
    assert "Kubernetes" in user and "FastAPI y PostgreSQL" in user

    for n in range(1, 6):
        r = await api.client.post(f"/interview/{iid}/message", json={"contenido": f"Respuesta número {n} con detalle"})
        assert r.status_code == 200, r.text
        assert r.json()["finalizada"] is False and r.json()["preguntaActual"] == n + 1
    # Toma en cuenta la respuesta del candidato.
    assert "Respuesta número 5" in fake_ai["prompts"][-1][1]

    last = await api.client.post(f"/interview/{iid}/message", json={"contenido": "Respuesta final"})
    assert last.status_code == 200 and last.json()["finalizada"] is True
    # Ya no admite más mensajes.
    assert (await api.client.post(f"/interview/{iid}/message", json={"contenido": "otra"})).status_code == 409

    fin = await api.client.post(f"/interview/{iid}/finish")
    assert fin.status_code == 200, fin.text
    ev = fin.json()
    assert ev["preguntasRespondidas"] == 6 and len(ev["preguntas"]) == 6
    assert ev["puntaje"] == round(sum(min(100, 60 + 10 * i) for i in range(6)) / 6)  # promedio (cada nota se limita a 100)
    assert ev["nivel"] == "Bueno"
    assert ev["preguntas"][0]["respuesta"] == "Respuesta número 1 con detalle"
    assert [c["nombre"] for c in ev["competencias"]] == ["Comunicación", "Conocimiento del puesto", "Ejemplos concretos (STAR)", "Motivación y encaje"]
    assert ev["recomendaciones"]

    # Pedirla de nuevo devuelve la misma evaluación sin volver a llamar a la IA.
    calls = fake_ai["n"]
    again = await api.client.post(f"/interview/{iid}/finish")
    assert again.status_code == 200 and again.json() == ev and fake_ai["n"] == calls


async def test_inicio_entrevista_borra_la_entrevista_si_falla_el_mensaje(api):
    from uuid import UUID
    from app.modules.interview.service import InterviewService

    match_id = await crear_match(api)
    api.supabase.fail_next[("mensajes", "insert")] = 1
    with pytest.raises(RuntimeError, match="simulated insert failure"):
        await InterviewService(api.supabase).iniciar_entrevista(
            UUID(api.user["sub"]), "free", UUID(match_id), "mixta", "Junior"
        )
    assert api.supabase.tables.get("entrevistas", []) == []


async def test_finalizar_entrevista_borra_evaluacion_si_falla_actualizacion(api):
    from uuid import UUID
    from app.modules.interview.service import InterviewService

    match_id = await crear_match(api)
    service = InterviewService(api.supabase)
    interview, _ = await service.iniciar_entrevista(
        UUID(api.user["sub"]), "free", UUID(match_id), "mixta", "Junior"
    )
    await service.registrar_interaccion(
        UUID(api.user["sub"]), "free", UUID(interview["id"]), "Respuesta con detalle"
    )
    api.supabase.fail_next[("entrevistas", "update")] = 1
    with pytest.raises(RuntimeError, match="simulated update failure"):
        await service.finalizar_entrevista(
            UUID(api.user["sub"]), "free", UUID(interview["id"])
        )
    assert api.supabase.tables.get("entrevista_evaluaciones", []) == []


async def test_entrevista_finalizada_antes_de_tiempo(api):
    jm = await crear_match(api)
    iid = (await api.client.post(f"/interview/start/{jm}", json={})).json()["entrevistaId"]
    await api.client.post(f"/interview/{iid}/message", json={"contenido": "Trabajé 3 años con FastAPI."})
    ev = (await api.client.post(f"/interview/{iid}/finish")).json()
    assert ev["preguntasRespondidas"] == 1 and ev["totalPreguntas"] == 6 and ev["puntaje"] == 60


async def test_entrevista_sin_respuestas_no_se_evalua(api):
    jm = await crear_match(api)
    iid = (await api.client.post(f"/interview/start/{jm}", json={})).json()["entrevistaId"]
    r = await api.client.post(f"/interview/{iid}/finish")
    assert r.status_code == 400 and "al menos una" in r.json()["detail"]


async def test_entrevista_de_otro_usuario_es_404(api):
    jm = await crear_match(api)
    iid = (await api.client.post(f"/interview/start/{jm}", json={})).json()["entrevistaId"]
    api.login("otro@test.cl")
    assert (await api.client.post(f"/interview/{iid}/message", json={"contenido": "hola"})).status_code == 404
    assert (await api.client.post(f"/interview/{iid}/finish")).status_code == 404


async def test_entrevista_tipo_invalido_es_422(api):
    jm = await crear_match(api)
    assert (await api.client.post(f"/interview/start/{jm}", json={"tipo": "rara"})).status_code == 422


async def test_entrevista_respuesta_en_blanco_es_422(api):
    jm = await crear_match(api)
    iid = (await api.client.post(f"/interview/start/{jm}", json={})).json()["entrevistaId"]
    assert (await api.client.post(f"/interview/{iid}/message", json={"contenido": "   "})).status_code == 422


async def test_evaluacion_muestra_solo_la_pregunta_sin_la_reaccion(api):
    jm = await crear_match(api)
    start = (await api.client.post(f"/interview/start/{jm}", json={})).json()
    assert start["respuesta"].startswith("Gracias por tu respuesta.")  # el candidato ve reacción + pregunta
    iid = start["entrevistaId"]
    await api.client.post(f"/interview/{iid}/message", json={"contenido": "Usé FastAPI en Acme."})
    ev = (await api.client.post(f"/interview/{iid}/finish")).json()
    assert ev["preguntas"][0]["pregunta"] == "Cuéntame sobre un proyecto donde usaste FastAPI."


def test_turno_del_entrevistador_tolera_formato_mensaje():
    from app.modules.interview.schemas import InterviewerTurn

    turn = InterviewerTurn.model_validate({"mensaje": "¿Qué sabes de Docker?"})
    assert turn.mensaje == "¿Qué sabes de Docker?"
    turn = InterviewerTurn.model_validate({"reaccion": "Bien.", "pregunta": "¿Y\nKubernetes?"})
    assert turn.mensaje == "Bien.\n\n¿Y Kubernetes?"


async def test_evaluacion_empareja_cada_respuesta_con_su_pregunta_aunque_el_reloj_no_avance(api, monkeypatch):
    """Regresión: con dos mensajes guardados en el mismo instante, la evaluación
    mostraba la pregunta siguiente en vez de la respondida."""
    from datetime import datetime as real_datetime, timezone
    from app.modules.interview import service as interview_service

    frozen = real_datetime(2026, 11, 14, 12, 0, 0, tzinfo=timezone.utc)

    class FrozenDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen

    monkeypatch.setattr(interview_service, "datetime", FrozenDatetime)

    jm = await crear_match(api)
    counter = {"n": 0}

    async def numbered(system_prompt, user_prompt, model=None, **kwargs):
        if '"reaccion"' in system_prompt:
            counter["n"] += 1
            return {"reaccion": "Gracias.", "pregunta": f"Pregunta P{counter['n']}"}
        return fake_response(system_prompt)

    monkeypatch.setattr("app.core.ai_router.generate_json", numbered)
    iid = (await api.client.post(f"/interview/start/{jm}", json={})).json()["entrevistaId"]
    for n in range(1, 4):
        assert (await api.client.post(f"/interview/{iid}/message", json={"contenido": f"Respuesta R{n}"})).status_code == 200
    ev = (await api.client.post(f"/interview/{iid}/finish")).json()
    assert [(q["pregunta"], q["respuesta"]) for q in ev["preguntas"]] == [
        ("Pregunta P1", "Respuesta R1"), ("Pregunta P2", "Respuesta R2"), ("Pregunta P3", "Respuesta R3")]
