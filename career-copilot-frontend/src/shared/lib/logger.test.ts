import { describe, expect, it, vi } from "vitest"
import { info } from "@/shared/lib/logger"

describe("logger", () => {
  it("removes query data and rejects sensitive field names", () => {
    const consoleSpy = vi.spyOn(console, "info").mockImplementation(() => undefined)

    info({
      event: "request started",
      method: "POST",
      route: "/api/job-match/analyze?email=private@example.test",
      fieldNames: ["private@example.test"],
      bodyLength: 42,
    })

    const output = JSON.stringify(consoleSpy.mock.calls)
    expect(output).not.toContain("private@example.test")
    expect(output).toContain("/api/job-match/analyze")
    expect(output).toContain("unknown")
    expect(output).toContain("42")
  })
})
