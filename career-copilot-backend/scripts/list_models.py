"""
Lista los modelos a los que tu API key (Groq u OpenAI, segun AI_PROVIDER)
tiene acceso realmente. Util cuando un modelo te da 404 "model_not_found"
y no sabes cual usar en su lugar.

Uso:
    python scripts/list_models.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.shared.ai_client import _resolve_base_url  # noqa: E402


def main() -> None:
    if not settings.OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY está vacío en tu .env.")
        return

    base_url = _resolve_base_url()
    print(f"Proveedor : {settings.AI_PROVIDER}")
    print(f"Base URL  : {base_url or '(default del SDK — api.openai.com)'}")
    print("-" * 60)

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=base_url)
    try:
        models = client.models.list()
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo listar modelos: {exc}")
        return

    ids = sorted(m.id for m in models.data)
    if not ids:
        print("Tu cuenta no tiene ningún modelo habilitado (revisa el dashboard).")
        return

    print(f"Tu API key tiene acceso a {len(ids)} modelo(s):")
    for model_id in ids:
        print(f"  - {model_id}")


if __name__ == "__main__":
    main()
