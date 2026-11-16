export interface StartInterviewRequest {
  targetRole: string
  jobMatchId: string
}

export interface SendInterviewMessageRequest {
  content: string
}

export interface InterviewMessageResponse {
  id: string
  role: "Astro" | "Candidate"
  content: string
  score: number | null
  feedback: string | null
  createdAt: string
}

export interface InterviewSessionResponse {
  id: string
  targetRole: string
  startedAt: string
  completedAt: string | null
  score: number | null
  feedback: string | null
  messages: InterviewMessageResponse[]
}
