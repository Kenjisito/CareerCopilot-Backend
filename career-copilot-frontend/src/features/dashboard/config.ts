import type { Module, IconName } from "@/shared/types"

export const moduleMeta: Record<Module, { label: string; icon: IconName }> = {
  overview: { label: "Resumen", icon: "history" },
  cv: { label: "Mi CV ATS", icon: "document" },
  jobmatch: { label: "JobMatch", icon: "target" },
  letters: { label: "Cartas & Emails", icon: "mail" },
  coach: { label: "Entrenador IA", icon: "message" },
  tracker: { label: "Historial & Tracker", icon: "history" },
}
