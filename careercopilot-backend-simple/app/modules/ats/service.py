from sqlalchemy.orm import Session

from app.db.models import AtsDiagnostic
from app.modules.ats.extract import extract_text
from app.modules.ats.prompts import ATS_SYSTEM_PROMPT, build_ats_user_prompt
from app.modules.ats.schemas import ATSDiagnostic
from app.shared.ai_client import generate_json


def analyze_cv(db: Session, user_id: str, file_bytes: bytes, filename: str) -> ATSDiagnostic:
    parsed_text = extract_text(file_bytes, filename)

    result = generate_json(ATS_SYSTEM_PROMPT, build_ats_user_prompt(parsed_text))

    diagnostic = ATSDiagnostic(
        score=result["score"],
        parsedText=parsed_text,
        summary=result["summary"],
        sections=result["sections"],
        strengths=result.get("strengths", []),
        improvements=result.get("improvements", []),
        missingKeywords=result.get("missingKeywords", []),
    )

    # Se guarda como "el más reciente" del usuario — soporta GET /ats/latest.
    record = AtsDiagnostic(
        user_id=user_id,
        file_name=filename,
        score=diagnostic.score,
        parsed_text=diagnostic.parsedText,
        summary=diagnostic.summary,
        sections=diagnostic.sections.model_dump(),
        strengths=diagnostic.strengths,
        improvements=diagnostic.improvements,
        missing_keywords=diagnostic.missingKeywords,
    )
    db.add(record)
    db.commit()

    return diagnostic


def get_latest(db: Session, user_id: str) -> ATSDiagnostic | None:
    record = (
        db.query(AtsDiagnostic)
        .filter(AtsDiagnostic.user_id == user_id)
        .order_by(AtsDiagnostic.created_at.desc())
        .first()
    )
    if not record:
        return None

    return ATSDiagnostic(
        score=record.score,
        parsedText=record.parsed_text,
        summary=record.summary,
        sections=record.sections,
        strengths=record.strengths,
        improvements=record.improvements,
        missingKeywords=record.missing_keywords,
    )
