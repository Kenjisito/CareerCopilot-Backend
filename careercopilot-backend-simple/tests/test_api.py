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
    m = await api.client.post("/job-match/analyze", json={"nombre": "Backend Dev", "ofertaTexto": "Buscamos dev Python con Docker " * 3})
    assert m.status_code == 201, m.text
    jm = m.json()["id"]
    e = await api.client.post("/email/generate", json={"jobMatchId": jm, "tone": "formal"})
    assert e.status_code == 201, e.text
    i = await api.client.post(f"/interview/start/{jm}", json={})
    assert i.status_code == 201, i.text
    iid = i.json()["entrevistaId"] if "entrevistaId" in i.json() else i.json()["id"]
    msg = await api.client.post(f"/interview/{iid}/message", json={"contenido": "Usé FastAPI"})
    assert msg.status_code == 200
    assert (await api.client.post(f"/interview/{iid}/finish")).status_code == 204


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

    async def bad(system_prompt, user_prompt, model=None):
        return {"cualquier": "cosa"}

    monkeypatch.setattr("app.core.ai_router.generate_json", bad)
    r = await api.client.post("/job-match/analyze", json={"nombre": "X", "ofertaTexto": "Oferta de trabajo " * 5})
    assert r.status_code == 502
