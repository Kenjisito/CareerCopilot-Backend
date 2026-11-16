import { useEffect, useState, type ReactNode } from "react"
import { AuthContext, type AuthState } from "@/features/auth/context"
import { useProfileDraftStore } from "@/features/profile/store"
import { queryClient } from "@/shared/lib/queryClient"
import {
  clearAuthSession,
  normalizeAuthSession,
  setAuthSession,
} from "@/shared/lib/authSession"
import { getSupabaseClient } from "@/shared/lib/supabase"

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ session: null, loading: true, error: null })

  useEffect(() => {
    let active = true
    let unsubscribe = () => {}

    const applySession = (session: Parameters<typeof normalizeAuthSession>[0] | null) => {
      if (!active) return
      if (session) {
        const normalized = normalizeAuthSession(session)
        setAuthSession(normalized)
        setState({ session: { user: normalized.user }, loading: false, error: null })
      } else {
        clearAuthSession()
        queryClient.clear()
        useProfileDraftStore.getState().clearDraft()
        setState({ session: null, loading: false, error: null })
      }
    }

    void Promise.resolve()
      .then(() => {
        if (!active) return null
        const supabase = getSupabaseClient()
        const { data } = supabase.auth.onAuthStateChange((_event, session) => {
          applySession(session)
        })
        unsubscribe = () => data.subscription.unsubscribe()
        return supabase.auth.getSession()
      })
      .then((result) => {
        if (!active || !result) return
        if (result.error) {
          setState({ session: null, loading: false, error: result.error.message })
          return
        }
        applySession(result.data.session)
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            session: null,
            loading: false,
            error: error instanceof Error ? error.message : "No se pudo validar la sesión.",
          })
        }
      })

    return () => {
      active = false
      unsubscribe()
    }
  }, [])

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>
}
