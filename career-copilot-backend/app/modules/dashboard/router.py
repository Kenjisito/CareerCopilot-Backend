from __future__ import annotations
from fastapi import APIRouter, Depends
from supabase import AsyncClient

from app.modules.dashboard.schemas import DashboardSummary
from app.modules.dashboard.service import get_summary
from app.modules.auth.schemas import UserResponse
from app.shared.dependencies import get_current_user, get_supabase

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def summary(user: UserResponse = Depends(get_current_user), supabase: AsyncClient = Depends(get_supabase)):
    return await get_summary(supabase, user.id, user.plan)
