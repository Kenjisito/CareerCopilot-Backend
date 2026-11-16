import { lazy } from "react"

export { useAuth } from "@/features/auth/useAuth"
export { AuthProvider } from "@/features/auth/AuthProvider"
export { ProtectedRoute } from "@/features/auth/ProtectedRoute"
export { useSignIn, useSignOut, useSignUp } from "@/features/auth/hooks"

export const AuthPage = lazy(() =>
  import("@/features/auth/pages/AuthPage").then((module) => ({ default: module.AuthPage })),
)
