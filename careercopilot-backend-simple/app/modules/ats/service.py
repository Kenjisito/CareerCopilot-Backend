from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_router import generate_json_response
from app.db.models import CVModel
from app.modules.ats.extract import extract_text
from app.modules.ats.prompts import ATS_SYSTEM_PROMPT, build_ats_user_prompt
from app.modules.ats.schemas import ATSDiagnostic, AtsSections


async def analyze_cv(db: AsyncSession, user_id: UUID, file_bytes: bytes, filename: str) -> ATSDiagnostic:
    parsed_text = extract_text(file_bytes, filename)
    result = await generate_json_response(ATS_SYSTEM_PROMPT, build_ats_user_prompt(parsed_text))
    diagnostic = ATSDiagnostic(
        score=max(0, min(100, int(result.get("score", 0)))),
        parsedText=parsed_text,
        summary=result.get("summary", ""),
        sections=AtsSections.model_validate(result.get("sections", {})),
        strengths=result.get("strengths", []),
        improvements=result.get("improvements", []),
        missingKeywords=result.get("missingKeywords", []),
    )
    db.add(CVModel(usuario_id=user_id, file_name=filename, parsed_text=parsed_text, score=diagnostic.score, analysis=diagnostic.model_dump()))
    await db.commit()
    return diagnostic


async def get_latest(db: AsyncSession, user_id: UUID) -> ATSDiagnostic | None:
    result = await db.execute(select(CVModel).where(CVModel.usuario_id == user_id).order_by(CVModel.created_at.desc()).limit(1))
    record = result.scalar_one_or_none()
    return ATSDiagnostic.model_validate(record.analysis) if record and record.analysis else None
