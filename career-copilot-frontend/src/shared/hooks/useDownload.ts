import { apiClient } from "@/shared/lib/apiClient"

interface SignedDownload {
  url: string
}

export function useDownload() {
  return async (endpoint: string, filename?: string) => {
    const { url } = await apiClient<SignedDownload>(endpoint)
    const anchor = document.createElement("a")
    anchor.href = url
    if (filename) anchor.download = filename
    anchor.rel = "noopener noreferrer"
    document.body.append(anchor)
    anchor.click()
    anchor.remove()
  }
}
