from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID

from supabase import AsyncClient

from app.core.config import settings
from app.modules.dashboard.schemas import DashboardSummary
from app.shared.supabase_utils import first_row


async def get_summary(supabase: AsyncClient, user_id: UUID, plan: str) -> DashboardSummary:
    normalized_id = str(user_id)
    latest_response = await (
        supabase.table("job_matches")
        .select("score_compatibilidad")
        .eq("usuario_id", normalized_id)
        .order("fecha", desc=True)
        .limit(1)
        .execute()
    )
    latest_match = first_row(latest_response)
    ats_response = await (
        supabase.table("cvs")
        .select("score")
        .eq("usuario_id", normalized_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    latest_cv = first_row(ats_response)
    count_response = await (
        supabase.table("job_matches")
        .select("id", count="exact")
        .eq("usuario_id", normalized_id)
        .execute()
    )
    interviews_response = await (
        supabase.table("entrevistas")
        .select("id", count="exact")
        .eq("usuario_id", normalized_id)
        .execute()
    )
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_response = await (
        supabase.table("job_matches")
        .select("id", count="exact")
        .eq("usuario_id", normalized_id)
        .gte("fecha", month_start.isoformat())
        .execute()
    )
    premium = plan == "premium"
    return DashboardSummary(
        currentAtsScore=latest_cv.get("score") if latest_cv else None,
        latestMatchScore=latest_match.get("score_compatibilidad") if latest_match else None,
        historyCount=count_response.count or 0,
        plan=plan,
        interviewsUsed=interviews_response.count or 0,
        monthMatches=month_response.count or 0,
        interviewsLimit=None if premium else settings.FREE_INTERVIEW_LIMIT,
        matchesLimit=None if premium else settings.FREE_MATCH_LIMIT,
    )
