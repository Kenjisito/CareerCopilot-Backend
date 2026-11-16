import { useMutation } from "@tanstack/react-query"
import { useLocation, useNavigate } from "react-router-dom"
import { signIn, signOut, signUp } from "@/features/auth/api"
import type { AuthCredentials, SignUpCredentials } from "@/features/auth/types"
import { queryClient } from "@/shared/lib/queryClient"

export function useSignIn() {
  const navigate = useNavigate()
  const location = useLocation()
  const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname
  return useMutation({
    mutationFn: (credentials: AuthCredentials) => signIn(credentials),
    onSuccess: async () => {
      await queryClient.invalidateQueries()
      navigate(destination ?? "/dashboard", { replace: true })
    },
  })
}

export function useSignUp() {
  const navigate = useNavigate()
  return useMutation({
    mutationFn: (credentials: SignUpCredentials) => signUp(credentials),
    onSuccess: () => navigate("/onboarding", { replace: true }),
  })
}

export function useSignOut() {
  const navigate = useNavigate()
  return useMutation({
    mutationFn: signOut,
    onSuccess: async () => {
      queryClient.clear()
      navigate("/", { replace: true })
    },
  })
}
