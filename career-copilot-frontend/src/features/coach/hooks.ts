import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createInterview,
  getInterview,
  sendInterviewMessage,
} from "@/features/coach/api"
import type {
  InterviewSessionResponse,
  SendInterviewMessageRequest,
  StartInterviewRequest,
} from "@/features/coach/types"
import { queryKeys } from "@/shared/lib/queryKeys"

export const interviewQueryKey = (id: string) => [...queryKeys.interviews, id] as const

export function useCreateInterview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ request, signal }: { request: StartInterviewRequest; signal: AbortSignal }) =>
      createInterview(request, signal),
    onSuccess: (session) => {
      queryClient.setQueryData<InterviewSessionResponse>(interviewQueryKey(session.id), session)
    },
  })
}

export function useInterview(id: string | null) {
  return useQuery({
    queryKey: id ? interviewQueryKey(id) : queryKeys.interviews,
    queryFn: ({ signal }) => {
      if (!id) throw new Error("Falta el identificador de la entrevista.")
      return getInterview(id, signal)
    },
    enabled: Boolean(id),
  })
}

export function useSendInterviewMessage(id: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ content, signal }: SendInterviewMessageRequest & { signal: AbortSignal }) => {
      if (!id) throw new Error("Inicia una entrevista antes de enviar mensajes.")
      return sendInterviewMessage(id, { content }, signal)
    },
    onSuccess: (session) => {
      queryClient.setQueryData<InterviewSessionResponse>(interviewQueryKey(session.id), session)
    },
  })
}
