export type ApplicationStatus = "Saved" | "Applied" | "Interview" | "Offer" | "Rejected"

export interface JobAnalysisResponse {
  id: string
  jobTitle: string
  company: string | null
  rawDescription: string
  matchScore: number
  matchedKeywords: string[]
  missingKeywords: string[]
  astroAdvice: string | null
  status: ApplicationStatus
}

export interface AnalyzeJobRequest {
  jobTitle: string
  company: string | null
  rawDescription: string
}

/** Oferta leída desde la URL de un portal (POST /job-match/extract). */
export interface ExtractedJobOffer {
  jobTitle: string
  company: string | null
  rawDescription: string
  /** "datos-estructurados": leída sin IA (schema.org JobPosting) · "ia": aislada por Astro
   *  desde la página · "texto": ordenada por Astro desde un texto pegado. */
  source: "datos-estructurados" | "ia" | "texto"
  url: string
}

export interface UpdateJobStatusRequest {
  status: ApplicationStatus
}
