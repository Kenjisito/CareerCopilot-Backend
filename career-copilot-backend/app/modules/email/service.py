from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from uuid import uuid4

from fastapi import HTTPException
from supabase import AsyncClient

from app.core.ai_router import generate_json_response
from app.shared.errors import upstream_ai_error
from app.modules.email.schemas import EmailGeneratePayload, EmailUpdatePayload
from app.shared.supabase_utils import first_row


async def create_email(supabase: AsyncClient, user_id: UUID, payload: EmailGeneratePayload) -> dict:
    match_response = await (
        supabase.table("job_matches")
        .select("id,nombre,oferta_texto")
        .eq("id", str(payload.jobMatchId))
        .eq("usuario_id", str(user_id))
        .limit(1)
        .execute()
    )
    match = first_row(match_response)
    if match is None:
        raise HTTPException(status_code=404, detail="Job Match no encontrado")
    prompt = f"Genera un email de postulación {payload.tone} para {match['nombre']}. Oferta: {match['oferta_texto']}. Destinatario: {payload.recipientName or 'Hiring Team'}. Devuelve subject y body."
    result = await generate_json_response("No inventes experiencia ni datos no presentes. Responde JSON.", prompt)
    if not str(result.get("body", "")).strip():
        raise upstream_ai_error()
    response = await (
        supabase.table("emails_generados")
        .insert({
            "id": str(uuid4()),
            "usuario_id": str(user_id),
            "job_match_id": match["id"],
            "subject": result.get("subject") or f"Postulación a {match['nombre']}",
            "body": result["body"],
            "tone": payload.tone,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        .select("*")
        .execute()
    )
    email = first_row(response)
    if email is None:
        raise HTTPException(status_code=500, detail="No se pudo guardar el correo generado.")
    return email


async def get_email(supabase: AsyncClient, user_id: UUID, email_id: UUID) -> dict:
    response = await (
        supabase.table("emails_generados")
        .select("*")
        .eq("id", str(email_id))
        .eq("usuario_id", str(user_id))
        .limit(1)
        .execute()
    )
    email = first_row(response)
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    return email


async def update_email(supabase: AsyncClient, user_id: UUID, email_id: UUID, payload: EmailUpdatePayload) -> dict:
    current = await get_email(supabase, user_id, email_id)
    changes = {}
    if payload.subject is not None:
        changes["subject"] = payload.subject
    if payload.body is not None:
        changes["body"] = payload.body
    if not changes:
        return current
    response = await (
        supabase.table("emails_generados")
        .update(changes)
        .eq("id", str(email_id))
        .eq("usuario_id", str(user_id))
        .select("*")
        .execute()
    )
    email = first_row(response)
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    return email
