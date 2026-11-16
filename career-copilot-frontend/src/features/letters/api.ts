import { apiClient } from "@/shared/api/apiClient"
import type { CoverLetterResponse, GenerateCoverLetterRequest } from "@/features/letters/types"

interface BackendEmail {
  id: string
  subject: string
  body: string
  jobMatchId: string
  tone: string
  createdAt: string
}

function toCoverLetter(email: BackendEmail): CoverLetterResponse {
  const tone = email.tone.toLowerCase()
  return {
    id: email.id,
    subject: email.subject,
    body: email.body,
    content: `${email.subject}\n\n${email.body}`,
    jobAnalysisId: email.jobMatchId,
    tone: tone === "formal" ? "Formal" : tone === "executive" ? "Executive" : "Dynamic",
    createdAt: email.createdAt,
  }
}

export function createCoverLetter(
  request: GenerateCoverLetterRequest,
  signal?: AbortSignal,
): Promise<CoverLetterResponse> {
  return apiClient<BackendEmail>("/email/generate", {
    method: "POST",
    body: { jobMatchId: request.jobAnalysisId, tone: request.tone.toLowerCase() },
    signal,
  }).then(toCoverLetter)
}

export function getCoverLetter(id: string, signal?: AbortSignal): Promise<CoverLetterResponse> {
  return apiClient<BackendEmail>(`/email/${encodeURIComponent(id)}`, { signal }).then(toCoverLetter)
}
