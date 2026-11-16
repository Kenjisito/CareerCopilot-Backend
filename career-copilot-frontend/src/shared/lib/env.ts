export interface AppEnv {
  apiUrl: string
}

export function getEnv(): AppEnv {
  const apiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1").trim()
  try {
    new URL(apiUrl)
  } catch {
    throw new Error("VITE_API_URL debe ser una URL válida.")
  }

  return { apiUrl: apiUrl.replace(/\/+$/, "") }
}

export const appEnv = getEnv()
