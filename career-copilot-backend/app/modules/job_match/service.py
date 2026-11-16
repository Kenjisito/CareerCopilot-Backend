from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from supabase import AsyncClient

from app.core.ai_router import generate_structured
from app.core.config import settings
from app.modules.job_match.prompts import JOB_MATCH_SYSTEM_PROMPT, build_job_match_user_prompt
from app.modules.job_match.schemas import JobMatchAnalysis, JobMatchPayload, JobMatchResult
from app.shared.supabase_utils import first_row
from app.shared.text import clip

# CV + oferta + respuesta ≈ 5.000 tokens, dentro de los 8.000 tokens/minuto del plan gratuito de Groq.
MAX_CV_CHARS_FOR_AI = 6000
MAX_OFFER_CHARS_FOR_AI = 6000


async def analyze_match(supabase: AsyncClient, user_id: UUID, plan: str, payload: JobMatchPayload) -> JobMatchResult:
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count_response = await (
        supabase.table("job_matches")
        .select("id", count="exact")
        .eq("usuario_id", str(user_id))
        .gte("fecha", month_start.isoformat())
        .execute()
    )
    count = count_response.count or 0
    if plan != "premium" and (count or 0) >= settings.FREE_MATCH_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Alcanzaste el límite de {settings.FREE_MATCH_LIMIT} análisis de Job Match del plan gratuito este mes.",
        )
    cv_response = await (
        supabase.table("cvs")
        .select("id,parsed_text")
        .eq("usuario_id", str(user_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    cv = first_row(cv_response)
    if cv is None:
        raise HTTPException(status_code=400, detail="Debes subir y procesar un CV en Diagnóstico ATS antes de realizar un Job Match.")

    analysis = await generate_structured(
        JOB_MATCH_SYSTEM_PROMPT,
        build_job_match_user_prompt(
            payload.nombre,
            clip(cv["parsed_text"], MAX_CV_CHARS_FOR_AI),
            clip(payload.ofertaTexto, MAX_OFFER_CHARS_FOR_AI),
        ),
        JobMatchAnalysis,
        premium=plan == "premium",
        temperature=0.2,
        max_tokens=1200,
    )
    match_id = str(uuid4())
    await (
        supabase.table("job_matches")
        .insert({
            "id": match_id,
            "usuario_id": str(user_id),
            "cv_id": cv["id"],
            "fecha": datetime.now(timezone.utc).isoformat(),
            "nombre": payload.nombre[:255],
            "oferta_texto": payload.ofertaTexto,
            "score_compatibilidad": analysis.score_compatibilidad,
            "cumple": analysis.cumple,
            "no_cumple": analysis.no_cumple,
        })
        .execute()
    )
    await (
        supabase.table("job_application_status")
        .insert({
            "job_match_id": match_id,
            "status": "Saved",
            "company": payload.empresa,
            "astro_advice": analysis.resumen,
        })
        .execute()
    )
    return JobMatchResult(
        id=match_id,
        scoreCompatibilidad=analysis.score_compatibilidad,
        cumple=analysis.cumple,
        noCumple=analysis.no_cumple,
        resumen=analysis.resumen,
        recomendaciones=analysis.recomendaciones,
    )
