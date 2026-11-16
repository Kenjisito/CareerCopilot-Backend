import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { CoachModule } from "@/features/coach"
import {
  useCreateInterview,
  useInterview,
  useSendInterviewMessage,
} from "@/features/coach/hooks"
import { useJobMatches } from "@/features/jobmatch/hooks"
import type { JobAnalysisResponse } from "@/features/jobmatch/types"

vi.mock("@/features/coach/hooks", () => ({
  useCreateInterview: vi.fn(),
  useInterview: vi.fn(),
  useSendInterviewMessage: vi.fn(),
}))

vi.mock("@/features/jobmatch/hooks", () => ({
  useJobMatches: vi.fn(),
}))

const createMutation = {
  isPending: false,
  isError: false,
  error: null,
  variables: undefined,
  mutate: vi.fn(),
}

const jobs: JobAnalysisResponse[] = [
  {
    id: "job-1",
    jobTitle: "Diseñador UX",
    company: "Empresa Uno",
    rawDescription: "Diseño de experiencias.",
    matchScore: 80,
    matchedKeywords: [],
    missingKeywords: [],
    astroAdvice: null,
    status: "Saved",
  },
  {
    id: "job-2",
    jobTitle: "Product Designer",
    company: "Empresa Dos",
    rawDescription: "Diseño de productos.",
    matchScore: 90,
    matchedKeywords: [],
    missingKeywords: [],
    astroAdvice: null,
    status: "Saved",
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useJobMatches).mockReturnValue({
    data: jobs,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useJobMatches>)
  vi.mocked(useCreateInterview).mockReturnValue(
    createMutation as unknown as ReturnType<typeof useCreateInterview>,
  )
  vi.mocked(useInterview).mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useInterview>)
  vi.mocked(useSendInterviewMessage).mockReturnValue(
    { isPending: false, isError: false } as unknown as ReturnType<typeof useSendInterviewMessage>,
  )
})

afterEach(() => {
  cleanup()
})

describe("CoachModule", () => {
  it("requires a saved JobMatch analysis to start practice", async () => {
    vi.mocked(useJobMatches).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useJobMatches>)
    const setActive = vi.fn()
    const user = userEvent.setup()
    render(<CoachModule setActive={setActive} />)

    expect(screen.getByText(/Solo puedes iniciar una entrevista con una oferta analizada/)).toBeTruthy()
    await user.click(screen.getByRole("button", { name: "Ir a JobMatch" }))

    expect(setActive).toHaveBeenCalledWith("jobmatch")
    expect(createMutation.mutate).not.toHaveBeenCalled()
  })

  it("starts the interview with the selected JobMatch record", async () => {
    const user = userEvent.setup()
    render(<CoachModule setActive={vi.fn()} />)

    await user.selectOptions(screen.getByLabelText(/Oferta analizada en JobMatch/), "job-2")
    await user.click(screen.getByRole("button", { name: "Comenzar entrevista" }))

    expect(createMutation.mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        request: { targetRole: "Product Designer", jobMatchId: "job-2" },
      }),
      expect.any(Object),
    )
  })

  it("shows a three-dot typing indicator while Astro prepares a reply", async () => {
    vi.mocked(useInterview).mockReturnValue({
      data: {
        id: "session-1",
        targetRole: "Diseñador UX",
        startedAt: "2026-01-01T00:00:00Z",
        completedAt: null,
        score: null,
        feedback: null,
        messages: [{
          id: "message-1",
          role: "Astro",
          content: "Cuéntame sobre un proyecto.",
          score: null,
          feedback: null,
          createdAt: "2026-01-01T00:00:00Z",
        }],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useInterview>)
    vi.mocked(useSendInterviewMessage).mockReturnValue({
      isPending: true,
      isError: false,
    } as unknown as ReturnType<typeof useSendInterviewMessage>)
    createMutation.mutate.mockImplementation((_request, callbacks) => {
      callbacks?.onSuccess?.({ id: "session-1" })
    })
    const user = userEvent.setup()
    render(<CoachModule setActive={vi.fn()} />)

    await user.click(screen.getByRole("button", { name: "Comenzar entrevista" }))
    await waitFor(() => expect(screen.getByText("Astro está escribiendo...")).toBeTruthy())

    expect(screen.getByRole("status").querySelectorAll(".typing-bubble i")).toHaveLength(3)
  })
})
