from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient

from app.modules.auth.schemas import UserResponse
from app.modules.profile.improvements import suggest_profile_improvements
from app.modules.profile.schemas import (
    ProfileImprovementRequest,
    ProfileImprovementsResponse,
    ProfileResponse,
    ProfileUpsert,
)
from app.shared.dependencies import get_current_user, get_supabase
from app.shared.rate_limit import ai_rate_limit
from app.shared.supabase_utils import first_row

router = APIRouter(prefix="/profile", tags=["Profile"])


def _response(profile: dict) -> ProfileResponse:
    return ProfileResponse(
        id=str(profile["usuario_id"]),
        fullName=profile["full_name"],
        headline=profile.get("headline"),
        email=profile["email"],
        phone=profile.get("phone"),
        country=profile.get("country"),
        region=profile.get("region"),
        commune=profile.get("commune"),
        professionalSummary=profile.get("professional_summary"),
        skills=profile.get("skills") or [],
        experiences=profile.get("experiences") or [],
        additionalSections=profile.get("additional_sections") or {},
    )


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    response = await (
        supabase.table("perfiles")
        .select("*")
        .eq("usuario_id", str(user.id))
        .limit(1)
        .execute()
    )
    profile = first_row(response)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado.")
    return _response(profile)


@router.put("", response_model=ProfileResponse)
async def upsert_profile(
    payload: ProfileUpsert,
    user: UserResponse = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase),
):
    existing_response = await (
        supabase.table("perfiles")
        .select("*")
        .eq("usuario_id", str(user.id))
        .limit(1)
        .execute()
    )
    profile = first_row(existing_response) or {}
    keep_existing = payload.preserveExistingOnEmpty and profile.get("full_name") is not None
    profile_data = {
        "usuario_id": str(user.id),
        "full_name": payload.fullName.strip(),
        "headline": profile.get("headline"),
        "email": str(payload.email),
        "phone": profile.get("phone"),
        "country": profile.get("country"),
        "region": profile.get("region"),
        "commune": profile.get("commune"),
        "professional_summary": profile.get("professional_summary"),
        "skills": profile.get("skills") or [],
        "experiences": profile.get("experiences") or [],
        "additional_sections": profile.get("additional_sections") or {},
    }
    if not keep_existing or payload.headline:
        profile_data["headline"] = payload.headline.strip() if payload.headline else None
    if not keep_existing or payload.phone is not None:
        profile_data["phone"] = payload.phone
    if not keep_existing or payload.country is not None:
        profile_data["country"] = payload.country
    if not keep_existing or payload.region is not None:
        profile_data["region"] = payload.region
    if not keep_existing or payload.commune is not None:
        profile_data["commune"] = payload.commune
    if not keep_existing or payload.professionalSummary:
        profile_data["professional_summary"] = payload.professionalSummary
    if not (keep_existing and not payload.skills):
        profile_data["skills"] = [skill.strip() for skill in payload.skills if skill.strip()]
    if not (keep_existing and not payload.experiences):
        profile_data["experiences"] = [item.model_dump(mode="json") for item in payload.experiences]
    if not (keep_existing and not payload.additionalSections):
        profile_data["additional_sections"] = payload.additionalSections

    response = await (
        supabase.table("perfiles")
        .upsert(profile_data, on_conflict="usuario_id")
        .select("*")
        .execute()
    )
    saved = first_row(response)
    if saved is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo guardar el perfil.")
    return _response(saved)


@router.post(
    "/improve",
    response_model=ProfileImprovementsResponse,
    dependencies=[Depends(ai_rate_limit)],
)
async def improve_profile(payload: ProfileImprovementRequest):
    return await suggest_profile_improvements(payload)
