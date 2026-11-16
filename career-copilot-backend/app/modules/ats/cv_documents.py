from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_router import generate_structured
from app.db.models import CVModel
from app.modules.ats.extract import extract_text
from app.modules.ats.prompts import ATS_SYSTEM_PROMPT, build_ats_user_prompt
from app.modules.ats.section_catalog import (
    build_field_mapping_guide,
    organize_cv_sections,
    split_text_chunks,
)
from app.modules.ats.schemas import AtsAIResult, ParsedCandidateProfile, ParsedExperience
from app.modules.ats.service import build_diagnostic
from app.shared.text import clip

MAX_PROFILE_CHUNK_CHARS = 7500
MAX_PROFILE_CHUNKS = 6
MAX_PROFILE_CHARS = MAX_PROFILE_CHUNK_CHARS * MAX_PROFILE_CHUNKS
PROFILE_SYSTEM_PROMPT = f"""Extrae información profesional explícita del CV y responde solo con JSON.
No inventes datos. Usa strings vacíos o null cuando falte información. No descartes un registro
por tener campos incompletos: conserva su texto original en rawText.
Asigna cada dato al campo correcto:
- headline: cargo objetivo o título profesional que aparece junto al nombre; no lo copies de la primera experiencia.
- professionalSummary: perfil profesional/académico, resumen, objetivo, presentación o about me.
- experiences: experiencia laboral/profesional/académica, empleo, trayectoria, docencia, investigación,
  prácticas, pasantías, trabajo freelance o work/employment/academic history.
- skills: habilidades, competencias, aptitudes, capacidades, fortalezas, conocimientos, stack,
  herramientas, soft/hard skills, skill(s), competency/competencies o expertise.
- additionalSections.education: educación, estudios, formación académica o academic background.
- additionalSections.certifications: cursos, licencias, certificaciones, credenciales o professional development.
- additionalSections.projects: proyectos, portafolio o selected/personal projects.
- additionalSections.languages: idiomas o language skills.
- additionalSections.achievements: logros, premios, reconocimientos o awards.
- additionalSections.volunteering: voluntariado o volunteer experience.
- additionalSections.publications: publicaciones o investigaciones.
- additionalSections.interests: intereses o hobbies.
- additionalSections.references: referencias laborales o profesionales.
- additionalSections.other: contenido de secciones no reconocidas o que no encajan con seguridad en otra categoría.
Devuelve additionalSections como un objeto cuyas claves sean esos nombres canónicos y cuyos valores
sean listas de textos. Cada elemento debe conservar institución/empresa, título, fechas, nivel,
emisor, URL y demás detalles presentes, unidos en una línea legible. No mezcles una categoría con otra.
En experiences extrae por separado role, company (también institución u organización), startDate,
endDate, isCurrent, description (qué hiciste), achievements (resultados cuantificables), experienceType
(professional, academic, internship, volunteering, freelance u other) y rawText (texto completo del registro).
En skills conserva cada competencia/habilidad individual como elemento independiente.
Los títulos pueden estar en español o inglés, tener sinónimos, abreviaturas o compartir línea con su contenido.
Usa el contexto para clasificar y no confundas títulos académicos con cargos ni cursos con empleos.
Si no puedes clasificar una sección con confianza, conserva el encabezado y el contenido bajo additionalSections.other.

Guía de variables y sinónimos:
{build_field_mapping_guide()}"""


def _merge_profiles(profiles: list[ParsedCandidateProfile]) -> ParsedCandidateProfile:
    def first_value(field: str) -> str | None:
        return next((value for profile in profiles if (value := getattr(profile, field))), None)

    skills: list[str] = []
    seen_skills: set[str] = set()
    experiences: list[ParsedExperience] = []
    seen_experiences: set[tuple[str, ...]] = set()
    summaries = []
    for profile in profiles:
        for skill in profile.skills:
            normalized = skill.strip().casefold()
            if normalized and normalized not in seen_skills:
                seen_skills.add(normalized)
                skills.append(skill.strip())
        for experience in profile.experiences:
            key = (
                experience.role.strip().casefold(),
                experience.company.strip().casefold(),
                experience.startDate.strip().casefold(),
                (experience.endDate or "").strip().casefold(),
                (experience.description or "").strip().casefold(),
                "|".join(item.strip().casefold() for item in experience.achievements),
                experience.experienceType,
                (experience.rawText or "").strip().casefold(),
            )
            if key not in seen_experiences:
                seen_experiences.add(key)
                experiences.append(experience)
        summary = profile.professionalSummary.strip() if profile.professionalSummary else ""
        if summary and summary.casefold() not in {item.casefold() for item in summaries}:
            summaries.append(summary)

    return ParsedCandidateProfile(
        fullName=first_value("fullName") or "",
        headline=first_value("headline"),
        email=first_value("email"),
        phone=first_value("phone"),
        country=first_value("country"),
        region=first_value("region"),
        commune=first_value("commune"),
        professionalSummary="\n\n".join(summaries)[:1500] or None,
        skills=skills,
        experiences=experiences,
        additionalSections={
            category: entries
            for category, entries in _merge_additional_sections(profiles).items()
        },
        nameInferred=any(profile.nameInferred for profile in profiles),
    )


def _merge_additional_sections(
    profiles: list[ParsedCandidateProfile],
) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = {}
    for profile in profiles:
        for category, entries in profile.additionalSections.items():
            category_sections = sections.setdefault(category, [])
            category_seen = seen.setdefault(category, set())
            for entry in entries:
                normalized = entry.strip().casefold()
                if normalized and normalized not in category_seen:
                    category_seen.add(normalized)
                    category_sections.append(entry.strip())
    return sections


async def parse_candidate_profile(
    db: AsyncSession,
    user_id: UUID,
    file_bytes: bytes,
    filename: str,
) -> ParsedCandidateProfile:
    text = extract_text(file_bytes, filename)
    if len(text) > MAX_PROFILE_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El CV contiene demasiado texto para procesarlo completo. Sube una versión más breve.",
        )
    organized_text = organize_cv_sections(text)
    try:
        chunks = split_text_chunks(organized_text, MAX_PROFILE_CHUNK_CHARS)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El CV contiene una línea demasiado larga para procesarla completa. Revisa el formato e inténtalo de nuevo.",
        ) from exc
    if len(chunks) > MAX_PROFILE_CHUNKS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El CV contiene demasiadas secciones para procesarlo completo. Sube una versión más breve.",
        )
    extracted_profiles = []
    for chunk in chunks:
        extracted_profiles.append(await generate_structured(
            PROFILE_SYSTEM_PROMPT,
            f"Clasifica y extrae cada dato de este fragmento estructurado del CV. Conserva todos los "
            f"registros aunque falten fechas, empresa o cargo; usa rawText y additionalSections.other "
            f"como respaldo sin omitir texto.\n\n{chunk}",
            ParsedCandidateProfile,
            temperature=0.1,
            max_tokens=1200,
        ))
    profile = _merge_profiles(extracted_profiles)
    ats_result = await generate_structured(
        ATS_SYSTEM_PROMPT,
        build_ats_user_prompt(clip(organized_text, 8000)),
        AtsAIResult,
        temperature=0.2,
        max_tokens=1200,
    )
    diagnostic = build_diagnostic(text, ats_result)
    db.add(CVModel(
        usuario_id=user_id,
        file_name=filename[:255],
        parsed_text=text,
        score=diagnostic.score,
        analysis=diagnostic.model_dump(mode="json"),
    ))
    await db.commit()
    if not profile.fullName.strip():
        candidate_name = next(
            (
                line.strip()
                for line in text.splitlines()
                if 2 <= len(line.strip()) <= 80
                and "@" not in line
                and not re.search(r"\d{4}", line)
            ),
            "",
        )
        profile.fullName = candidate_name
        profile.nameInferred = bool(candidate_name)
    return profile
