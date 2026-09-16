from fastapi import APIRouter

from app.modules.job_match import service
from app.modules.job_match.schemas import JobMatchPayload, JobMatchResult

router = APIRouter(prefix="/job-match", tags=["Job Match"])


@router.post("/analyze", response_model=JobMatchResult, status_code=201)
def analyze(payload: JobMatchPayload):
    return service.analyze_match(payload)
