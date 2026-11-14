from __future__ import annotations
"""
Único punto de contacto con el proveedor de IA. Ningún módulo llama al
SDK de OpenAI directamente — todos pasan por `generate_json()` (vía
`app/core/ai_router.py`) — para que cambiar de proveedor implique tocar
solo este archivo.

Groq expone una API compatible con el SDK de OpenAI (mismo formato de
`chat.completions.create`), así que para usar Groq basta con apuntar el
cliente de OpenAI a la `base_url` de Groq. Esto se resuelve según
`AI_PROVIDER` (ver `core/config.py`):

- AI_PROVIDER=groq    -> https://api.groq.com/openai/v1 (recomendado: openai/gpt-oss-120b)
- AI_PROVIDER=openai  -> servidores de OpenAI

`OPENAI_API_KEY` es la key del proveedor elegido (`gsk_...` de Groq o
`sk-...` de OpenAI). `AI_BASE_URL`, si se define, tiene prioridad.

Particularidades de Groq que este archivo maneja:
- El modo JSON (`response_format=json_object`) exige que el prompt mencione
  "JSON"; si el modelo genera JSON inválido, Groq responde 400
  `json_validate_failed` → se reintenta una vez.
- El plan gratuito limita tokens por minuto y `max_tokens` cuenta para ese
  límite, por eso cada llamada pide solo los tokens que necesita.
- Los modelos gpt-oss razonan antes de responder y ese razonamiento consume
  `max_tokens`: se les envía `reasoning_effort` (AI_REASONING_EFFORT, "low").
- 429 (límite de uso) → el SDK ya reintenta respetando `retry-after`; si
  aun así falla se devuelve un 503 con un mensaje claro.
"""
import json
import logging
import re
from typing import Any

from fastapi import HTTPException, status
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from app.core.config import settings
from app.shared.errors import upstream_ai_error

logger = logging.getLogger(__name__)
_client: AsyncOpenAI | None = None

# Proveedores compatibles con el SDK de OpenAI (mismo formato de request/response).
_PROVIDER_BASE_URLS: dict[str, str | None] = {
    "openai": None,  # None = usa el default del SDK (api.openai.com)
    "groq": "https://api.groq.com/openai/v1",
}

# Intentos ante una respuesta que no es JSON válido (además del primero).
_JSON_RETRIES = 1


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
            timeout=settings.AI_TIMEOUT_SECONDS,
            # Ante un 429 el SDK espera lo que indica Groq (retry-after) y reintenta.
            max_retries=3,
        )
    return _client


def _parse_json(content: str) -> dict[str, Any]:
    """Parsea la respuesta del modelo. Tolera bloques ```json ... ``` y texto
    alrededor del objeto (algunos modelos los agregan aun en modo JSON)."""
    text = content.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("La respuesta del modelo no es un objeto JSON")
    return data


def _extra_body(model: str) -> dict[str, Any] | None:
    effort = settings.AI_REASONING_EFFORT.strip().lower()
    if effort and "gpt-oss" in model:
        return {"reasoning_effort": effort}
    return None


def _service_unavailable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


async def generate_json(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    *,
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Llama al modelo pidiendo EXCLUSIVAMENTE un objeto JSON y lo parsea.

    Errores (el detalle real queda solo en el log del servidor; al usuario no
    se le expone texto del proveedor):
    - 503 si la IA no está configurada o se agotó el límite de uso de Groq.
    - 504 si el proveedor tarda demasiado.
    - 502 para cualquier otra falla o si la respuesta no es JSON válido.
    """
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY vacío: configura la key de Groq/OpenAI en el .env del backend")
        raise _service_unavailable("El servicio de IA no está configurado en el servidor.")

    client = _get_client()
    used_model = model or settings.OPENAI_MODEL
    last_error: Exception | None = None

    for attempt in range(_JSON_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=used_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=_extra_body(used_model),
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Respuesta vacía del modelo")
            return _parse_json(content)
        except RateLimitError as exc:
            logger.warning("Límite de uso del proveedor de IA alcanzado (%s): %s", used_model, exc)
            raise _service_unavailable(
                "La IA alcanzó su límite de uso por minuto. Espera unos segundos e inténtalo de nuevo."
            ) from exc
        except APITimeoutError as exc:
            logger.warning("Timeout del proveedor de IA (%s)", used_model)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="La IA tardó demasiado en responder. Inténtalo de nuevo.",
            ) from exc
        except (AuthenticationError, PermissionDeniedError) as exc:
            logger.error("La key de IA fue rechazada por el proveedor (%s): %s", settings.AI_PROVIDER, exc)
            raise upstream_ai_error("El servicio de IA no está disponible (credenciales inválidas en el servidor).") from exc
        except NotFoundError as exc:
            logger.error("Modelo de IA no encontrado: %s — revisa OPENAI_MODEL/AI_PREMIUM_MODEL. %s", used_model, exc)
            raise upstream_ai_error() from exc
        except BadRequestError as exc:
            # Groq: `json_validate_failed` cuando el modelo produce JSON inválido → reintentar.
            if "json_validate_failed" in str(exc) and attempt < _JSON_RETRIES:
                logger.info("Groq devolvió JSON inválido, reintentando (%s)", used_model)
                last_error = exc
                continue
            logger.error("Solicitud rechazada por el proveedor de IA (%s): %s", used_model, exc)
            raise upstream_ai_error() from exc
        except APIConnectionError as exc:
            logger.error("No se pudo conectar con el proveedor de IA: %s", exc)
            raise upstream_ai_error() from exc
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt < _JSON_RETRIES:
                logger.info("Respuesta de IA no parseable, reintentando (%s)", used_model)
                last_error = exc
                continue
            logger.error("La IA devolvió una respuesta que no es JSON válido: %s", exc)
            raise upstream_ai_error() from exc
        except Exception as exc:  # noqa: BLE001 — cualquier otra falla del proveedor se traduce a 502
            logger.exception("Falla inesperada del proveedor de IA")
            raise upstream_ai_error() from exc

    logger.error("La IA no devolvió JSON válido tras reintentar: %s", last_error)
    raise upstream_ai_error()
