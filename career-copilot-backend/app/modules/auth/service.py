from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from supabase import AsyncClient

from app.modules.auth.schemas import UserResponse
from app.shared.supabase_utils import first_row, response_rows


class AuthService:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def get_user_by_id(self, user_id: UUID | str) -> UserResponse:
        try:
            normalized_id = str(UUID(str(user_id)))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identificador de usuario inválido",
            ) from exc
        response = await (
            self.supabase.table("usuarios")
            .select("*")
            .eq("id", normalized_id)
            .limit(1)
            .execute()
        )
        user = first_row(response)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        return UserResponse.model_validate(user)

    async def get_or_create_from_token(self, payload: dict) -> UserResponse:
        """Return the token user, inserting its application record on first access."""
        try:
            return await self.get_user_by_id(payload["sub"])
        except HTTPException as exc:
            if exc.status_code != status.HTTP_404_NOT_FOUND:
                raise

        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: falta el correo del usuario.",
            )
        try:
            user_id = str(UUID(str(payload["sub"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identificador de usuario inválido",
            ) from exc

        metadata = payload.get("user_metadata") or {}
        user_data = {
            "id": user_id,
            "email": email,
            "nombre_completo": metadata.get("full_name") or metadata.get("name"),
            "plan": "free",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await (
            self.supabase.table("usuarios")
            .upsert(user_data, on_conflict="id", ignore_duplicates=True)
            .execute()
        )
        return await self.get_user_by_id(user_id)

    async def delete_user_completely(self, user_id: UUID) -> None:
        normalized_id = str(user_id)

        interview_response = await (
            self.supabase.table("entrevistas")
            .select("id")
            .eq("usuario_id", normalized_id)
            .execute()
        )
        interview_ids = [row["id"] for row in response_rows(interview_response)]
        if interview_ids:
            await (
                self.supabase.table("mensajes")
                .delete()
                .in_("entrevista_id", interview_ids)
                .execute()
            )
            await (
                self.supabase.table("entrevista_evaluaciones")
                .delete()
                .in_("entrevista_id", interview_ids)
                .execute()
            )
        await (
            self.supabase.table("entrevistas")
            .delete()
            .eq("usuario_id", normalized_id)
            .execute()
        )
        await (
            self.supabase.table("emails_generados")
            .delete()
            .eq("usuario_id", normalized_id)
            .execute()
        )

        match_response = await (
            self.supabase.table("job_matches")
            .select("id")
            .eq("usuario_id", normalized_id)
            .execute()
        )
        match_ids = [row["id"] for row in response_rows(match_response)]
        if match_ids:
            await (
                self.supabase.table("job_application_status")
                .delete()
                .in_("job_match_id", match_ids)
                .execute()
            )
        await (
            self.supabase.table("job_matches")
            .delete()
            .eq("usuario_id", normalized_id)
            .execute()
        )
        await (
            self.supabase.table("cvs")
            .delete()
            .eq("usuario_id", normalized_id)
            .execute()
        )
        await (
            self.supabase.table("perfiles")
            .delete()
            .eq("usuario_id", normalized_id)
            .execute()
        )
        await (
            self.supabase.table("usuarios")
            .delete()
            .eq("id", normalized_id)
            .execute()
        )
        await self.supabase.auth.admin.delete_user(normalized_id)
