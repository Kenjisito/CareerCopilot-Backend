# Pruebas E2E (navegador real, sin servicios externos)

Recorren la página completa con Playwright contra un backend y un frontend locales.
`mock_services.py` imita Supabase Auth (registro, login, recuperación de contraseña, JWKS ES256)
y una API compatible con OpenAI, así que **no se gasta cuota ni se necesitan claves**.

## Cómo correrlas
```bash
pip install -r requirements-dev.txt playwright && playwright install chromium

# 1) Servicios de prueba (puerto 9000)
python tests/e2e/mock_services.py &

# 2) Backend apuntando al mock
SUPABASE_URL=http://127.0.0.1:9000 AI_BASE_URL=http://127.0.0.1:9000/v1 OPENAI_API_KEY=test \
OPENAI_MODEL=m AI_PREMIUM_MODEL=m DATABASE_URL=sqlite+aiosqlite:///./e2e.db \
uvicorn app.main:app --port 8000 &

# 3) Frontend (en su repo) con .env.local:
#    NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
#    NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:9000
#    NEXT_PUBLIC_SUPABASE_ANON_KEY=test-anon-key
npm run build && npx next start -p 3000

# 4) Recorridos (escritorio y móvil)
python tests/e2e/e2e_flujo_completo.py ; python tests/e2e/e2e_flujo_completo.py mobile
python tests/e2e/e2e_cuenta_y_extras.py ; python tests/e2e/e2e_cuenta_y_extras.py mobile
```
Las capturas se guardan en `./shots/`. Si Chromium no se detecta solo, define `CHROMIUM_PATH`.

Para pruebas unitarias/de API (sin navegador): `pytest`.
