import { z } from "zod"

export const loginSchema = z.object({
  email: z.email("Ingresa un correo válido.").max(320, "El correo admite hasta 320 caracteres."),
  password: z.string().min(1, "Ingresa tu contraseña.").max(128, "La contraseña admite hasta 128 caracteres."),
})

export const signUpSchema = loginSchema.extend({
  password: z.string().min(12, "La contraseña debe tener al menos 12 caracteres.").max(128, "La contraseña admite hasta 128 caracteres."),
  fullName: z.string().trim().min(2, "Ingresa tu nombre completo.").max(200, "El nombre admite hasta 200 caracteres."),
})
