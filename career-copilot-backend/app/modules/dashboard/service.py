from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import CVModel, EntrevistaModel, JobMatchModel
from app.modules.dashboard.schemas import DashboardSummary


async def get_summary(db: AsyncSession, user_id: UUID, plan: str) -> DashboardSummary:
    latest = await db.scalar(select(JobMatchModel.score_compatibilidad).where(JobMatchModel.usuario_id == user_id).order_by(JobMatchModel.fecha.desc()).limit(1))
    ats_score = await db.scalar(select(CVModel.score).where(CVModel.usuario_id == user_id).order_by(CVModel.created_at.desc()).limit(1))
    count = await db.scalar(select(func.count(JobMatchModel.id)).where(JobMatchModel.usuario_id == user_id))
    interviews = await db.scalar(select(func.count(EntrevistaModel.id)).where(EntrevistaModel.usuario_id == user_id))
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_matches = await db.scalar(select(func.count(JobMatchModel.id)).where(JobMatchModel.usuario_id == user_id, JobMatchModel.fecha >= month_start))
    premium = plan == "premium"
    return DashboardSummary(
        currentAtsScore=ats_score,
        latestMatchScore=latest,
        historyCount=count or 0,
        plan=plan,
        interviewsUsed=interviews or 0,
        monthMatches=month_matches or 0,
        interviewsLimit=None if premium else settings.FREE_INTERVIEW_LIMIT,
        matchesLimit=None if premium else settings.FREE_MATCH_LIMIT,
    )
