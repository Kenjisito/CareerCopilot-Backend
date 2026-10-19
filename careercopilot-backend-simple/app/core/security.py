
from __future__ import annotations

import asyncio
import logging
import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient, PyJWKClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer()

# URL e issuer oficiales de Supabase Auth para este proyecto.
SUPABASE_URL = (
    settings.SUPABASE_URL.rstrip("/")
    if settings.SUPABASE_URL
    else None
)

SUPABASE_ISSUER = (
    f"{SUPABASE_URL}/auth/v1"
    if SUPABASE_URL
    else None
)

JWKS_URL = (
    f"{SUPABASE_ISSUER}/.well-known/jwks.json"
    if SUPABASE_ISSUER
    else None
)

jwks_client = (
    PyJWKClient(JWKS_URL, timeout=5)
    if JWKS_URL
    else None
)


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """Verifica un access token de Supabase Auth mediante su clave pública."""

    if not jwks_client or not SUPABASE_ISSUER:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La configuración de autenticación de Supabase está incompleta.",
        )

    token = credentials.credentials

    try:
        # Obtiene la clave pública correspondiente al kid del JWT.
        signing_key = await asyncio.to_thread(
            jwks_client.get_signing_key_from_jwt,
            token,
        )

        # Se permite exclusivamente ES256 y se validan los claims esenciales.
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=SUPABASE_ISSUER,
            options={
                "require": ["exp", "iss", "sub", "aud"],
            },
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de acceso ha expirado. Inicia sesión nuevamente.",
        )

    except PyJWKClientError:
        # Si no se pueden consultar las claves, no aceptar el token
        # ni confundir el fallo de red con una credencial inválida.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudieron consultar las claves de autenticación.",
        )

    except jwt.PyJWTError as exc:
        logger.warning(
            "JWT rechazado: %s - %s",
            type(exc).__name__,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido.",
        )
