import { apiClient } from "@/shared/api/apiClient"
import { cvFileSchema } from "@/features/profile/schemas"
import { ApiError } from "@/shared/lib/apiError"
import type { ParsedCandidateProfileResponse } from "@/features/profile/types"

export interface AtsDiagnostic {
  score: number
  summary: string
  sections: {
    contactInfo: boolean
    workExperience: boolean
    education: boolean
    skills: boolean
  }
  strengths: string[]
  improvements: string[]
  missingKeywords: string[]
}

export function getLatestAtsDiagnostic(signal?: AbortSignal) {
  return apiClient<AtsDiagnostic | null>("/ats/latest", { signal })
}

export function parseCv(file: File, signal?: AbortSignal): Promise<ParsedCandidateProfileResponse> {
  const validation = cvFileSchema.safeParse(file)
  if (!validation.success) {
    throw new ApiError(
      400,
      "validation_error",
      validation.error.issues[0]?.message ?? "Selecciona un archivo PDF o DOCX válido.",
      "file",
    )
  }

  const body = new FormData()
  body.set("file", file)
  return apiClient<ParsedCandidateProfileResponse>("/cv-documents/parse", {
    method: "POST",
    body,
    signal,
  })
}

