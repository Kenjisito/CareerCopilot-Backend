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
