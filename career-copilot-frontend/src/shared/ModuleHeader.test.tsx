import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { ModuleHeader } from "@/shared/ModuleHeader"

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("ModuleHeader", () => {
  it("provides one mobile disclosure for multiple actions", () => {
    vi.stubGlobal("matchMedia", () => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList))

    render(
      <ModuleHeader title="Tu CV" copy="Revisa tu perfil.">
        <button>Editar CV</button>
        <button>Mejorar con Astro</button>
      </ModuleHeader>,
    )

    expect(screen.getByText("Acciones").tagName).toBe("SUMMARY")
    expect(screen.getByRole("button", { name: "Editar CV" })).toBeTruthy()
    expect(screen.getByRole("button", { name: "Mejorar con Astro" })).toBeTruthy()
    expect(screen.getByText("Acciones").parentElement?.hasAttribute("open")).toBe(false)
  })

  it("keeps actions visible directly on desktop", () => {
    render(
      <ModuleHeader title="Tu CV" copy="Revisa tu perfil.">
        <button>Editar CV</button>
        <button>Mejorar con Astro</button>
      </ModuleHeader>,
    )

    expect(screen.getAllByRole("button", { name: "Editar CV" })).toHaveLength(1)
    expect(screen.queryByText("Acciones")).toBeNull()
  })

  it("keeps a single action directly visible on compact layouts", () => {
    vi.stubGlobal("matchMedia", () => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList))

    render(
      <ModuleHeader title="Tracker" copy="Sigue tus ofertas.">
        <button>Buscar ofertas</button>
      </ModuleHeader>,
    )

    expect(screen.getByRole("button", { name: "Buscar ofertas" })).toBeTruthy()
    expect(screen.queryByText("Acciones")).toBeNull()
  })
})
