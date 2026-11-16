import { apiClient } from "@/shared/api/apiClient"
import { ApiError } from "@/shared/lib/apiError"
import type {
  ApplicationStatus,
  AnalyzeJobRequest,
  JobAnalysisResponse,
  UpdateJobStatusRequest,
} from "@/features/jobmatch/types"

const fieldLimits: Record<keyof AnalyzeJobRequest, number> = {
  jobTitle: 300,
  company: 200,
  rawDescription: 10_000,
}

interface BackendJobMatch {
  id: string
  nombre: string
  empresa: string | null
  ofertaTexto: string
  scoreCompatibilidad: number
  cumple: string[]
  noCumple: string[]
  resumen: string | null
  status: ApplicationStatus
}

interface BackendJobMatchResult {
  id: string
  scoreCompatibilidad: number
  cumple: string[]
  noCumple: string[]
  resumen: string
  recomendaciones: string[]
}

function toJobAnalysis(
  match: BackendJobMatch,
): JobAnalysisResponse {
  return {
    id: match.id,
    jobTitle: match.nombre,
    company: match.empresa,
    rawDescription: match.ofertaTexto,
    matchScore: match.scoreCompatibilidad,
    matchedKeywords: match.cumple,
    missingKeywords: match.noCumple,
    astroAdvice: match.resumen,
    status: match.status,
  }
}

export function getJobMatches(signal?: AbortSignal): Promise<JobAnalysisResponse[]> {
  return apiClient<BackendJobMatch[]>("/job-match", { signal }).then((matches) =>
    matches.map(toJobAnalysis),
  )
}

export function getJobMatch(id: string, signal?: AbortSignal): Promise<JobAnalysisResponse> {
  return apiClient<BackendJobMatch>(`/job-match/${encodeURIComponent(id)}`, { signal }).then(toJobAnalysis)
}

export function analyzeJobMatch(request: AnalyzeJobRequest, signal?: AbortSignal) {
  for (const field of Object.keys(fieldLimits) as (keyof AnalyzeJobRequest)[]) {
    const value = request[field]
    if (field !== "company" && !value?.trim()) {
      throw new ApiError(400, "validation_error", "Completa todos los campos de la oferta.", field)
    }
    if (value && value.length > fieldLimits[field]) {
      throw new ApiError(
        400,
        "validation_error",
        `Este campo admite hasta ${fieldLimits[field]} caracteres.`,
        field,
      )
    }
  }

  const body: AnalyzeJobRequest = {
    jobTitle: request.jobTitle.trim(),
    company: request.company?.trim() || null,
    rawDescription: request.rawDescription.trim(),
  }

  if (body.rawDescription.length < 100) {
    throw new ApiError(
      400,
      "validation_error",
      "La descripción debe tener al menos 100 caracteres.",
      "rawDescription",
    )
  }

  return apiClient<BackendJobMatchResult>("/job-match/analyze", {
    method: "POST",
    body: {
      nombre: body.jobTitle,
      empresa: body.company,
      ofertaTexto: body.rawDescription,
    },
    signal,
  }).then((result) => ({
    id: result.id,
    jobTitle: body.jobTitle,
    company: body.company,
    rawDescription: body.rawDescription,
    matchScore: result.scoreCompatibilidad,
    matchedKeywords: result.cumple,
    missingKeywords: result.noCumple,
    astroAdvice: [result.resumen, ...result.recomendaciones].filter(Boolean).join("\n\n"),
    status: "Saved" as const,
  }))
}

export function updateApplicationStatus(
  applicationId: string,
  request: UpdateJobStatusRequest,
  signal?: AbortSignal,
) {
  return apiClient<BackendJobMatch>(`/job-match/${encodeURIComponent(applicationId)}/status`, {
    method: "PATCH",
    body: { status: request.status },
    signal,
  }).then(toJobAnalysis)
}
