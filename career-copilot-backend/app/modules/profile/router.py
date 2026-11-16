from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfileModel, UsuarioModel
from app.db.session import get_db
from app.modules.profile.improvements import suggest_profile_improvements
from app.modules.profile.schemas import (
    ProfileImprovementRequest,
    ProfileImprovementsResponse,
    ProfileResponse,
    ProfileUpsert,
)
from app.shared.dependencies import get_current_user
from app.shared.rate_limit import ai_rate_limit

router = APIRouter(prefix="/profile", tags=["Profile"])


def _response(profile: ProfileModel) -> ProfileResponse:
    return ProfileResponse(
        id=str(profile.usuario_id),
        fullName=profile.full_name,
        headline=profile.headline,
        email=profile.email,
        phone=profile.phone,
        country=profile.country,
        region=profile.region,
        commune=profile.commune,
        professionalSummary=profile.professional_summary,
        skills=profile.skills or [],
        experiences=profile.experiences or [],
        additionalSections=profile.additional_sections or {},
    )


@router.get("", response_model=ProfileResponse)
async def get_profile(user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await db.get(ProfileModel, user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado.")
    return _response(profile)


@router.put("", response_model=ProfileResponse)
async def upsert_profile(
    payload: ProfileUpsert,
    user: UsuarioModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(ProfileModel, user.id)
    if profile is None:
        profile = ProfileModel(usuario_id=user.id)
        db.add(profile)

    keep_existing = payload.preserveExistingOnEmpty and profile.full_name is not None
    profile.full_name = payload.fullName.strip()
    if not keep_existing or payload.headline:
        profile.headline = payload.headline.strip() if payload.headline else None
    profile.email = str(payload.email)
    if not keep_existing or payload.phone is not None:
        profile.phone = payload.phone
    if not keep_existing or payload.country is not None:
        profile.country = payload.country
    if not keep_existing or payload.region is not None:
        profile.region = payload.region
    if not keep_existing or payload.commune is not None:
        profile.commune = payload.commune
    if not keep_existing or payload.professionalSummary:
        profile.professional_summary = payload.professionalSummary
    if not (keep_existing and not payload.skills):
        profile.skills = [skill.strip() for skill in payload.skills if skill.strip()]
    if not (keep_existing and not payload.experiences):
        profile.experiences = [item.model_dump() for item in payload.experiences]
    if not (keep_existing and not payload.additionalSections):
        profile.additional_sections = payload.additionalSections

    await db.commit()
    await db.refresh(profile)
    return _response(profile)


@router.post(
    "/improve",
    response_model=ProfileImprovementsResponse,
    dependencies=[Depends(ai_rate_limit)],
)
async def improve_profile(payload: ProfileImprovementRequest):
    return await suggest_profile_improvements(payload)
