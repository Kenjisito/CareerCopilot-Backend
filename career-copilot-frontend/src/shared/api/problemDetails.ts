import { ApiError } from "@/shared/lib/apiError"

export interface ProblemDetails {
  type?: string
  title?: string
  status?: number
  detail?: string
  instance?: string
  errors?: Record<string, string | string[]>
  [extension: string]: unknown
}

type LegacyApiError = {
  error?: {
    code?: string
    message?: string
    field?: string
  }
}

const statusMessages: Record<number, string> = {
  413: "El archivo supera el límite máximo de 2 MB.",
  429: "Límite de consultas de IA alcanzado. Espera unos segundos e intenta de nuevo.",
  502: "El servicio de IA no está disponible, intenta de nuevo.",
  503: "El servicio de IA no está disponible, intenta de nuevo.",
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function normalizeValidationErrors(
  errors: ProblemDetails["errors"],
): Record<string, string[]> | undefined {
  if (!errors) return undefined

  const normalized: Record<string, string[]> = {}
  for (const [field, messages] of Object.entries(errors)) {
    if (typeof messages === "string") normalized[field] = [messages]
    else if (Array.isArray(messages)) {
      normalized[field] = messages.filter((message): message is string => typeof message === "string")
    }
  }
  return Object.keys(normalized).length > 0 ? normalized : undefined
}

export function toApiError(
  payload: unknown,
  status: number,
  retryAfter?: number,
  headerTraceId?: string | null,
): ApiError {
  const body = isRecord(payload) ? payload : {}
  const legacy = body as LegacyApiError
  const problem = body as ProblemDetails
  const legacyError = legacy.error
  const validationErrors = normalizeValidationErrors(problem.errors)
  const code =
    (typeof legacyError?.code === "string" && legacyError.code) ||
    (status === 400 ? "validation_error" : `http_${status}`)
  const bodyTraceId = typeof problem.traceId === "string" ? problem.traceId : undefined
  const traceId = headerTraceId || bodyTraceId
  const message =
    status === 401
      ? "Sesión expirada"
      : status === 500
        ? "Ocurrió un error inesperado"
        : statusMessages[status] ??
          (typeof legacyError?.message === "string" && legacyError.message) ??
          (typeof problem.detail === "string" && problem.detail) ??
          (typeof problem.title === "string" && problem.title) ??
          (status === 400
            ? "Revisa los datos ingresados e inténtalo nuevamente."
            : "Ocurrió un error. Inténtalo nuevamente.")

  return new ApiError(
    status,
    code,
    message,
    typeof legacyError?.field === "string" ? legacyError.field : undefined,
    retryAfter,
    validationErrors,
    traceId,
  )
}
