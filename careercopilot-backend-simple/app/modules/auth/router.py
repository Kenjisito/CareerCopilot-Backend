from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import UsuarioModel
from app.db.session import get_db
from app.modules.auth.schemas import PlanUpdate, ProfileUpdate, UserResponse
from app.modules.auth.service import AuthService
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(user: UsuarioModel = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(payload: ProfileUpdate, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.nombre_completo = payload.nombre_completo
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/admin/plan", response_model=UserResponse)
async def set_user_plan(payload: PlanUpdate, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Activación manual de Premium: solo para correos listados en ADMIN_EMAILS."""
    admins = {e.strip().lower() for e in settings.ADMIN_EMAILS}
    if user.email.lower() not in admins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos de administrador.")
    result = await db.execute(select(UsuarioModel).where(func.lower(UsuarioModel.email) == payload.email.lower()))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe un usuario con ese correo (debe iniciar sesión al menos una vez).")
    target.plan = payload.plan
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await AuthService(db).delete_user_completely(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
