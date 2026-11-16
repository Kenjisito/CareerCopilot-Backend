import { beforeEach, describe, expect, it, vi } from "vitest"
import { apiClient } from "@/shared/api/apiClient"
import { improveProfile, profileDraftFromParsedCandidate } from "@/features/profile/api"
import type { ParsedCandidateProfileResponse, ProfileDraft } from "@/features/profile/types"

vi.mock("@/shared/api/apiClient", () => ({ apiClient: vi.fn() }))

beforeEach(() => {
  vi.clearAllMocks()
})

describe("profileDraftFromParsedCandidate", () => {
  it("replaces previous profile data with the newly parsed CV", () => {
    const current: ProfileDraft = {
      full_name: "Ana Pérez",
      email: "old@example.com",
      phone: "555-0101",
      headline: "Senior Data Engineer",
      summary: "Resumen anterior",
      location: { country_code: "CL", region_id: "RM", commune_id: "Providencia" },
      experiences: [{
        id: "old-experience",
        title: "Analista",
        company: "Empresa anterior",
        start_date: "2020-01",
        end_date: null,
        is_current: false,
        description: "Experiencia anterior",
        achievements: [],
        experience_type: "professional",
        raw_text: null,
      }],
      skills: ["Python", "COBOL"],
      additional_sections: {
        education: ["Ingeniería · Universidad de Chile"],
        projects: ["Proyecto anterior"],
      },
      source_cv_id: null,
    }
    const candidate: ParsedCandidateProfileResponse = {
      fullName: "Ana Pérez",
      headline: "Líder de Datos",
      email: "new@example.com",
      phone: null,
      country: null,
      region: null,
      commune: null,
      professionalSummary: null,
      skills: ["Python", "SQL"],
      experiences: [{
        role: "Data Engineer",
        company: "Acme",
        startDate: "2023-01",
        endDate: null,
        isCurrent: true,
        description: "Diseñó pipelines de datos.",
        achievements: ["Redujo la latencia en 35%."],
        experienceType: "professional",
        rawText: "Data Engineer en Acme desde 2023.",
      }, {
        role: "Docente de Informática",
        company: "",
        startDate: "",
        endDate: null,
        isCurrent: false,
        description: "Dictó cursos de programación.",
        achievements: [],
        experienceType: "academic",
        rawText: "Docente de Informática — dictó cursos de programación.",
      }],
      additionalSections: {
        education: ["Ingeniería · Universidad de Chile", "Diplomado en Analítica"],
        projects: ["Proyecto nuevo"],
        languages: ["Inglés: avanzado"],
      },
    }

    const draft = profileDraftFromParsedCandidate(candidate, current)

    expect(draft.headline).toBe("Líder de Datos")
    expect(draft.email).toBe("new@example.com")
    expect(draft.experiences[0]?.title).toBe("Data Engineer")
    expect(draft.experiences[0]?.achievements).toEqual(["Redujo la latencia en 35%."])
    expect(draft.experiences[1]?.experience_type).toBe("academic")
    expect(draft.experiences[1]?.raw_text).toContain("Docente de Informática")
    expect(draft.experiences).toHaveLength(2)
    expect(draft.skills).toEqual(["Python", "SQL"])
    expect(draft.additional_sections).toEqual({
      education: ["Ingeniería · Universidad de Chile", "Diplomado en Analítica"],
      projects: ["Proyecto nuevo"],
      languages: ["Inglés: avanzado"],
    })
    expect(draft.phone).toBe("")
    expect(draft.summary).toBe("")
    expect(draft.location).toEqual({ country_code: "", region_id: "", commune_id: "" })
    expect(draft.preserveExistingOnEmpty).toBe(false)
    expect(draft.source_cv_id).toBeNull()
    expect(profileDraftFromParsedCandidate(
      { ...candidate, email: null },
      current,
      "account@example.com",
    ).email).toBe("account@example.com")
    expect(profileDraftFromParsedCandidate({ ...candidate, email: null }, current).email).toBe("")
  })
})

describe("improveProfile", () => {
  it("sends only CV content and keeps experience ids for safe review", async () => {
    vi.mocked(apiClient).mockResolvedValue({ summary: "Revisado", changes: [] } as never)
    const profile: ProfileDraft = {
      full_name: "Ana Pérez",
      email: "private@example.com",
      phone: "555-0101",
      headline: "Desarrolladora",
      summary: "Experiencia en backend.",
      location: { country_code: "CL", region_id: "RM", commune_id: "Santiago" },
      experiences: [{
        id: "experience-1",
        title: "Desarrolladora",
        company: "Acme",
        start_date: "2023-01",
        end_date: null,
        is_current: true,
        description: "Desarrolló APIs.",
        achievements: ["Redujo tiempos de carga."],
      }],
      skills: ["Python"],
      additional_sections: {},
      source_cv_id: null,
    }

    await improveProfile(profile)

    expect(apiClient).toHaveBeenCalledWith("/profile/improve", {
      method: "POST",
      body: {
        headline: "Desarrolladora",
        professionalSummary: "Experiencia en backend.",
        skills: ["Python"],
        experiences: [{
          id: "experience-1",
          role: "Desarrolladora",
          company: "Acme",
          description: "Desarrolló APIs.",
          achievements: ["Redujo tiempos de carga."],
        }],
      },
      signal: undefined,
      timeoutMs: 90_000,
    })
  })
})
