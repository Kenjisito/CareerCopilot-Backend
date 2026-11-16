import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"
import { AuthPage } from "@/features/auth/pages/AuthPage"
import { useAuth } from "@/features/auth/useAuth"
import { useSignIn, useSignUp } from "@/features/auth/hooks"

vi.mock("@/features/auth/useAuth", () => ({ useAuth: vi.fn() }))
vi.mock("@/features/auth/hooks", () => ({
  useSignIn: vi.fn(),
  useSignUp: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useAuth).mockReturnValue({ error: null } as unknown as ReturnType<typeof useAuth>)
  vi.mocked(useSignIn).mockReturnValue({
    error: null,
    isPending: false,
    mutateAsync: vi.fn(),
  } as unknown as ReturnType<typeof useSignIn>)
  vi.mocked(useSignUp).mockReturnValue({
    error: null,
    isPending: false,
    mutateAsync: vi.fn(),
  } as unknown as ReturnType<typeof useSignUp>)
})

afterEach(() => {
  cleanup()
})

describe("AuthPage", () => {
  it("toggles password visibility without clearing its value", async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <AuthPage mode="login" />
      </MemoryRouter>,
    )
    const password = screen.getByLabelText("Contraseña") as HTMLInputElement

    await user.type(password, "career123")
    await user.click(screen.getByRole("button", { name: "Mostrar contraseña" }))

    expect(password.type).toBe("text")
    expect(password.value).toBe("career123")

    await user.click(screen.getByRole("button", { name: "Ocultar contraseña" }))
    expect(password.type).toBe("password")
  })
})
