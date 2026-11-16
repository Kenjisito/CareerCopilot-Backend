import io

from docx import Document

from tests.conftest import FAKE_CV


def make_docx(text=FAKE_CV) -> bytes:
    buf = io.BytesIO()
    d = Document()
    d.add_paragraph(text)
    d.save(buf)
    return buf.getvalue()


async def upload(api, data, name="cv.docx"):
    return await api.client.post("/ats/analyze", files={"file": (name, data)})


async def test_primer_login_crea_usuario_free(api):
    r = await api.client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["plan"] == "free" and r.json()["nombre_completo"] == "Usuario Test"


async def test_editar_perfil(api):
    r = await api.client.patch("/auth/me", json={"nombre_completo": "  Kenji Romero "})
    assert r.status_code == 200 and r.json()["nombre_completo"] == "Kenji Romero"
    assert (await api.client.patch("/auth/me", json={"nombre_completo": "x"})).status_code == 422


async def test_perfil_profesional_se_guarda_y_se_recupera(api):
    assert (await api.client.get("/profile")).status_code == 404
    payload = {
        "fullName": "Ana Pérez",
        "headline": "Desarrolladora Backend",
        "email": "ana@mail.cl",
        "phone": None,
        "country": "CL",
        "region": None,
        "commune": None,
        "professionalSummary": "Desarrolladora backend.",
        "skills": ["Python"],
        "additionalSections": {
            "education": ["Ingeniería en Informática · Universidad de Chile"],
            "certifications": ["AWS Certified Solutions Architect"],
        },
        "experiences": [{
            "role": "Desarrolladora",
            "company": "Acme",
            "startDate": "2023-01-01T00:00:00Z",
            "endDate": None,
            "isCurrent": True,
            "description": "APIs con FastAPI.",
            "achievements": ["Publicó una API usada por 20 mil personas."],
            "experienceType": "academic",
            "rawText": "Desarrolladora en Acme; APIs con FastAPI.",
        }],
    }
    saved = await api.client.put("/profile", json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["fullName"] == "Ana Pérez"
    loaded = await api.client.get("/profile")
    assert loaded.status_code == 200
    assert loaded.json()["experiences"][0]["company"] == "Acme"
    assert loaded.json()["experiences"][0]["experienceType"] == "academic"
    assert loaded.json()["experiences"][0]["rawText"] == "Desarrolladora en Acme; APIs con FastAPI."
    assert loaded.json()["headline"] == "Desarrolladora Backend"
    assert loaded.json()["additionalSections"] == payload["additionalSections"]


async def test_mejoras_de_cv_devuelven_cambios_revisables_sin_guardarlos(api, fake_ai):
    payload = {
        "headline": "Desarrolladora Backend",
        "professionalSummary": "Desarrolladora backend con experiencia en Python.",
        "skills": ["Python", "FastAPI"],
        "experiences": [{
            "id": "experience-acme",
            "role": "Desarrolladora backend",
            "company": "Acme",
            "description": "Servicios con FastAPI.",
            "achievements": ["Redujo la latencia en 35%."],
        }],
    }

    response = await api.client.post("/profile/improve", json=payload)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["summary"] == "Astro encontró mejoras de claridad y enfoque ATS."
    assert result["changes"] == [
        {
            "field": "professionalSummary",
            "experienceIndex": None,
            "currentValue": payload["professionalSummary"],
            "suggestedValue": "Desarrolladora backend especializada en Python.",
            "reason": "Resume el perfil y destaca una especialidad presente.",
            "experienceId": None,
        },
        {
            "field": "experienceDescription",
            "experienceIndex": 0,
            "currentValue": "Servicios con FastAPI.",
            "suggestedValue": "Desarrolló servicios con FastAPI.",
            "reason": "Expresa la responsabilidad con mayor claridad.",
            "experienceId": "experience-acme",
        },
    ]
    assert "user@test.cl" not in fake_ai["prompts"][0][1]
    assert (await api.client.get("/profile")).status_code == 404


async def test_mejoras_de_cv_rechazan_indices_de_experiencia_invalidos(api, monkeypatch):
    async def invalid_suggestion(*args, **kwargs):
        return {
            "summary": "Hay sugerencias.",
            "changes": [{
                "field": "experienceDescription",
                "experienceIndex": 3,
                "suggestedValue": "Texto modificado.",
                "reason": "Mejora la claridad.",
            }],
        }

    monkeypatch.setattr("app.core.ai_router.generate_json", invalid_suggestion)
    response = await api.client.post("/profile/improve", json={
        "headline": "",
        "professionalSummary": "",
        "skills": [],
        "experiences": [],
    })

    assert response.status_code == 502


async def test_parse_cv_para_onboarding_y_job_match(api):
    response = await api.client.post(
        "/cv-documents/parse",
        files={"file": ("cv.docx", make_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["fullName"] == "Ana Pérez"
    assert response.json()["headline"] == "Desarrolladora Backend"
    assert response.json()["experiences"][0]["role"] == "Desarrolladora backend"
    assert response.json()["experiences"][0]["achievements"] == ["Redujo la latencia en 35%."]
    assert response.json()["additionalSections"]["education"] == ["Ingeniería en Informática · Universidad de Chile"]
    assert response.json()["additionalSections"]["languages"] == ["Español: nativo", "Inglés: avanzado"]
    assert (await api.client.get("/ats/latest")).json()["score"] == 74


async def test_parse_cv_acepta_campos_nulos_que_groq_devuelve_como_desconocidos(api, monkeypatch):
    from tests.conftest import fake_response

    calls = 0

    async def groq_response(system_prompt, user_prompt, model=None, **kwargs):
        nonlocal calls
        calls += 1
        result = fake_response(system_prompt)
        if "Extrae información profesional explícita" in system_prompt:
            result["experiences"][0]["role"] = None
            result["experiences"][0]["company"] = None
            result["experiences"][0]["startDate"] = None
        return result

    monkeypatch.setattr("app.core.ai_router.generate_json", groq_response)
    response = await api.client.post(
        "/cv-documents/parse",
        files={"file": ("cv.docx", make_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 200, response.text
    experience = response.json()["experiences"][0]
    assert experience["role"] == ""
    assert experience["company"] == ""
    assert experience["startDate"] == ""
    assert calls == 2


async def test_ats_ok_y_dashboard(api):
    r = await upload(api, make_docx())
    assert r.status_code == 201 and r.json()["score"] == 74
    d = (await api.client.get("/dashboard/summary")).json()
    assert d["currentAtsScore"] == 74 and d["interviewsLimit"] == 3 and d["interviewsUsed"] == 0


async def test_ats_archivo_danado_es_400(api):
    assert (await upload(api, b"basura", "cv.pdf")).status_code == 400
    assert (await upload(api, b"basura", "cv.docx")).status_code == 400


async def test_ats_formato_invalido_y_tamano(api):
    assert (await upload(api, b"x" * 100, "cv.txt")).status_code == 400
    assert (await upload(api, b"0" * (5 * 1024 * 1024 + 1), "cv.pdf")).status_code == 413


async def test_ats_historial_y_detalle_aislado_por_usuario(api):
    await upload(api, make_docx())
    await upload(api, make_docx())
    hist = (await api.client.get("/ats/history")).json()
    assert len(hist) == 2 and hist[0]["score"] == 74
    assert (await api.client.get(f"/ats/{hist[0]['id']}")).status_code == 200
    api.login("otro@test.cl")
    assert (await api.client.get(f"/ats/{hist[0]['id']}")).status_code == 404
    assert (await api.client.get("/ats/history")).json() == []


async def test_job_match_email_y_entrevista(api):
    await upload(api, make_docx())
    m = await api.client.post("/job-match/analyze", json={"nombre": "Backend Dev", "empresa": "Acme", "ofertaTexto": "Buscamos dev Python con Docker " * 3})
    assert m.status_code == 201, m.text
    jm = m.json()["id"]
    listed = await api.client.get("/job-match")
    assert listed.status_code == 200 and listed.json()[0]["empresa"] == "Acme"
    updated = await api.client.patch(f"/job-match/{jm}/status", json={"status": "Applied"})
    assert updated.status_code == 200 and updated.json()["status"] == "Applied"
    assert (await api.client.get(f"/job-match/{jm}")).json()["status"] == "Applied"
    e = await api.client.post("/email/generate", json={"jobMatchId": jm, "tone": "formal"})
    assert e.status_code == 201, e.text
    assert (await api.client.get(f"/email/{e.json()['id']}")).json()["tone"] == "formal"
    i = await api.client.post(f"/interview/start/{jm}", json={})
    assert i.status_code == 201, i.text
    iid = i.json()["entrevistaId"] if "entrevistaId" in i.json() else i.json()["id"]
    session = await api.client.get(f"/interview/{iid}")
    assert session.status_code == 200 and session.json()["messages"][0]["role"] == "Astro"
    msg = await api.client.post(f"/interview/{iid}/message", json={"contenido": "Usé FastAPI"})
    assert msg.status_code == 200
    fin = await api.client.post(f"/interview/{iid}/finish")
    assert fin.status_code == 200, fin.text
    assert fin.json()["preguntasRespondidas"] == 1


async def test_limite_3_entrevistas_gratis_y_premium_sin_limite(api):
    await upload(api, make_docx())
    jm = (await api.client.post("/job-match/analyze", json={"nombre": "X", "ofertaTexto": "Oferta de trabajo " * 5})).json()["id"]
    for _ in range(3):
        assert (await api.client.post(f"/interview/start/{jm}", json={})).status_code == 201
    r = await api.client.post(f"/interview/start/{jm}", json={})
    assert r.status_code == 402 and "3" in r.json()["detail"]
    # activación manual por admin
    api.login("admin@test.cl", "Admin")
    await api.client.get("/auth/me")
    api.login("user@test.cl")
    api.login("admin@test.cl")
    ok = await api.client.post("/auth/admin/plan", json={"email": "user@test.cl", "plan": "premium"})
    assert ok.status_code == 200 and ok.json()["plan"] == "premium"
    api.login("user@test.cl")
    assert (await api.client.post(f"/interview/start/{jm}", json={})).status_code == 201


async def test_admin_plan_requiere_admin(api):
    r = await api.client.post("/auth/admin/plan", json={"email": "user@test.cl", "plan": "premium"})
    assert r.status_code == 403


async def test_error_502_no_filtra_texto_del_proveedor(api, monkeypatch):
    from app.shared import ai_client

    class Boom:
        class chat:
            class completions:
                @staticmethod
                async def create(**kw):
                    raise RuntimeError("sk-SECRETO invalid api key org-123")

    monkeypatch.setattr("app.core.ai_router.generate_json", ai_client.generate_json)
    monkeypatch.setattr(ai_client, "_get_client", lambda: Boom())
    r = await upload(api, make_docx())
    assert r.status_code == 502
    assert "SECRETO" not in r.text and "org-123" not in r.text


async def test_rate_limit_ia(api, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AI_RATE_LIMIT_PER_HOUR", 2)
    assert (await upload(api, make_docx())).status_code == 201
    assert (await upload(api, make_docx())).status_code == 201
    r = await upload(api, make_docx())
    assert r.status_code == 429 and "límite" in r.json()["detail"]


async def test_sin_token_es_401():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as c:
        assert (await c.get("/auth/me")).status_code in (401, 403)


async def test_ia_con_json_invalido_es_502_no_500(api, monkeypatch):
    await upload(api, make_docx())

    async def bad(system_prompt, user_prompt, model=None, **kwargs):
        return {"cualquier": "cosa"}

    monkeypatch.setattr("app.core.ai_router.generate_json", bad)
    r = await api.client.post("/job-match/analyze", json={"nombre": "X", "ofertaTexto": "Oferta de trabajo " * 5})
    assert r.status_code == 502
