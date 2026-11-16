from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Response, status
from supabase import AsyncClient

from app.core.config import settings
from app.modules.auth.schemas import PlanUpdate, ProfileUpdate, UserResponse
from app.modules.auth.service import AuthService
from app.shared.dependencies import get_current_user, get_supabase
from app.shared.supabase_utils import first_row

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(user: UserResponse = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: ProfileUpdate,
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    response = await (
        supabase.table("usuarios")
        .update({"nombre_completo": payload.nombre_completo})
        .eq("id", str(user.id))
        .select("*")
        .execute()
    )
    updated = first_row(response)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UserResponse.model_validate(updated)


@router.post("/admin/plan", response_model=UserResponse)
async def set_user_plan(
    payload: PlanUpdate,
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    """Activación manual de Premium: solo para correos listados en ADMIN_EMAILS."""
    admins = {e.strip().lower() for e in settings.ADMIN_EMAILS}
    if user.email.lower() not in admins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos de administrador.")
    target_response = await (
        supabase.table("usuarios")
        .select("id")
        .ilike("email", str(payload.email))
        .limit(1)
        .execute()
    )
    target = first_row(target_response)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe un usuario con ese correo (debe iniciar sesión al menos una vez).")
    response = await (
        supabase.table("usuarios")
        .update({"plan": payload.plan})
        .eq("id", target["id"])
        .select("*")
        .execute()
    )
    updated = first_row(response)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UserResponse.model_validate(updated)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    await AuthService(supabase).delete_user_completely(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
