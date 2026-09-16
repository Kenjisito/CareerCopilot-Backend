from typing import Optional

from pydantic import BaseModel


class JobMatchPayload(BaseModel):
    cvText: str
    jobDescription: str


class SkillsGap(BaseModel):
    matching: list[str]
    missing: list[str]


class GapAnalysis(BaseModel):
    technicalSkills: SkillsGap
    softSkills: SkillsGap


class JobMatchResult(BaseModel):
    matchPercentage: int
    jobTitle: str
    companyName: Optional[str] = None
    summary: str
    gaps: GapAnalysis
    recommendations: list[str]
