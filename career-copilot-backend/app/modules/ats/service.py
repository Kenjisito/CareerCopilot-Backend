from __future__ import annotations
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_router import generate_structured
from app.db.models import CVModel
from app.modules.ats.extract import extract_text
from app.modules.ats.prompts import ATS_SYSTEM_PROMPT, build_ats_user_prompt
from app.modules.ats.schemas import RUBRIC, ATSDiagnostic, ATSHistoryItem, AtsAIResult, AtsSections, ScoreItem
from app.modules.ats.section_catalog import detect_section_categories, organize_cv_sections
from app.shared.errors import not_found
from app.shared.text import clip

# Presupuesto por llamada ≈ 4.000 tokens (entrada + max_tokens): el plan gratuito de Groq
# permite 8.000 tokens/minuto y max_tokens también cuenta. 8.000 caracteres cubren un CV de 2-3 páginas.
MAX_CV_CHARS_FOR_AI = 8000

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
def _detect_sections(cv_text: str) -> AtsSections:
    """Detección determinista que complementa a la IA: si el texto tiene un
    email/teléfono o un título equivalente reconocido, la sección existe."""
    categories = detect_section_categories(cv_text)

    return AtsSections(
        contactInfo="contact" in categories or bool(_EMAIL_RE.search(cv_text) or _PHONE_RE.search(cv_text)),
        workExperience="experience" in categories,
        education="education" in categories,
        skills="skills" in categories,
    )


def _mentions(text: str, keyword: str) -> bool:
    """True si `keyword` aparece como palabra completa (evita que "Go" coincida con "Google")."""
    return re.search(rf"(?<!\w){re.escape(keyword.lower())}(?!\w)", text.lower()) is not None


def build_diagnostic(parsed_text: str, ai: AtsAIResult) -> ATSDiagnostic:
    detected = _detect_sections(parsed_text)
    sections = AtsSections(**{
        name: getattr(ai.sections, name) or getattr(detected, name) for name in AtsSections.model_fields
    })
    breakdown = [ScoreItem(label=label, score=ai.rubrica[key], max=maximum) for key, label, maximum in RUBRIC]
    return ATSDiagnostic(
        score=max(0, min(100, sum(item.score for item in breakdown))),
        parsedText=parsed_text,
        summary=ai.summary.strip(),
        sections=sections,
        strengths=ai.strengths,
        improvements=ai.improvements,
        missingKeywords=[kw for kw in ai.missingKeywords if not _mentions(parsed_text, kw)],
        scoreBreakdown=breakdown,
        detectedRole=ai.detectedRole,
    )


async def analyze_cv(db: AsyncSession, user_id: UUID, file_bytes: bytes, filename: str) -> ATSDiagnostic:
    parsed_text = extract_text(file_bytes, filename)
    organized_text = organize_cv_sections(parsed_text)
    ai = await generate_structured(
        ATS_SYSTEM_PROMPT,
        build_ats_user_prompt(clip(organized_text, MAX_CV_CHARS_FOR_AI)),
        AtsAIResult,
        temperature=0.2,
        max_tokens=1200,
    )
    diagnostic = build_diagnostic(parsed_text, ai)
    db.add(CVModel(usuario_id=user_id, file_name=filename[:255], parsed_text=parsed_text, score=diagnostic.score, analysis=diagnostic.model_dump()))
    await db.commit()
    return diagnostic


async def get_latest(db: AsyncSession, user_id: UUID) -> ATSDiagnostic | None:
    result = await db.execute(select(CVModel).where(CVModel.usuario_id == user_id).order_by(CVModel.created_at.desc()).limit(1))
    record = result.scalar_one_or_none()
    return ATSDiagnostic.model_validate(record.analysis) if record and record.analysis else None


async def get_history(db: AsyncSession, user_id: UUID) -> list[ATSHistoryItem]:
    result = await db.execute(select(CVModel).where(CVModel.usuario_id == user_id).order_by(CVModel.created_at.desc()).limit(50))
    return [ATSHistoryItem(id=r.id, fileName=r.file_name, score=r.score, createdAt=r.created_at) for r in result.scalars()]


async def get_by_id(db: AsyncSession, user_id: UUID, cv_id: UUID) -> ATSDiagnostic:
    result = await db.execute(select(CVModel).where(CVModel.id == cv_id, CVModel.usuario_id == user_id))
    record = result.scalar_one_or_none()
    if record is None or not record.analysis:
        raise not_found("Diagnóstico no encontrado")
    return ATSDiagnostic.model_validate(record.analysis)
