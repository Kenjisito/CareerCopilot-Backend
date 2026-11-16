from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.core.ai_router import generate_structured
from app.modules.profile.schemas import (
    ProfileImprovementAIResult,
    ProfileImprovementChange,
    ProfileImprovementRequest,
    ProfileImprovementsResponse,
)
from app.shared.errors import upstream_ai_error

PROFILE_IMPROVEMENT_SYSTEM_PROMPT = """Eres un editor de CV experto en reclutamiento y sistemas ATS.
Devuelve JSON con las claves "summary" y "changes". Cada cambio debe tener
"field", "experienceIndex", "suggestedValue" y "reason".

Solo sugiere cambios concretos en headline, professionalSummary, skills,
experienceDescription o experienceAchievements. Para campos de experiencia,
usa el índice exacto del registro recibido; para los demás, usa null.
suggestedValue reemplaza todo el campo: en skills y experienceAchievements,
separa cada elemento con un salto de línea.

No inventes empresas, cargos, fechas, herramientas, resultados, métricas,
certificaciones ni responsabilidades. Usa únicamente información explícita
en el perfil recibido. Mantén intactos los hechos y el sentido; mejora la
claridad, concisión, gramática y relevancia ATS. No propongas un cambio si no
mejora el contenido. Prioriza los cambios con mayor impacto y devuelve como
máximo 12. Incluye una razón breve y profesional por cambio. No devuelvas
campos sin cambios ni explicaciones fuera del JSON."""

MAX_PROFILE_IMPROVEMENT_INPUT_CHARS = 20_000
EXPERIENCE_FIELDS = {"experienceDescription", "experienceAchievements"}


def _current_value(payload: ProfileImprovementRequest, field: str, index: int | None) -> str:
    if field == "headline":
        return payload.headline or ""
    if field == "professionalSummary":
        return payload.professionalSummary or ""
    if field == "skills":
        return "\n".join(payload.skills)
    if field in EXPERIENCE_FIELDS:
        if index is None or index >= len(payload.experiences):
            raise upstream_ai_error()
        experience = payload.experiences[index]
        if field == "experienceDescription":
            return experience.description or ""
        return "\n".join(experience.achievements)
    raise upstream_ai_error()


async def suggest_profile_improvements(
    payload: ProfileImprovementRequest,
) -> ProfileImprovementsResponse:
    source = json.dumps({
        "headline": payload.headline,
        "professionalSummary": payload.professionalSummary,
        "skills": payload.skills,
        "experiences": [
            {
                "role": experience.role,
                "company": experience.company,
                "description": experience.description,
                "achievements": experience.achievements,
            }
            for experience in payload.experiences
        ],
    }, ensure_ascii=False)
    if len(source) > MAX_PROFILE_IMPROVEMENT_INPUT_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El contenido del CV es muy extenso para mejorarlo en una sola solicitud.",
        )

    ai_result = await generate_structured(
        PROFILE_IMPROVEMENT_SYSTEM_PROMPT,
        f"Mejora un CV sin inventar información. Perfil estructurado:\n{source}",
        ProfileImprovementAIResult,
        temperature=0.2,
        max_tokens=1400,
    )

    changes: list[ProfileImprovementChange] = []
    seen: set[tuple[str, int | None]] = set()
    for suggestion in ai_result.changes:
        if suggestion.field in EXPERIENCE_FIELDS:
            if suggestion.experienceIndex is None or suggestion.experienceIndex >= len(payload.experiences):
                raise upstream_ai_error()
        elif suggestion.experienceIndex is not None:
            raise upstream_ai_error()

        key = (suggestion.field, suggestion.experienceIndex)
        if key in seen:
            raise upstream_ai_error()
        seen.add(key)

        current = _current_value(payload, suggestion.field, suggestion.experienceIndex)
        proposed = suggestion.suggestedValue.strip()
        if proposed == current.strip():
            continue
        changes.append(ProfileImprovementChange(
            field=suggestion.field,
            experienceIndex=suggestion.experienceIndex,
            currentValue=current,
            suggestedValue=proposed,
            reason=suggestion.reason.strip(),
            experienceId=(
                payload.experiences[suggestion.experienceIndex].id
                if suggestion.field in EXPERIENCE_FIELDS and suggestion.experienceIndex is not None
                else None
            ),
        ))

    return ProfileImprovementsResponse(summary=ai_result.summary.strip(), changes=changes)
