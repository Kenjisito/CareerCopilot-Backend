from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UsuarioModel
from app.db.session import get_db
from app.modules.interview.schemas import (
    InterviewEvaluation,
    InterviewStartPayload,
    InterviewStartResponse,
    MessagePayload,
    MessageResponse,
)
from app.modules.interview.service import InterviewService
from app.shared.rate_limit import ai_rate_limit
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/interview", tags=["Interview"])


async def _start(job_match_id: UUID, config: InterviewStartPayload, user: UsuarioModel, db: AsyncSession) -> InterviewStartResponse:
    service = InterviewService(db)
    interview, response = await service.iniciar_entrevista(user.id, user.plan, job_match_id, config.tipo, config.seniority)
    return InterviewStartResponse(entrevistaId=interview.id, respuesta=response, preguntaActual=1, totalPreguntas=service.total)


@router.post("/start", response_model=InterviewStartResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(ai_rate_limit)])
async def start(payload: InterviewStartPayload, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.jobMatchId is None:
        raise HTTPException(status_code=422, detail="jobMatchId es requerido")
    return await _start(payload.jobMatchId, payload, user, db)


@router.post("/start/{job_match_id}", response_model=InterviewStartResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(ai_rate_limit)])
async def start_for_match(job_match_id: UUID, payload: InterviewStartPayload | None = None, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _start(job_match_id, payload or InterviewStartPayload(), user, db)


@router.post("/{entrevista_id}/message", response_model=MessageResponse, dependencies=[Depends(ai_rate_limit)])
@router.post("/message/{entrevista_id}", response_model=MessageResponse, dependencies=[Depends(ai_rate_limit)])
async def message(entrevista_id: UUID, payload: MessagePayload, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = InterviewService(db)
    reply, finished, current = await service.registrar_interaccion(user.id, user.plan, entrevista_id, payload.contenido)
    return MessageResponse(respuesta=reply, finalizada=finished, preguntaActual=current, totalPreguntas=service.total)


@router.post("/{entrevista_id}/finish", response_model=InterviewEvaluation, dependencies=[Depends(ai_rate_limit)])
async def finish(entrevista_id: UUID, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Termina la entrevista y devuelve la evaluación (puntaje, feedback por
    pregunta y recomendaciones). Si ya fue evaluada, devuelve la misma."""
    return await InterviewService(db).finalizar_entrevista(user.id, user.plan, entrevista_id)
