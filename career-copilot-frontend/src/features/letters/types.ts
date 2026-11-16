export type CoverLetterTone = "Formal" | "Dynamic" | "Executive"

export interface GenerateCoverLetterRequest {
  jobAnalysisId: string
  tone: CoverLetterTone
}

export interface CoverLetterResponse {
  id: string
  subject: string
  body: string
  content: string
  jobAnalysisId: string
  tone: CoverLetterTone
  createdAt: string
}
