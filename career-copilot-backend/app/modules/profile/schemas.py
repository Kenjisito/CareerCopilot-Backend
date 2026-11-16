from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.shared.cv_profile import validate_additional_sections


class ExperiencePayload(BaseModel):
    role: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=200)
    startDate: str = Field(default="", max_length=40)
    endDate: str | None = Field(default=None, max_length=40)
    isCurrent: bool = False
    description: str | None = Field(default=None, max_length=3000)
    achievements: list[str] = Field(default_factory=list, max_length=100)
    experienceType: Literal["professional", "academic", "internship", "volunteering", "freelance", "other"] = "professional"
    rawText: str | None = Field(default=None, max_length=12000)


class ProfileUpsert(BaseModel):
    fullName: str = Field(min_length=2, max_length=200)
    headline: str | None = Field(default=None, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    commune: str | None = Field(default=None, max_length=100)
    professionalSummary: str | None = Field(default=None, max_length=5000)
    skills: list[str] = Field(default_factory=list, max_length=100)
    experiences: list[ExperiencePayload] = Field(default_factory=list, max_length=100)
    additionalSections: dict[str, list[str]] = Field(default_factory=dict)
    preserveExistingOnEmpty: bool = False

    @field_validator("additionalSections", mode="before")
    @classmethod
    def _additional_sections(cls, value: Any) -> dict[str, list[str]]:
        return validate_additional_sections(value)


class ProfileResponse(BaseModel):
    id: str
    fullName: str
    headline: str | None = None
    email: str
    phone: str | None
    country: str | None
    region: str | None
    commune: str | None
    professionalSummary: str | None
    skills: list[str]
    experiences: list[dict]
    additionalSections: dict[str, list[str]] = Field(default_factory=dict)


class ProfileImprovementExperience(BaseModel):
    id: str | None = Field(default=None, max_length=64)
    role: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=200)
    description: str | None = Field(default=None, max_length=3000)
    achievements: list[str] = Field(default_factory=list, max_length=100)


class ProfileImprovementRequest(BaseModel):
    headline: str | None = Field(default=None, max_length=200)
    professionalSummary: str | None = Field(default=None, max_length=5000)
    skills: list[str] = Field(default_factory=list, max_length=100)
    experiences: list[ProfileImprovementExperience] = Field(default_factory=list, max_length=100)


class ProfileImprovementSuggestion(BaseModel):
    field: Literal[
        "headline",
        "professionalSummary",
        "skills",
        "experienceDescription",
        "experienceAchievements",
    ]
    experienceIndex: int | None = Field(default=None, ge=0)
    suggestedValue: str = Field(min_length=1, max_length=5000)
    reason: str = Field(min_length=1, max_length=500)


class ProfileImprovementAIResult(BaseModel):
    summary: str = Field(min_length=1, max_length=500)
    changes: list[ProfileImprovementSuggestion] = Field(default_factory=list, max_length=12)


class ProfileImprovementChange(ProfileImprovementSuggestion):
    currentValue: str
    experienceId: str | None = None


class ProfileImprovementsResponse(BaseModel):
    summary: str
    changes: list[ProfileImprovementChange]
