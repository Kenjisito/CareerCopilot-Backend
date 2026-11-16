from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApplicationStatusModel, JobMatchModel, UsuarioModel
from app.db.session import get_db
from app.modules.job_match.extractor import extract_job_offer, extract_job_offer_from_text
from app.modules.job_match.schemas import JobExtractPayload, JobExtractResult, JobExtractTextPayload, JobMatchListItem, JobMatchPayload, JobMatchResult, JobStatusUpdate
from app.modules.job_match.service import analyze_match
from app.shared.rate_limit import ai_rate_limit
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/job-match", tags=["Job Match"])


def _match_item(match: JobMatchModel, state: ApplicationStatusModel | None) -> JobMatchListItem:
    return JobMatchListItem(
        id=str(match.id),
        nombre=match.nombre,
        empresa=state.company if state else None,
        ofertaTexto=match.oferta_texto,
        scoreCompatibilidad=match.score_compatibilidad,
        cumple=match.cumple or [],
        noCumple=match.no_cumple or [],
        resumen=state.astro_advice if state else None,
        status=state.status if state else "Saved",
    )


@router.get("", response_model=list[JobMatchListItem])
async def list_matches(user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(JobMatchModel, ApplicationStatusModel)
        .outerjoin(ApplicationStatusModel, ApplicationStatusModel.job_match_id == JobMatchModel.id)
        .where(JobMatchModel.usuario_id == user.id)
        .order_by(JobMatchModel.fecha.desc())
    )
    return [_match_item(match, state) for match, state in rows]


@router.get("/{match_id}", response_model=JobMatchListItem)
async def get_match(match_id: UUID, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        select(JobMatchModel, ApplicationStatusModel)
        .outerjoin(ApplicationStatusModel, ApplicationStatusModel.job_match_id == JobMatchModel.id)
        .where(JobMatchModel.id == match_id, JobMatchModel.usuario_id == user.id)
    )
    result = row.first()
    if result is None:
        raise HTTPException(status_code=404, detail="Match no encontrado.")
    return _match_item(*result)


@router.patch("/{match_id}/status", response_model=JobMatchListItem)
async def update_status(
    match_id: UUID,
    payload: JobStatusUpdate,
    user: UsuarioModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    match = await db.scalar(select(JobMatchModel).where(JobMatchModel.id == match_id, JobMatchModel.usuario_id == user.id))
    if match is None:
        raise HTTPException(status_code=404, detail="Match no encontrado.")
    state = await db.get(ApplicationStatusModel, match.id)
    if state is None:
        state = ApplicationStatusModel(job_match_id=match.id, status=payload.status)
        db.add(state)
    else:
        state.status = payload.status
    await db.commit()
    await db.refresh(state)
    return _match_item(match, state)


@router.post("/analyze", response_model=JobMatchResult, status_code=201, dependencies=[Depends(ai_rate_limit)])
@router.post("/create", response_model=JobMatchResult, status_code=201, dependencies=[Depends(ai_rate_limit)])
async def analyze(payload: JobMatchPayload, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await analyze_match(db, user.id, user.plan, payload)


@router.post("/extract", response_model=JobExtractResult, dependencies=[Depends(ai_rate_limit)])
async def extract(payload: JobExtractPayload):
    """Lee la oferta laboral desde la URL de un portal de empleo. No guarda
    nada: el usuario revisa el texto y luego llama a /analyze."""
    return await extract_job_offer(str(payload.url))


@router.post("/extract-text", response_model=JobExtractResult, dependencies=[Depends(ai_rate_limit)])
async def extract_text(payload: JobExtractTextPayload):
    """Ordena una oferta copiada y pegada desde cualquier página: devuelve título,
    empresa y el texto de la oferta sin menús ni contenido ajeno. No guarda nada."""
    return await extract_job_offer_from_text(payload.texto)
