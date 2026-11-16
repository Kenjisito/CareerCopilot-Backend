import { useEffect, useRef, useState } from "react"
import { useLocation } from "react-router-dom"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm, useWatch } from "react-hook-form"
import { z } from "zod"
import { Astro, Brand, Button, Icon } from "@/shared/ui"
import type { Experience } from "@/shared/types/api"
import { ApiError } from "@/shared/lib/apiError"
import { EmptyState, ErrorState, Skeleton } from "@/shared/components"
import {
  cvFileSchema,
  profileSchema,
  useProfile,
  useProfileDraftStore,
  useSaveProfile,
  profileDraftFromParsedCandidate,
  type ProfileDraft,
  PROFILE_ADDITIONAL_SECTIONS,
} from "@/features/profile"
import { useAuth } from "@/features/auth"
import { useParseCv } from "@/features/onboarding/hooks"

const onboardingTitles = [
  "Elige cómo comenzar",
  "Sube tu CV",
  "Confirma tu archivo",
  "Experiencia laboral",
  "Resumen profesional",
  "Educación y otras secciones",
  "Datos personales",
]

const monthNames = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

function formatMonth(value: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(value)
  if (!match) return value
  return `${monthNames[Number(match[2]) - 1] ?? match[2]} ${match[1]}`
}

function parseMonth(value: string) {
  const apiFormat = /^(\d{4})-(\d{2})$/.exec(value)
  if (apiFormat) return value
  const displayFormat = /^([a-záéíóú]{3})\s+(\d{4})$/i.exec(value)
  if (!displayFormat) return value
  const month = monthNames.findIndex((name) => name.toLowerCase() === displayFormat[1].toLowerCase())
  return month < 0 ? value : `${displayFormat[2]}-${String(month + 1).padStart(2, "0")}`
}

export function Onboarding({ onFinish }: { onFinish: () => void }) {
  const location = useLocation()
  const routeState = location.state as { step?: unknown } | null
  const initialStep =
    routeState?.step === 2 && useProfileDraftStore.getState().draft ? 2 : 0
  const [step, setStep] = useState(initialStep)
  const [uploadError, setUploadError] = useState("")
  const [saved, setSaved] = useState(false)
  const [selectedCv, setSelectedCv] = useState<File | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const retryFile = useRef<File | null>(null)
  const parseController = useRef<AbortController | null>(null)
  const saveController = useRef<AbortController | null>(null)
  const finishTimer = useRef<number | null>(null)
  const { session } = useAuth()
  const profileQuery = useProfile()
  const draft = useProfileDraftStore((state) => state.draft)
  const setDraft = useProfileDraftStore((state) => state.setDraft)
  const updateDraft = useProfileDraftStore((state) => state.updateDraft)
  const clearDraft = useProfileDraftStore((state) => state.clearDraft)
  const parse = useParseCv()
  const save = useSaveProfile()
  const currentStep = step
  const isUploading = parse.isPending
  const currentUploadError = uploadError
  const personalForm = useForm<{
    full_name: string
    headline: string
    phone: string
    country_code: string
    region_id: string
    commune_id: string
  }>({
    resolver: zodResolver(z.object({
      full_name: z.string().trim().min(1, "Ingresa tu nombre completo.").max(200),
      headline: z.string().max(200),
      phone: z.string().max(50),
      country_code: z.string().trim().min(1, "Ingresa un país.").max(100),
      region_id: z.string().trim().min(1, "Ingresa una región.").max(100),
      commune_id: z.string().trim().min(1, "Ingresa una comuna.").max(100),
    })),
    defaultValues: {
      full_name: "",
      headline: "",
      phone: "",
      country_code: "Chile",
      region_id: "Región Metropolitana",
      commune_id: "Providencia",
    },
  })
  const selectedCommuneForm = useWatch({ control: personalForm.control, name: "commune_id" }) ?? ""
  const draftPhone = draft?.phone
  const draftFullName = draft?.full_name
  const draftHeadline = draft?.headline
  const draftCountryCode = draft?.location.country_code
  const draftRegionId = draft?.location.region_id
  const draftCommuneId = draft?.location.commune_id
  const resetPersonalForm = personalForm.reset

  useEffect(() => () => {
    parseController.current?.abort()
    saveController.current?.abort()
    if (finishTimer.current !== null) window.clearTimeout(finishTimer.current)
  }, [])

  useEffect(() => {
    if (profileQuery.data && !draft && !saved) {
      setDraft(profileQuery.data)
    } else if (
      profileQuery.error instanceof ApiError &&
      profileQuery.error.status === 404 &&
      !draft
    ) {
      setDraft({
        full_name: session?.user.full_name ?? "",
        email: session?.user.email ?? "",
        phone: "",
        headline: "",
        summary: "",
        location: {
          country_code: "Chile",
          region_id: "Región Metropolitana",
          commune_id: "Providencia",
        },
        experiences: [],
        skills: [],
        additional_sections: {},
        source_cv_id: null,
      })
    }
  }, [
    profileQuery.data,
    profileQuery.error,
    draft,
    saved,
    session?.user.email,
    session?.user.full_name,
    setDraft,
  ])

  useEffect(() => {
    if (draftFullName) {
      resetPersonalForm({
        full_name: draftFullName,
        headline: draftHeadline ?? "",
        phone: draftPhone ?? "",
        country_code: draftCountryCode ?? "",
        region_id: draftRegionId ?? "",
        commune_id: draftCommuneId ?? "",
      })
    }
  }, [draftFullName, draftHeadline, draftPhone, draftCountryCode, draftRegionId, draftCommuneId, resetPersonalForm])

  const updateExperience = (index: number, update: Partial<Experience>) => {
    updateDraft((current) => ({
      ...current,
      experiences: current.experiences.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...update } : item,
      ),
    }))
  }

  const updateAdditionalSection = (section: string, value: string) =>
    updateDraft((current) => ({
      ...current,
      additional_sections: {
        ...(current.additional_sections ?? {}),
        [section]: value.split(/\r?\n/).map((entry) => entry.trim()).filter(Boolean),
      },
    }))

  const updateSkills = (value: string) =>
    updateDraft((current) => ({
      ...current,
      skills: value.split(/\r?\n/).map((skill) => skill.trim()).filter(Boolean),
    }))

  const uploadFile = async (file: File) => {
    if (parseController.current) return
    setUploadError("")
    const validation = cvFileSchema.safeParse(file)
    if (!validation.success) {
      setUploadError(validation.error.issues[0]?.message ?? "Archivo inválido.")
      return
    }
    retryFile.current = file
    const controller = new AbortController()
    parseController.current = controller
    try {
      const parsedCandidate = await parse.mutateAsync({ file, signal: controller.signal })
      setSelectedCv(file)
      const base = draft ?? {
        full_name: session?.user.full_name ?? "",
        email: session?.user.email ?? "",
        phone: "",
        headline: "",
        summary: "",
        location: {
          country_code: "Chile",
          region_id: "Región Metropolitana",
          commune_id: "Providencia",
        },
        experiences: [],
        skills: [],
        additional_sections: {},
        source_cv_id: null,
      }
      setDraft(profileDraftFromParsedCandidate(parsedCandidate, base, session?.user.email))
      setStep(2)
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return
      setUploadError(error instanceof ApiError ? error.message : "No se pudo subir el archivo.")
    } finally {
      parseController.current = null
    }
  }

  const next = async () => {
    if (currentStep < 6) {
      setStep(currentStep + 1)
      return
    }
    if (!draft) return
    setUploadError("")
    const isPersonalValid = await personalForm.trigger()
    if (!isPersonalValid) {
      setUploadError("Revisa tus datos personales antes de continuar.")
      return
    }
    const personal = personalForm.getValues()
    const payload: ProfileDraft = {
      ...draft,
      full_name: personal.full_name,
      headline: personal.headline,
      email: session?.user.email ?? draft.email ?? "",
      phone: personal.phone,
      location: {
        country_code: personal.country_code,
        region_id: personal.region_id,
        commune_id: personal.commune_id,
      },
    }
    const validation = profileSchema.safeParse(payload)
    if (!validation.success) {
      setUploadError(validation.error.issues[0]?.message ?? "Revisa los datos del perfil.")
      return
    }
    if (saveController.current) return
    const controller = new AbortController()
    saveController.current = controller
    try {
      await save.mutateAsync({ profile: payload, signal: controller.signal })
      clearDraft()
      setSaved(true)
      finishTimer.current = window.setTimeout(onFinish, 800)
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return
      setUploadError(error instanceof Error ? error.message : "No se pudo guardar el perfil.")
    } finally {
      saveController.current = null
    }
  }

  const addExperience = () =>
    updateDraft((current) => ({
      ...current,
      experiences: [...current.experiences, {
        id: crypto.randomUUID(),
        title: "",
        company: "",
        start_date: new Date().toISOString().slice(0, 7),
        end_date: null,
        is_current: true,
        description: "",
        achievements: [],
        experience_type: "professional",
      }],
    }))

  if (profileQuery.isLoading) {
    return (
      <div className="onboarding">
        <header className="onboarding-header">
          <Brand />
        </header>
        <main className="onboarding-main" aria-busy="true" aria-label="Cargando perfil">
          <Skeleton width="35%" height={14} variant="text" />
          <Skeleton width="70%" height={34} />
          <Skeleton width="60%" height={16} variant="text" />
          <div className="onboarding-loading-grid">
            <Skeleton height={180} />
            <Skeleton height={180} />
          </div>
          <Skeleton width="100%" height={120} />
        </main>
      </div>
    )
  }

  if (
    profileQuery.isError &&
    !(profileQuery.error instanceof ApiError && profileQuery.error.status === 404)
  ) {
    return (
      <div className="onboarding">
        <ErrorState
          message={profileQuery.error instanceof Error ? profileQuery.error.message : "No se pudo cargar tu perfil."}
          onRetry={() => void profileQuery.refetch()}
          error={profileQuery.error}
        />
      </div>
    )
  }

  return (
    <div className="onboarding">
      <header className="onboarding-header">
        <Brand />
        <button className="help-link">¿Necesitas ayuda?</button>
      </header>
      <div className="onboarding-progress">
        <span style={{ width: `${((currentStep + 1) / 7) * 100}%` }} />
      </div>
      <main className="onboarding-main">
        <div className="onboarding-top">
          <span>PASO {currentStep + 1} DE 7</span>
          <h1>
            {currentStep === 0
              ? `¡Hola, ${draft?.full_name.split(" ")[0] ?? session?.user.full_name.split(" ")[0] ?? ""}! ¿Cómo quieres crear tu perfil?`
              : onboardingTitles[currentStep]}
          </h1>
          <p>
            {currentStep === 0
              ? "Astro te ayudará a tener todo listo para despegar."
              : "Revisa la información. Podrás editarla cuando quieras."}
          </p>
        </div>
        {currentStep === 0 && (
          <div className="choice-layout">
            <div className="choice-grid">
              <button
                className="choice-card recommended"
                onClick={() => setStep(1)}
              >
                <span className="recommended-label">RECOMENDADO</span>
                <div className="choice-icon">
                  <Icon name="spark" />
                </div>
                <h3>Lectura automática con Astro</h3>
                <p>Sube tu CV y la IA completará tu perfil en segundos.</p>
                <span className="choice-action">
                  Comenzar con IA <Icon name="arrow" size={17} />
                </span>
              </button>
              <button className="choice-card" onClick={() => setStep(3)}>
                <div className="choice-icon muted">
                  <Icon name="edit" />
                </div>
                <h3>Carga manual</h3>
                <p>Completa cada sección paso a paso y a tu propio ritmo.</p>
                <span className="choice-action">
                  Completar manualmente <Icon name="arrow" size={17} />
                </span>
              </button>
            </div>
            <div className="onboarding-astro">
              <Astro size="medium" pose="wave" />
              <div className="astro-bubble">
                ¡Yo me encargo del trabajo pesado!
              </div>
            </div>
          </div>
        )}
        {currentStep === 1 && (
          <div className="upload-wrap">
            <div
              className={`upload-dropzone ${isUploading ? "is-uploading" : ""}`}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault()
                const file = event.dataTransfer.files[0]
                if (file) void uploadFile(file)
              }}
              aria-busy={isUploading}
            >
              <span className="upload-icon">
                <Icon name="upload" size={28} />
              </span>
              <h3>{isUploading ? "Astro está leyendo tu CV" : "Dale tu CV a Astro"}</h3>
              <p>Lo organizaré para dejar tu perfil listo para despegar.</p>
              <button
                type="button"
                className="ai-upload-button"
                onClick={() => fileInput.current?.click()}
                disabled={isUploading}
              >
                <Icon name="spark" size={18} />
                {isUploading ? "Analizando tu CV..." : "Elegir mi CV"}
              </button>
              <small>o arrástralo aquí · PDF o DOCX · Máximo 2 MB</small>
              {isUploading && (
                <span className="upload-bar">
                  <i className="upload-progress-indeterminate" />
                </span>
              )}
            </div>
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="sr-only"
              tabIndex={-1}
              onChange={(event) => {
                const file = event.currentTarget.files?.[0]
                if (file) void uploadFile(file)
                event.currentTarget.value = ""
              }}
            />
            <div className="privacy-note">
              <Icon name="check" size={16} /> Tus datos están cifrados y seguros
            </div>
          </div>
        )}
        {currentStep === 2 && (
          <div className="file-confirm">
            <div className="file-card">
              <div className="pdf-icon">
                {selectedCv?.name.toLowerCase().endsWith(".docx") ? "DOCX" : "PDF"}
              </div>
              <div>
                <h3>{selectedCv?.name ?? "CV cargado correctamente"}</h3>
                <p>
                  {selectedCv
                    ? `${(selectedCv.size / (1024 * 1024)).toFixed(1)} MB · Cargado correctamente`
                    : "Archivo procesado correctamente"}
                </p>
              </div>
              <span className="success-check">
                <Icon name="check" />
              </span>
            </div>
            <div className="file-actions">
              <Button
                variant="secondary"
                icon="upload"
                onClick={() => setStep(1)}
              >
                Reemplazar
              </Button>
            </div>
            <div className="astro-tip">
              <Astro size="small" pose="celebrate" />
              <p>
                <b>¡Todo listo!</b> Organicé experiencia, estudios, cursos,
                proyectos, idiomas y habilidades. Revisemos cada sección.
              </p>
            </div>
          </div>
        )}
        {currentStep === 3 && (
          <div className="form-panel">
            <div className="panel-heading">
              <div>
                <h3>Experiencia laboral</h3>
                <p>Astro encontró {draft?.experiences.length ?? 0} experiencias en tu CV.</p>
              </div>
              <Button
                variant="secondary"
                icon="plus"
                onClick={addExperience}
              >
                Agregar experiencia
              </Button>
            </div>
            {draft?.experiences.length === 0 && (
              <EmptyState
                title="Aún no agregas experiencia"
                description="Añade tus cargos y logros para completar tu perfil."
                actionLabel="Agregar experiencia"
                onAction={addExperience}
              />
            )}
            {(draft?.experiences ?? []).map((item, index) => (
              <div className="experience-card" key={item.id}>
                <div className="experience-number">{index + 1}</div>
                <div className="field-grid">
                  <label>
                    Cargo
                    <input
                      value={item.title}
                      onChange={(e) =>
                        updateExperience(index, { title: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Empresa o institución
                    <input
                      value={item.company}
                      onChange={(e) =>
                        updateExperience(index, { company: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Tipo de experiencia
                    <select
                      value={item.experience_type ?? "professional"}
                      onChange={(e) => updateExperience(index, {
                        experience_type: e.target.value as Experience["experience_type"],
                      })}
                    >
                      <option value="professional">Profesional</option>
                      <option value="academic">Académica</option>
                      <option value="internship">Práctica o pasantía</option>
                      <option value="volunteering">Voluntariado</option>
                      <option value="freelance">Freelance</option>
                      <option value="other">Otra</option>
                    </select>
                  </label>
                  <label className="full-field">
                    Periodo
                    <input
                      value={`${formatMonth(item.start_date)} — ${item.is_current ? "Actualidad" : formatMonth(item.end_date ?? "")}`}
                      onChange={(e) =>
                        (() => {
                          const [start, end] = e.target.value.split("—").map((part) => part.trim())
                          updateExperience(index, {
                            start_date: parseMonth(start || item.start_date),
                            is_current: !end || end.toLowerCase() === "actualidad",
                            end_date: !end || end.toLowerCase() === "actualidad" ? null : parseMonth(end),
                          })
                        })()
                      }
                    />
                  </label>
                  <label className="full-field">
                    Funciones y responsabilidades
                    <textarea
                      rows={3}
                      maxLength={3000}
                      value={item.description}
                      onChange={(e) =>
                        updateExperience(index, { description: e.target.value })
                      }
                    />
                    <span className="char-count">{item.description.length} / 3000</span>
                  </label>
                  <label className="full-field">
                    Logros y resultados
                    <textarea
                      rows={2}
                      maxLength={3000}
                      value={(item.achievements ?? []).join("\n")}
                      onChange={(e) => updateExperience(index, {
                        achievements: e.target.value.split(/\r?\n/).map((entry) => entry.trim()).filter(Boolean),
                      })}
                      placeholder="Un logro por línea, idealmente con métricas"
                    />
                  </label>
                </div>
                <button
                  className="icon-button"
                  aria-label="Eliminar experiencia"
                  onClick={() => updateDraft((current) => ({
                    ...current,
                    experiences: current.experiences.filter((experience) => experience.id !== item.id),
                  }))}
                >
                  <Icon name="trash" />
                </button>
              </div>
            ))}
          </div>
        )}
        {currentStep === 4 && (
          <div className="form-panel summary-panel">
            <div className="astro-tip compact">
              <Astro size="small" pose="think" />
              <p>
                <b>Consejo de Astro</b> Incluye tu especialidad, años de
                experiencia y el impacto que generas.
              </p>
            </div>
            <label>
              Tu resumen profesional
              <textarea
                rows={8}
                maxLength={1500}
                value={draft?.summary ?? ""}
                onChange={(e) => updateDraft((current) => ({ ...current, summary: e.target.value }))}
              />
              <span className="char-count">{draft?.summary.length ?? 0} / 1500</span>
            </label>
            <Button variant="secondary" icon="spark">
              Mejorar con Astro
            </Button>
          </div>
        )}
        {currentStep === 5 && (
          <div className="form-panel additional-sections-panel">
            <div className="panel-heading">
              <div>
                <h3>Información organizada por sección</h3>
                <p>Revisa que cada dato esté en la categoría correcta. Puedes editar o agregar líneas.</p>
              </div>
            </div>
            <label className="full-field">
              Competencias y habilidades
              <textarea
                rows={4}
                maxLength={10000}
                value={(draft?.skills ?? []).join("\n")}
                onChange={(event) => updateSkills(event.target.value)}
                placeholder="Una habilidad o competencia por línea"
              />
            </label>
            <div className="additional-sections-grid">
              {PROFILE_ADDITIONAL_SECTIONS.map(({ key, label }) => (
                <label key={key}>
                  {label}
                  <textarea
                    rows={3}
                    maxLength={45000}
                    value={(draft?.additional_sections?.[key] ?? []).join("\n")}
                    onChange={(event) => updateAdditionalSection(key, event.target.value)}
                    placeholder={`Una entrada por línea para ${label.toLowerCase()}`}
                  />
                </label>
              ))}
            </div>
          </div>
        )}
        {currentStep === 6 && (
          <div className="details-layout">
            <div className="form-panel">
              <div className="field-grid">
                <label>
                  Nombre completo
                  <input maxLength={200} {...personalForm.register("full_name")} />
                </label>
                <label>
                  Correo electrónico
                  <input value={session?.user.email ?? ""} readOnly />
                </label>
                  <label className="full-field">
                    Cargo o título profesional
                    <input maxLength={200} {...personalForm.register("headline")} />
                  </label>
                  <label>
                    Teléfono
                    <input type="tel" maxLength={50} {...personalForm.register("phone")} />
                  </label>
                <label>
                  País
                  <input maxLength={100} {...personalForm.register("country_code")} />
                </label>
                <label>
                  Región
                  <input maxLength={100} {...personalForm.register("region_id")} />
                </label>
                <label className="full-field">
                  Comuna
                  <input maxLength={100} {...personalForm.register("commune_id")} />
                </label>
              </div>
            </div>
            <div className="map-card">
              <div className="map-grid" />
              <div className="map-pin">
                <Icon name="map" />
              </div>
              <div className="map-caption">
                <b>{selectedCommuneForm || "Agrega una comuna"}</b>
                <span>Ubicación seleccionada</span>
              </div>
            </div>
          </div>
        )}
        {currentStep > 0 && (
          <div className="onboarding-footer">
            <Button
              variant="ghost"
              onClick={() => setStep(currentStep - 1)}
            >
              Volver
            </Button>
            <div className="step-dots">
              {Array.from({ length: 7 }).map((_, i) => (
                <span key={i} className={i <= currentStep ? "active" : ""} />
              ))}
            </div>
            <Button
              onClick={() => void next()}
              icon={saved ? "check" : "arrow"}
              disabled={save.isPending || parse.isPending || saved || currentStep === 1}
            >
              {saved
                ? "Perfil guardado"
                : save.isPending
                  ? "Guardando..."
                  : currentStep === 6
                    ? "Ir a mi dashboard"
                    : currentStep === 2
                      ? "Revisar información"
                      : "Guardar y continuar"}
            </Button>
          </div>
        )}
        {saved && (
          <p className="profile-save-success" role="status">
            Perfil guardado correctamente. Abriendo tu dashboard...
          </p>
        )}
        {currentUploadError && (
          <ErrorState
            message={currentUploadError}
            onRetry={() => {
              if (currentStep === 6) void next()
              else if (retryFile.current) void uploadFile(retryFile.current)
              else fileInput.current?.click()
            }}
          />
        )}
        {selectedCv && (
          <span className="sr-only">Archivo cargado correctamente</span>
        )}
      </main>
    </div>
  )
}
