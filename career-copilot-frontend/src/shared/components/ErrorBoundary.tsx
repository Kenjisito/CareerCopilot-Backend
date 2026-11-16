import { Component, type ReactNode } from "react"
import { error as logError } from "@/shared/lib/logger"

type ErrorBoundaryProps = {
  children: ReactNode
}

type ErrorBoundaryState = {
  hasError: boolean
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(caught: Error): void {
    logError({
      event: "react render failed",
      errorType: caught.name,
      messageLength: caught.message.length,
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="global-error-state" role="alert">
          <h1>Ocurrió un error inesperado</h1>
          <p>Recarga la página para volver a intentarlo.</p>
          <button className="btn btn-primary" type="button" onClick={() => window.location.reload()}>
            Recargar
          </button>
        </main>
      )
    }

    return this.props.children
  }
}
