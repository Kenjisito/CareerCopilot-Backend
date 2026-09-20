from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UsuarioModel
from app.db.session import get_db
from app.modules.dashboard.schemas import DashboardSummary
from app.modules.dashboard.service import get_summary
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def summary(user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_summary(db, user.id, user.plan)
