import { createContext } from "react"
import type { AuthSession } from "@/shared/lib/authSession"

export interface AuthState {
  session: Pick<AuthSession, "user"> | null
  loading: boolean
  error: string | null
}

export const AuthContext = createContext<AuthState | null>(null)
