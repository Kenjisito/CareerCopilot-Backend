import { QueryClient } from "@tanstack/react-query"
import { ApiError } from "@/shared/lib/apiError"

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false
        }
        if (error instanceof ApiError && error.status >= 500) return failureCount < 2
        return failureCount < 2
      },
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
})
