export type LogEvent =
  | "request started"
  | "request completed"
  | "request failed"
  | "request canceled"
  | "window error"
  | "unhandled rejection"
  | "react render failed"
  | "trace copy failed"

export type LogMetadata = {
  event: LogEvent
  method?: string
  route?: string
  status?: number
  durationMs?: number
  traceId?: string
  bodyLength?: number
  fieldNames?: readonly string[]
  errorType?: string
  messageLength?: number
}

type LogLevel = "debug" | "info" | "warn" | "error"

function sanitizeRoute(route: string): string {
  const path = route.split(/[?#]/, 1)[0] ?? ""
  return path
    .replace(/\/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, "/:id")
    .replace(/\/[^/]*(?:@|%40)[^/]*/gi, "/:param")
    .replace(/\/\d+(?=\/|$)/g, "/:id")
    .slice(0, 200)
}

function sanitizeMetadata(metadata: LogMetadata): Record<string, unknown> {
  const safe: Record<string, unknown> = {}

  if (metadata.method && /^[A-Za-z]{1,10}$/.test(metadata.method)) {
    safe.method = metadata.method.toUpperCase()
  }
  if (metadata.route) safe.route = sanitizeRoute(metadata.route)
  if (Number.isFinite(metadata.status)) safe.status = metadata.status
  if (Number.isFinite(metadata.durationMs)) {
    safe.durationMs = Math.max(0, Math.round(metadata.durationMs ?? 0))
  }
  if (metadata.traceId && /^[\w-]{1,128}$/.test(metadata.traceId)) {
    safe.traceId = metadata.traceId
  }
  if (Number.isFinite(metadata.bodyLength)) {
    safe.bodyLength = Math.max(0, Math.round(metadata.bodyLength ?? 0))
  }
  if (Number.isFinite(metadata.messageLength)) {
    safe.messageLength = Math.max(0, Math.round(metadata.messageLength ?? 0))
  }
  if (metadata.errorType) {
    safe.errorType = metadata.errorType.replace(/[^A-Za-z0-9_.-]/g, "").slice(0, 60)
  }
  if (metadata.fieldNames) {
    safe.fieldNames = metadata.fieldNames.map((field) =>
      /^[A-Za-z][A-Za-z0-9_.[\]]{0,79}$/.test(field) ? field : "unknown",
    )
  }

  return safe
}

function write(level: LogLevel, metadata: LogMetadata): void {
  if (!import.meta.env.DEV && level !== "warn" && level !== "error") return

  const prefix = `[CareerCopilot ${new Date().toISOString()}] ${metadata.event}`
  console[level](prefix, sanitizeMetadata(metadata))
}

export function debug(metadata: LogMetadata): void {
  write("debug", metadata)
}

export function info(metadata: LogMetadata): void {
  write("info", metadata)
}

export function warn(metadata: LogMetadata): void {
  write("warn", metadata)
}

export function error(metadata: LogMetadata): void {
  write("error", metadata)
}
