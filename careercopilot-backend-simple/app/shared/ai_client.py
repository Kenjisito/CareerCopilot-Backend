"""
Único punto de contacto con el proveedor de IA. Ningún módulo llama al
SDK de OpenAI directamente — todos pasan por `generate_json()` — para
que cambiar de proveedor (Anthropic, Gemini, como sugiere el
integrarbackend.txt del repo) implique tocar solo este archivo.
"""
import json
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.shared.errors import upstream_ai_error

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=15.0, max_retries=1)
    return _client


def generate_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Llama al modelo pidiendo EXCLUSIVAMENTE un objeto JSON como
    respuesta (ver los system prompts de cada módulo) y lo parsea.
    Lanza un 502 (upstream_ai_error) si el proveedor falla o devuelve
    algo que no se puede parsear, para que el frontend pueda mostrar
    "reintentar" sin perder el contexto ya ingresado por el usuario."""
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
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
