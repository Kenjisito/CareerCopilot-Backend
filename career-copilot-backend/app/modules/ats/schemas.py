from __future__ import annotations
"""
Contrato de frontend/types/ats.ts (ATSDiagnostic) y schema interno de la
respuesta de la IA (AtsAIResult), que se valida antes de armar el diagnóstico.
"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.shared.cv_profile import validate_additional_sections

class AtsSections(BaseModel):
    contactInfo: bool = False
    workExperience: bool = False
    education: bool = False
    skills: bool = False


class ScoreItem(BaseModel):
    label: str
    score: int
    max: int


class ATSHistoryItem(BaseModel):
    id: UUID
    fileName: str
    score: int | None = None
    createdAt: datetime


class ATSDiagnostic(BaseModel):
    score: int
    parsedText: str
    summary: str
    sections: AtsSections
    strengths: list[str]
    improvements: list[str]
    missingKeywords: list[str]
    # Opcionales: los diagnósticos guardados antes de esta versión no los tienen.
    scoreBreakdown: list[ScoreItem] | None = None
    detectedRole: str | None = None


class ParsedExperience(BaseModel):
    role: str = ""
    company: str = ""
    startDate: str = ""
    endDate: str | None = None
    isCurrent: bool = False
    description: str | None = None
    achievements: list[str] = Field(default_factory=list, max_length=100)
    experienceType: Literal["professional", "academic", "internship", "volunteering", "freelance", "other"] = "professional"
    rawText: str | None = Field(default=None, max_length=12000)

    @field_validator("role", "company", "startDate", mode="before")
    @classmethod
    def _missing_text(cls, value: Any) -> Any:
        return "" if value is None else value


class ParsedCandidateProfile(BaseModel):
    fullName: str = ""
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None
    region: str | None = None
    commune: str | None = None
    professionalSummary: str | None = None
    skills: list[str] = Field(default_factory=list, max_length=100)
    experiences: list[ParsedExperience] = Field(default_factory=list, max_length=100)
    additionalSections: dict[str, list[str]] = Field(default_factory=dict)
    nameInferred: bool = False

    @field_validator("fullName", mode="before")
    @classmethod
    def _missing_name(cls, value: Any) -> Any:
        return "" if value is None else value

    @field_validator("additionalSections", mode="before")
    @classmethod
    def _additional_sections(cls, value: Any) -> dict[str, list[str]]:
        return validate_additional_sections(value)


# --- Respuesta de la IA -------------------------------------------------------

def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(round(value))
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit() or ch == ".")
        return int(round(float(digits))) if digits and digits != "." else 0
    return 0


def _to_str_list(value: Any, limit: int) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, dict):  # p. ej. {"texto": "..."}
            item = next((v for v in item.values() if isinstance(v, str)), "")
        text = str(item).strip(" -•\t\n")
        if text and text.lower() not in seen:
            seen.add(text.lower())
            items.append(text)
    return items[:limit]


# (clave en la respuesta de la IA, etiqueta visible, puntaje máximo)
RUBRIC: list[tuple[str, str, int]] = [
    ("estructura", "Estructura y secciones", 20),
    ("contacto", "Datos de contacto", 10),
    ("experiencia", "Experiencia y logros", 30),
    ("habilidades", "Habilidades y palabras clave", 20),
    ("legibilidad", "Formato y legibilidad ATS", 20),
]


class AtsAIResult(BaseModel):
    rubrica: dict[str, int]
    summary: str = Field(min_length=1)
    detectedRole: str | None = None
    sections: AtsSections = AtsSections()
    strengths: list[str] = []
    improvements: list[str] = []
    missingKeywords: list[str] = []

    @field_validator("rubrica", mode="before")
    @classmethod
    def _rubrica(cls, value: Any) -> dict[str, int]:
        if not isinstance(value, dict):
            raise ValueError("rubrica debe ser un objeto")
        clean: dict[str, int] = {}
        for key, _label, maximum in RUBRIC:
            raw = value.get(key)
            if isinstance(raw, dict):  # {"puntaje": 15, ...}
                raw = next((v for v in raw.values() if isinstance(v, (int, float, str))), 0)
            clean[key] = max(0, min(maximum, _to_int(raw)))
        if not any(key in value for key, _, _ in RUBRIC):
            raise ValueError("rubrica sin criterios conocidos")
        return clean

    @field_validator("sections", mode="before")
    @classmethod
    def _sections(cls, value: Any) -> Any:
        return value if isinstance(value, dict) else {}

    @field_validator("strengths", "improvements", mode="before")
    @classmethod
    def _lists(cls, value: Any) -> list[str]:
        return _to_str_list(value, 8)

    @field_validator("missingKeywords", mode="before")
    @classmethod
    def _keywords(cls, value: Any) -> list[str]:
        return _to_str_list(value, 12)

    @field_validator("detectedRole", mode="before")
    @classmethod
    def _role(cls, value: Any) -> str | None:
        return str(value).strip()[:120] or None if value else None
