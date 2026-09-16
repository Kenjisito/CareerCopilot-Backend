"""
Replica exacta de frontend/types/ats.ts (ATSDiagnostic) — el contrato
real que ya usa hooks/use-ats.ts y services/ats-service.ts.
"""
from typing import Optional

from pydantic import BaseModel


class AtsSections(BaseModel):
    contactInfo: bool
    workExperience: bool
    education: bool
    skills: bool


class ATSDiagnostic(BaseModel):
    score: int
    parsedText: str
    summary: str
    sections: AtsSections
    strengths: list[str]
    improvements: list[str]
    missingKeywords: list[str]
