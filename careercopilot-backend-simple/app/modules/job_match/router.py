from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UsuarioModel
from app.db.session import get_db
from app.modules.job_match.schemas import JobMatchPayload, JobMatchResult
from app.modules.job_match.service import analyze_match
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/job-match", tags=["Job Match"])


@router.post("/analyze", response_model=JobMatchResult, status_code=201)
@router.post("/create", response_model=JobMatchResult, status_code=201)
async def analyze(payload: JobMatchPayload, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await analyze_match(db, user.id, user.plan, payload)
