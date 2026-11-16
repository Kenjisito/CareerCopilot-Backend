from __future__ import annotations
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    currentAtsScore: int | None = None
    latestMatchScore: int | None = None
    historyCount: int
    plan: str
    interviewsUsed: int = 0
    interviewsLimit: int | None = None  # None = sin límite (premium)
    monthMatches: int = 0
    matchesLimit: int | None = None