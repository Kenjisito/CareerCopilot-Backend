import { describe, expect, it } from "vitest"
import { buildGmailComposeUrl } from "@/features/letters/gmail"

describe("Gmail compose URL", () => {
  it("uses the supplied recipient, generated subject and body", () => {
    const recipient = "recruiter@example.test"
    const generatedSubject = "Postulación — Product Designer"
    const generatedBody = "Hola, me interesa la oportunidad. Saludos."
    const url = new URL(buildGmailComposeUrl(recipient, generatedSubject, generatedBody))

    expect(url.origin + url.pathname).toBe("https://mail.google.com/mail/u/0/")
    expect(url.searchParams.get("fs")).toBe("1")
    expect(url.searchParams.get("to")).toBe(recipient)
    expect(url.searchParams.get("su")).toBe(generatedSubject)
    expect(url.searchParams.get("body")).toBe(generatedBody)
    expect(url.searchParams.get("tf")).toBe("cm")
  })
})
