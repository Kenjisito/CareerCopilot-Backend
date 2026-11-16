import { getSupabaseClient } from "@/shared/lib/supabase"
import {
  clearAuthSession,
  normalizeAuthSession,
  setAuthSession,
  type AuthSession,
} from "@/shared/lib/authSession"
import type { AuthCredentials, SignUpCredentials } from "@/features/auth/types"

export async function signIn(credentials: AuthCredentials): Promise<AuthSession> {
  const { data, error } = await getSupabaseClient().auth.signInWithPassword(credentials)
  if (error) throw new Error(error.message)
  if (!data.session) throw new Error("Supabase no devolvió una sesión válida.")
  const session = normalizeAuthSession(data.session)
  setAuthSession(session)
  return session
}

export async function signUp({
  email,
  password,
  fullName,
}: SignUpCredentials): Promise<{ session: AuthSession }> {
  const { data, error } = await getSupabaseClient().auth.signUp({
    email,
    password,
    options: { data: { full_name: fullName } },
  })
  if (error) throw new Error(error.message)
  if (!data.session) {
    throw new Error("Revisa tu correo y confirma la cuenta antes de iniciar sesión.")
  }
  const session = normalizeAuthSession(data.session)
  setAuthSession(session)
  return { session }
}

export async function signOut(): Promise<void> {
  const { error } = await getSupabaseClient().auth.signOut()
  if (error) throw new Error(error.message)
  clearAuthSession()
}
