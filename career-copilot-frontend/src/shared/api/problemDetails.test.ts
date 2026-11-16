import { describe, expect, it } from "vitest"
import { toApiError } from "@/shared/api/problemDetails"

describe("toApiError con respuestas de FastAPI", () => {
  it("usa el detail del backend como mensaje (antes llegaba 'false')", () => {
    expect(toApiError({ detail: "Debes subir y procesar un CV antes de realizar un Job Match." }, 400).message)
      .toBe("Debes subir y procesar un CV antes de realizar un Job Match.")
    expect(toApiError({ detail: "Alcanzaste el límite mensual." }, 402).message).toBe("Alcanzaste el límite mensual.")
    expect(toApiError({ detail: "Match no encontrado." }, 404).message).toBe("Match no encontrado.")
  })

  it("prefiere el mensaje específico del backend en 429/503", () => {
    expect(toApiError({ detail: "La IA alcanzó su límite de uso por minuto." }, 503).message)
      .toBe("La IA alcanzó su límite de uso por minuto.")
    expect(toApiError({}, 503).message).toBe("El servicio de IA no está disponible, intenta de nuevo.")
  })

  it("convierte los errores de validación de Pydantic en errores por campo", () => {
    const error = toApiError(
      { detail: [{ loc: ["body", "url"], msg: "Input should be a valid URL", type: "url_parsing" }] },
      422,
    )
    expect(error.message).toBe("Revisa los datos ingresados e inténtalo nuevamente.")
    expect(error.fieldErrors).toEqual({ url: ["Input should be a valid URL"] })
  })

  it("mantiene los mensajes genéricos de 401 y 500", () => {
    expect(toApiError({ detail: "x" }, 401).message).toBe("Sesión expirada")
    expect(toApiError({ detail: "x" }, 500).message).toBe("Ocurrió un error inesperado")
  })
})
