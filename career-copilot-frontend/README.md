# Career Copilot

Frontend React + TypeScript + Vite conectado al backend FastAPI y a Supabase Auth.

## Configuración

Requiere Node.js 22.12+ y npm. Copia `.env.example` a `.env.development` y
configura:

```dotenv
VITE_API_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=https://TU-PROYECTO.supabase.co
VITE_SUPABASE_ANON_KEY=tu-anon-key-publica
```

La clave anon es pública y se usa para autenticar en Supabase Auth. No pongas
claves de IA ni `SUPABASE_SERVICE_ROLE_KEY` en variables `VITE_*`.
El botón de Gmail abre la ventana de redacción con el destinatario, asunto y
cuerpo precargados; el usuario revisa el borrador y confirma el envío desde Gmail.

Inicia primero el backend (`CareerCopilot-Backend/careercopilot-backend-simple`)
y luego el frontend:

```bash
npm ci
npm run dev
```

Vite muestra `http://localhost:5173`. El backend acepta ese origen por CORS de
forma predeterminada. El frontend llama directamente a la API en
`/api/v1`; no hay proxy ni acceso directo a la base de datos desde el navegador.

## Integración

- Registro, inicio y cierre de sesión usan Supabase Auth; el SDK renueva los
  tokens y el frontend envía el access token JWT al backend.
- El backend crea el registro local del usuario al recibir su primer JWT.
- Perfil, análisis ATS, Job Match, seguimiento de postulaciones, entrevistas y
  cartas usan endpoints FastAPI autenticados.
- En Mi CV ATS puedes editar el documento y revisar, aceptar, denegar o adaptar
  las mejoras de Astro antes de guardarlas. Las cartas se revelan progresivamente
  y el entrenador muestra cuándo Astro está escribiendo.
- El onboarding guarda el borrador en `sessionStorage` y persiste el perfil
  al confirmar.

## Comandos

```bash
npm run dev
npm run build
npm run lint
npm test
npm run preview
```
