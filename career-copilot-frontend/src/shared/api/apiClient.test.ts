import { afterEach, describe, expect, it, vi } from "vitest"
import { apiClient } from "@/shared/api/apiClient"
import { ApiError } from "@/shared/lib/apiError"

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe("apiClient", () => {
  it("uses the FastAPI v1 base URL without duplicating the API prefix", async () => {
    vi.stubEnv("VITE_API_URL", "http://localhost:8000/api/v1")
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }))
    vi.stubGlobal("fetch", fetchMock)

    await apiClient("/profile", { auth: false })

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/profile",
      expect.any(Object),
    )
  })

  it("parses ProblemDetails field errors and the trace header", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            title: "One or more validation errors occurred.",
            status: 400,
            errors: { RawDescription: ["La descripción es demasiado corta."] },
          }),
          {
            status: 400,
            headers: { "Content-Type": "application/problem+json", "X-Trace-Id": "trace-123" },
          },
        ),
      ),
    )

    const request = apiClient("/api/job-match/analyze", { method: "POST", auth: false })
    const caught = await request.catch((error: unknown) => error)

    expect(caught).toBeInstanceOf(ApiError)
    expect(caught).toMatchObject({
      status: 400,
      traceId: "trace-123",
      fieldErrors: { RawDescription: ["La descripción es demasiado corta."] },
    })
  })

  it("converts fetch network errors to a friendly ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")))

    const caught = await apiClient("/profile", { auth: false }).catch(
      (error: unknown) => error,
    )

    expect(caught).toBeInstanceOf(ApiError)
    expect(caught).toMatchObject({
      message: "No se pudo conectar con el servidor",
      isNetworkError: true,
    })
  })

  it("uses a generic 500 message and extracts its body trace id", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: 500, traceId: "body-trace" }), {
          status: 500,
          headers: { "Content-Type": "application/problem+json" },
        }),
      ),
    )

    const caught = await apiClient("/api/job-match/analyze", { auth: false }).catch(
      (error: unknown) => error,
    )

    expect(caught).toMatchObject({
      message: "Ocurrió un error inesperado",
      traceId: "body-trace",
      status: 500,
    })
  })

  it("converts request timeouts to a network ApiError", async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      "fetch",
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener(
            "abort",
            () => reject(new DOMException("Aborted", "AbortError")),
            { once: true },
          )
        }),
      ),
    )

    const request = apiClient("/profile", { auth: false, timeoutMs: 100 }).catch(
      (error: unknown) => error,
    )
    await vi.advanceTimersByTimeAsync(100)
    const caught = await request

    expect(caught).toBeInstanceOf(ApiError)
    expect(caught).toMatchObject({ isNetworkError: true, code: "timeout_error" })
  })
})
