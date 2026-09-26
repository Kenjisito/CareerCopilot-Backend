# CareerCopilot — Backend

> **Estado (20-09-2026):** Brando integró Supabase (Auth + Postgres) y una
> capa de API REST más completa (dashboard, email, historial). Ángel agregó
> soporte para Groq como proveedor de IA gratuito. Ver "Estado actual y
> pendientes reales" más abajo — es importante leerlo antes de probar.

## Stack

| Componente | Tecnología | Por qué |
|---|---|---|
| Framework | FastAPI (async) | Elección original del equipo |
| Base de datos | Postgres vía Supabase (`asyncpg`); cae a SQLite local si no defines `DATABASE_URL` | Migrado por Brando |
| Auth | Supabase Auth — el backend valida el JWT que emite Supabase (`SUPABASE_JWT_SECRET`) | Migrado por Brando |
| IA | OpenAI o **Groq** (gratis), configurable con `AI_PROVIDER` | Groq agregado por Ángel — ver `app/shared/ai_client.py` |

## Estructura (por módulo, no por tipo de archivo)

```
app/
├── main.py                    # arma la app FastAPI, monta routers bajo /api/v1
├── core/
│   ├── config.py               # variables de entorno (incluye AI_PROVIDER / AI_BASE_URL)
│   ├── security.py             # valida el JWT de Supabase
│   ├── supabase.py             # clientes Supabase (anon + service role)
│   ├── ai_router.py            # elige modelo free/premium y llama a ai_client
│   └── monitoring.py           # logging
├── db/
│   ├── session.py               # engine async (Postgres/Supabase o SQLite) + get_db
│   ├── base.py
│   └── models.py                 # todas las tablas
├── modules/
│   ├── auth/        (router, schemas, service)        # /auth/me, /auth/account
│   ├── ats/         (router, schemas, service, extract.py, ocr.py, parsers.py, prompts.py, storage.py)
│   ├── job_match/   (router, schemas, service, prompts.py)
│   ├── interview/   (router, schemas, service, prompts.py)
│   ├── historial/   (router, schemas, service)
│   ├── email/       (router, schemas, service)
│   └── dashboard/   (router, schemas, service)
└── shared/
    ├── ai_client.py          # ÚNICO punto de contacto con el proveedor de IA (OpenAI/Groq)
    ├── dependencies.py       # get_current_user, get_current_user_id, require_plan
    ├── errors.py
    └── exceptions.py
scripts/
└── test_ia.py                # prueba la IA (Groq/OpenAI) sin backend ni Supabase
```

## Endpoints implementados

| Método | Ruta | Requiere auth |
|---|---|---|
| GET | `/api/v1/auth/me` | Sí |
| DELETE | `/api/v1/auth/account` | Sí |
| POST | `/api/v1/ats/analyze` (alias `/ats/process`) | Sí |
| GET | `/api/v1/ats/latest` | Sí |
| POST | `/api/v1/job-match/analyze` (alias `/job-match/create`) | Sí |
| POST | `/api/v1/interview/start`, `/interview/start/{job_match_id}` | Sí |
| POST | `/api/v1/interview/message/{entrevista_id}`, `/interview/{entrevista_id}/message` | Sí |
| POST | `/api/v1/interview/{entrevista_id}/finish` | Sí |
| POST | `/api/v1/email/generate` | Sí |
| PUT | `/api/v1/email/{email_id}` | Sí |
| GET/DELETE | `/api/v1/historial/matches`, `/historial/matches/{match_id}` | Sí |
| GET | `/api/v1/dashboard/summary` | Sí |
| GET | `/health` | No |

(Lista sacada directamente de las rutas registradas por FastAPI en este
repo — corre `python -c "import app.main as m; [print(r.methods, r.path) for r in m.app.routes]"`
si quieres verla actualizada tú mismo.)

**Ya no existen `/auth/register` ni `/auth/login` en este backend** — el
registro y login los maneja directamente Supabase Auth (desde el frontend,
cuando se conecte, o vía la API REST de Supabase mientras tanto).

## Estado actual y pendientes reales (importante antes de probar)

Con el cambio de Brando, **todos** los endpoints (menos `/health`) ahora
exigen un JWT real emitido por Supabase Auth (`get_current_user` en
`shared/dependencies.py` → `core/security.py`, valida contra
`SUPABASE_JWT_SECRET`). Ya no existe la auth "suave" de la versión anterior
(la que nunca daba 401 y usaba un usuario anónimo).

Dos cosas quedan pendientes para que el flujo funcione de punta a punta:

1. **El frontend todavía no habla con Supabase.** `app/(auth)/login/page.tsx`
   y `.../register/page.tsx` siguen simulando el login con `setTimeout` +
   `localStorage` (token falso `"mock_jwt_token_12345"`). Mientras eso no se
   reemplace por el SDK de Supabase (`@supabase/ssr`, como describe la
   arquitectura "ideal" del informe), **todas las llamadas del frontend al
   backend van a devolver 401**, porque el token que mandan no es un JWT
   válido de Supabase. Esto es trabajo pendiente de integración
   frontend↔Supabase, no relacionado con la IA.
2. **No hay sincronización automática entre Supabase Auth y la tabla
   `usuarios`.** `AuthService.get_user_by_id` (en
   `modules/auth/service.py`) devuelve 404 si el `id` del token no existe
   ya en la tabla local — no crea el usuario automáticamente. Falta un
   paso (trigger de Supabase, o un endpoint `POST /auth/sync` llamado tras
   el signup) que inserte la fila en `usuarios` cuando alguien se registra.

**Para probar hoy sin quedar bloqueado por esto**, hay dos caminos
(detallados paso a paso en la guía que te dieron en el chat):

- Probar la integración de IA (Groq) de forma aislada, sin backend ni
  Supabase: `python scripts/test_ia.py`.
- Probar los endpoints reales por Swagger usando un JWT válido obtenido
  directamente de la API de Supabase Auth (no del frontend) y una fila
  creada a mano en `usuarios`.

## Decisión de diseño: proveedor de IA intercambiable

`app/shared/ai_client.py` es el único archivo que llama al SDK de IA.
`AI_PROVIDER` en `.env` decide a qué servidor apunta (`openai` o `groq`,
ambos hablan el mismo protocolo, el de OpenAI); `AI_BASE_URL` permite un
override manual si hiciera falta. Cambiar de proveedor no toca ningún
módulo (`ats`, `job_match`, `interview`, `email`) — todos pasan por
`core/ai_router.py` → `generate_json_response()`.

## Decisión de diseño: sesión de entrevista sin `sessionId`

`hooks/use-interview.ts` solo manda `questionId` + `answer` en cada
respuesta — nunca un `sessionId` explícito. Por eso toda la sesión
(cargo, categoría, cuántas preguntas van, historial de preguntas y
respuestas) vive en la tabla de preguntas de entrevista, indexada por el
mismo id que el frontend ya conoce como `questionId`.

## Cómo correrlo

```bash
python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # completa tus credenciales reales (ver abajo)
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva en `http://localhost:8000/docs`.

### Variables mínimas para levantar el servidor

- `OPENAI_API_KEY` (tu key de Groq u OpenAI) y `AI_PROVIDER` — para que la IA
  funcione.
- `SUPABASE_JWT_SECRET` — **obligatorio incluso para probar sin Supabase
  real**, porque `core/security.py` lo exige al decodificar cualquier
  token (lanza 500 si está vacío). Si aún no tienes un proyecto Supabase,
  pon cualquier valor de relleno en desarrollo; simplemente no vas a poder
  generar un JWT válido para pasar la auth sin un proyecto real.
- `DATABASE_URL` — si la dejas vacía, usa SQLite local (cero configuración).

## Pendientes (decisiones que faltan, no solo código)

1. **Conectar el login/registro real del frontend a Supabase Auth.** Hoy
   siguen mockeados con `setTimeout`. Hay que reemplazar eso por el SDK de
   Supabase (`@supabase/ssr`) en `app/(auth)/login/page.tsx` y
   `.../register/page.tsx`.
2. **Sincronizar Supabase Auth con la tabla `usuarios`** (ver arriba) —
   sin esto, un usuario que se registra vía Supabase nunca podrá usar
   ningún endpoint (siempre 404).
3. **Historial** y **Email**: revisar si `modules/historial` y
   `modules/email` (ya implementados por Brando) calzan con lo que
   esperan `app/(dashboard)/historial/page.tsx` y `.../email/page.tsx`,
   que últimamente seguían con datos hardcodeados en el frontend.
4. **Probar la IA con una key real de Groq** — no se pudo verificar en
   este entorno de desarrollo (sandbox sin salida de red hacia
   `api.groq.com`). El código importa sin errores y la estructura de la
   llamada es la misma que ya se usaba con OpenAI (solo cambia la
   `base_url`), pero falta la prueba real con una `OPENAI_API_KEY` de
   Groq — ver `scripts/test_ia.py` y la guía de pruebas.
