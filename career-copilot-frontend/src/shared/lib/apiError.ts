export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly field?: string
  readonly retryAfter?: number
  readonly validationErrors?: Record<string, string[]>
  readonly fieldErrors?: Record<string, string[]>
  readonly traceId?: string
  readonly isNetworkError: boolean

  constructor(
    status: number,
    code: string,
    message: string,
    field?: string,
    retryAfter?: number,
    validationErrors?: Record<string, string[]>,
    traceId?: string,
    isNetworkError = false,
  ) {
    super(message)
    this.status = status
    this.code = code
    this.field = field
    this.retryAfter = retryAfter
    this.validationErrors = validationErrors
    this.fieldErrors = validationErrors ?? (field ? { [field]: [message] } : undefined)
    this.traceId = traceId
    this.isNetworkError = isNetworkError
    this.name = "ApiError"
  }
}
