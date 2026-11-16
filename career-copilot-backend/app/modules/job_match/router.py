from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import AsyncClient

from app.modules.auth.schemas import UserResponse
from app.modules.job_match.extractor import extract_job_offer
from app.modules.job_match.schemas import JobExtractPayload, JobExtractResult, JobMatchListItem, JobMatchPayload, JobMatchResult, JobStatusUpdate
from app.modules.job_match.service import analyze_match
from app.shared.rate_limit import ai_rate_limit
from app.shared.dependencies import get_current_user, get_supabase
from app.shared.supabase_utils import first_row, response_rows

router = APIRouter(prefix="/job-match", tags=["Job Match"])


def _match_item(match: dict, state: dict | None) -> JobMatchListItem:
    return JobMatchListItem(
        id=str(match["id"]),
        nombre=match["nombre"],
        empresa=state.get("company") if state else None,
        ofertaTexto=match["oferta_texto"],
        scoreCompatibilidad=match["score_compatibilidad"],
        cumple=match.get("cumple") or [],
        noCumple=match.get("no_cumple") or [],
        resumen=state.get("astro_advice") if state else None,
        status=state.get("status", "Saved") if state else "Saved",
    )


@router.get("", response_model=list[JobMatchListItem])
async def list_matches(
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    match_response = await (
        supabase.table("job_matches")
        .select("*")
        .eq("usuario_id", str(user.id))
        .order("fecha", desc=True)
        .execute()
    )
    matches = response_rows(match_response)
    if not matches:
        return []
    status_response = await (
        supabase.table("job_application_status")
        .select("*")
        .in_("job_match_id", [match["id"] for match in matches])
        .execute()
    )
    statuses = {row["job_match_id"]: row for row in response_rows(status_response)}
    return [_match_item(match, statuses.get(match["id"])) for match in matches]


@router.get("/{match_id}", response_model=JobMatchListItem)
async def get_match(
    match_id: UUID,
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    response = await (
        supabase.table("job_matches")
        .select("*")
        .eq("id", str(match_id))
        .eq("usuario_id", str(user.id))
        .limit(1)
        .execute()
    )
    match = first_row(response)
    if match is None:
        raise HTTPException(status_code=404, detail="Match no encontrado.")
    status_response = await (
        supabase.table("job_application_status")
        .select("*")
        .eq("job_match_id", match["id"])
        .limit(1)
        .execute()
    )
    return _match_item(match, first_row(status_response))


@router.patch("/{match_id}/status", response_model=JobMatchListItem)
async def update_status(
    match_id: UUID,
    payload: JobStatusUpdate,
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    match_response = await (
        supabase.table("job_matches")
        .select("*")
        .eq("id", str(match_id))
        .eq("usuario_id", str(user.id))
        .limit(1)
        .execute()
    )
    match = first_row(match_response)
    if match is None:
        raise HTTPException(status_code=404, detail="Match no encontrado.")
    state_response = await (
        supabase.table("job_application_status")
        .select("*")
        .eq("job_match_id", match["id"])
        .limit(1)
        .execute()
    )
    state = first_row(state_response)
    if state is None:
        state_response = await (
            supabase.table("job_application_status")
            .insert({"job_match_id": match["id"], "status": payload.status})
            .select("*")
            .execute()
        )
    else:
        state_response = await (
            supabase.table("job_application_status")
            .update({"status": payload.status})
            .eq("job_match_id", match["id"])
            .select("*")
            .execute()
        )
    state = first_row(state_response)
    return _match_item(match, state)


@router.post("/analyze", response_model=JobMatchResult, status_code=201, dependencies=[Depends(ai_rate_limit)])
@router.post("/create", response_model=JobMatchResult, status_code=201, dependencies=[Depends(ai_rate_limit)])
async def analyze(
    payload: JobMatchPayload,
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    return await analyze_match(supabase, user.id, user.plan, payload)


@router.post("/extract", response_model=JobExtractResult, dependencies=[Depends(ai_rate_limit)])
async def extract(payload: JobExtractPayload):
    """Lee la oferta laboral desde la URL de un portal de empleo. No guarda
    nada: el usuario revisa el texto y luego llama a /analyze."""
    return await extract_job_offer(str(payload.url))
