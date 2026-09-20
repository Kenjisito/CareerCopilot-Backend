from pydantic import BaseModel


class DashboardSummary(BaseModel):
    currentAtsScore: int | None = None
    latestMatchScore: int | None = None
    historyCount: int
    plan: str