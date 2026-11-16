import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useCoverLetter, useCreateCoverLetter } from "@/features/letters/hooks"
import type { CoverLetterResponse } from "@/features/letters/types"
import { LettersModule } from "@/features/letters"
import { useJobMatches } from "@/features/jobmatch/hooks"
import type { JobAnalysisResponse } from "@/features/jobmatch/types"

vi.mock("@/features/letters/hooks", () => ({
  useCoverLetter: vi.fn(),
  useCreateCoverLetter: vi.fn(),
}))
vi.mock("@/features/jobmatch/hooks", () => ({ useJobMatches: vi.fn() }))

const job: JobAnalysisResponse = {
  id: "job-1",
  jobTitle: "Desarrolladora backend",
  company: "Acme",
  rawDescription: "Desarrollo de APIs.",
  matchScore: 82,
  matchedKeywords: [],
  missingKeywords: [],
  astroAdvice: null,
  status: "Saved",
}

const letter: CoverLetterResponse = {
  id: "letter-1",
  subject: "Postulación",
  body: "Me interesa la oportunidad.",
  content: "Me interesa la oportunidad y puedo aportar experiencia en backend.",
  jobAnalysisId: "job-1",
  tone: "Dynamic",
  createdAt: "2026-01-01T00:00:00Z",
}

const createMutation = {
  isPending: false,
  isError: false,
  error: null,
  variables: undefined,
  mutate: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useJobMatches).mockReturnValue({
    data: [job],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useJobMatches>)
  vi.mocked(useCreateCoverLetter).mockReturnValue(
    createMutation as unknown as ReturnType<typeof useCreateCoverLetter>,
  )
  vi.mocked(useCoverLetter).mockImplementation((id) => ({
    data: id === letter.id ? letter : undefined,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useCoverLetter>))
})

afterEach(() => {
  cleanup()
})

describe("LettersModule", () => {
  it("reveals the generated letter progressively in the output", async () => {
    createMutation.mutate.mockImplementation((_request, callbacks) => {
      callbacks?.onSuccess?.({ id: letter.id })
    })
    const user = userEvent.setup()
    render(<LettersModule setActive={vi.fn()} />)

    await user.click(screen.getByRole("button", { name: "Generar con Astro" }))
    const output = await screen.findByRole("textbox", { name: "Carta generada" })

    await waitFor(() => {
      expect((output as HTMLTextAreaElement).value.length).toBeGreaterThan(0)
    })
    expect((output as HTMLTextAreaElement).value.length).toBeLessThan(letter.content.length)
    await waitFor(() => {
      expect((output as HTMLTextAreaElement).value).toBe(letter.content)
    })
  })
})
