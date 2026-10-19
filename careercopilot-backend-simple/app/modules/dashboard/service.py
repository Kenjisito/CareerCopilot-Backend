from __future__ import annotations
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CVModel, JobMatchModel
from app.modules.dashboard.schemas import DashboardSummary


async def get_summary(db: AsyncSession, user_id: UUID, plan: str) -> DashboardSummary:
    latest = await db.scalar(select(JobMatchModel.score_compatibilidad).where(JobMatchModel.usuario_id == user_id).order_by(JobMatchModel.fecha.desc()).limit(1))
    ats_score = await db.scalar(select(CVModel.score).where(CVModel.usuario_id == user_id).order_by(CVModel.created_at.desc()).limit(1))
    count = await db.scalar(select(func.count(JobMatchModel.id)).where(JobMatchModel.usuario_id == user_id))
    return DashboardSummary(currentAtsScore=ats_score, latestMatchScore=latest, historyCount=count or 0, plan=plan)
