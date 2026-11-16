export const queryKeys = {
  profile: ["profile"] as const,
  cvAts: ["cv-ats"] as const,
  jobMatchResults: (filters: Record<string, string | number | undefined>) =>
    ["jobmatch", "results", filters] as const,
  jobMatchAnalysis: (id: string) => ["jobmatch", "analyses", id] as const,
  letters: ["letters"] as const,
  interviews: ["interviews"] as const,
  applications: (status?: string) => ["applications", { status }] as const,
  history: ["history"] as const,
  me: ["me"] as const,
}
