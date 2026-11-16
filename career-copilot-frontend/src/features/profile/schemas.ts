import { z } from "zod"

export const profileSchema = z.object({
  full_name: z.string().trim().min(1, "Ingresa tu nombre completo.").max(200, "El nombre admite hasta 200 caracteres."),
  email: z.email("Ingresa un correo válido.").max(320, "El correo admite hasta 320 caracteres."),
  summary: z.string().max(1500, "El resumen admite hasta 1500 caracteres."),
  location: z.object({
    country_code: z.string().max(100),
    region_id: z.string().max(100),
    commune_id: z.string().max(100),
  }),
  phone: z.string().max(50, "El teléfono admite hasta 50 caracteres."),
  experiences: z.array(z.object({
    id: z.string(),
    title: z.string().trim().max(200, "El cargo admite hasta 200 caracteres."),
    company: z.string().trim().max(200, "La empresa admite hasta 200 caracteres."),
    start_date: z.string(),
    end_date: z.string().nullable(),
    is_current: z.boolean(),
    description: z.string().max(3000, "La descripción admite hasta 3000 caracteres."),
    achievements: z.array(z.string().max(3000)).max(100).optional(),
    experience_type: z.enum(["professional", "academic", "internship", "volunteering", "freelance", "other"]).optional(),
    raw_text: z.string().max(12000).nullable().optional(),
  })).superRefine((experiences, context) => {
    experiences.forEach((experience, index) => {
      if (experience.end_date && experience.end_date < experience.start_date) {
        context.addIssue({
          code: "custom",
          path: [index, "end_date"],
          message: "La fecha de término no puede ser anterior a la fecha de inicio.",
        })
      }
      if (experience.is_current && experience.end_date) {
        context.addIssue({
          code: "custom",
          path: [index, "end_date"],
          message: "Una experiencia actual no puede tener fecha de término.",
        })
      }
    })
  }),
  skills: z.array(z.string().trim().min(1).max(100)).max(100),
  additional_sections: z.record(
    z.string(),
    z.array(z.string().trim().min(1).max(3000)).max(100),
  ).default({}).superRefine((sections, context) => {
    if (Object.keys(sections).length > 20) {
      context.addIssue({ code: "custom", message: "El perfil admite hasta 20 secciones adicionales." })
    }
  }),
  source_cv_id: z.string().nullable(),
})

export const cvFileSchema = z.instanceof(File).refine(
  (file) => {
    const filename = file.name.toLowerCase()
    const mime = file.type.toLowerCase()
    return (
      (filename.endsWith(".pdf") && mime === "application/pdf") ||
      (filename.endsWith(".docx") &&
        mime === "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    )
  },
  "Selecciona un archivo PDF o DOCX válido.",
).refine(
  (file) => file.size <= 2_097_152,
  "El archivo supera el límite máximo de 2 MB.",
)

export type ProfileFormValues = z.infer<typeof profileSchema>
