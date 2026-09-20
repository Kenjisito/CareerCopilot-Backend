from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_router import generate_json_response
from app.core.config import settings
from app.db.models import CVModel, JobMatchModel
from app.modules.job_match.prompts import JOB_MATCH_SYSTEM_PROMPT, build_job_match_user_prompt
from app.modules.job_match.schemas import JobMatchAnalysis, JobMatchPayload, JobMatchResult


async def analyze_match(db: AsyncSession, user_id: UUID, plan: str, payload: JobMatchPayload) -> JobMatchResult:
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count = await db.scalar(select(func.count(JobMatchModel.id)).where(JobMatchModel.usuario_id == user_id, JobMatchModel.fecha >= month_start))
    if plan != "premium" and (count or 0) >= settings.FREE_MATCH_LIMIT:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Límite mensual del plan free alcanzado")
    cv_result = await db.execute(select(CVModel).where(CVModel.usuario_id == user_id).order_by(CVModel.created_at.desc()).limit(1))
    cv = cv_result.scalar_one_or_none()
    if cv is None:
        raise HTTPException(status_code=400, detail="Debes subir y procesar un CV antes de realizar un Job Match")
    raw = await generate_json_response(JOB_MATCH_SYSTEM_PROMPT, build_job_match_user_prompt(cv.parsed_text, payload.ofertaTexto), premium=plan == "premium")
    analysis = JobMatchAnalysis.model_validate(raw)
    match = JobMatchModel(usuario_id=user_id, cv_id=cv.id, nombre=payload.nombre, oferta_texto=payload.ofertaTexto, score_compatibilidad=analysis.score_compatibilidad, cumple=analysis.cumple, no_cumple=analysis.no_cumple)
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return JobMatchResult(id=str(match.id), scoreCompatibilidad=analysis.score_compatibilidad, cumple=analysis.cumple, noCumple=analysis.no_cumple, resumen=analysis.resumen)
