import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { Link } from "react-router-dom"
import { useAuth } from "@/features/auth/useAuth"
import { useSignIn, useSignUp } from "@/features/auth/hooks"
import { loginSchema, signUpSchema } from "@/features/auth/schemas"
import type { AuthCredentials, SignUpCredentials } from "@/features/auth/types"
import { Brand, Button, Icon } from "@/shared/ui"

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const auth = useAuth()
  const login = useSignIn()
  const register = useSignUp()
  const [showPassword, setShowPassword] = useState(false)
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
    <main className="auth-page">
      <header className="auth-hero">
        <div className="auth-orbit" aria-hidden="true" />
        <div className="auth-stars" aria-hidden="true" />
        <Link className="auth-brand" to="/" aria-label="Career Copilot, volver al inicio">
          <Brand light />
        </Link>
        <p className="auth-tagline">Tu carrera, lista para despegar</p>
        <Link className="auth-home-link" to="/">Volver al inicio</Link>
      </header>
      <section className="auth-content" aria-labelledby="auth-title">
        <form className="auth-card" onSubmit={(event) => void submit(event)}>
          <div className="auth-card-heading">
            <h1 id="auth-title">{isRegister ? "Crea tu cuenta" : "Inicia sesión"}</h1>
            <p>
              {isRegister
                ? "Tu copiloto de carrera te espera."
                : "Ingresa tus credenciales para continuar con Career Copilot."}
            </p>
          </div>
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
          <label htmlFor="auth-password">Contraseña</label>
          <div className="auth-password-field">
            <input
              id="auth-password"
              type={showPassword ? "text" : "password"}
              autoComplete={isRegister ? "new-password" : "current-password"}
              {...form.register("password")}
            />
            <button
              className="auth-password-toggle"
              type="button"
              aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
              aria-controls="auth-password"
              aria-pressed={showPassword}
              onClick={() => setShowPassword((visible) => !visible)}
            >
              <Icon name={showPassword ? "eyeOff" : "eye"} size={20} />
            </button>
          </div>
          <small role="alert">{form.formState.errors.password?.message}</small>
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
