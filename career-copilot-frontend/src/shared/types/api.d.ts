export interface Experience {
  id: string
  title: string
  company: string
  start_date: string
  end_date: string | null
  is_current: boolean
  description: string
  achievements?: string[]
  experience_type?: "professional" | "academic" | "internship" | "volunteering" | "freelance" | "other"
  raw_text?: string | null
}

export interface Profile {
  id: string
  full_name: string
  email?: string
  phone?: string
  headline: string
  summary: string
  location: {
    country_code: string
    region_id: string
    commune_id: string
    lat?: number
    lng?: number
  }
  experiences: Experience[]
  skills: string[]
  additional_sections?: Record<string, string[]>
  source_cv_id: string | null
  updated_at: string
}

export interface CvFile {
  id: string
  filename: string
  mime: string
  size_bytes: number
  status: "uploaded" | "parsing" | "parsed" | "failed"
  uploaded_at: string
}

export interface Paginated<T> {
  items: T[]
  next_cursor: string | null
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    field?: string
  }
}
