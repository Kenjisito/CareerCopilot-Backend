import { useEffect, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Navigate, useNavigate } from "react-router-dom"
import { useAuth } from "@/features/auth"
import { getLatestAtsDiagnostic } from "@/features/cv/api"
import { useParseCv } from "@/features/cv/hooks"
import {
  cvFileSchema,
  profileDraftFromParsedCandidate,
  PROFILE_ADDITIONAL_SECTIONS,
  useImproveProfile,
  useProfile,
  useSaveProfile,
  useProfileDraftStore,
} from "@/features/profile"
import type { ProfileDraft, ProfileImprovementChange } from "@/features/profile"
import { ApiError } from "@/shared/lib/apiError"
import { EmptyState, ErrorState, ModuleSkeleton } from "@/shared/components"
import { ModuleHeader } from "@/shared/ModuleHeader"
import { Astro, Button, Icon } from "@/shared/ui"
import { queryKeys } from "@/shared/lib/queryKeys"
import type { Experience, Profile } from "@/shared/types/api"

const experienceTypeLabels = {
  professional: "Profesional",
  academic: "Académica",
  internship: "Práctica",
  volunteering: "Voluntariado",
  freelance: "Freelance",
  other: "Otra",
} as const

function cloneProfile(profile: Profile): ProfileDraft {
  return {
    ...profile,
    location: { ...profile.location },
    experiences: profile.experiences.map((experience) => ({
      ...experience,
      achievements: [...(experience.achievements ?? [])],
    })),
    skills: [...profile.skills],
    additional_sections: Object.fromEntries(
      Object.entries(profile.additional_sections ?? {}).map(([key, entries]) => [key, [...entries]]),
    ),
  }
}

function splitLines(value: string): string[] {
  return value.split(/\r?\n/).filter((line) => line.trim().length > 0)
}

function CvEditorField({
  label,
  value,
  onChange,
  multiline = false,
  rows = 3,
  type = "text",
  maxLength,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  multiline?: boolean
  rows?: number
  type?: "text" | "email" | "tel" | "month"
  maxLength?: number
}) {
  return (
    <label className="cv-editor-field">
      <span>{label}</span>
      {multiline ? (
        <textarea
          value={value}
          rows={rows}
          maxLength={maxLength}
          onChange={(event) => onChange(event.currentTarget.value)}
        />
      ) : (
        <input
          type={type}
          value={value}
          maxLength={maxLength}
          onChange={(event) => onChange(event.currentTarget.value)}
        />
      )}
    </label>
  )
}

function CvEditor({
  profile,
  onUpdate,
}: {
  profile: ProfileDraft
  onUpdate: (update: (current: ProfileDraft) => ProfileDraft) => void
}) {
  const updateExperience = (index: number, patch: Partial<Experience>) => {
    onUpdate((current) => ({
      ...current,
      experiences: current.experiences.map((experience, currentIndex) =>
        currentIndex === index ? { ...experience, ...patch } : experience,
      ),
    }))
  }
  const configuredSections = PROFILE_ADDITIONAL_SECTIONS.map((section) => section.key)
  const sectionKeys = [...new Set([
    ...configuredSections,
    ...Object.keys(profile.additional_sections ?? {}),
  ])]

  return (
    <div className="cv-editor">
      <div className="cv-heading cv-heading-editor">
        <div className="cv-heading-fields">
          <CvEditorField
            label="Nombre completo"
            value={profile.full_name}
            maxLength={200}
            onChange={(full_name) => onUpdate((current) => ({ ...current, full_name }))}
          />
          <CvEditorField
            label="Titular profesional"
            value={profile.headline}
            maxLength={200}
            onChange={(headline) => onUpdate((current) => ({ ...current, headline }))}
          />
        </div>
      </div>
      <div className="cv-editor-contacts">
        <CvEditorField
          label="Correo"
          type="email"
          value={profile.email ?? ""}
          onChange={(email) => onUpdate((current) => ({ ...current, email }))}
        />
        <CvEditorField
          label="Teléfono"
          type="tel"
          value={profile.phone ?? ""}
          onChange={(phone) => onUpdate((current) => ({ ...current, phone }))}
        />
        <CvEditorField
          label="Comuna o ciudad"
          value={profile.location.commune_id}
          onChange={(commune_id) => onUpdate((current) => ({
            ...current,
            location: { ...current.location, commune_id },
          }))}
        />
        <CvEditorField
          label="Región"
          value={profile.location.region_id}
          onChange={(region_id) => onUpdate((current) => ({
            ...current,
            location: { ...current.location, region_id },
          }))}
        />
        <CvEditorField
          label="País"
          value={profile.location.country_code}
          onChange={(country_code) => onUpdate((current) => ({
            ...current,
            location: { ...current.location, country_code },
          }))}
        />
      </div>
      <div className="cv-section cv-section-editor">
        <h3>PERFIL</h3>
        <CvEditorField
          label="Resumen profesional"
          value={profile.summary}
          multiline
          rows={5}
          maxLength={5000}
          onChange={(summary) => onUpdate((current) => ({ ...current, summary }))}
        />
      </div>
      <div className="cv-section cv-section-editor">
        <div className="cv-editor-section-heading">
          <h3>EXPERIENCIA</h3>
          <button
            className="cv-add-entry"
            type="button"
            onClick={() => onUpdate((current) => ({
              ...current,
              experiences: [...current.experiences, {
                id: crypto.randomUUID(),
                title: "",
                company: "",
                start_date: "",
                end_date: null,
                is_current: false,
                description: "",
                achievements: [],
                experience_type: "professional",
                raw_text: null,
              }],
            }))}
          >
            <Icon name="plus" size={16} />
            Agregar experiencia
          </button>
        </div>
        {profile.experiences.map((experience, index) => (
          <div className="cv-role cv-role-editor" key={experience.id}>
            <div className="cv-editor-section-heading">
              <b>Experiencia {index + 1}</b>
              <button
                className="cv-remove-entry"
                type="button"
                aria-label={`Eliminar experiencia ${index + 1}`}
                onClick={() => onUpdate((current) => ({
                  ...current,
                  experiences: current.experiences.filter((_, currentIndex) => currentIndex !== index),
                }))}
              >
                Eliminar
              </button>
            </div>
            <div className="cv-editor-grid">
              <CvEditorField
                label="Cargo o actividad"
                value={experience.title}
                maxLength={200}
                onChange={(title) => updateExperience(index, { title })}
              />
              <CvEditorField
                label="Empresa o institución"
                value={experience.company}
                maxLength={200}
                onChange={(company) => updateExperience(index, { company })}
              />
              <CvEditorField
                label="Fecha de inicio"
                type="month"
                value={experience.start_date.slice(0, 7)}
                onChange={(start_date) => updateExperience(index, { start_date })}
              />
              {!experience.is_current && (
                <CvEditorField
                  label="Fecha de término"
                  type="month"
                  value={experience.end_date?.slice(0, 7) ?? ""}
                  onChange={(value) => updateExperience(index, { end_date: value || null })}
                />
              )}
              <label className="cv-current-checkbox">
                <input
                  type="checkbox"
                  checked={experience.is_current}
                  onChange={(event) => updateExperience(index, {
                    is_current: event.currentTarget.checked,
                    end_date: event.currentTarget.checked ? null : experience.end_date,
                  })}
                />
                Actualmente trabajo aquí
              </label>
              <CvEditorField
                label="Descripción"
                value={experience.description || experience.raw_text || ""}
                multiline
                rows={4}
                maxLength={3000}
                onChange={(description) => updateExperience(index, { description })}
              />
              <CvEditorField
                label="Logros (uno por línea)"
                value={(experience.achievements ?? []).join("\n")}
                multiline
                rows={3}
                onChange={(value) => updateExperience(index, { achievements: splitLines(value) })}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="cv-section cv-section-editor">
        <h3>HABILIDADES</h3>
        <CvEditorField
          label="Una habilidad por línea"
          value={profile.skills.join("\n")}
          multiline
          rows={4}
          onChange={(value) => onUpdate((current) => ({ ...current, skills: splitLines(value) }))}
        />
      </div>
      {sectionKeys.map((key) => (
        <div className="cv-section cv-section-editor" key={key}>
          <h3>{PROFILE_ADDITIONAL_SECTIONS.find((section) => section.key === key)?.label ?? key}</h3>
          <CvEditorField
            label="Un elemento por línea"
            value={(profile.additional_sections?.[key] ?? []).join("\n")}
            multiline
            rows={3}
            onChange={(value) => onUpdate((current) => ({
              ...current,
              additional_sections: {
                ...current.additional_sections,
                [key]: splitLines(value),
              },
            }))}
          />
        </div>
      ))}
    </div>
  )
}

function changeLabel(change: ProfileImprovementChange, profile: ProfileDraft): string {
  const labels = {
    headline: "Titular profesional",
    professionalSummary: "Perfil profesional",
    skills: "Habilidades",
    experienceDescription: "Descripción de experiencia",
    experienceAchievements: "Logros de experiencia",
  } satisfies Record<ProfileImprovementChange["field"], string>
  if (change.experienceId) {
    const experience = profile.experiences.find((item) => item.id === change.experienceId)
    if (experience) return `${labels[change.field]} · ${experience.title || experience.company}`
  }
  return labels[change.field]
}

export function CvModule() {
  const navigate = useNavigate()
  const { session } = useAuth()
  const profileQuery = useProfile()
  const setDraft = useProfileDraftStore((state) => state.setDraft)
  const fileInput = useRef<HTMLInputElement>(null)
  const parseController = useRef<AbortController | null>(null)
  const retryFile = useRef<File | null>(null)
  const [fileError, setFileError] = useState("")
  const parse = useParseCv()
  const improve = useImproveProfile()
  const save = useSaveProfile()
  const improveController = useRef<AbortController | null>(null)
  const saveController = useRef<AbortController | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [profileDraft, setProfileDraft] = useState<ProfileDraft | null>(null)
  const [improvements, setImprovements] = useState<{
    summary: string
    changes: ProfileImprovementChange[]
  } | null>(null)
  const [reviewedChanges, setReviewedChanges] = useState<Record<number, "accepted" | "rejected" | "adapted">>({})
  const [adaptingChange, setAdaptingChange] = useState<number | null>(null)
  const [adaptedValue, setAdaptedValue] = useState("")
  const atsQuery = useQuery({
    queryKey: queryKeys.cvAts,
    queryFn: ({ signal }) => getLatestAtsDiagnostic(signal),
  })

  useEffect(() => () => {
    parseController.current?.abort()
    improveController.current?.abort()
    saveController.current?.abort()
  }, [])

  const uploadFile = (file: File) => {
    const validation = cvFileSchema.safeParse(file)
    if (!validation.success) {
      setFileError(validation.error.issues[0]?.message ?? "Selecciona un archivo PDF o DOCX válido.")
      return
    }
    if (!profileQuery.data || parseController.current || parse.isPending) return

    setFileError("")
    retryFile.current = file
    const controller = new AbortController()
    parseController.current = controller
    parse.mutate(
      { file, signal: controller.signal },
      {
        onSuccess: (candidate) => {
        setDraft(profileDraftFromParsedCandidate(candidate, profileQuery.data, session?.user.email))
          navigate("/onboarding", { state: { step: 2 } })
        },
        onSettled: () => {
          if (parseController.current === controller) parseController.current = null
        },
      },
    )
  }

  const startDownload = () => {
    window.print()
  }

  const updateDraft = (update: (current: ProfileDraft) => ProfileDraft) => {
    setProfileDraft((current) => current ? update(current) : current)
  }

  const startEditing = () => {
    if (!profileQuery.data) return
    improve.reset()
    save.reset()
    setImprovements(null)
    setReviewedChanges({})
    setProfileDraft(cloneProfile(profileQuery.data))
    setIsEditing(true)
  }

  const cancelEditing = () => {
    improveController.current?.abort()
    improveController.current = null
    setProfileDraft(null)
    setImprovements(null)
    setReviewedChanges({})
    setAdaptingChange(null)
    setIsEditing(false)
    improve.reset()
    save.reset()
  }

  const requestImprovements = () => {
    if (!profileQuery.data || improveController.current || improve.isPending) return
    const source = profileDraft ?? cloneProfile(profileQuery.data)
    const controller = new AbortController()
    improveController.current = controller
    setProfileDraft(source)
    setIsEditing(true)
    setImprovements(null)
    setReviewedChanges({})
    improve.mutate(
      { profile: source, signal: controller.signal },
      {
        onSuccess: (result) => setImprovements(result),
        onSettled: () => {
          if (improveController.current === controller) improveController.current = null
        },
      },
    )
  }

  const saveChanges = () => {
    if (!profileDraft || saveController.current || save.isPending) return
    const controller = new AbortController()
    saveController.current = controller
    save.mutate(
      { profile: profileDraft, signal: controller.signal },
      {
        onSuccess: () => {
          setProfileDraft(null)
          setImprovements(null)
          setReviewedChanges({})
          setIsEditing(false)
        },
        onSettled: () => {
          if (saveController.current === controller) saveController.current = null
        },
      },
    )
  }

  const applyChange = (
    changeIndex: number,
    value: string,
    status: "accepted" | "adapted",
  ) => {
    const change = improvements?.changes[changeIndex]
    if (!change) return
    updateDraft((current) => {
      if (change.field === "headline") return { ...current, headline: value }
      if (change.field === "professionalSummary") return { ...current, summary: value }
      if (change.field === "skills") return { ...current, skills: splitLines(value) }

      const experience = current.experiences.find((item) =>
        change.experienceId ? item.id === change.experienceId :
          current.experiences.indexOf(item) === change.experienceIndex,
      )
      if (!experience) return current
      return {
        ...current,
        experiences: current.experiences.map((item) => item.id !== experience.id ? item : {
          ...item,
          ...(change.field === "experienceDescription"
            ? { description: value }
            : { achievements: splitLines(value) }),
        }),
      }
    })
    setReviewedChanges((current) => ({ ...current, [changeIndex]: status }))
    setAdaptingChange(null)
  }

  if (profileQuery.isLoading) return <ModuleSkeleton />

  if (profileQuery.isError) {
    if (profileQuery.error instanceof ApiError && profileQuery.error.status === 404) {
      return <Navigate to="/onboarding" replace />
    }

    return (
      <ErrorState
        message={profileQuery.error instanceof Error ? profileQuery.error.message : "No se pudo cargar tu perfil."}
        onRetry={() => void profileQuery.refetch()}
        error={profileQuery.error}
      />
    )
  }

  const profile = profileQuery.data
  if (!profile) {
    return (
      <EmptyState
        title="Completa tu perfil para crear tu CV"
        description="Agrega tu experiencia y habilidades para preparar una versión optimizada para ATS."
        actionLabel="Completar perfil"
        onAction={() => navigate("/onboarding")}
      />
    )
  }

  const displayedProfile = profileDraft ?? profile

  return (
    <>
      <ModuleHeader
        title="Tu CV está listo para despegar"
        copy="Formato limpio, profesional y optimizado para sistemas ATS."
      >
        <Button
          variant="secondary"
          icon="upload"
          onClick={() => fileInput.current?.click()}
          disabled={parse.isPending || isEditing || save.isPending || improve.isPending}
        >
          {parse.isPending ? "Leyendo CV..." : "Actualizar desde mi CV"}
        </Button>
        {isEditing ? (
          <>
            <Button variant="secondary" onClick={cancelEditing} disabled={save.isPending || improve.isPending}>
              Descartar
            </Button>
            <Button icon="check" onClick={saveChanges} disabled={save.isPending || improve.isPending}>
              {save.isPending ? "Guardando..." : "Guardar cambios"}
            </Button>
          </>
        ) : (
          <>
            <Button variant="secondary" icon="edit" onClick={startEditing}>
              Editar CV
            </Button>
            <Button icon="spark" onClick={requestImprovements} disabled={improve.isPending}>
              {improve.isPending ? "Astro está revisando..." : "Mejorar con Astro"}
            </Button>
          </>
        )}
        <Button
          icon="download"
          onClick={startDownload}
          disabled={isEditing || save.isPending}
        >
          Imprimir / guardar PDF
        </Button>
      </ModuleHeader>
      <input
        ref={fileInput}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="sr-only"
        tabIndex={-1}
        onChange={(event) => {
          const file = event.currentTarget.files?.[0]
          if (file) uploadFile(file)
          event.currentTarget.value = ""
        }}
      />
      {fileError && <p className="cv-file-error" role="alert">{fileError}</p>}
      {parse.isPending && (
        <div className="cv-parse-progress" role="status" aria-live="polite">
          <span>Leyendo tu CV para actualizar el perfil...</span>
          <span className="upload-bar"><i className="upload-progress-indeterminate" /></span>
        </div>
      )}
      {parse.isError && (
        <ErrorState
          title="No se pudo procesar el CV"
          message={parse.error instanceof Error ? parse.error.message : "Inténtalo nuevamente."}
          error={parse.error}
          onRetry={() => {
            if (retryFile.current) uploadFile(retryFile.current)
            else fileInput.current?.click()
          }}
        />
      )}
      {improve.isPending && (
        <div className="cv-ai-progress" role="status" aria-live="polite">
          <span className="typing-indicator" aria-hidden="true"><i /><i /><i /></span>
          <span>Astro está revisando tu CV y preparando cambios verificables.</span>
        </div>
      )}
      {improve.isError && (
        <ErrorState
          title="Astro no pudo preparar las mejoras"
          message={improve.error instanceof Error ? improve.error.message : "Inténtalo nuevamente."}
          error={improve.error}
          onRetry={requestImprovements}
        />
      )}
      {save.isError && (
        <ErrorState
          title="No se pudieron guardar los cambios"
          message={save.error instanceof Error ? save.error.message : "Inténtalo nuevamente."}
          error={save.error}
          onRetry={saveChanges}
        />
      )}
      {improvements && (
        <section className="cv-improvements" aria-labelledby="cv-improvements-title">
          <div className="cv-improvements-heading">
            <div>
              <span><Icon name="spark" size={16} />Revisión de Astro</span>
              <h2 id="cv-improvements-title">Decide qué cambios aplicar</h2>
              <p>{improvements.summary}</p>
            </div>
            {isEditing && <span className="cv-unsaved-note">Guarda el CV para conservar los cambios aceptados.</span>}
          </div>
          {improvements.changes.length === 0 ? (
            <p className="cv-no-improvements">Astro no encontró cambios necesarios sin agregar información nueva.</p>
          ) : (
            <div className="cv-change-list">
              {improvements.changes.map((change, index) => {
                const status = reviewedChanges[index]
                const targetExists = change.field !== "experienceDescription" &&
                  change.field !== "experienceAchievements" ||
                  (change.experienceId
                    ? profileDraft?.experiences.some((item) => item.id === change.experienceId)
                    : change.experienceIndex != null && change.experienceIndex < (profileDraft?.experiences.length ?? 0))
                const label = changeLabel(change, profileDraft ?? profile)
                return (
                  <article className="cv-change-card" key={`${change.field}-${change.experienceId ?? "profile"}`}>
                    <div className="cv-change-title">
                      <strong>{label}</strong>
                      {status && <span className={`cv-change-status cv-change-status-${status}`}>
                        {status === "accepted" ? "Aceptado" : status === "adapted" ? "Adaptado" : "Rechazado"}
                      </span>}
                    </div>
                    <p className="cv-change-reason">{change.reason}</p>
                    <div className="cv-change-comparison">
                      <div className="cv-change-old">
                        <span>Actual</span>
                        <p>{change.currentValue || "Sin contenido"}</p>
                      </div>
                      <div className="cv-change-new">
                        <span>Propuesta de Astro</span>
                        <p>{change.suggestedValue}</p>
                      </div>
                    </div>
                    {adaptingChange === index && (
                      <div className="cv-adapt-editor">
                        <label htmlFor={`cv-adapt-${index}`}>Adapta la propuesta a tu estilo</label>
                        <textarea
                          id={`cv-adapt-${index}`}
                          value={adaptedValue}
                          rows={4}
                          onChange={(event) => setAdaptedValue(event.currentTarget.value)}
                        />
                        <div>
                          <button
                            className="btn btn-secondary"
                            type="button"
                            onClick={() => setAdaptingChange(null)}
                          >
                            Seguir revisando
                          </button>
                          <button
                            className="btn btn-primary"
                            type="button"
                            disabled={!adaptedValue.trim() || !targetExists}
                            onClick={() => applyChange(index, adaptedValue, "adapted")}
                          >
                            Usar mi versión
                          </button>
                        </div>
                      </div>
                    )}
                    {status == null && adaptingChange !== index && (
                      <div className="cv-change-actions">
                        <button
                          className="btn btn-primary"
                          type="button"
                          disabled={!targetExists}
                          onClick={() => applyChange(index, change.suggestedValue, "accepted")}
                        >
                          <Icon name="check" size={16} />Aceptar
                        </button>
                        <button
                          className="btn btn-secondary"
                          type="button"
                          onClick={() => setReviewedChanges((current) => ({ ...current, [index]: "rejected" }))}
                        >
                          <Icon name="x" size={16} />Denegar
                        </button>
                        <button
                          className="btn btn-secondary"
                          type="button"
                          onClick={() => {
                            setAdaptedValue(change.suggestedValue)
                            setAdaptingChange(index)
                          }}
                        >
                          <Icon name="edit" size={16} />Adaptar
                        </button>
                      </div>
                    )}
                    {!targetExists && (
                      <p className="cv-change-warning">Esta experiencia ya no está en el borrador; no se aplicará una propuesta a otra.</p>
                    )}
                  </article>
                )
              })}
            </div>
          )}
        </section>
      )}
      <div className="cv-layout">
        <section className="cv-paper">
          {isEditing && profileDraft ? (
            <CvEditor profile={profileDraft} onUpdate={updateDraft} />
          ) : (
            <>
              <div className="cv-heading">
                <div>
                  <h2>{displayedProfile.full_name}</h2>
                  <strong>{displayedProfile.headline}</strong>
                  <p className="cv-contact">
                    {[
                      displayedProfile.email,
                      displayedProfile.phone,
                      displayedProfile.location.commune_id,
                      displayedProfile.location.region_id,
                      displayedProfile.location.country_code,
                    ].filter(Boolean).join(" · ")}
                  </p>
                </div>
              </div>
              <div className="cv-section">
                <h3>PERFIL</h3>
                {displayedProfile.summary ? (
                  <p>{displayedProfile.summary}</p>
                ) : (
                  <EmptyState
                    title="Agrega un resumen profesional"
                    description="Un resumen claro ayuda a destacar tu experiencia."
                    actionLabel="Completar perfil"
                    onAction={() => navigate("/onboarding")}
                  />
                )}
              </div>
              <div className="cv-section">
                <h3>EXPERIENCIA</h3>
                {displayedProfile.experiences.length > 0 ? displayedProfile.experiences.map((experience) => (
                  <div className="cv-role" key={experience.id}>
                    <b>{experience.title || "Experiencia"}</b>
                    {(experience.company || experience.start_date || experience.end_date || experience.experience_type) && (
                      <span>
                        {[
                          experience.company,
                          experience.start_date && `${experience.start_date}${experience.is_current ? " — Actualidad" : experience.end_date ? ` — ${experience.end_date}` : ""}`,
                          experience.experience_type && experience.experience_type !== "professional"
                            ? experienceTypeLabels[experience.experience_type]
                            : "",
                        ].filter(Boolean).join(" · ")}
                      </span>
                    )}
                    {(experience.description || experience.raw_text) && (
                      <p>{experience.description || experience.raw_text}</p>
                    )}
                    {!!experience.achievements?.length && <p>{experience.achievements.join(" · ")}</p>}
                  </div>
                )) : (
                  <EmptyState
                    title="Aún no agregas experiencia"
                    description="Completa tu trayectoria para incluirla en el CV."
                    actionLabel="Agregar experiencia"
                    onAction={() => navigate("/onboarding")}
                  />
                )}
              </div>
              <div className="cv-section">
                <h3>HABILIDADES</h3>
                {displayedProfile.skills.length > 0 ? (
                  <p>{displayedProfile.skills.join(" · ")}</p>
                ) : (
                  <EmptyState
                    title="Aún no agregas habilidades"
                    description="Incluye tus competencias para mejorar la lectura ATS."
                    actionLabel="Agregar habilidades"
                    onAction={() => navigate("/onboarding")}
                  />
                )}
              </div>
              {Object.entries(displayedProfile.additional_sections ?? {}).map(([key, entries]) => {
                if (!entries.length) return null
                const label = PROFILE_ADDITIONAL_SECTIONS.find((section) => section.key === key)?.label ?? key
                return (
                  <div className="cv-section" key={key}>
                    <h3>{label}</h3>
                    {entries.map((entry, index) => <p key={`${key}-${index}`}>{entry}</p>)}
                  </div>
                )
              })}
            </>
          )}
        </section>
        <aside className="ats-panel">
          <div className="ats-score">
            <div>
              {atsQuery.isLoading ? "…" : atsQuery.data?.score ?? "—"}<span>/100</span>
            </div>
            <h3>{atsQuery.data ? "Diagnóstico ATS" : "Diagnóstico pendiente"}</h3>
            <p>
              {atsQuery.data?.summary ??
                "Actualiza tu CV para analizar su legibilidad y recibir recomendaciones reales."}
            </p>
            {isEditing && <p className="cv-score-stale">El diagnóstico se actualizará al guardar el CV.</p>}
          </div>
          <ul>
            {atsQuery.data
              ? Object.entries(atsQuery.data.sections).map(([section, present]) => (
                  <li key={section}>
                    <Icon name={present ? "check" : "x"} />
                    {section === "contactInfo" ? "Datos de contacto" :
                      section === "workExperience" ? "Experiencia" :
                        section === "education" ? "Educación" : "Habilidades"}
                  </li>
                ))
              : <li><Icon name="spark" />Sube o actualiza tu CV para iniciar el diagnóstico.</li>}
          </ul>
          <div className="astro-tip compact">
            <Astro size="small" pose="think" />
            <p>
              <b>Tip de Astro</b> Actualiza tu CV para cada oferta usando
              JobMatch.
            </p>
          </div>
        </aside>
      </div>
      {atsQuery.isError && (
        <ErrorState
          message={atsQuery.error instanceof Error ? atsQuery.error.message : "No se pudo cargar el diagnóstico ATS."}
          error={atsQuery.error}
          onRetry={() => void atsQuery.refetch()}
        />
      )}
    </>
  )
}
