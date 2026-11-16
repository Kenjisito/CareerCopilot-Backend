import { lazy, Suspense } from "react"
import { Route, Routes, useNavigate } from "react-router-dom"
import { AuthPage, useSignOut } from "@/features/auth"
import { AppSkeleton } from "@/shared/Skeleton"
import { ProfileRouteGate, ProtectedRoutes, PublicRoutes } from "@/app/router"

const Landing = lazy(() =>
  import("@/features/landing").then((module) => ({ default: module.Landing })),
)
const Onboarding = lazy(() =>
  import("@/features/onboarding").then((module) => ({ default: module.Onboarding })),
)
const Dashboard = lazy(() =>
  import("@/features/dashboard").then((module) => ({ default: module.Dashboard })),
)

export function AppRoutes() {
  const navigate = useNavigate()
  const signOut = useSignOut()

  return (
    <Suspense fallback={<AppSkeleton />}>
      <Routes>
        <Route
          path="/"
          element={<Landing onStart={() => navigate("/register")} onLogin={() => navigate("/login")} />}
        />
        <Route element={<PublicRoutes />}>
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
        </Route>
        <Route element={<ProtectedRoutes />}>
          <Route path="/onboarding" element={<Onboarding onFinish={() => navigate("/dashboard")} />} />
          <Route element={<ProfileRouteGate />}>
            <Route path="/dashboard" element={<Dashboard onHome={() => signOut.mutate()} />} />
          </Route>
        </Route>
        <Route
          path="*"
          element={<Landing onStart={() => navigate("/register")} onLogin={() => navigate("/login")} />}
        />
      </Routes>
    </Suspense>
  )
}
