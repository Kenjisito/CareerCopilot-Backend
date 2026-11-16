import { getSupabaseClient } from "@/shared/lib/supabase"

export interface AuthUser {
  id: string
  email: string
  full_name: string
}

export interface AuthSession {
  access_token: string
  expires_at: number
  user: AuthUser
}

const storageKey = "career-copilot-auth"
let memorySession: AuthSession | null = null

function getStorage(): Storage | null {
  if (typeof window === "undefined") return null
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

function removeLegacySession(): void {
  try {
    window.localStorage.removeItem(storageKey)
  } catch {
    return
  }
}

function isAuthSession(value: unknown): value is AuthSession {
  if (!value || typeof value !== "object") return false
  const session = value as Partial<AuthSession>
  return (
    typeof session.access_token === "string" &&
    session.access_token.length > 0 &&
    typeof session.expires_at === "number" &&
    Number.isFinite(session.expires_at) &&
    Boolean(session.user) &&
    typeof session.user?.id === "string" &&
    typeof session.user.email === "string" &&
    typeof session.user.full_name === "string"
  )
}

export function getAuthSession(): AuthSession | null {
  removeLegacySession()
  const storage = getStorage()
  if (!storage) return memorySession

  let serialized: string | null
  try {
    serialized = storage.getItem(storageKey)
  } catch {
    return memorySession
  }
  if (!serialized) return memorySession

  let parsed: unknown
  try {
    parsed = JSON.parse(serialized)
  } catch {
    try {
      storage.removeItem(storageKey)
    } catch {
      memorySession = null
    }
    memorySession = null
    return null
  }
  if (isAuthSession(parsed)) {
    memorySession = parsed
    return parsed
  }
  try {
    storage.removeItem(storageKey)
  } catch {
    memorySession = null
  }
  memorySession = null
  return null
}

export async function getActiveAuthSession(): Promise<AuthSession | null> {
  const session = getAuthSession()
  if (!session || session.expires_at > Math.floor(Date.now() / 1000) + 30) return session

  const { data, error } = await getSupabaseClient().auth.getSession()
  if (error) throw new Error(error.message)
  if (!data.session) {
    clearAuthSession()
    return null
  }
  const refreshed = normalizeAuthSession(data.session)
  setAuthSession(refreshed)
  return refreshed
}

export function setAuthSession(session: AuthSession): void {
  memorySession = session
  removeLegacySession()
  try {
    getStorage()?.setItem(storageKey, JSON.stringify(session))
  } catch {
    try {
      getStorage()?.removeItem(storageKey)
    } catch {
      memorySession = session
    }
    memorySession = session
  }
  window.dispatchEvent(new Event("auth:changed"))
}

export function clearAuthSession(): void {
  memorySession = null
  removeLegacySession()
  try {
    getStorage()?.removeItem(storageKey)
  } catch {
    memorySession = null
  }
  window.dispatchEvent(new Event("auth:changed"))
}

export function normalizeAuthSession(
  payload: {
    access_token: unknown
    expires_at?: unknown
    user: { id?: unknown; email?: unknown; user_metadata?: Record<string, unknown> } | null
  },
): AuthSession {
  const accessToken = payload.access_token
  const user = payload.user
  const email = user?.email
  const id = user?.id
  const expiresAt = payload.expires_at ?? Math.floor(Date.now() / 1000) + 3600

  if (typeof accessToken !== "string" || accessToken.length === 0) {
    throw new Error("La respuesta de autenticación no contiene un token válido.")
  }
  if (typeof id !== "string" || typeof email !== "string") {
    throw new Error("La respuesta de autenticación no incluye una identidad válida.")
  }
  if (typeof expiresAt !== "number" || !Number.isFinite(expiresAt)) {
    throw new Error("La respuesta de autenticación no incluye una fecha de expiración válida.")
  }

  const metadata = user?.user_metadata ?? {}
  const fullName = metadata.full_name ?? metadata.name
  return {
    access_token: accessToken,
    expires_at: expiresAt,
    user: {
      id,
      email,
      full_name: typeof fullName === "string" ? fullName : email.split("@")[0],
    },
  }
}

