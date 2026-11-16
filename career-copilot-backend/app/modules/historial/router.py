from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from supabase import AsyncClient

from app.modules.historial.schemas import HistoryMatchDetail, HistoryMatchOut
from app.modules.historial.service import delete_match, get_match, list_matches
from app.shared.dependencies import get_current_user_id, get_supabase

router = APIRouter(prefix="/historial", tags=["Historial"])


@router.get("/matches", response_model=list[HistoryMatchOut])
async def list_items(user_id=Depends(get_current_user_id), supabase: AsyncClient = Depends(get_supabase)):
    return await list_matches(supabase, user_id)


@router.get("/matches/{match_id}", response_model=HistoryMatchDetail)
async def get_item(match_id: UUID, user_id=Depends(get_current_user_id), supabase: AsyncClient = Depends(get_supabase)):
    return await get_match(supabase, user_id, match_id)


@router.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(match_id: UUID, user_id=Depends(get_current_user_id), supabase: AsyncClient = Depends(get_supabase)):
    await delete_match(supabase, user_id, match_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
