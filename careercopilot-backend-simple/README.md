# CareerCopilot — Backend (adaptado al frontend existente)

Este backend está construido para calzar **exactamente** con el código real
que ya existe en el repo `CareerCopilot-Frontend` — no con la documentación
de arquitectura "ideal" (OpenAPI/Supabase/pgvector) que el equipo había
diseñado antes de que se escribiera el frontend. Ver la sección
"Por qué esta arquitectura y no la otra" más abajo.

## Stack

| Componente | Tecnología | Por qué |
|---|---|---|
| Framework | FastAPI | Ya era la elección del equipo, se mantiene |
| Base de datos | SQLite (archivo local) | El frontend no requiere Postgres/Supabase; cero configuración |
| Auth | JWT propio (PyJWT + passlib/bcrypt) | El frontend guarda un Bearer token en `localStorage`, no usa el SDK de Supabase |
| IA | OpenAI (configurable) | Mismo enfoque sugerido en `integrarbackend.txt` del repo del frontend |

## Estructura (por módulo, no por tipo de archivo)

```
app/
├── main.py                  # arma la app FastAPI, monta routers bajo /api/v1
├── core/
│   ├── config.py             # variables de entorno
│   └── security.py           # JWT, hashing, get_current_user (ver nota abajo)
├── db/
│   ├── session.py             # engine SQLite + dependency get_db
│   └── models.py              # todas las tablas
├── modules/
│   ├── auth/        (router, schemas, service)
│   ├── ats/         (router, schemas, service, extract.py, prompts.py)
│   ├── job_match/   (router, schemas, service, prompts.py)
│   ├── interview/   (router, schemas, service, prompts.py)
│   ├── historial/   (carpeta reservada — ver pendientes)
│   └── email/       (carpeta reservada — ver pendientes)
└── shared/
    ├── ai_client.py          # único punto de contacto con OpenAI
    └── errors.py
```

## Endpoints implementados (calzan exactamente con `services/*.ts`)

| Método | Ruta | Coincide con |
|---|---|---|
| POST | `/api/v1/auth/register` | `types/user.ts` — no conectado aún en el frontend (ver pendientes) |
| POST | `/api/v1/auth/login` | `types/user.ts` — no conectado aún en el frontend |
| POST | `/api/v1/ats/analyze` | `services/ats-service.ts` |
| GET | `/api/v1/ats/latest` | `services/ats-service.ts` |
| POST | `/api/v1/job-match/analyze` | `services/job-match-service.ts` |
| POST | `/api/v1/interview/start` | `services/interview-service.ts` |
| POST | `/api/v1/interview/answer` | `services/interview-service.ts` |

## Decisión de diseño importante: auth "suave"

El login/register del frontend **hoy están mockeados** (`setTimeout` +
`localStorage`, ver `app/(auth)/login/page.tsx`), así que si conectaras
ATS/Job Match/Entrevista tal cual están ahora, mandarían un Bearer token
falso (`"mock_jwt_token_12345"`).

Por eso `get_current_user_id` (en `core/security.py`) nunca lanza 401: si
el token es inválido o no existe, usa un usuario anónimo (`"anonymous"`).
Esto permite que el backend funcione HOY con el frontend tal cual está,
y que además ya quede listo el sistema de auth real: apenas alguien
reemplace el mock del login/register por una llamada real a
`/api/v1/auth/login`, todo lo demás (ATS, Job Match, Entrevista) empieza
a asociarse al usuario real sin tocar una línea más de código.

## Decisión de diseño: sesión de entrevista sin `sessionId`

`hooks/use-interview.ts` solo manda `questionId` + `answer` en cada
respuesta — nunca un `sessionId` explícito. Por eso toda la sesión
(cargo, categoría, cuántas preguntas van, historial de preguntas y
respuestas) vive en la tabla `interview_questions`, indexada por el
mismo id que el frontend ya conoce como `questionId`.

## Cómo correrlo

```bash
python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # completa tu OPENAI_API_KEY real
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva en `http://localhost:8000/docs`.

El frontend, corriendo en paralelo con `npm run dev` (puerto 3000), ya
apunta a `http://localhost:8000/api/v1` por defecto — no requiere ningún
cambio de configuración para hablar con este backend.

## Pendientes (decisiones que faltan, no solo código)

1. **Conectar el login/register real del frontend.** Hoy siguen
   mockeados. Hay que reemplazar el `setTimeout` en
   `app/(auth)/login/page.tsx` y `.../register/page.tsx` por un fetch
   real a `/api/v1/auth/login` y `/api/v1/auth/register` (que ya existen
   y funcionan).

2. **Historial** (`app/(dashboard)/historial/page.tsx`) también está
   100% mockeado con datos hardcodeados en `useState`. No existe
   `historial-service.ts`. Antes de construir el backend de este módulo
   hay que decidir: ¿lista solo diagnósticos ATS guardados, o también
   Job Matches? ¿Se guarda automáticamente cada análisis, o el usuario
   elige qué guardar (como planteaba el `OpenAPI` original)?

3. **Email** (`app/(dashboard)/email/page.tsx`) muestra un borrador
   **estático hardcodeado** — ni siquiera usa el `historyId` que recibe
   por la URL. Existe `types/email.ts` con un contrato (tono, tipo,
   destinatario) pero ninguna página ni hook lo usa todavía. Hay que
   decidir cuál de los dos diseños seguir antes de construir el backend
   de este módulo.

4. **No se pudo probar la llamada real a OpenAI en este entorno de
   desarrollo** (sandbox sin salida de red hacia `api.openai.com`). Sí
   se verificó que: la app importa sin errores, todas las rutas
   registran correctamente, auth funciona end-to-end (probado con
   `curl`), y el manejo de errores de IA devuelve un 502 limpio en vez
   de un crash. Falta que alguien con acceso a internet normal la
   pruebe con una `OPENAI_API_KEY` real.
