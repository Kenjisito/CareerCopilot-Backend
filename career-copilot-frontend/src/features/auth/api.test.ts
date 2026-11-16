import { describe, expect, it } from "vitest"
import { authErrorMessage } from "@/features/auth/api"

describe("authErrorMessage", () => {
  it("traduce los errores de Supabase al español", () => {
    expect(authErrorMessage({ message: "Invalid login credentials", code: "invalid_credentials" }))
      .toBe("Correo o contraseña incorrectos.")
    expect(authErrorMessage({ message: "Email not confirmed" })).toContain("confirmar tu correo")
    expect(authErrorMessage({ message: "User already registered" })).toContain("Ya existe una cuenta")
    expect(authErrorMessage({ message: "Password should be at least 6 characters." })).toContain("6 caracteres")
    expect(authErrorMessage({ message: "email rate limit exceeded", code: "over_email_send_rate_limit" }))
      .toContain("demasiados intentos")
  })

  it("deja pasar mensajes desconocidos", () => {
    expect(authErrorMessage({ message: "Algo raro" })).toBe("Algo raro")
  })
})
