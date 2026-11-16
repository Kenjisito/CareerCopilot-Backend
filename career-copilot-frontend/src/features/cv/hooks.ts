import { useMutation, useQueryClient } from "@tanstack/react-query"
import { parseCv } from "@/features/cv/api"
import { queryKeys } from "@/shared/lib/queryKeys"

export function useParseCv() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, signal }: { file: File; signal: AbortSignal }) =>
      parseCv(file, signal),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.cvAts }),
  })
}
