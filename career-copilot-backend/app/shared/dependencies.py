from __future__ import annotations
# app/shared/dependencies.py
"""Dependencias FastAPI reutilizables entre módulos."""
from uuid import UUID
from fastapi import Depends, HTTPException, Request, status
from supabase import AsyncClient

from app.core.security import get_current_user_payload
from app.modules.auth.schemas import UserResponse
from app.modules.auth.service import AuthService


async def get_supabase(request: Request) -> AsyncClient:
    client = getattr(request.app.state, "supabase", None)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El cliente de Supabase no está disponible.",
        )
    return client


async def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    supabase: AsyncClient = Depends(get_supabase),
) -> UserResponse:
    """
    Garantiza que el token JWT sea válido y que el usuario
    exista en la tabla 'usuarios' de PostgreSQL.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: falta identificador de usuario."
        )
    service = AuthService(supabase)
    return await service.get_or_create_from_token(payload)


async def get_current_user_id(
    user: UserResponse = Depends(get_current_user)
) -> UUID:
    """Retorna directamente el UUID del usuario autenticado."""
    return user.id


def require_plan(min_plan: str):
    """
    Dependencia para validar si el usuario autenticado cumple con el plan requerido ('free' o 'premium').
    """
    async def dependency(user: UserResponse = Depends(get_current_user)):
        # Si requiere plan 'premium' y el usuario está en plan 'free'
        if min_plan == "premium" and user.plan != "premium":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Esta funcionalidad es exclusiva para usuarios con suscripción Premium."
            )
        return user

    return dependency


__all__ = ["get_supabase", "get_current_user", "get_current_user_id", "require_plan"]