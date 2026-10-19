from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UsuarioModel
from app.db.session import get_db
from app.modules.interview.schemas import InterviewStartPayload, InterviewStartResponse, MessagePayload, MessageResponse
from app.modules.interview.service import InterviewService
from app.shared.rate_limit import ai_rate_limit
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/interview", tags=["Interview"])


@router.post("/start", response_model=InterviewStartResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(ai_rate_limit)])
async def start(payload: InterviewStartPayload, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.jobMatchId is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="jobMatchId es requerido")
    interview, response = await InterviewService(db).iniciar_entrevista(user.id, user.plan, payload.jobMatchId, payload.tipo, payload.seniority)
    return InterviewStartResponse(entrevistaId=interview.id, respuesta=response)


@router.post("/start/{job_match_id}", response_model=InterviewStartResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(ai_rate_limit)])
async def start_for_match(job_match_id: UUID, payload: InterviewStartPayload | None = None, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = payload or InterviewStartPayload()
    interview, response = await InterviewService(db).iniciar_entrevista(user.id, user.plan, job_match_id, config.tipo, config.seniority)
    return InterviewStartResponse(entrevistaId=interview.id, respuesta=response)


@router.post("/{entrevista_id}/message", response_model=MessageResponse, dependencies=[Depends(ai_rate_limit)])
@router.post("/message/{entrevista_id}", response_model=MessageResponse, dependencies=[Depends(ai_rate_limit)])
async def message(entrevista_id: UUID, payload: MessagePayload, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    response = await InterviewService(db).registrar_interaccion(user.id, entrevista_id, payload.contenido)
    return MessageResponse(respuesta=response)


@router.post("/{entrevista_id}/finish", status_code=status.HTTP_204_NO_CONTENT)
async def finish(entrevista_id: UUID, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await InterviewService(db).finalizar_entrevista(user.id, entrevista_id)
