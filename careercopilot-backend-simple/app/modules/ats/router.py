from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.modules.ats import service
from app.modules.ats.schemas import ATSDiagnostic

# Prefijo sin /cvs ni /api — el frontend llama exactamente a
# `${API_BASE_URL}/ats/analyze` y `${API_BASE_URL}/ats/latest`,
# con API_BASE_URL ya incluyendo /api/v1 (ver app/main.py).
router = APIRouter(prefix="/ats", tags=["ATS"])


@router.post("/analyze", response_model=ATSDiagnostic, status_code=201)
async def analyze(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    return service.analyze_cv(db, user_id, file_bytes, file.filename or "cv")


@router.get("/latest", response_model=Optional[ATSDiagnostic])
def latest(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return service.get_latest(db, user_id)
