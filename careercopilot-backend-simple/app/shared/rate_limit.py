from __future__ import annotations
"""Límite de uso de la IA por usuario (ventana deslizante de 1 hora).

Vive en memoria del proceso: sirve para proteger la cuota del proveedor con
una sola instancia del backend. Si se escala a varias instancias hay que
moverlo a Redis (misma interfaz)."""
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.core.config import settings
from app.db.models import UsuarioModel
from app.shared.dependencies import get_current_user

WINDOW_SECONDS = 3600
_hits: dict[str, deque[float]] = defaultdict(deque)


def _check(user_id: str, limit: int) -> None:
    now = time.monotonic()
    hits = _hits[user_id]
    while hits and now - hits[0] > WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= limit:
        minutes = max(1, int((WINDOW_SECONDS - (now - hits[0])) // 60) + 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Alcanzaste el límite de uso de la IA por hora. Intenta de nuevo en unos {minutes} minutos.",
        )
    hits.append(now)


async def ai_rate_limit(user: UsuarioModel = Depends(get_current_user)) -> None:
    limit = settings.AI_RATE_LIMIT_PREMIUM_PER_HOUR if user.plan == "premium" else settings.AI_RATE_LIMIT_PER_HOUR
    _check(str(user.id), limit)


def reset() -> None:
    """Solo para tests."""
    _hits.clear()
