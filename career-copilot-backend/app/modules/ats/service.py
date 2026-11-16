from __future__ import annotations
import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from supabase import AsyncClient

from app.core.ai_router import generate_structured
from app.modules.ats.extract import extract_text
from app.modules.ats.prompts import ATS_SYSTEM_PROMPT, build_ats_user_prompt
from app.modules.ats.schemas import RUBRIC, ATSDiagnostic, ATSHistoryItem, AtsAIResult, AtsSections, ScoreItem
from app.modules.ats.section_catalog import detect_section_categories, organize_cv_sections
from app.shared.errors import not_found
from app.shared.supabase_utils import first_row, response_rows
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


async def save_cv(
    supabase: AsyncClient,
    user_id: UUID,
    filename: str,
    parsed_text: str,
    diagnostic: ATSDiagnostic,
) -> None:
    await (
        supabase.table("cvs")
        .insert({
            "id": str(uuid4()),
            "usuario_id": str(user_id),
            "file_name": filename[:255],
            "parsed_text": parsed_text,
            "score": diagnostic.score,
            "analysis": diagnostic.model_dump(mode="json"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        .execute()
    )


async def analyze_cv(supabase: AsyncClient, user_id: UUID, file_bytes: bytes, filename: str) -> ATSDiagnostic:
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
    await save_cv(supabase, user_id, filename, parsed_text, diagnostic)
    return diagnostic


async def get_latest(supabase: AsyncClient, user_id: UUID) -> ATSDiagnostic | None:
    response = await (
        supabase.table("cvs")
        .select("analysis")
        .eq("usuario_id", str(user_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    record = first_row(response)
    return ATSDiagnostic.model_validate(record["analysis"]) if record and record.get("analysis") else None


async def get_history(supabase: AsyncClient, user_id: UUID) -> list[ATSHistoryItem]:
    response = await (
        supabase.table("cvs")
        .select("id,file_name,score,created_at")
        .eq("usuario_id", str(user_id))
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return [
        ATSHistoryItem(
            id=row["id"],
            fileName=row["file_name"],
            score=row["score"],
            createdAt=row["created_at"],
        )
        for row in response_rows(response)
    ]


async def get_by_id(supabase: AsyncClient, user_id: UUID, cv_id: UUID) -> ATSDiagnostic:
    response = await (
        supabase.table("cvs")
        .select("analysis")
        .eq("id", str(cv_id))
        .eq("usuario_id", str(user_id))
        .limit(1)
        .execute()
    )
    record = first_row(response)
    if record is None or not record.get("analysis"):
        raise not_found("Diagnóstico no encontrado")
    return ATSDiagnostic.model_validate(record["analysis"])
