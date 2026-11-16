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

export interface UpdateJobStatusRequest {
  status: ApplicationStatus
}
