import { useEffect, useState, type ReactNode } from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { useLocation, useNavigate } from "react-router-dom"
import { AuthProvider } from "@/features/auth"
import { queryClient } from "@/shared/lib/queryClient"
import { AppRouter } from "@/app/router"

function NavigationEvents({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [quota, setQuota] = useState<{ retryAfter?: number; message?: string } | null>(null)

  useEffect(() => {
    const unauthorized = () =>
      navigate("/login", { replace: true, state: { from: location } })
    const quotaExceeded = (event: Event) => {
      const detail = (event as CustomEvent<{ retryAfter?: number; message?: string }>).detail
      setQuota(detail)
    }
    window.addEventListener("auth:unauthorized", unauthorized)
    window.addEventListener("api:quota-exceeded", quotaExceeded)
    return () => {
      window.removeEventListener("auth:unauthorized", unauthorized)
      window.removeEventListener("api:quota-exceeded", quotaExceeded)
    }
  }, [location, navigate])

  return (
    <>
      {children}
      {quota && (
        <div
          role="presentation"
          onClick={() => setQuota(null)}
          style={{ position: "fixed", inset: 0, zIndex: 1000, display: "grid", placeItems: "center", background: "rgba(17,24,63,.45)", padding: 20 }}
        >
          <section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="quota-title"
            className="form-panel"
            onClick={(event) => event.stopPropagation()}
            style={{ width: "min(100%, 480px)" }}
          >
            <h2 id="quota-title">Límite de uso alcanzado</h2>
            <p>{quota.message ?? "Has alcanzado la cuota disponible para tu plan."}</p>
            {quota.retryAfter !== undefined && (
              <p>Inténtalo nuevamente en {quota.retryAfter} segundos.</p>
            )}
            <button className="btn btn-primary" onClick={() => setQuota(null)}>Entendido</button>
          </section>
        </div>
      )}
    </>
  )
}

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRouter>
        <AuthProvider>
          <NavigationEvents>{children}</NavigationEvents>
        </AuthProvider>
      </AppRouter>
    </QueryClientProvider>
  )
}
