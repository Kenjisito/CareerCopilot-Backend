from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.supabase import supabase_admin_client
from app.db.models import CVModel, EmailGenerated, EntrevistaModel, JobMatchModel, UsuarioModel


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: UUID | str) -> UsuarioModel:
        try:
            normalized_id = UUID(str(user_id))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identificador de usuario inválido") from exc
        result = await self.db.execute(select(UsuarioModel).where(UsuarioModel.id == normalized_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        return user

    async def get_or_create_from_token(self, payload: dict) -> UsuarioModel:
        """Devuelve el usuario del token; si es su primer acceso (cuenta recién
        creada en Supabase) lo crea en la tabla `usuarios` con plan 'free'."""
        try:
            return await self.get_user_by_id(payload["sub"])
        except HTTPException as exc:
            if exc.status_code != status.HTTP_404_NOT_FOUND:
                raise
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: falta el correo del usuario.")
        metadata = payload.get("user_metadata") or {}
        user = UsuarioModel(
            id=UUID(str(payload["sub"])),
            email=email,
            nombre_completo=metadata.get("full_name") or metadata.get("name"),
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError:
            # Otra petición simultánea ya lo creó.
            await self.db.rollback()
            return await self.get_user_by_id(payload["sub"])
        await self.db.refresh(user)
        return user

    async def delete_user_completely(self, user_id: UUID) -> None:
        await self.db.execute(delete(EmailGenerated).where(EmailGenerated.usuario_id == user_id))
        await self.db.execute(delete(EntrevistaModel).where(EntrevistaModel.usuario_id == user_id))
        await self.db.execute(delete(JobMatchModel).where(JobMatchModel.usuario_id == user_id))
        await self.db.execute(delete(CVModel).where(CVModel.usuario_id == user_id))
        await self.db.execute(delete(UsuarioModel).where(UsuarioModel.id == user_id))
        await self.db.commit()
        if supabase_admin_client is not None:
            supabase_admin_client.auth.admin.delete_user(str(user_id))
