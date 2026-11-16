import React from "react"
import ReactDOM from "react-dom/client"
import { AppProviders } from "@/app/providers"
import App from "@/App"
import "@/index.css"
import { ErrorBoundary } from "@/shared/components/ErrorBoundary"
import { error as logError } from "@/shared/lib/logger"

window.addEventListener("error", (event) => {
  const caught = event.error
  logError({
    event: "window error",
    errorType: caught instanceof Error ? caught.name : "UnknownError",
    messageLength: typeof event.message === "string" ? event.message.length : undefined,
  })
})

window.addEventListener("unhandledrejection", (event) => {
  const reason = event.reason
  logError({
    event: "unhandled rejection",
    errorType: reason instanceof Error ? reason.name : typeof reason,
    messageLength: reason instanceof Error
      ? reason.message.length
      : typeof reason === "string"
        ? reason.length
        : undefined,
  })
})

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AppProviders>
        <App />
      </AppProviders>
    </ErrorBoundary>
  </React.StrictMode>,
)
