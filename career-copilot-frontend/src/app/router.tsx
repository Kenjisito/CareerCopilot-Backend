import type { ReactNode } from "react"
import { BrowserRouter, Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "@/features/auth/useAuth"
import { useProfile } from "@/features/profile"
import { ApiError } from "@/shared/lib/apiError"
import { ErrorState } from "@/shared/components"
import { AppSkeleton } from "@/shared/Skeleton"

export function ProtectedRoutes() {
  const { session, loading, error } = useAuth()
  const location = useLocation()

  if (loading) return <AppSkeleton />
  if (error) return <main className="onboarding-main" role="alert">{error}</main>
  if (!session) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

export function PublicRoutes() {
  const { session, loading, error } = useAuth()
  const location = useLocation()

  if (loading) return <AppSkeleton />
  if (error) return <main className="onboarding-main" role="alert">{error}</main>
  if (!session) return <Outlet />

  const state = location.state as { from?: { pathname?: string } | string } | null
  const requestedPath =
    typeof state?.from === "string" ? state.from : state?.from?.pathname
  const isInternalPath =
    requestedPath?.startsWith("/") && !requestedPath.startsWith("//") &&
    requestedPath !== "/login" && requestedPath !== "/register"
  const destination =
    (isInternalPath ? requestedPath : undefined) ??
    (location.pathname === "/register" ? "/onboarding" : "/dashboard")

  return <Navigate to={destination} replace />
}

export function ProfileRouteGate() {
  const profile = useProfile()

  if (profile.isLoading) return <AppSkeleton />
  if (profile.isError) {
    if (profile.error instanceof ApiError && profile.error.status === 404) {
      return <Navigate to="/onboarding" replace />
    }
    return (
      <main className="dashboard-state">
        <ErrorState
          message={profile.error instanceof Error ? profile.error.message : "No se pudo cargar tu perfil."}
          onRetry={() => void profile.refetch()}
          error={profile.error}
        />
      </main>
    )
  }
  if (!profile.data) return <Navigate to="/onboarding" replace />
  return <Outlet />
}

export function AppRouter({ children }: { children: ReactNode }) {
  return <BrowserRouter>{children}</BrowserRouter>
}
