"""Servidor de pruebas LOCAL: imita Supabase Auth (JWKS ES256, login, signup) y una API compatible con OpenAI.
Solo sirve para probar CareerCopilot sin internet ni credenciales reales."""
import json, re, time, uuid, jwt
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
TABLES: dict[str, list[dict]] = {}
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

def _rest_filters(r: Request):
    filters = []
    for column, expression in r.query_params.multi_items():
        if column in {"select", "order", "limit", "on_conflict"}:
            continue
        if "." not in expression:
            continue
        operator, value = expression.split(".", 1)
        if operator == "in":
            values = value.strip("()").split(",") if value.strip("()") else []
            filters.append((operator, column, values))
        else:
            filters.append((operator, column, value))
    return filters

def _rest_matches(row, filters):
    for operator, column, value in filters:
        current = row.get(column)
        if operator == "eq" and str(current) != value:
            return False
        if operator == "in" and str(current) not in value:
            return False
        if operator == "gte" and (current is None or str(current) < value):
            return False
        if operator == "ilike" and str(current).casefold() != value.casefold():
            return False
    return True

def _rest_project(row, columns):
    if columns == "*":
        return dict(row)
    return {column: row[column] for column in columns.split(",") if column in row}

def _rest_page(r: Request, rows):
    result = list(rows)
    order_values = r.query_params.getlist("order")
    for order_value in reversed(order_values):
        for clause in reversed(order_value.split(",")):
            pieces = clause.split(".")
            result.sort(key=lambda row: row.get(pieces[0]) or "", reverse=len(pieces) > 1 and pieces[1] == "desc")
    limit = r.query_params.get("limit")
    if limit is not None:
        result = result[:int(limit)]
    return result

@app.get("/rest/v1/{table}")
async def rest_select(table: str, r: Request):
    rows = [row for row in TABLES.get(table, []) if _rest_matches(row, _rest_filters(r))]
    count = len(rows)
    page = _rest_page(r, rows)
    columns = r.query_params.get("select", "*")
    response = JSONResponse([_rest_project(row, columns) for row in page])
    if "count=exact" in r.headers.get("prefer", ""):
        response.headers["content-range"] = f"*/{count}" if count == 0 else f"0-{count - 1}/{count}"
    return response

@app.post("/rest/v1/{table}")
async def rest_insert(table: str, r: Request):
    payload = await r.json()
    incoming = payload if isinstance(payload, list) else [payload]
    rows = TABLES.setdefault(table, [])
    on_conflict = r.query_params.get("on_conflict")
    ignore_duplicates = "resolution=ignore-duplicates" in r.headers.get("prefer", "")
    result = []
    for item in incoming:
        existing = next((row for row in rows if on_conflict and row.get(on_conflict) == item.get(on_conflict)), None)
        if existing is None:
            rows.append(dict(item))
            result.append(item)
        elif not ignore_duplicates:
            existing.update(item)
            result.append(existing)
    if "return=representation" in r.headers.get("prefer", ""):
        columns = r.query_params.get("select", "*")
        return JSONResponse([_rest_project(row, columns) for row in result], status_code=201)
    return Response(status_code=201)

@app.patch("/rest/v1/{table}")
async def rest_update(table: str, r: Request):
    changes = await r.json()
    matches = [row for row in TABLES.setdefault(table, []) if _rest_matches(row, _rest_filters(r))]
    for row in matches:
        row.update(changes)
    if "return=representation" in r.headers.get("prefer", ""):
        columns = r.query_params.get("select", "*")
        return JSONResponse([_rest_project(row, columns) for row in matches])
    return Response(status_code=204)

@app.delete("/rest/v1/{table}")
async def rest_delete(table: str, r: Request):
    rows = TABLES.setdefault(table, [])
    matches = [row for row in rows if _rest_matches(row, _rest_filters(r))]
    TABLES[table] = [row for row in rows if not _rest_matches(row, _rest_filters(r))]
    if "return=representation" in r.headers.get("prefer", ""):
        columns = r.query_params.get("select", "*")
        return JSONResponse([_rest_project(row, columns) for row in matches])
    return Response(status_code=204)

@app.delete("/auth/v1/admin/users/{user_id}")
def delete_auth_user(user_id: str):
    for email, user in list(USERS.items()):
        if user["id"] == user_id:
            del USERS[email]
            break
    return {}

@app.post("/v1/chat/completions")
async def chat(r: Request):
    """Imita a Groq: responde con la forma de JSON que pide cada prompt."""
    b = await r.json(); system = b["messages"][0]["content"]; user_p = b["messages"][-1]["content"]
    if '"rubrica"' in system:  # Diagnóstico ATS
        out = {"rubrica": {"estructura": 16, "contacto": 8, "experiencia": 20, "habilidades": 14, "legibilidad": 16},
               "detectedRole": "Desarrollador Backend",
               "summary": "CV con buena estructura; faltan métricas y palabras clave técnicas.",
               "sections": {"contactInfo": True, "workExperience": True, "education": True, "skills": True},
               "strengths": ["Estructura clara", "Experiencia relevante listada"],
               "improvements": ["Agregar logros cuantificables", "Incluir enlace a GitHub"],
               "missingKeywords": ["Docker", "CI/CD", "TypeScript"]}
    elif '"es_oferta"' in system:  # extracción de oferta desde una URL
        out = {"es_oferta": True, "nombre": "Analista de Datos", "empresa": "DataCorp",
               "oferta_texto": "Buscamos Analista de Datos con SQL, Python y Power BI. Requisitos: 2 años de experiencia."}
    elif '"score_compatibilidad"' in system:  # Job Match
        out = {"score_compatibilidad": 68, "cumple": ["Python", "FastAPI", "SQL"], "no_cumple": ["Kubernetes", "AWS"],
               "resumen": "Buen encaje con el stack principal; brechas en infraestructura cloud.",
               "recomendaciones": ["Destaca tus APIs con FastAPI y su impacto", "Menciona cualquier experiencia con contenedores"]}
    elif '"puntaje_general"' in system:  # evaluación final de la entrevista
        n = int(re.search(r"\((\d+) preguntas respondidas\)", user_p).group(1)) if re.search(r"\((\d+) preguntas respondidas\)", user_p) else 1
        out = {"puntaje_general": 72, "resumen": "Respondiste con claridad, pero te faltó cuantificar resultados.",
               "preguntas": [{"puntaje": 65 + 5 * (i % 3), "comentario": "Respuesta pertinente, con poco detalle del resultado.",
                              "sugerencia": "Agrega una cifra concreta del impacto logrado."} for i in range(n)],
               "competencias": [{"nombre": c, "puntaje": p} for c, p in (("Comunicación", 78), ("Conocimiento del puesto", 70), ("Ejemplos concretos (STAR)", 60), ("Motivación y encaje", 75))],
               "fortalezas": ["Comunicación clara", "Experiencia práctica con FastAPI"],
               "recomendaciones": ["Estructura tus respuestas con el método STAR", "Cuantifica tus logros", "Prepara ejemplos sobre Kubernetes"]}
    elif '"reaccion"' in system:  # turno del entrevistador
        out = {"reaccion": "Gracias, buen punto.", "pregunta": "Cuéntame sobre un proyecto en el que hayas usado FastAPI y qué resultado obtuviste."}
    else:  # email
        out = {"subject": "Postulación — Desarrollador Backend", "body": "Estimado equipo:\n\nMe gustaría postular al cargo. Mi experiencia con Python y FastAPI se ajusta a lo que buscan.\n\nSaludos,\nPostulante"}
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
