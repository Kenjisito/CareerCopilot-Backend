import { ApiError } from "@/shared/lib/apiError"
import { toApiError } from "@/shared/api/problemDetails"
import { appEnv } from "@/shared/lib/env"
import { clearAuthSession, getAuthSession } from "@/shared/lib/authSession"

export async function uploadWithProgress<T>(
  path: string,
  formData: FormData,
  onProgress: (progress: number) => void,
  method: "POST" | "PUT" = "POST",
): Promise<T> {
  const session = getAuthSession()

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const requestPath = path.startsWith("/api/")
      ? path
      : `/api${path.startsWith("/") ? path : `/${path}`}`
    xhr.open(method, `${appEnv.apiUrl}${requestPath}`)
    xhr.setRequestHeader("Accept", "application/json")
    if (session?.access_token) {
      xhr.setRequestHeader("Authorization", "Bearer " + session.access_token)
    }
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
    }
    xhr.onerror = () =>
      reject(new ApiError(0, "network_error", "No fue posible conectar con el servidor."))
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        if (xhr.status === 204 || !xhr.responseText) {
          resolve(undefined as T)
          return
        }
        try {
          resolve(JSON.parse(xhr.responseText) as T)
        } catch {
          reject(new Error("La respuesta de subida no contiene JSON válido."))
        }
        return
      }
      let body: unknown
      try {
        body = JSON.parse(xhr.responseText) as unknown
      } catch {
        body = null
      }
      const retryAfterHeader = xhr.getResponseHeader("Retry-After")
      const retryAfter = retryAfterHeader ? Number(retryAfterHeader) : undefined
      const apiError = toApiError(
        body,
        xhr.status,
        retryAfter !== undefined && Number.isFinite(retryAfter) ? retryAfter : undefined,
      )
      if (xhr.status === 401) {
        clearAuthSession()
        window.dispatchEvent(new Event("auth:unauthorized"))
      }
      if (xhr.status === 429) {
        window.dispatchEvent(
          new CustomEvent("api:quota-exceeded", {
            detail: { retryAfter, message: apiError.message },
          }),
        )
      }
      reject(apiError)
    }
    xhr.send(formData)
  })
}
