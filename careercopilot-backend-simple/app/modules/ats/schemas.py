from __future__ import annotations
"""
Replica exacta de frontend/types/ats.ts (ATSDiagnostic) — el contrato
real que ya usa hooks/use-ats.ts y services/ats-service.ts.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AtsSections(BaseModel):
    contactInfo: bool = False
    workExperience: bool = False
    education: bool = False
    skills: bool = False


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
