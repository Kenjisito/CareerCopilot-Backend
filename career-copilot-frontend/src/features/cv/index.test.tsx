import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useAuth } from "@/features/auth"
import { useParseCv } from "@/features/cv/hooks"
import { CvModule } from "@/features/cv"
import { useImproveProfile, useProfile, useSaveProfile } from "@/features/profile"
import type { ProfileImprovementChange } from "@/features/profile"
import { useQuery } from "@tanstack/react-query"
import type { Profile } from "@/shared/types/api"

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>()
  return { ...actual, useQuery: vi.fn() }
})
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return { ...actual, useNavigate: vi.fn(() => vi.fn()) }
})
vi.mock("@/features/auth", () => ({ useAuth: vi.fn() }))
vi.mock("@/features/cv/hooks", () => ({ useParseCv: vi.fn() }))
vi.mock("@/features/profile", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/profile")>()
  return {
    ...actual,
    useImproveProfile: vi.fn(),
    useProfile: vi.fn(),
    useSaveProfile: vi.fn(),
    useProfileDraftStore: vi.fn(() => vi.fn()),
  }
})

const profile: Profile = {
  id: "profile-1",
  full_name: "Ana Pérez",
  email: "ana@example.com",
  phone: "+56 9 1234 5678",
  headline: "Desarrolladora backend",
  summary: "Desarrolladora con experiencia en servicios web.",
  location: { country_code: "CL", region_id: "RM", commune_id: "Santiago" },
  experiences: [{
    id: "experience-1",
    title: "Desarrolladora",
    company: "Acme",
    start_date: "2023-01",
    end_date: null,
    is_current: true,
    description: "Desarrolló servicios con FastAPI.",
    achievements: ["Redujo la latencia en 35%."],
    experience_type: "professional",
    raw_text: null,
  }],
  skills: ["Python", "FastAPI"],
  additional_sections: { education: ["Ingeniería en Informática"] },
  source_cv_id: null,
  updated_at: "",
}

const saveMutation = { mutate: vi.fn(), isPending: false, isError: false, error: null, reset: vi.fn() }
const improveMutation = { mutate: vi.fn(), isPending: false, isError: false, error: null, reset: vi.fn() }

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useAuth).mockReturnValue({ session: null } as unknown as ReturnType<typeof useAuth>)
  vi.mocked(useQuery).mockReturnValue({
    data: null,
    isLoading: false,
    isError: false,
  } as never)
  vi.mocked(useProfile).mockReturnValue({
    data: profile,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useProfile>)
  vi.mocked(useParseCv).mockReturnValue({
    isPending: false,
    isError: false,
    mutate: vi.fn(),
  } as unknown as ReturnType<typeof useParseCv>)
  vi.mocked(useSaveProfile).mockReturnValue(
    saveMutation as unknown as ReturnType<typeof useSaveProfile>,
  )
  vi.mocked(useImproveProfile).mockReturnValue(
    improveMutation as unknown as ReturnType<typeof useImproveProfile>,
  )
})

afterEach(() => {
  cleanup()
})

describe("CvModule", () => {
  it("edits the rendered CV and saves the changed profile", async () => {
    const user = userEvent.setup()
    render(<CvModule />)

    await user.click(screen.getByRole("button", { name: "Editar CV" }))
    const summary = screen.getByRole("textbox", { name: "Resumen profesional" })
    await user.clear(summary)
    await user.type(summary, "Nueva trayectoria en backend.")
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }))

    expect(saveMutation.mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        profile: expect.objectContaining({ summary: "Nueva trayectoria en backend." }),
        signal: expect.any(AbortSignal),
      }),
      expect.any(Object),
    )
  })

  it("lets the user accept, reject, and save individual Astro suggestions", async () => {
    const change: ProfileImprovementChange = {
      field: "professionalSummary",
      experienceIndex: null,
      experienceId: null,
      currentValue: profile.summary,
      suggestedValue: "Desarrolladora backend especializada en servicios web.",
      reason: "Destaca la especialidad sin agregar información nueva.",
    }
    const rejectedChange: ProfileImprovementChange = {
      field: "headline",
      experienceIndex: null,
      experienceId: null,
      currentValue: profile.headline,
      suggestedValue: "Ingeniera de software",
      reason: "Ajusta el titular.",
    }
    improveMutation.mutate.mockImplementation((_request, callbacks) => {
      callbacks?.onSuccess?.({
        summary: "Se encontraron mejoras verificables.",
        changes: [change, rejectedChange],
      })
    })
    const user = userEvent.setup()
    render(<CvModule />)

    await user.click(screen.getByRole("button", { name: "Mejorar con Astro" }))
    await waitFor(() => expect(screen.getByText("Decide qué cambios aplicar")).toBeTruthy())
    const acceptButton = screen.getAllByRole("button", { name: /Aceptar/ })[0]
    if (!acceptButton) throw new Error("No se encontró la primera sugerencia.")
    await user.click(acceptButton)
    await user.click(screen.getByRole("button", { name: /Denegar/ }))

    expect(screen.getByRole("textbox", { name: "Resumen profesional" })).toHaveProperty(
      "value",
      change.suggestedValue,
    )
    expect(screen.getByRole("textbox", { name: "Titular profesional" })).toHaveProperty(
      "value",
      profile.headline,
    )
    expect(screen.getByText("Rechazado")).toBeTruthy()
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }))

    expect(saveMutation.mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        profile: expect.objectContaining({ summary: change.suggestedValue }),
      }),
      expect.any(Object),
    )
  })

  it("lets the user adapt an Astro suggestion before applying it", async () => {
    const change: ProfileImprovementChange = {
      field: "professionalSummary",
      experienceIndex: null,
      experienceId: null,
      currentValue: profile.summary,
      suggestedValue: "Desarrolladora backend especializada.",
      reason: "Hace el perfil más directo.",
    }
    improveMutation.mutate.mockImplementation((_request, callbacks) => {
      callbacks?.onSuccess?.({ summary: "Propuestas listas.", changes: [change] })
    })
    const user = userEvent.setup()
    render(<CvModule />)

    await user.click(screen.getByRole("button", { name: "Mejorar con Astro" }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Adaptar" })).toBeTruthy())
    await user.click(screen.getByRole("button", { name: "Adaptar" }))
    const editor = screen.getByRole("textbox", { name: "Adapta la propuesta a tu estilo" })
    await user.clear(editor)
    await user.type(editor, "Mi versión adaptada.")
    await user.click(screen.getByRole("button", { name: "Usar mi versión" }))

    expect(screen.getByRole("textbox", { name: "Resumen profesional" })).toHaveProperty(
      "value",
      "Mi versión adaptada.",
    )
    expect(screen.getByText("Adaptado")).toBeTruthy()
  })
})
