import { apiClient } from "@/shared/api/apiClient"
import type {
  InterviewSessionResponse,
  SendInterviewMessageRequest,
  StartInterviewRequest,
} from "@/features/coach/types"

interface InterviewStartResponse {
  entrevistaId: string
  respuesta: string
}

interface InterviewMessageResponse {
  finalizada: boolean
}

export async function createInterview(
  request: StartInterviewRequest,
  signal?: AbortSignal,
): Promise<InterviewSessionResponse> {
  if (!request.jobMatchId) throw new Error("Selecciona una oferta analizada para iniciar la entrevista.")
  const response = await apiClient<InterviewStartResponse>("/interview/start", {
    method: "POST",
    body: { jobMatchId: request.jobMatchId },
    signal,
  })
  return {
    id: response.entrevistaId,
    targetRole: request.targetRole,
    startedAt: new Date().toISOString(),
    completedAt: null,
    score: null,
    feedback: null,
    messages: [{
      id: `${response.entrevistaId}-first`,
      role: "Astro",
      content: response.respuesta,
      score: null,
      feedback: null,
      createdAt: new Date().toISOString(),
    }],
  }
}

export function getInterview(id: string, signal?: AbortSignal): Promise<InterviewSessionResponse> {
  return apiClient<InterviewSessionResponse>(`/interview/${encodeURIComponent(id)}`, { signal })
}

export async function sendInterviewMessage(
  id: string,
  request: SendInterviewMessageRequest,
  signal?: AbortSignal,
): Promise<InterviewSessionResponse> {
  const response = await apiClient<InterviewMessageResponse>(
    `/interview/${encodeURIComponent(id)}/message`,
    { method: "POST", body: { contenido: request.content }, signal },
  )
  if (response.finalizada) {
    await apiClient(`/interview/${encodeURIComponent(id)}/finish`, { method: "POST", signal })
  }
  return getInterview(id, signal)
}
