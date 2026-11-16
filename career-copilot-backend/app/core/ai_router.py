from __future__ import annotations
"""Capa única para seleccionar modelo de IA y validar sus respuestas.

Los módulos llaman a:
- `generate_json_response()` cuando aceptan un dict libre.
- `generate_structured()` cuando necesitan un schema Pydantic: si la IA
  devuelve un JSON con otra forma, se reintenta UNA vez indicándole el
  error; si vuelve a fallar se responde 502 (nunca un 500).
"""
import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.shared.ai_client import generate_json
from app.shared.errors import upstream_ai_error

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


async def generate_json_response(
    system_prompt: str,
    user_prompt: str,
    *,
    premium: bool = False,
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Genera una respuesta usando el modelo configurado para el plan."""
    model = settings.AI_PREMIUM_MODEL if premium else settings.OPENAI_MODEL
    return await generate_json(system_prompt, user_prompt, model=model, temperature=temperature, max_tokens=max_tokens)


async def generate_structured(
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
    *,
    premium: bool = False,
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> T:
    """Genera y valida contra `schema`, con un reintento correctivo."""
    raw = await generate_json_response(system_prompt, user_prompt, premium=premium, temperature=temperature, max_tokens=max_tokens)
    try:
        return schema.model_validate(raw)
    except ValidationError as first_error:
        logger.info("Respuesta de IA no cumple %s, reintentando: %s", schema.__name__, first_error.errors()[:3])
        correction = (
            f"{user_prompt}\n\n"
            "IMPORTANTE: tu respuesta anterior no tenía el formato pedido. "
            "Devuelve SOLO el objeto JSON con exactamente las claves y tipos indicados en las instrucciones."
        )
        raw = await generate_json_response(system_prompt, correction, premium=premium, temperature=0.1, max_tokens=max_tokens)
        try:
            return schema.model_validate(raw)
        except ValidationError as exc:
            logger.error("La IA devolvió un JSON inválido para %s: %s", schema.__name__, exc.errors()[:3])
            raise upstream_ai_error() from exc
