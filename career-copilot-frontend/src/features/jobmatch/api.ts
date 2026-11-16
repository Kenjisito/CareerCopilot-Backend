import { apiClient } from "@/shared/api/apiClient"
import { ApiError } from "@/shared/lib/apiError"
import type {
  ApplicationStatus,
  AnalyzeJobRequest,
  ExtractedJobOffer,
  JobAnalysisResponse,
  UpdateJobStatusRequest,
} from "@/features/jobmatch/types"

// Deben coincidir con JobMatchPayload del backend (nombre ≤ 255, empresa ≤ 200)
// y con el máximo que devuelve la extracción desde URL (15.000 caracteres).
export const fieldLimits: Record<keyof AnalyzeJobRequest, number> = {
  jobTitle: 255,
  company: 200,
  rawDescription: 15_000,
}

export const MIN_DESCRIPTION_LENGTH = 100

interface BackendJobExtract {
  nombre: string
  empresa: string | null
  ofertaTexto: string
  fuente: "datos-estructurados" | "ia" | "texto"
  url: string
}

/** Mismo formato que guarda el backend (format_astro_advice): resumen y recomendaciones en viñetas. */
export function formatAstroAdvice(resumen: string, recomendaciones: string[]): string {
  const tips = recomendaciones
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => `• ${item}`)
  return [resumen.trim(), tips.join("\n")].filter(Boolean).join("\n\n")
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

  if (body.rawDescription.length < MIN_DESCRIPTION_LENGTH) {
    throw new ApiError(
      400,
      "validation_error",
      `La descripción debe tener al menos ${MIN_DESCRIPTION_LENGTH} caracteres.`,
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
    astroAdvice: formatAstroAdvice(result.resumen, result.recomendaciones ?? []),
    status: "Saved" as const,
  }))
}

function toExtractedOffer(offer: BackendJobExtract): ExtractedJobOffer {
  return {
    jobTitle: offer.nombre.slice(0, fieldLimits.jobTitle),
    company: offer.empresa ? offer.empresa.slice(0, fieldLimits.company) : null,
    rawDescription: offer.ofertaTexto.slice(0, fieldLimits.rawDescription),
    source: offer.fuente,
    url: offer.url,
  }
}

/** Lee la oferta desde la URL de un portal de empleo. No guarda nada. */
export function extractJobOffer(url: string, signal?: AbortSignal): Promise<ExtractedJobOffer> {
  return apiClient<BackendJobExtract>("/job-match/extract", {
    method: "POST",
    body: { url: url.trim() },
    signal,
  }).then(toExtractedOffer)
}

/** Ordena una oferta copiada y pegada desde cualquier página (con menús u otro
 *  contenido alrededor): devuelve título, empresa y descripción limpia. */
export function extractJobOfferFromText(text: string, signal?: AbortSignal): Promise<ExtractedJobOffer> {
  return apiClient<BackendJobExtract>("/job-match/extract-text", {
    method: "POST",
    body: { texto: text },
    signal,
  }).then(toExtractedOffer)
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
