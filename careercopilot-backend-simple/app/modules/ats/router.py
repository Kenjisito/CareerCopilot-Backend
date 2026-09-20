from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.ats import service
from app.modules.ats.schemas import ATSDiagnostic
from app.shared.dependencies import get_current_user_id

router = APIRouter(prefix="/ats", tags=["ATS"])


@router.post("/analyze", response_model=ATSDiagnostic, status_code=201)
@router.post("/process", response_model=ATSDiagnostic, status_code=201)
async def analyze(file: Annotated[UploadFile, File(...)], user_id=Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await service.analyze_cv(db, user_id, await file.read(), file.filename or "cv")


@router.get("/latest", response_model=ATSDiagnostic | None)
async def latest(user_id=Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await service.get_latest(db, user_id)
