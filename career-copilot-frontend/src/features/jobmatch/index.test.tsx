import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { JobMatchModule } from "@/features/jobmatch"
import {
  useAnalyzeJobMatch,
  useExtractJobOffer,
  useJobMatch,
  useJobMatches,
} from "@/features/jobmatch/hooks"
import { ApiError } from "@/shared/lib/apiError"

vi.mock("@/features/jobmatch/hooks", () => ({
  useAnalyzeJobMatch: vi.fn(),
  useExtractJobOffer: vi.fn(),
  useJobMatch: vi.fn(),
  useJobMatches: vi.fn(),
}))

const idleMutation = {
  isPending: false,
  isError: false,
  error: null,
  variables: undefined,
  mutate: vi.fn(),
  reset: vi.fn(),
}

const extractMutation = {
  isPending: false,
  isError: false,
  error: null,
  mutate: vi.fn(),
  reset: vi.fn(),
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
  vi.mocked(useExtractJobOffer).mockReturnValue(
    extractMutation as unknown as ReturnType<typeof useExtractJobOffer>,
  )
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
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

  it("imports an offer from a link and fills the form", async () => {
    extractMutation.mutate.mockImplementation((_vars, options) => {
      options?.onSuccess?.({
        jobTitle: "Desarrollador .NET",
        company: "Abenis",
        rawDescription: "Funciones y requisitos de la oferta. ".repeat(5),
        source: "datos-estructurados",
        url: "https://cl.computrabajo.com/ofertas-de-trabajo/x",
      })
    })
    const user = userEvent.setup()
    render(<JobMatchModule />)

    const importButton = screen.getByRole("button", { name: "Importar" })
    expect(importButton.hasAttribute("disabled")).toBe(true)
    await user.type(screen.getByRole("textbox", { name: "Enlace de la oferta" }), "https://cl.computrabajo.com/ofertas-de-trabajo/x")
    await user.click(screen.getByRole("button", { name: "Importar" }))

    expect(extractMutation.mutate.mock.calls[0]?.[0]).toMatchObject({ url: "https://cl.computrabajo.com/ofertas-de-trabajo/x" })
    expect((screen.getByRole("textbox", { name: "Título del puesto" }) as HTMLInputElement).value).toBe("Desarrollador .NET")
    expect((screen.getByRole("textbox", { name: "Empresa" }) as HTMLInputElement).value).toBe("Abenis")
    expect(screen.getByText(/Oferta importada desde cl.computrabajo.com/)).toBeTruthy()
    expect(screen.getByRole("button", { name: "Analizar JobMatch" }).hasAttribute("disabled")).toBe(false)
  })

  it("offers to import when a link is pasted into the description", async () => {
    const user = userEvent.setup()
    render(<JobMatchModule />)

    await user.type(screen.getByRole("textbox", { name: "Título del puesto" }), "Backend")
    await user.type(screen.getByRole("textbox", { name: "Descripción de la oferta" }), "https://www.linkedin.com/jobs/view/123/")
    expect(screen.getByRole("button", { name: "Analizar JobMatch" }).hasAttribute("disabled")).toBe(true)
    await user.click(screen.getByRole("button", { name: "Importar la oferta desde este enlace" }))

    expect(extractMutation.mutate.mock.calls[0]?.[0]).toMatchObject({ url: "https://www.linkedin.com/jobs/view/123/" })
  })

  it("shows extraction errors next to the link field with a hint to paste the text", async () => {
    vi.mocked(useExtractJobOffer).mockReturnValue({
      ...extractMutation,
      isError: true,
      error: new ApiError(422, "http_422", "Ese sitio no permite leer la oferta sin iniciar sesión."),
    } as unknown as ReturnType<typeof useExtractJobOffer>)
    const user = userEvent.setup()
    render(<JobMatchModule />)
    expect(screen.queryByRole("alert")).toBeNull()

    await user.type(screen.getByRole("textbox", { name: "Enlace de la oferta" }), "https://www.indeed.com/viewjob?jk=1")
    await user.click(screen.getByRole("button", { name: "Importar" }))

    expect(screen.getByRole("alert").textContent).toContain("no permite leer la oferta")
    expect(screen.getByRole("alert").textContent).toContain("pegarlo en la descripción")
  })

  it("maps FastAPI field names (nombre, ofertaTexto) to the form controls", () => {
    vi.mocked(useAnalyzeJobMatch).mockReturnValue({
      ...idleMutation,
      isError: true,
      error: new ApiError(422, "http_422", "Revisa los datos.", undefined, undefined, {
        nombre: ["String should have at most 255 characters"],
        ofertaTexto: ["String should have at least 20 characters"],
      }),
    } as unknown as ReturnType<typeof useAnalyzeJobMatch>)
    render(<JobMatchModule />)

    expect(screen.getByText("String should have at most 255 characters")).toBeTruthy()
    expect(screen.getByText("String should have at least 20 characters")).toBeTruthy()
  })

  it("tidies an offer pasted from any page and allows undoing it", async () => {
    const pastedPage =
      "Inicio Empleos Empresas Ingresar\nJefe de turno RM - Under Pizza\nRequisitos: 2 años liderando equipos en gastronomía. ".repeat(4)
    extractMutation.mutate.mockImplementation((_vars, options) => {
      options?.onSuccess?.({
        jobTitle: "Jefe de turno RM",
        company: "Under Pizza",
        rawDescription: "Requisitos: 2 años liderando equipos en gastronomía, manejo de caja e inventario. Beneficios: colación.",
        source: "texto",
        url: "",
      })
    })
    const user = userEvent.setup()
    render(<JobMatchModule />)

    await user.click(screen.getByRole("textbox", { name: "Descripción de la oferta" }))
    await user.paste(pastedPage)

    expect(extractMutation.mutate.mock.calls[0]?.[0]).toMatchObject({ text: pastedPage })
    expect((screen.getByRole("textbox", { name: "Título del puesto" }) as HTMLInputElement).value).toBe("Jefe de turno RM")
    expect((screen.getByRole("textbox", { name: "Empresa" }) as HTMLInputElement).value).toBe("Under Pizza")
    expect(screen.getByText(/Astro ordenó la oferta que pegaste/)).toBeTruthy()

    await user.click(screen.getByRole("button", { name: "Deshacer" }))
    expect((screen.getByRole("textbox", { name: "Descripción de la oferta" }) as HTMLTextAreaElement).value).toBe(pastedPage)
    expect((screen.getByRole("textbox", { name: "Título del puesto" }) as HTMLInputElement).value).toBe("")
  })

  it("does not tidy short pastes and keeps a typed title", async () => {
    const user = userEvent.setup()
    render(<JobMatchModule />)
    await user.click(screen.getByRole("textbox", { name: "Descripción de la oferta" }))
    await user.paste("Requisitos: Python.")
    expect(extractMutation.mutate).not.toHaveBeenCalled()
  })

  it("lets the user tidy typed text with the 'Ordenar con Astro' button", async () => {
    const user = userEvent.setup()
    render(<JobMatchModule />)
    const text = "Funciones y requisitos de la oferta con texto extra. ".repeat(3)
    await user.type(screen.getByRole("textbox", { name: "Descripción de la oferta" }), text)
    await user.click(screen.getByRole("button", { name: "Ordenar con Astro" }))
    expect(extractMutation.mutate.mock.calls[0]?.[0]).toMatchObject({ text })
  })
})
