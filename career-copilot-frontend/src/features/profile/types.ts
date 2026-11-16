import type { Profile } from "@/shared/types/api"

export const PROFILE_ADDITIONAL_SECTIONS = [
  { key: "education", label: "Educación y formación" },
  { key: "certifications", label: "Certificaciones y cursos" },
  { key: "projects", label: "Proyectos" },
  { key: "languages", label: "Idiomas" },
  { key: "achievements", label: "Logros y reconocimientos" },
  { key: "volunteering", label: "Voluntariado" },
  { key: "publications", label: "Publicaciones e investigaciones" },
  { key: "interests", label: "Intereses" },
  { key: "references", label: "Referencias" },
  { key: "other", label: "Otra información" },
] as const

export type ProfileAdditionalSections = Record<string, string[]>

export type ProfileDraft = Omit<Profile, "id" | "updated_at"> & {
  id?: string
  updated_at?: string
  preserveExistingOnEmpty?: boolean
}

export interface UpsertExperienceRequest {
  role: string
  company: string
  startDate: string
  endDate: string | null
  isCurrent: boolean
  description: string | null
  achievements?: string[]
  experienceType?: "professional" | "academic" | "internship" | "volunteering" | "freelance" | "other"
  rawText?: string | null
}

export interface UpsertProfileRequest {
  fullName: string
  headline: string | null
  email: string
  phone: string | null
  country: string | null
  region: string | null
  commune: string | null
  professionalSummary: string | null
  skills: string[]
  experiences: UpsertExperienceRequest[]
  additionalSections: ProfileAdditionalSections
  preserveExistingOnEmpty?: boolean
}

export interface ExperienceResponse extends UpsertExperienceRequest {
  id: string
}

export interface ProfileResponse {
  id: string
  fullName: string
  headline?: string | null
  email: string
  phone: string | null
  country: string | null
  region: string | null
  commune: string | null
  professionalSummary: string | null
  skills: string[]
  experiences: ExperienceResponse[]
  additionalSections?: ProfileAdditionalSections
}

export type ProfileImprovementField =
  | "headline"
  | "professionalSummary"
  | "skills"
  | "experienceDescription"
  | "experienceAchievements"

export interface ProfileImprovementRequest {
  headline: string | null
  professionalSummary: string | null
  skills: string[]
  experiences: Array<{
    id: string
    role: string
    company: string
    description: string
    achievements: string[]
  }>
}

export interface ProfileImprovementChange {
  field: ProfileImprovementField
  experienceIndex: number | null
  currentValue: string
  suggestedValue: string
  reason: string
  experienceId: string | null
}

export interface ProfileImprovementsResponse {
  summary: string
  changes: ProfileImprovementChange[]
}

export interface ParsedExperienceResponse {
  role: string
  company: string
  startDate: string
  endDate: string | null
  isCurrent: boolean
  description: string | null
  achievements?: string[]
  experienceType?: "professional" | "academic" | "internship" | "volunteering" | "freelance" | "other"
  rawText?: string | null
}

export interface ParsedCandidateProfileResponse {
  fullName: string
  headline?: string | null
  email: string | null
  phone: string | null
  country: string | null
  region: string | null
  commune: string | null
  professionalSummary: string | null
  skills: string[]
  experiences: ParsedExperienceResponse[]
  additionalSections?: ProfileAdditionalSections
  nameInferred?: boolean
  warnings?: string[] | null
  strategy?: string | null
}
