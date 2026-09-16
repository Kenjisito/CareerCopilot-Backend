from app.modules.job_match.prompts import JOB_MATCH_SYSTEM_PROMPT, build_job_match_user_prompt
from app.modules.job_match.schemas import JobMatchPayload, JobMatchResult
from app.shared.ai_client import generate_json


def analyze_match(payload: JobMatchPayload) -> JobMatchResult:
    # Sin persistencia: el frontend envía cvText + jobDescription completos
    # en cada llamada (services/job-match-service.ts) y no existe ningún
    # "GET /job-match/latest" — es un análisis puntual, stateless.
    result = generate_json(
        JOB_MATCH_SYSTEM_PROMPT,
        build_job_match_user_prompt(payload.cvText, payload.jobDescription),
    )
    return JobMatchResult(**result)
