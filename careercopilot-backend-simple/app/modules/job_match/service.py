from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_router import generate_structured
from app.core.config import settings
from app.db.models import CVModel, JobMatchModel
from app.modules.job_match.prompts import JOB_MATCH_SYSTEM_PROMPT, build_job_match_user_prompt
from app.modules.job_match.schemas import JobMatchAnalysis, JobMatchPayload, JobMatchResult
from app.shared.text import clip

# CV + oferta + respuesta ≈ 5.000 tokens, dentro de los 8.000 tokens/minuto del plan gratuito de Groq.
MAX_CV_CHARS_FOR_AI = 6000
MAX_OFFER_CHARS_FOR_AI = 6000


async def analyze_match(db: AsyncSession, user_id: UUID, plan: str, payload: JobMatchPayload) -> JobMatchResult:
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count = await db.scalar(select(func.count(JobMatchModel.id)).where(JobMatchModel.usuario_id == user_id, JobMatchModel.fecha >= month_start))
    if plan != "premium" and (count or 0) >= settings.FREE_MATCH_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Alcanzaste el límite de {settings.FREE_MATCH_LIMIT} análisis de Job Match del plan gratuito este mes.",
        )
    cv_result = await db.execute(select(CVModel).where(CVModel.usuario_id == user_id).order_by(CVModel.created_at.desc()).limit(1))
    cv = cv_result.scalar_one_or_none()
    if cv is None:
        raise HTTPException(status_code=400, detail="Debes subir y procesar un CV en Diagnóstico ATS antes de realizar un Job Match.")

    analysis = await generate_structured(
        JOB_MATCH_SYSTEM_PROMPT,
        build_job_match_user_prompt(
            payload.nombre,
            clip(cv.parsed_text, MAX_CV_CHARS_FOR_AI),
            clip(payload.ofertaTexto, MAX_OFFER_CHARS_FOR_AI),
        ),
        JobMatchAnalysis,
        premium=plan == "premium",
        temperature=0.2,
        max_tokens=1200,
    )
    match = JobMatchModel(
        usuario_id=user_id,
        cv_id=cv.id,
        nombre=payload.nombre[:255],
        oferta_texto=payload.ofertaTexto,
        score_compatibilidad=analysis.score_compatibilidad,
        cumple=analysis.cumple,
        no_cumple=analysis.no_cumple,
    )
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return JobMatchResult(
        id=str(match.id),
        scoreCompatibilidad=analysis.score_compatibilidad,
        cumple=analysis.cumple,
        noCumple=analysis.no_cumple,
        resumen=analysis.resumen,
        recomendaciones=analysis.recomendaciones,
    )
