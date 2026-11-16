import { useMutation, useQuery } from "@tanstack/react-query"
import { createCoverLetter, getCoverLetter } from "@/features/letters/api"
import type { GenerateCoverLetterRequest } from "@/features/letters/types"
import { queryKeys } from "@/shared/lib/queryKeys"

export const coverLetterQueryKey = (id: string) => [...queryKeys.letters, id] as const

export function useCreateCoverLetter() {
  return useMutation({
    mutationFn: ({ request, signal }: { request: GenerateCoverLetterRequest; signal: AbortSignal }) =>
      createCoverLetter(request, signal),
  })
}

export function useCoverLetter(id: string | null) {
  return useQuery({
    queryKey: id ? coverLetterQueryKey(id) : queryKeys.letters,
    queryFn: ({ signal }) => {
      if (!id) throw new Error("Falta el identificador de la carta.")
      return getCoverLetter(id, signal)
    },
    enabled: Boolean(id),
  })
}
