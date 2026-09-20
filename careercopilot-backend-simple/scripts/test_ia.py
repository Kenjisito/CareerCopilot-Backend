"""
Prueba aislada de la integración de IA (Groq u OpenAI), SIN necesidad de
levantar el servidor, sin base de datos y sin tocar Supabase/JWT.

Sirve para confirmar que AI_PROVIDER / OPENAI_API_KEY / OPENAI_MODEL en tu
.env están bien configurados antes de probar los endpoints reales.

Uso:
    cd careercopilot-backend-simple
    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
    pip install -r requirements.txt
    cp .env.example .env   # y completa OPENAI_API_KEY con tu key de Groq
    python scripts/test_ia.py
"""
import asyncio
import sys
from pathlib import Path

# Permite correr el script desde la raíz del proyecto sin instalarlo como paquete.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.shared.ai_client import generate_json  # noqa: E402


async def main() -> None:
    print(f"Proveedor configurado : {settings.AI_PROVIDER}")
    print(f"Modelo configurado    : {settings.OPENAI_MODEL}")
    print(f"API key presente      : {'sí' if settings.OPENAI_API_KEY else 'NO (falta en .env)'}")
    print("-" * 60)

    if not settings.OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY está vacío en tu .env. Complétalo y vuelve a intentar.")
        return

    system_prompt = "Respondes únicamente con un objeto JSON."
    user_prompt = (
        'Devuelve exactamente este JSON, sin texto adicional: '
        '{"ok": true, "mensaje": "Groq respondiendo correctamente"}'
    )

    try:
        result = await generate_json(system_prompt, user_prompt)
        print("Respuesta del modelo:")
        print(result)
        print("-" * 60)
        print("ÉXITO: la integración de IA está funcionando.")
    except Exception as exc:  # noqa: BLE001 — queremos ver cualquier error tal cual
        print("FALLÓ la llamada a la IA:")
        print(exc)
        print("-" * 60)
        print("Revisa: la API key es válida, el modelo existe para ese proveedor,")
        print("y no hay typos en AI_PROVIDER (debe ser 'groq' u 'openai').")


if __name__ == "__main__":
    asyncio.run(main())
