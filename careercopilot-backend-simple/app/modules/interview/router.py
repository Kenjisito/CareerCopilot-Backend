from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.modules.interview import service
from app.modules.interview.schemas import (
    InterviewQuestion,
    InterviewSessionConfig,
    SubmitAnswerPayload,
    SubmitAnswerResult,
)

router = APIRouter(prefix="/interview", tags=["Entrevista"])


@router.post("/start", response_model=InterviewQuestion, status_code=201)
def start(
    config: InterviewSessionConfig,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return service.start_session(db, user_id, config)


@router.post("/answer", response_model=SubmitAnswerResult, status_code=201)
def answer(
    payload: SubmitAnswerPayload,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return service.submit_answer(db, user_id, payload.questionId, payload.answer)
