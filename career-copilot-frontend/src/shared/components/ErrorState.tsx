import type { ReactNode } from "react"
import { ApiError } from "@/shared/lib/apiError"
import { warn } from "@/shared/lib/logger"

type ErrorStateProps = {
  message: string
  onRetry: () => void
  title?: string
  children?: ReactNode
  traceId?: string
  error?: unknown
}

export function ErrorState({
  message,
  onRetry,
  title = "No pudimos cargar la información",
  children,
  traceId,
  error,
}: ErrorStateProps) {
  const referenceId =
    traceId ??
    (error instanceof ApiError && error.status >= 500 ? error.traceId : undefined)

  return (
    <section className="error-state" role="alert">
      <h2>{title}</h2>
      <p>{message}</p>
      {referenceId && (
        <button
          className="error-trace-id"
          type="button"
          aria-label="Copiar código de referencia"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(referenceId)
            } catch (caught) {
              warn({
                event: "trace copy failed",
                errorType: caught instanceof Error ? caught.name : "UnknownError",
              })
            }
          }}
        >
          Código de referencia: <code>{referenceId}</code>
        </button>
      )}
      {children}
      <button className="btn btn-primary" type="button" onClick={onRetry}>
        Reintentar
      </button>
    </section>
  )
}
