import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { JobMatchModule } from "@/features/jobmatch"
import {
  useAnalyzeJobMatch,
  useJobMatch,
  useJobMatches,
} from "@/features/jobmatch/hooks"
import { ApiError } from "@/shared/lib/apiError"

vi.mock("@/features/jobmatch/hooks", () => ({
  useAnalyzeJobMatch: vi.fn(),
  useJobMatch: vi.fn(),
  useJobMatches: vi.fn(),
}))

const idleMutation = {
  isPending: false,
  isError: false,
  error: null,
  variables: undefined,
  mutate: vi.fn(),
}

beforeEach(() => {
  vi.mocked(useJobMatches).mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useJobMatches>)
  vi.mocked(useJobMatch).mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useJobMatch>)
  vi.mocked(useAnalyzeJobMatch).mockReturnValue(
    idleMutation as unknown as ReturnType<typeof useAnalyzeJobMatch>,
  )
})

afterEach(() => {
  cleanup()
})

describe("JobMatchModule", () => {
  it("keeps analysis details collapsed until requested on compact layouts", async () => {
    const result = {
      id: "match-1",
      jobTitle: "Diseñador/a UX",
      company: "Acme",
      rawDescription: "Descripción de la oferta",
      matchScore: 82,
      matchedKeywords: ["Research"],
      missingKeywords: ["Prototipado"],
      astroAdvice: "Destaca tus proyectos.",
      status: "Saved" as const,
    }
    vi.mocked(useJobMatches).mockReturnValue({
      data: [result],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useJobMatches>)
    vi.mocked(useJobMatch).mockReturnValue({
      data: result,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useJobMatch>)
    const user = userEvent.setup()
    render(<JobMatchModule />)

    const toggle = screen.getByRole("button", { name: "Ver detalles del análisis" })
    expect(toggle.getAttribute("aria-expanded")).toBe("false")
    await user.click(toggle)

    expect(screen.getByRole("button", { name: "Ocultar detalles" }).getAttribute("aria-expanded")).toBe("true")
    expect(screen.getByText("Recomendación de Astro")).toBeTruthy()
  })

  it("shows the description counter and disables submission below 100 characters", async () => {
    const user = userEvent.setup()
    render(<JobMatchModule />)

    await user.type(screen.getByRole("textbox", { name: "Título del puesto" }), "Diseñador")
    const description = screen.getByRole("textbox", { name: "Descripción de la oferta" })
    await user.type(description, "a".repeat(99))

    expect(screen.getByText("99/100")).toBeTruthy()
    expect(screen.getByRole("button", { name: "Analizar JobMatch" }).hasAttribute("disabled")).toBe(true)
    await user.type(description, " ")
    expect(screen.getByText("99/100")).toBeTruthy()
    expect(screen.getByRole("button", { name: "Analizar JobMatch" }).hasAttribute("disabled")).toBe(true)

    await user.keyboard("{Backspace}")
    await user.type(description, "a")

    expect(screen.getByText("100/100")).toBeTruthy()
    const analyzeButton = screen.getByRole("button", { name: "Analizar JobMatch" })
    expect(analyzeButton.hasAttribute("disabled")).toBe(false)

    await user.click(analyzeButton)

    expect(idleMutation.mutate).toHaveBeenCalledOnce()
    expect(idleMutation.mutate.mock.calls[0]?.[0]).toMatchObject({
      request: { jobTitle: "Diseñador", company: "", rawDescription: "a".repeat(100) },
    })
  })

  it("shows backend field errors next to the corresponding controls", () => {
    vi.mocked(useAnalyzeJobMatch).mockReturnValue({
      ...idleMutation,
      isError: true,
      error: new ApiError(400, "validation_error", "Revisa los datos.", undefined, undefined, {
        JobTitle: ["El título es obligatorio."],
        Company: ["La empresa es obligatoria."],
        RawDescription: ["La descripción debe tener al menos 100 caracteres."],
      }),
    } as unknown as ReturnType<typeof useAnalyzeJobMatch>)

    render(<JobMatchModule />)

    expect(screen.getByText("El título es obligatorio.")).toBeTruthy()
    expect(screen.getByText("La empresa es obligatoria.")).toBeTruthy()
    expect(screen.getByText("La descripción debe tener al menos 100 caracteres.")).toBeTruthy()
  })
})
