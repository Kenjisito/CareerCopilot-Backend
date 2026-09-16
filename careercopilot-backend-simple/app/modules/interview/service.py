from sqlalchemy.orm import Session

from app.db.models import InterviewQuestionRecord, InterviewSession
from app.modules.interview.prompts import (
    FEEDBACK_SYSTEM_PROMPT,
    INTERVIEW_QUESTION_SYSTEM_PROMPT,
    build_feedback_prompt,
    build_first_question_prompt,
    build_next_question_prompt,
)
from app.modules.interview.schemas import (
    AnswerFeedback,
    InterviewQuestion,
    InterviewSessionConfig,
    SubmitAnswerResult,
)
from app.shared.ai_client import generate_json
from app.shared.errors import not_found

"""
Nota de diseño clave: hooks/use-interview.ts + services/interview-service.ts
solo mandan `questionId` y `answer` en submitAnswer — nunca un `sessionId`.
Por eso toda la sesión (cargo, categoría, cuántas preguntas van, historial
de preguntas/respuestas) vive en la base de datos, indexada por el id de
cada pregunta (InterviewQuestionRecord.id == questionId del frontend).
"""


def start_session(db: Session, user_id: str, config: InterviewSessionConfig) -> InterviewQuestion:
    session = InterviewSession(
        user_id=user_id,
        job_title=config.jobTitle,
        category=config.category,
        number_of_questions=config.numberOfQuestions,
    )
    db.add(session)
    db.flush()  # asigna session.id sin cerrar la transacción

    result = generate_json(
        INTERVIEW_QUESTION_SYSTEM_PROMPT,
        build_first_question_prompt(config.jobTitle, config.category),
    )

    question = InterviewQuestionRecord(
        session_id=session.id,
        index=0,
        category=result["category"],
        question=result["question"],
        context_or_tips=result.get("contextOrTips"),
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return InterviewQuestion(
        id=question.id,
        category=question.category,
        question=question.question,
        contextOrTips=question.context_or_tips,
    )


def _build_history_text(session: InterviewSession) -> str:
    lines = []
    for q in session.questions:
        if q.answer:
            lines.append(f"P: {q.question}\nR: {q.answer}")
    return "\n\n".join(lines) if lines else "(sin preguntas respondidas todavía)"


def submit_answer(db: Session, user_id: str, question_id: str, answer: str) -> SubmitAnswerResult:
    question = db.query(InterviewQuestionRecord).filter(InterviewQuestionRecord.id == question_id).first()
    if not question:
        raise not_found("Pregunta de entrevista no encontrada")

    session = question.session
    if session.user_id != user_id:
        raise not_found("Pregunta de entrevista no encontrada")  # no revelar existencia a otro usuario

    # 1) Feedback de la respuesta actual
    feedback_raw = generate_json(FEEDBACK_SYSTEM_PROMPT, build_feedback_prompt(question.question, answer))
    feedback = AnswerFeedback(**feedback_raw)

    question.answer = answer
    question.feedback_score = feedback.score
    question.feedback_strengths = feedback.strengths
    question.feedback_improvements = feedback.areasForImprovement
    question.feedback_suggested_answer = feedback.suggestedAnswer
    db.add(question)
    db.commit()

    # 2) ¿Ya se alcanzó el número de preguntas configurado?
    answered_count = question.index + 1
    if answered_count >= session.number_of_questions:
        return SubmitAnswerResult(feedback=feedback, nextQuestion=None)

    # 3) Si no, generar la siguiente pregunta
    db.refresh(session)
    history_text = _build_history_text(session)
    next_raw = generate_json(
        INTERVIEW_QUESTION_SYSTEM_PROMPT,
        build_next_question_prompt(session.job_title, session.category, history_text),
    )

    next_question = InterviewQuestionRecord(
        session_id=session.id,
        index=answered_count,
        category=next_raw["category"],
        question=next_raw["question"],
        context_or_tips=next_raw.get("contextOrTips"),
    )
    db.add(next_question)
    db.commit()
    db.refresh(next_question)

    return SubmitAnswerResult(
        feedback=feedback,
        nextQuestion=InterviewQuestion(
            id=next_question.id,
            category=next_question.category,
            question=next_question.question,
            contextOrTips=next_question.context_or_tips,
        ),
    )
