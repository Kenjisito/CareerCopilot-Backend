import { toApiError } from "@/shared/api/problemDetails"
import { ApiError } from "@/shared/lib/apiError"
import { error as logError, info, warn } from "@/shared/lib/logger"
import {
  clearAuthSession,
  getActiveAuthSession,
} from "@/shared/lib/authSession"
import { getSupabaseClient, isSupabaseConfigured } from "@/shared/lib/supabase"
import { queryClient } from "@/shared/lib/queryClient"

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown> | unknown[] | null
  auth?: boolean
  responseType?: "json" | "blob"
  timeoutMs?: number
}

const apiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1")
  .trim()
  .replace(/\/+$/, "")

export async function apiClient<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    auth = true,
    responseType = "json",
    timeoutMs: requestedTimeout,
    signal: externalSignal,
    ...requestOptions
  } = options
  const headers = new Headers(options.headers)
  const isFormData = options.body instanceof FormData
  const isJsonBody =
    options.body !== undefined &&
    options.body !== null &&
    !isFormData &&
    typeof options.body !== "string" &&
    !(options.body instanceof Blob)

  headers.set("Accept", responseType === "blob" ? "application/pdf" : "application/json")
  if (isJsonBody) headers.set("Content-Type", "application/json; charset=utf-8")

  const body: BodyInit | null | undefined = isJsonBody
    ? JSON.stringify(options.body)
    : (options.body as BodyInit | null | undefined)
  const route = path.split(/[?#]/, 1)[0] ?? path
  const method = requestOptions.method ?? "GET"
  const timeoutMs = getTimeoutMs(route, requestedTimeout)
  const startedAt = Date.now()
  const controller = new AbortController()
  let timedOut = false
  const timeoutHandle = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  const forwardAbort = () => controller.abort(externalSignal?.reason)

  if (externalSignal?.aborted) forwardAbort()
  else externalSignal?.addEventListener("abort", forwardAbort, { once: true })

  info({
    event: "request started",
    method,
    route,
    bodyLength: getBodyLength(body),
  })

  let traceId: string | undefined
  try {
    const session = auth ? await getActiveAuthSession() : null
    if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`)
    else if (auth) headers.delete("Authorization")

    const response = await fetch(getRequestUrl(path), {
      ...requestOptions,
      headers,
      body,
      signal: controller.signal,
    })
    traceId = response.headers.get("X-Trace-Id") ?? undefined

    if (!response.ok) {
      const responseText = await response.text()
      const payload = parseJson(responseText)
      const retryHeader = response.headers.get("Retry-After")
      const retryAfter = retryHeader ? Number(retryHeader) : undefined
      const apiError = toApiError(
        payload,
        response.status,
        Number.isFinite(retryAfter) ? retryAfter : undefined,
        traceId,
      )
      if (response.status === 401) expireSession()
      if (response.status === 429) {
        window.dispatchEvent(
          new CustomEvent("api:quota-exceeded", {
            detail: { retryAfter: apiError.retryAfter, message: apiError.message },
          }),
        )
      }
      throw apiError
    }

    let result: T
    if (response.status === 204) result = undefined as T
    else if (responseType === "blob") result = (await response.blob()) as T
    else result = parseJson(await response.text()) as T

    info({
      event: "request completed",
      method,
      route,
      status: response.status,
      durationMs: Date.now() - startedAt,
      traceId,
    })
    return result
  } catch (caught) {
    const durationMs = Date.now() - startedAt
    if (caught instanceof ApiError) {
      warn({
        event: "request failed",
        method,
        route,
        status: caught.status,
        durationMs,
        traceId: caught.traceId ?? traceId,
        fieldNames: Object.keys(caught.fieldErrors ?? {}),
        errorType: caught.isNetworkError ? "NetworkError" : caught.name,
      })
      throw caught
    }
    if (externalSignal?.aborted && !timedOut) {
      info({ event: "request canceled", method, route, durationMs })
      throw caught
    }
    if (timedOut || caught instanceof TypeError) {
      const networkError = new ApiError(
        0,
        timedOut ? "timeout_error" : "network_error",
        "No se pudo conectar con el servidor",
        undefined,
        undefined,
        undefined,
        undefined,
        true,
      )
      warn({
        event: "request failed",
        method,
        route,
        status: 0,
        durationMs,
        traceId,
        errorType: timedOut ? "TimeoutError" : "NetworkError",
      })
      throw networkError
    }

    logError({
      event: "request failed",
      method,
      route,
      durationMs,
      traceId,
      errorType: caught instanceof Error ? caught.name : "UnknownError",
      messageLength: caught instanceof Error ? caught.message.length : undefined,
    })
    throw caught
  } finally {
    clearTimeout(timeoutHandle)
    externalSignal?.removeEventListener("abort", forwardAbort)
  }
}

function getTimeoutMs(path: string, requestedTimeout?: number): number {
  if (requestedTimeout !== undefined && Number.isFinite(requestedTimeout) && requestedTimeout > 0) {
    return requestedTimeout
  }
  if (
    path === "/job-match/analyze" ||
    path === "/cv-documents/parse" ||
    path === "/api/job-match/analyze" ||
    path === "/api/cv-documents/parse"
  ) return 90_000
  return 30_000
}

function getBodyLength(body: BodyInit | null | undefined): number | undefined {
  if (typeof body === "string") return body.length
  if (body instanceof Blob) return body.size
  if (body instanceof FormData) {
    let length = 0
    body.forEach((value) => {
      length += typeof value === "string" ? value.length : value.size
    })
    return length
  }
  if (body instanceof URLSearchParams) return body.toString().length
  if (body instanceof ArrayBuffer) return body.byteLength
  if (ArrayBuffer.isView(body)) return body.byteLength
  return undefined
}

function parseJson(text: string): unknown {
  if (!text) return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    return null
  }
}

function getRequestUrl(path: string): string {
  const apiPath = path.startsWith("/api/") ? path.slice(4) : path
  return `${apiUrl}${apiPath.startsWith("/") ? apiPath : `/${apiPath}`}`
}

function expireSession(): void {
  clearAuthSession()
  queryClient.clear()
  if (isSupabaseConfigured()) {
    void getSupabaseClient().auth.signOut({ scope: "local" }).then(({ error }) => {
      if (error) {
        logError({ event: "request failed", errorType: error.name })
      }
    }).catch((caught: unknown) => {
      logError({
        event: "request failed",
        errorType: caught instanceof Error ? caught.name : "UnknownError",
      })
    })
  }
  window.dispatchEvent(new Event("auth:unauthorized"))
}

