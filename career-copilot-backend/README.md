# Career Copilot API

Backend FastAPI que sirve a `career-copilot-frontend`. La API usa `/api/v1`,
JWT de Supabase Auth y el Data API de Supabase mediante `supabase-py`.

## Inicio local

1. Crea el archivo local de configuración y activa un entorno Python 3.12:

   ```powershell
   Copy-Item .env.example .env
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   ```

2. En `.env`, configura `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y
   `OPENAI_API_KEY` (Groq u OpenAI, según `AI_PROVIDER`). La clave de servicio
   solo se usa en el backend. `SUPABASE_URL` también permite validar los JWT
   mediante el endpoint JWKS de Supabase.
3. Ejecuta [`supabase/migrations/001_setup.sql`](./supabase/migrations/001_setup.sql)
   en el SQL Editor de Supabase para añadir `emails_generados.tone` y habilitar
   RLS en las tablas usadas por la API.
4. Inicia el servidor:

   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```

   Swagger queda disponible en `http://localhost:8000/docs`; salud en
   `http://localhost:8000/health`.

El frontend debe tener `VITE_API_URL=http://localhost:8000/api/v1`,
`VITE_SUPABASE_URL` y `VITE_SUPABASE_ANON_KEY`. Las variables del navegador
solo llevan la clave anon pública; nunca expongas `SUPABASE_SERVICE_ROLE_KEY`
ni una clave de IA en el frontend.

## Contrato usado por el frontend

Todos los endpoints salvo `/health` requieren `Authorization: Bearer <JWT de Supabase>`.
El primer endpoint autenticado crea automáticamente la fila local del usuario.

| Método | Ruta | Uso |
|---|---|---|
| GET/PATCH | `/api/v1/auth/me` | Identidad y nombre de usuario |
| GET/PUT | `/api/v1/profile` | Cargar y guardar perfil profesional |
| POST | `/api/v1/cv-documents/parse` | Extraer perfil y ejecutar diagnóstico ATS desde PDF/DOCX |
| POST/GET | `/api/v1/job-match/analyze`, `/api/v1/job-match` | Analizar oferta y listar resultados |
| GET/PATCH | `/api/v1/job-match/{id}`, `/api/v1/job-match/{id}/status` | Ver análisis y actualizar estado |
| POST/GET | `/api/v1/interview/start`, `/api/v1/interview/{id}` | Iniciar y cargar una entrevista |
| POST | `/api/v1/interview/{id}/message`, `/api/v1/interview/{id}/finish` | Conversar y evaluar |
| POST/GET | `/api/v1/email/generate`, `/api/v1/email/{id}` | Generar y volver a cargar una carta |
| POST/GET | `/api/v1/ats/analyze`, `/api/v1/ats/latest` | Diagnóstico ATS |
| GET | `/api/v1/dashboard/summary` | Métricas del dashboard |

El Job Match necesita un CV procesado previamente. La entrevista requiere una
oferta analizada. El historial y los estados de postulación se guardan por usuario.

## Extracción de CV

La extracción lee párrafos y tablas del cuerpo, encabezados y pies de DOCX, y
elige el mejor orden de lectura disponible por página en PDF. En páginas PDF sin
texto seleccionable aplica OCR en español e inglés. El análisis reconoce títulos
y sinónimos de secciones en ambos idiomas, agrupa su contenido y procesa perfiles
largos en fragmentos acotados para no omitir el final del documento.
El perfil guarda el cargo profesional por separado de la experiencia laboral, y
mantiene educación, cursos, proyectos, idiomas, logros, voluntariado, publicaciones,
intereses y referencias en campos independientes que se pueden revisar antes de guardar
y que aparecen en la vista del CV. Cada experiencia separa cargo, empresa/institución,
fechas, funciones, logros y tipo (profesional, académica, práctica, voluntariado o
freelance); si faltan datos, conserva también el texto original. Las secciones que no
coinciden con el catálogo se guardan en "Otra información" para no descartarlas.

El endpoint admite archivos de hasta 5 MB; el parseo de perfil procesa hasta
45.000 caracteres y el OCR hasta 20 páginas escaneadas por solicitud. En
instalaciones locales, el OCR requiere Tesseract con los modelos de español e
inglés instalados y disponible en `PATH`. La imagen Docker instala Tesseract y el
modelo de español automáticamente.

## Docker Compose

Desde esta carpeta, copia `.env.example` a `.env`, completa las variables
anteriores y ejecuta:

```powershell
docker compose up --build
```

Frontend: `http://localhost:5173`; API: `http://localhost:8000/docs`.
Compose conecta la API al Data API de Supabase por HTTPS.

## Pruebas

```powershell
py -3.12 -m pytest
```
