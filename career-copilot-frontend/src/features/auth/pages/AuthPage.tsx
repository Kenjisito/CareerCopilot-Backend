import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { Link } from "react-router-dom"
import { useAuth } from "@/features/auth/useAuth"
import { useSignIn, useSignUp } from "@/features/auth/hooks"
import { loginSchema, signUpSchema } from "@/features/auth/schemas"
import type { AuthCredentials, SignUpCredentials } from "@/features/auth/types"
import { Brand, Button } from "@/shared/ui"

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const auth = useAuth()
  const login = useSignIn()
  const register = useSignUp()
  const isRegister = mode === "register"
  const form = useForm<AuthCredentials & Partial<Pick<SignUpCredentials, "fullName">>>({
    resolver: zodResolver(isRegister ? signUpSchema : loginSchema),
    defaultValues: { email: "", password: "", fullName: "" },
  })
  const error = login.error ?? register.error

  const submit = form.handleSubmit(async (values) => {
    try {
      if (isRegister) {
        await register.mutateAsync({
          email: values.email,
          password: values.password,
          fullName: values.fullName ?? "",
        })
      } else {
        await login.mutateAsync({ email: values.email, password: values.password })
      }
    } catch {
      // Mutation errors are rendered below.
    }
  })

  return (
    <main className="onboarding">
      <header className="onboarding-header">
        <Link to="/" aria-label="Volver al inicio"><Brand /></Link>
        <Link className="help-link" to="/">Volver al inicio</Link>
      </header>
      <section className="onboarding-main" style={{ maxWidth: 560 }}>
        <div className="onboarding-top">
          <h1>{isRegister ? "Crea tu cuenta" : "Inicia sesión"}</h1>
          <p>
            {isRegister ? "Tu copiloto de carrera te espera." : "Continúa tu búsqueda con Astro."}
          </p>
        </div>
        <form className="form-panel" onSubmit={(event) => void submit(event)}>
          {isRegister && (
            <label>
              Nombre completo
              <input {...form.register("fullName")} autoComplete="name" />
              <small role="alert">{form.formState.errors.fullName?.message}</small>
            </label>
          )}
          <label>
            Correo electrónico
            <input
              type="email"
              autoComplete="email"
              {...form.register("email")}
            />
            <small role="alert">{form.formState.errors.email?.message}</small>
          </label>
          <label>
            Contraseña
            <input
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              {...form.register("password")}
            />
            <small role="alert">{form.formState.errors.password?.message}</small>
          </label>
          {error && <p role="alert">{error.message}</p>}
          {auth.error && <p role="alert">{auth.error}</p>}
          <Button type="submit" disabled={login.isPending || register.isPending}>
            {isRegister ? "Crear cuenta gratis" : "Iniciar sesión"}
          </Button>
          <p>
            {isRegister ? "¿Ya tienes cuenta? " : "¿Aún no tienes cuenta? "}
            <Link to={isRegister ? "/login" : "/register"}>
              {isRegister ? "Inicia sesión" : "Crear cuenta"}
            </Link>
          </p>
        </form>
      </section>
    </main>
  )
}
