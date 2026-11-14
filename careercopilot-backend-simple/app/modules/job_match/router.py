from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UsuarioModel
from app.db.session import get_db
from app.modules.job_match.extractor import extract_job_offer
from app.modules.job_match.schemas import JobExtractPayload, JobExtractResult, JobMatchPayload, JobMatchResult
from app.modules.job_match.service import analyze_match
from app.shared.rate_limit import ai_rate_limit
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/job-match", tags=["Job Match"])


@router.post("/analyze", response_model=JobMatchResult, status_code=201, dependencies=[Depends(ai_rate_limit)])
@router.post("/create", response_model=JobMatchResult, status_code=201, dependencies=[Depends(ai_rate_limit)])
async def analyze(payload: JobMatchPayload, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await analyze_match(db, user.id, user.plan, payload)


@router.post("/extract", response_model=JobExtractResult, dependencies=[Depends(ai_rate_limit)])
async def extract(payload: JobExtractPayload):
    """Lee la oferta laboral desde la URL de un portal de empleo. No guarda
    nada: el usuario revisa el texto y luego llama a /analyze."""
    return await extract_job_offer(str(payload.url))
