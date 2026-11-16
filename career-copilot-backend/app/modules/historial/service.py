from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException
from supabase import AsyncClient

from app.modules.historial.schemas import HistoryMatchDetail, HistoryMatchOut
from app.shared.supabase_utils import first_row, response_rows


def _summary(match: dict) -> HistoryMatchOut:
    return HistoryMatchOut(
        id=match["id"],
        nombre=match["nombre"],
        scoreCompatibilidad=match["score_compatibilidad"],
        fecha=match["fecha"],
    )


async def list_matches(supabase: AsyncClient, user_id: UUID) -> list[HistoryMatchOut]:
    response = await (
        supabase.table("job_matches")
        .select("*")
        .eq("usuario_id", str(user_id))
        .order("fecha", desc=True)
        .execute()
    )
    return [_summary(match) for match in response_rows(response)]


async def get_match(supabase: AsyncClient, user_id: UUID, match_id: UUID) -> HistoryMatchDetail:
    response = await (
        supabase.table("job_matches")
        .select("*")
        .eq("id", str(match_id))
        .eq("usuario_id", str(user_id))
        .limit(1)
        .execute()
    )
    match = first_row(response)
    if match is None:
        raise HTTPException(status_code=404, detail="Match no encontrado")
    return HistoryMatchDetail(
        id=match["id"],
        nombre=match["nombre"],
        scoreCompatibilidad=match["score_compatibilidad"],
        fecha=match["fecha"],
        cumple=match.get("cumple") or [],
        noCumple=match.get("no_cumple") or [],
        ofertaTexto=match["oferta_texto"],
    )


async def delete_match(supabase: AsyncClient, user_id: UUID, match_id: UUID) -> None:
    response = await (
        supabase.table("job_matches")
        .select("id")
        .eq("id", str(match_id))
        .eq("usuario_id", str(user_id))
        .limit(1)
        .execute()
    )
    match = first_row(response)
    if match is None:
        raise HTTPException(status_code=404, detail="Match no encontrado")
    await (
        supabase.table("job_matches")
        .delete()
        .eq("id", match["id"])
        .eq("usuario_id", str(user_id))
        .execute()
    )
