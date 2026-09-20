# app/shared/dependencies.py
"""Dependencias FastAPI reutilizables entre módulos."""
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_payload
from app.db.session import get_db
from app.db.models import UsuarioModel
from app.modules.auth.service import AuthService


async def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
) -> UsuarioModel:
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
    service = AuthService(db)
    return await service.get_user_by_id(user_id)


async def get_current_user_id(
    user: UsuarioModel = Depends(get_current_user)
) -> UUID:
    """Retorna directamente el UUID del usuario autenticado."""
    return user.id


def require_plan(min_plan: str):
    """
    Dependencia para validar si el usuario autenticado cumple con el plan requerido ('free' o 'premium').
    """
    async def dependency(user: UsuarioModel = Depends(get_current_user)):
        # Si requiere plan 'premium' y el usuario está en plan 'free'
        if min_plan == "premium" and user.plan != "premium":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Esta funcionalidad es exclusiva para usuarios con suscripción Premium."
            )
        return user

    return dependency


__all__ = ["get_db", "get_current_user", "get_current_user_id", "require_plan"]