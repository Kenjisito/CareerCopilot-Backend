import { getSupabaseClient } from "@/shared/lib/supabase"
import {
  clearAuthSession,
  normalizeAuthSession,
  setAuthSession,
  type AuthSession,
} from "@/shared/lib/authSession"
import type { AuthCredentials, SignUpCredentials } from "@/features/auth/types"

/** Supabase responde en inglés ("Invalid login credentials"...): se traduce al español. */
export function authErrorMessage(error: { message: string; code?: string }): string {
  const code = error.code ?? ""
  const message = error.message.toLowerCase()
  if (code === "invalid_credentials" || message.includes("invalid login credentials")) {
    return "Correo o contraseña incorrectos."
  }
  if (code === "email_not_confirmed" || message.includes("email not confirmed")) {
    return "Debes confirmar tu correo antes de iniciar sesión. Revisa tu bandeja de entrada y la carpeta de spam."
  }
  if (code === "user_already_exists" || message.includes("already registered")) {
    return "Ya existe una cuenta con ese correo. Inicia sesión."
  }
  if (code === "weak_password" || message.includes("password should be")) {
    return "La contraseña debe tener al menos 6 caracteres."
  }
  if (code.includes("rate_limit") || message.includes("rate limit")) {
    return "Se hicieron demasiados intentos. Espera unos minutos e inténtalo de nuevo."
  }
  if (message.includes("failed to fetch") || message.includes("network")) {
    return "No se pudo conectar con el servicio de autenticación. Revisa tu conexión."
  }
  return error.message
}

export async function signIn(credentials: AuthCredentials): Promise<AuthSession> {
  const { data, error } = await getSupabaseClient().auth.signInWithPassword(credentials)
  if (error) throw new Error(authErrorMessage(error))
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
  if (error) throw new Error(authErrorMessage(error))
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
