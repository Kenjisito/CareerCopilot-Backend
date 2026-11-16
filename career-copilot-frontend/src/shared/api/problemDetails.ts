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

// Solo se usan si el backend no envía un mensaje propio (FastAPI manda `detail`
// en español con la causa concreta: CV faltante, límite del plan, etc.).
const statusMessages: Record<number, string> = {
  413: "El archivo supera el tamaño máximo permitido.",
  429: "Límite de consultas de IA alcanzado. Espera unos minutos e intenta de nuevo.",
  502: "El servicio de IA no está disponible, intenta de nuevo.",
  503: "El servicio de IA no está disponible, intenta de nuevo.",
  504: "La IA tardó demasiado en responder, intenta de nuevo.",
}

const VALIDATION_MESSAGE = "Revisa los datos ingresados e inténtalo nuevamente."

/** Primer valor que sea un texto no vacío (evita que `false`/`""` lleguen como mensaje). */
function firstText(...values: unknown[]): string | undefined {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value
  }
  return undefined
}

/** FastAPI/Pydantic: `detail: [{ loc: ["body", "campo"], msg: "..." }]` → `{ campo: ["..."] }`. */
function fastApiValidationErrors(detail: unknown): Record<string, string[]> | undefined {
  if (!Array.isArray(detail)) return undefined
  const normalized: Record<string, string[]> = {}
  for (const item of detail) {
    if (!isRecord(item) || typeof item.msg !== "string") continue
    const loc = Array.isArray(item.loc) ? item.loc : []
    const field = String(loc[loc.length - 1] ?? "general")
    normalized[field] = [...(normalized[field] ?? []), item.msg]
  }
  return Object.keys(normalized).length > 0 ? normalized : undefined
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
  const rawDetail: unknown = problem.detail
  const validationErrors =
    normalizeValidationErrors(problem.errors) ?? fastApiValidationErrors(rawDetail)
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
        : firstText(
            legacyError?.message,
            rawDetail,
            Array.isArray(rawDetail) ? VALIDATION_MESSAGE : undefined,
            statusMessages[status],
            problem.title,
          ) ??
          (status === 400 || status === 422
            ? VALIDATION_MESSAGE
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
