from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.ats.cv_documents import parse_candidate_profile
from app.modules.ats.schemas import ParsedCandidateProfile
from app.shared.dependencies import get_current_user_id
from app.shared.rate_limit import ai_rate_limit

router = APIRouter(prefix="/cv-documents", tags=["CV"])
MAX_CV_BYTES = 5 * 1024 * 1024


@router.post("/parse", response_model=ParsedCandidateProfile, dependencies=[Depends(ai_rate_limit)])
async def parse_cv(
    file: Annotated[UploadFile, File(...)],
    user_id=Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    data = await file.read(MAX_CV_BYTES + 1)
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el máximo de 5 MB.")
    return await parse_candidate_profile(db, user_id, data, file.filename or "cv")
