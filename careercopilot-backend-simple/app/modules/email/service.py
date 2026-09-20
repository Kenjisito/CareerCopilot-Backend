from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_router import generate_json_response
from app.db.models import EmailGenerated, JobMatchModel
from app.modules.email.schemas import EmailGeneratePayload, EmailUpdatePayload


async def create_email(db: AsyncSession, user_id: UUID, payload: EmailGeneratePayload) -> EmailGenerated:
    match = await db.scalar(select(JobMatchModel).where(JobMatchModel.id == payload.jobMatchId, JobMatchModel.usuario_id == user_id))
    if match is None:
        raise HTTPException(status_code=404, detail="Job Match no encontrado")
    prompt = f"Genera un email de postulación {payload.tone} para {match.nombre}. Oferta: {match.oferta_texto}. Destinatario: {payload.recipientName or 'Hiring Team'}. Devuelve subject y body."
    result = await generate_json_response("No inventes experiencia ni datos no presentes. Responde JSON.", prompt)
    email = EmailGenerated(usuario_id=user_id, job_match_id=match.id, subject=result.get("subject", f"Application for {match.nombre}"), body=result.get("body", ""))
    db.add(email)
    await db.commit()
    await db.refresh(email)
    return email


async def update_email(db: AsyncSession, user_id: UUID, email_id: UUID, payload: EmailUpdatePayload) -> EmailGenerated:
    email = await db.scalar(select(EmailGenerated).where(EmailGenerated.id == email_id, EmailGenerated.usuario_id == user_id))
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    if payload.subject is not None:
        email.subject = payload.subject
    if payload.body is not None:
        email.body = payload.body
    await db.commit()
    await db.refresh(email)
    return email
