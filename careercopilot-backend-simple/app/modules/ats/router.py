from __future__ import annotations
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.ats import service
from app.modules.ats.schemas import ATSDiagnostic, ATSHistoryItem
from app.shared.dependencies import get_current_user_id
from app.shared.rate_limit import ai_rate_limit

router = APIRouter(prefix="/ats", tags=["ATS"])
MAX_CV_BYTES = 5 * 1024 * 1024


@router.post("/analyze", response_model=ATSDiagnostic, status_code=201, dependencies=[Depends(ai_rate_limit)])
@router.post("/process", response_model=ATSDiagnostic, status_code=201, dependencies=[Depends(ai_rate_limit)])
async def analyze(file: Annotated[UploadFile, File(...)], user_id=Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    data = await file.read(MAX_CV_BYTES + 1)
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el máximo de 5 MB.")
    return await service.analyze_cv(db, user_id, data, file.filename or "cv")


@router.get("/latest", response_model=ATSDiagnostic | None)
async def latest(user_id=Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await service.get_latest(db, user_id)


@router.get("/history", response_model=list[ATSHistoryItem])
async def history(user_id=Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await service.get_history(db, user_id)


@router.get("/{cv_id}", response_model=ATSDiagnostic)
async def detail(cv_id: UUID, user_id=Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await service.get_by_id(db, user_id, cv_id)
