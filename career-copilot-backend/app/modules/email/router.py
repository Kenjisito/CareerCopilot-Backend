from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends
from supabase import AsyncClient

from app.modules.auth.schemas import UserResponse
from app.modules.email.schemas import EmailGeneratePayload, EmailOut, EmailUpdatePayload
from app.modules.email.service import create_email, get_email, update_email
from app.shared.rate_limit import ai_rate_limit
from app.shared.dependencies import get_current_user, get_supabase

router = APIRouter(prefix="/email", tags=["Email"])


def _email_out(email) -> EmailOut:
    return EmailOut(
        id=email["id"],
        subject=email["subject"],
        body=email["body"],
        jobMatchId=email.get("job_match_id"),
        tone=email["tone"],
        createdAt=email["created_at"],
    )


@router.post("/generate", response_model=EmailOut, status_code=201, dependencies=[Depends(ai_rate_limit)])
async def generate(
    payload: EmailGeneratePayload,
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    return _email_out(await create_email(supabase, user.id, payload))


@router.get("/{email_id}", response_model=EmailOut)
async def get_generated_email(
    email_id: UUID,
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    return _email_out(await get_email(supabase, user.id, email_id))


@router.put("/{email_id}", response_model=EmailOut)
async def update(
    email_id: UUID,
    payload: EmailUpdatePayload,
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    return _email_out(await update_email(supabase, user.id, email_id, payload))
