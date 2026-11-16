import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  analyzeJobMatch,
  extractJobOffer,
  extractJobOfferFromText,
  getJobMatch,
  getJobMatches,
  updateApplicationStatus,
} from "@/features/jobmatch/api"
import type {
  AnalyzeJobRequest,
  JobAnalysisResponse,
  UpdateJobStatusRequest,
} from "@/features/jobmatch/types"
import { queryKeys } from "@/shared/lib/queryKeys"

export const jobMatchQueryKey = queryKeys.jobMatchResults({})

export function useJobMatches() {
  return useQuery({
    queryKey: jobMatchQueryKey,
    queryFn: ({ signal }) => getJobMatches(signal),
  })
}

export function useJobMatch(id: string | null) {
  return useQuery({
    queryKey: queryKeys.jobMatchAnalysis(id ?? ""),
    queryFn: ({ signal }) => {
      if (!id) throw new Error("Se requiere el identificador del análisis.")
      return getJobMatch(id, signal)
    },
    enabled: id !== null,
  })
}

export function useAnalyzeJobMatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ request, signal }: { request: AnalyzeJobRequest; signal: AbortSignal }) =>
      analyzeJobMatch(request, signal),
    onSuccess: (result) => {
      queryClient.setQueryData<JobAnalysisResponse[]>(jobMatchQueryKey, (current) =>
        [result, ...(current ?? []).filter((item) => item.id !== result.id)],
      )
    },
  })
}

export type ExtractJobOfferInput =
  | { url: string; text?: undefined; signal?: AbortSignal }
  | { text: string; url?: undefined; signal?: AbortSignal }

/** Trae una oferta desde un enlace o desde un texto copiado de cualquier página. */
export function useExtractJobOffer() {
  return useMutation({
    mutationFn: (input: ExtractJobOfferInput) =>
      input.url !== undefined
        ? extractJobOffer(input.url, input.signal)
        : extractJobOfferFromText(input.text, input.signal),
  })
}

export function useUpdateApplicationStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      applicationId,
      request,
      signal,
    }: {
      applicationId: string
      request: UpdateJobStatusRequest
      signal: AbortSignal
    }) => updateApplicationStatus(applicationId, request, signal),
    onMutate: async ({ applicationId, request }) => {
      await queryClient.cancelQueries({ queryKey: jobMatchQueryKey })
      const previous = queryClient.getQueryData<JobAnalysisResponse[]>(jobMatchQueryKey)
      queryClient.setQueryData<JobAnalysisResponse[]>(jobMatchQueryKey, (current) =>
        current?.map((item) =>
          item.id === applicationId ? { ...item, status: request.status } : item,
        ),
      )
      return { previous }
    },
    onError: (_error, _variables, context) => {
      if (context) queryClient.setQueryData(jobMatchQueryKey, context.previous)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: jobMatchQueryKey })
    },
  })
}
