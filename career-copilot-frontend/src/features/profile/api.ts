import { apiClient } from "@/shared/api/apiClient"
import type { Experience, Profile } from "@/shared/types/api"
import type {
  ParsedCandidateProfileResponse,
  ProfileImprovementRequest,
  ProfileImprovementsResponse,
  ProfileDraft,
  ProfileResponse,
  UpsertProfileRequest,
} from "@/features/profile/types"

function monthValue(value: string | null | undefined): string {
  if (!value) return ""
  return /^\d{4}-\d{2}/.test(value) ? value.slice(0, 7) : value
}

function dateTimeOffsetValue(value: string): string {
  if (/^\d{4}-\d{2}$/.test(value)) return `${value}-01T00:00:00.000Z`
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return `${value}T00:00:00.000Z`
  return value
}

function profileFromResponse(response: ProfileResponse): Profile {
  const experiences: Experience[] = response.experiences.map((experience) => ({
    id: experience.id,
    title: experience.role,
    company: experience.company,
    start_date: monthValue(experience.startDate),
    end_date: experience.endDate ? monthValue(experience.endDate) : null,
    is_current: experience.isCurrent,
    description: experience.description ?? "",
    achievements: experience.achievements ?? [],
    experience_type: experience.experienceType ?? "professional",
    raw_text: experience.rawText ?? null,
  }))

  return {
    id: response.id,
    full_name: response.fullName,
    email: response.email,
    phone: response.phone ?? "",
    headline: response.headline?.trim() || experiences[0]?.title || "",
    summary: response.professionalSummary ?? "",
    location: {
      country_code: response.country ?? "",
      region_id: response.region ?? "",
      commune_id: response.commune ?? "",
    },
    experiences,
    skills: response.skills,
    additional_sections: response.additionalSections ?? {},
    source_cv_id: null,
    updated_at: "",
  }
}

function toUpsertRequest(profile: ProfileDraft): UpsertProfileRequest {
  return {
    fullName: profile.full_name,
    headline: profile.headline || null,
    email: profile.email ?? "",
    phone: profile.phone || null,
    country: profile.location.country_code || null,
    region: profile.location.region_id || null,
    commune: profile.location.commune_id || null,
    professionalSummary: profile.summary || null,
    skills: profile.skills,
    experiences: profile.experiences.map((experience) => ({
      id: experience.id,
      role: experience.title,
      company: experience.company,
      startDate: dateTimeOffsetValue(experience.start_date),
      endDate: experience.end_date ? dateTimeOffsetValue(experience.end_date) : null,
      isCurrent: experience.is_current,
      description: experience.description,
      achievements: experience.achievements ?? [],
      experienceType: experience.experience_type ?? "professional",
      rawText: experience.raw_text ?? null,
    })),
    additionalSections: profile.additional_sections ?? {},
    preserveExistingOnEmpty: profile.preserveExistingOnEmpty === true,
  }
}

export async function getProfile(signal?: AbortSignal): Promise<Profile> {
  const response = await apiClient<ProfileResponse>("/profile", { signal })
  return profileFromResponse(response)
}

export async function saveProfile(profile: ProfileDraft, signal?: AbortSignal): Promise<Profile> {
  const response = await apiClient<ProfileResponse>("/profile", {
    method: "PUT",
    body: { ...toUpsertRequest(profile) },
    signal,
  })
  return profileFromResponse(response)
}

export function improveProfile(
  profile: ProfileDraft,
  signal?: AbortSignal,
): Promise<ProfileImprovementsResponse> {
  const body: ProfileImprovementRequest = {
    headline: profile.headline || null,
    professionalSummary: profile.summary || null,
    skills: profile.skills,
    experiences: profile.experiences.map((experience) => ({
      id: experience.id,
      role: experience.title,
      company: experience.company,
      description: experience.description,
      achievements: experience.achievements ?? [],
    })),
  }
  return apiClient<ProfileImprovementsResponse>("/profile/improve", {
    method: "POST",
    body: { ...body },
    signal,
    timeoutMs: 90_000,
  })
}

export function profileDraftFromParsedCandidate(
  candidate: ParsedCandidateProfileResponse,
  current?: ProfileDraft,
  accountEmail?: string,
): ProfileDraft {
  const base: ProfileDraft = current ?? {
    full_name: "",
    email: "",
    phone: "",
    headline: "",
    summary: "",
    location: { country_code: "", region_id: "", commune_id: "" },
    experiences: [],
    skills: [],
    additional_sections: {},
    source_cv_id: null,
  }

  const parsedExperiences = candidate.experiences.map((experience) => ({
    id: crypto.randomUUID(),
    title: experience.role,
    company: experience.company,
    start_date: monthValue(experience.startDate),
    end_date: experience.endDate ? monthValue(experience.endDate) : null,
    is_current: experience.isCurrent,
    description: experience.description ?? "",
    achievements: experience.achievements ?? [],
    experience_type: experience.experienceType ?? "professional",
    raw_text: experience.rawText ?? null,
  }))

  return {
    ...base,
    preserveExistingOnEmpty: false,
    full_name: candidate.fullName?.trim() ?? "",
    email: candidate.email?.trim() || accountEmail?.trim() || "",
    phone: candidate.phone?.trim() ?? "",
    headline: candidate.headline?.trim() ?? "",
    summary: candidate.professionalSummary?.trim() ?? "",
    location: {
      country_code: candidate.country?.trim() ?? "",
      region_id: candidate.region?.trim() ?? "",
      commune_id: candidate.commune?.trim() ?? "",
    },
    skills: candidate.skills ?? [],
    experiences: parsedExperiences,
    additional_sections: candidate.additionalSections ?? {},
    source_cv_id: null,
  }
}

async function updateProfile(
  update: (profile: Profile) => ProfileDraft,
): Promise<Profile> {
  const profile = await getProfile()
  return saveProfile(update(profile))
}

export function updateProfileSummary(summary: string) {
  return updateProfile((profile) => ({ ...profile, summary }))
}

export function updatePersonalProfile(payload: Partial<ProfileDraft>) {
  return updateProfile((profile) => ({
    ...profile,
    ...payload,
    location: { ...profile.location, ...payload.location },
  }))
}

export async function addExperience(experience: Omit<Experience, "id">) {
  const created = { ...experience, id: crypto.randomUUID() }
  await updateProfile((profile) => ({
    ...profile,
    experiences: [...profile.experiences, created],
  }))
  return created
}

export async function updateExperience(id: string, experience: Partial<Experience>) {
  let updatedExperience: Experience | undefined
  await updateProfile((profile) => ({
    ...profile,
    experiences: profile.experiences.map((current) => {
      if (current.id !== id) return current
      updatedExperience = { ...current, ...experience }
      return updatedExperience
    }),
  }))
  if (!updatedExperience) throw new Error("No encontramos esa experiencia.")
  return updatedExperience
}

export async function deleteExperience(id: string) {
  await updateProfile((profile) => ({
    ...profile,
    experiences: profile.experiences.filter((experience) => experience.id !== id),
  }))
}

