"""
Único punto de contacto con el proveedor de IA. Ningún módulo llama al
SDK de OpenAI directamente — todos pasan por `generate_json()` — para
que cambiar de proveedor implique tocar solo este archivo.

Groq expone una API compatible con el SDK de OpenAI (mismo formato de
`chat.completions.create`), así que para usar Groq basta con apuntar el
cliente de OpenAI a la `base_url` de Groq en vez de la de OpenAI. Esto se
resuelve automáticamente según `AI_PROVIDER` (ver `core/config.py`):

- AI_PROVIDER=openai  -> usa los servidores de OpenAI (comportamiento default)
- AI_PROVIDER=groq    -> usa https://api.groq.com/openai/v1 (gratis, con límites)

En ambos casos `OPENAI_API_KEY` es la key del proveedor elegido (una
`sk-...` de OpenAI o una `gsk_...` de Groq) y `OPENAI_MODEL` /
`AI_PREMIUM_MODEL` deben ser nombres de modelo válidos para ese proveedor.
`AI_BASE_URL`, si se define explícitamente, tiene prioridad sobre el mapeo
por proveedor (útil para un proxy propio o un proveedor nuevo sin tocar código).
"""
import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.shared.errors import upstream_ai_error

_client: AsyncOpenAI | None = None

# Proveedores compatibles con el SDK de OpenAI (mismo formato de request/response).
_PROVIDER_BASE_URLS: dict[str, str | None] = {
    "openai": None,  # None = usa el default del SDK (api.openai.com)
    "groq": "https://api.groq.com/openai/v1",
}


def _resolve_base_url() -> str | None:
    if settings.AI_BASE_URL:
        return settings.AI_BASE_URL
    return _PROVIDER_BASE_URLS.get(settings.AI_PROVIDER.strip().lower())


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=_resolve_base_url(),
            timeout=30.0,
            max_retries=1,
        )
    return _client


async def generate_json(system_prompt: str, user_prompt: str, model: str | None = None) -> dict[str, Any]:
    """Llama al modelo pidiendo EXCLUSIVAMENTE un objeto JSON como
    respuesta (ver los system prompts de cada módulo) y lo parsea.
    Lanza un 502 (upstream_ai_error) si el proveedor falla o devuelve
    algo que no se puede parsear, para que el frontend pueda mostrar
    "reintentar" sin perder el contexto ya ingresado por el usuario."""
    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=model or settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Respuesta vacía del modelo")
        return json.loads(content)
    except Exception as exc:  # noqa: BLE001 — cualquier falla del proveedor se traduce a 502
        raise upstream_ai_error(f"Error al generar contenido con IA: {exc}") from exc
