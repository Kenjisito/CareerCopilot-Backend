"""Servidor de pruebas LOCAL: imita Supabase Auth (JWKS ES256, login, signup) y una API compatible con OpenAI.
Solo sirve para probar CareerCopilot sin internet ni credenciales reales."""
import json, time, uuid, jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

PORT = 9000
BASE = f"http://127.0.0.1:{PORT}"
key = ec.generate_private_key(ec.SECP256R1())
jwk = json.loads(ECAlgorithm.to_jwk(key.public_key())); jwk.update(kid="test-key", alg="ES256", use="sig")
USERS: dict[str, dict] = {}
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def session_for(u):
    now = int(time.time())
    tok = jwt.encode({"iss": f"{BASE}/auth/v1", "sub": u["id"], "aud": "authenticated", "exp": now + 3600, "iat": now,
                      "email": u["email"], "role": "authenticated", "user_metadata": u["user_metadata"]},
                     key, algorithm="ES256", headers={"kid": "test-key"})
    return {"access_token": tok, "token_type": "bearer", "expires_in": 3600, "expires_at": now + 3600,
            "refresh_token": "r-" + u["id"], "user": u_public(u)}

def u_public(u):
    return {"id": u["id"], "aud": "authenticated", "role": "authenticated", "email": u["email"],
            "user_metadata": u["user_metadata"], "app_metadata": {}, "created_at": "2026-10-19T00:00:00Z"}

@app.get("/auth/v1/.well-known/jwks.json")
def jwks(): return {"keys": [jwk]}

@app.post("/auth/v1/signup")
async def signup(r: Request):
    b = await r.json(); email = b["email"].lower()
    if email in USERS: return JSONResponse({"code": 422, "error_code": "user_already_exists", "msg": "User already registered"}, 422)
    if len(b.get("password", "")) < 6: return JSONResponse({"code": 422, "error_code": "weak_password", "msg": "Password should be at least 6 characters."}, 422)
    u = {"id": str(uuid.uuid4()), "email": email, "password": b["password"], "user_metadata": b.get("data") or {}}
    USERS[email] = u; return session_for(u)

@app.post("/auth/v1/token")
async def token(r: Request):
    b = await r.json(); u = USERS.get(b.get("email", "").lower())
    if not u or u["password"] != b.get("password"):
        return JSONResponse({"code": 400, "error_code": "invalid_credentials", "msg": "Invalid login credentials"}, 400)
    return session_for(u)

@app.get("/auth/v1/user")
def user(): return {}

@app.post("/auth/v1/logout")
def logout(): return Response(status_code=204)

@app.post("/v1/chat/completions")
async def chat(r: Request):
    b = await r.json(); system = b["messages"][0]["content"]; user_p = b["messages"][-1]["content"]
    if "ATS" in system:
        out = {"score": 74, "summary": "CV con buena estructura; faltan métricas y palabras clave técnicas.",
               "sections": {"contactInfo": True, "workExperience": True, "education": True, "skills": True},
               "strengths": ["Estructura clara", "Experiencia relevante listada"],
               "improvements": ["Agregar logros cuantificables", "Incluir enlace a GitHub"],
               "missingKeywords": ["Docker", "CI/CD", "TypeScript"]}
    elif "compatib" in system.lower() or "Job Match" in system or "score_compatibilidad" in system:
        out = {"score_compatibilidad": 68, "cumple": ["Python", "FastAPI", "SQL"], "no_cumple": ["Kubernetes", "AWS"],
               "resumen": "Buen encaje con el stack principal; brechas en infraestructura cloud."}
    elif "email" in user_p.lower() or "correo" in user_p.lower():
        out = {"subject": "Postulación — Desarrollador Backend", "body": "Estimado equipo:\n\nMe gustaría postular al cargo. Mi experiencia con Python y FastAPI se ajusta a lo que buscan.\n\nSaludos,\nPostulante"}
    else:
        out = {"respuesta": "Cuéntame sobre un proyecto en el que hayas usado FastAPI y qué resultado obtuviste."}
    return {"id": "x", "object": "chat.completion", "created": int(time.time()), "model": b.get("model", "m"),
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(out)}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}


# --- recuperación de contraseña (solo pruebas) ---
RECOVERIES: list[str] = []

@app.post("/auth/v1/recover")
async def recover(r: Request):
    b = await r.json(); RECOVERIES.append(b.get("email", "").lower()); return {}

@app.get("/__recoveries")
def recoveries(): return RECOVERIES

def _user_from_bearer(r: Request):
    tok = r.headers.get("authorization", "").split(" ")[-1]
    try: sub = jwt.decode(tok, key.public_key(), algorithms=["ES256"], audience="authenticated")["sub"]
    except Exception: return None
    return next((u for u in USERS.values() if u["id"] == sub), None)

@app.get("/auth/v1/user")
def get_user(r: Request):
    u = _user_from_bearer(r)
    return u_public(u) if u else JSONResponse({"code": 401, "msg": "invalid JWT"}, 401)

@app.put("/auth/v1/user")
async def put_user(r: Request):
    u = _user_from_bearer(r)
    if not u: return JSONResponse({"code": 401, "msg": "invalid JWT"}, 401)
    b = await r.json()
    if b.get("password") == u["password"]:
        return JSONResponse({"code": 422, "error_code": "same_password", "msg": "New password should be different from the old password."}, 422)
    if b.get("password"): u["password"] = b["password"]
    if b.get("data"): u["user_metadata"].update(b["data"])
    return u_public(u)

@app.get("/__token")
def mk_token(email: str):
    return session_for(USERS[email.lower()])

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
