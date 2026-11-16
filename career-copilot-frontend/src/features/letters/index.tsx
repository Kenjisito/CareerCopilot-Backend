import { useEffect, useRef, useState } from "react"
import { useCoverLetter, useCreateCoverLetter } from "@/features/letters/hooks"
import { buildGmailComposeUrl } from "@/features/letters/gmail"
import type { CoverLetterTone, GenerateCoverLetterRequest } from "@/features/letters/types"
import { useJobMatches } from "@/features/jobmatch/hooks"
import { EmptyState, ErrorState, Skeleton } from "@/shared/components"
import { ModuleHeader } from "@/shared/ModuleHeader"
import { Astro, Button, Icon } from "@/shared/ui"
import type { Module } from "@/shared/types"

const tones: { value: CoverLetterTone; label: string }[] = [
  { value: "Formal", label: "Formal" },
  { value: "Dynamic", label: "Dinámico" },
  { value: "Executive", label: "Ejecutivo" },
]
const toneLabels: Record<CoverLetterTone, string> = {
  Formal: "Formal",
  Dynamic: "Dinámico",
  Executive: "Ejecutivo",
}

function LettersSkeleton() {
  return (
    <>
      <ModuleHeader
        title="Cartas que abren puertas"
        copy="Una buena oportunidad merece un mensaje que suene a ti."
      />
      <div className="letters-workspace" aria-busy="true" aria-label="Cargando ofertas">
        <section className="generator-form letters-form letter-loading">
          <Skeleton width="70%" height={42} />
          <Skeleton width="100%" height={46} />
          <Skeleton width="100%" height={46} />
          <Skeleton width="100%" height={48} />
        </section>
        <section className="output-card letters-output">
          <div className="output-header"><Skeleton width="42%" height={20} /></div>
          <div className="letter-loading">
            <Skeleton width="92%" height={13} variant="text" />
            <Skeleton width="84%" height={13} variant="text" />
            <Skeleton width="88%" height={13} variant="text" />
            <Skeleton width="78%" height={13} variant="text" />
          </div>
        </section>
      </div>
    </>
  )
}

export function LettersModule({ setActive }: { setActive: (module: Module) => void }) {
  const [jobAnalysisId, setJobAnalysisId] = useState<string | null>(null)
  const [tone, setTone] = useState<CoverLetterTone>("Dynamic")
  const [letterId, setLetterId] = useState<string | null>(null)
  const [displayedLetter, setDisplayedLetter] = useState<{
    id: string | null
    content: string
  }>({ id: null, content: "" })
  const [recipient, setRecipient] = useState("")
  const createController = useRef<AbortController | null>(null)
  const recipientInput = useRef<HTMLInputElement | null>(null)
  const jobsQuery = useJobMatches()
  const createLetter = useCreateCoverLetter()
  const letterQuery = useCoverLetter(letterId)
  const jobs = jobsQuery.data ?? []
  const selectedJob = jobs.find((job) => job.id === jobAnalysisId) ?? jobs[0]
  const letter = letterQuery.data
  const generatedContent = letter?.content ?? ""
  const generatedId = letter?.id ?? null

  useEffect(() => () => {
    createController.current?.abort()
  }, [])

  useEffect(() => {
    if (!generatedContent || !generatedId) return

    let position = 0
    const timer = window.setInterval(() => {
      position = Math.min(position + 5, generatedContent.length)
      setDisplayedLetter({ id: generatedId, content: generatedContent.slice(0, position) })
      if (position === generatedContent.length) window.clearInterval(timer)
    }, 24)

    return () => window.clearInterval(timer)
  }, [generatedContent, generatedId])
  const displayedContent = displayedLetter.id === generatedId ? displayedLetter.content : ""

  const openGmailCompose = () => {
    if (!letter || !recipientInput.current?.reportValidity()) return
    const url = buildGmailComposeUrl(
      recipient.trim(),
      letter.subject,
      letter.body,
    )
    window.open(url, "_blank", "noopener,noreferrer")
  }

  const generate = (request?: GenerateCoverLetterRequest) => {
    const payload = request ?? (selectedJob ? { jobAnalysisId: selectedJob.id, tone } : null)
    if (!payload || createController.current || createLetter.isPending) return

    const controller = new AbortController()
    createController.current = controller
    setLetterId(null)
    createLetter.mutate(
      { request: payload, signal: controller.signal },
      {
        onSuccess: ({ id }) => setLetterId(id),
        onSettled: () => {
          if (createController.current === controller) createController.current = null
        },
      },
    )
  }

  if (jobsQuery.isLoading) return <LettersSkeleton />

  if (jobsQuery.isError && jobs.length === 0) {
    return (
      <>
        <ModuleHeader
          title="Cartas que abren puertas"
          copy="Una buena oportunidad merece un mensaje que suene a ti."
        />
        <ErrorState
          message={jobsQuery.error.message}
          onRetry={() => void jobsQuery.refetch()}
          error={jobsQuery.error}
        />
      </>
    )
  }

  return (
    <div className="letters-module">
      <ModuleHeader
        title="Cartas que abren puertas"
        copy="Una buena oportunidad merece un mensaje que suene a ti."
      />
      {jobs.length === 0 ? (
        <EmptyState
          title="Primero analiza una oferta"
          description="Selecciona una oferta analizada para que Astro pueda personalizar tu carta."
          actionLabel="Ir a JobMatch"
          onAction={() => setActive("jobmatch")}
        />
      ) : (
        <div className="letters-workspace">
          <section className="generator-form letters-form">
            <div className="letters-section-heading">
              <span className="letters-icon-tile"><Icon name="edit" size={18} /></span>
              <div><h2>Prepara tu mensaje</h2><p>Elige una oferta analizada y el tono de tu carta.</p></div>
            </div>
            <label>
              <span className="letters-field-label"><Icon name="target" size={15} />Oferta objetivo</span>
              <select
                value={selectedJob?.id ?? ""}
                disabled={createLetter.isPending}
                onChange={(event) => {
                  setJobAnalysisId(event.currentTarget.value)
                  setLetterId(null)
                  createLetter.reset()
                }}
              >
                {jobs.map((job) => (
                  <option value={job.id} key={job.id}>
                    {job.jobTitle} · {job.company}
                  </option>
                ))}
              </select>
            </label>
            <fieldset disabled={createLetter.isPending}>
              <legend><span className="letters-field-label"><Icon name="message" size={15} />Elige el tono</span></legend>
              <div className="tone-options">
                {tones.map(({ value, label }) => (
                  <button
                    type="button"
                    className={tone === value ? "active" : ""}
                    onClick={() => setTone(value)}
                    key={value}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </fieldset>
            {jobsQuery.isError && (
              <ErrorState
                message={jobsQuery.error.message}
                onRetry={() => void jobsQuery.refetch()}
                error={jobsQuery.error}
              />
            )}
            <Button
              onClick={() => generate()}
              icon="spark"
              disabled={!selectedJob || createLetter.isPending}
            >
              {createLetter.isPending ? "Generando..." : "Generar con Astro"}
            </Button>
            {createLetter.isPending && (
              <div className="letter-progress letters-writing-status" role="status" aria-live="polite">
                <span className="typing-indicator" aria-hidden="true"><i /><i /><i /></span>
                <span>Astro está pensando y redactando tu carta...</span>
              </div>
            )}
          </section>
          <section className={`output-card letters-output ${letter ? "generated" : ""}`}>
            <div className="output-header">
              <div>
                <h2>Carta de presentación</h2>
                {selectedJob && (
                  <p>{[selectedJob.jobTitle, selectedJob.company].filter(Boolean).join(" · ")}</p>
                )}
              </div>
              {letter && (
                <button
                  className="icon-button"
                  type="button"
                  title="Copiar texto"
                  aria-label="Copiar texto"
                  onClick={() => void navigator.clipboard?.writeText(letter.content)}
                >
                  <Icon name="copy" />
                </button>
              )}
            </div>
            {createLetter.isError && (
              <ErrorState
                title="No se pudo generar la carta"
                message={createLetter.error.message}
                error={createLetter.error}
                onRetry={() => {
                  const request = createLetter.variables?.request
                  if (request) generate(request)
                }}
              />
            )}
            {letterId && letterQuery.isLoading && <CoverLetterSkeleton />}
            {letterId && letterQuery.isError && (
              <ErrorState
                title="No se pudo cargar la carta"
                message={letterQuery.error.message}
                onRetry={() => void letterQuery.refetch()}
                error={letterQuery.error}
              />
            )}
            {letter && (
              <>
                <textarea
                  className="letter-output"
                  value={displayedContent}
                  readOnly
                  rows={17}
                  aria-label="Carta generada"
                />
                <div className="output-footer">
                  <span>
                    <span className="letters-success-icon"><Icon name="check" size={12} /></span>
                    Personalizada para {selectedJob?.company ?? "la oferta seleccionada"} · Tono {toneLabels[letter.tone]}
                  </span>
                  <div className="letters-send-controls">
                    <form
                      className="letters-send-form"
                      onSubmit={(event) => {
                        event.preventDefault()
                        openGmailCompose()
                      }}
                    >
                      <input
                        type="email"
                        required
                        ref={recipientInput}
                        value={recipient}
                        onChange={(event) => {
                          setRecipient(event.currentTarget.value)
                        }}
                        placeholder="correo@empresa.com"
                        aria-label="Correo de destino"
                      />
                      <button className="gmail-compose-button" type="submit">
                        <Icon name="gmail" size={18} />
                        Abrir en Gmail
                      </button>
                    </form>
                    <Button
                      variant="secondary"
                      icon="copy"
                      onClick={() => void navigator.clipboard?.writeText(letter.content)}
                    >
                      Copiar texto
                    </Button>
                  </div>
                </div>
              </>
            )}
            {!letterId && !letter && !createLetter.isPending && !createLetter.isError && (
              <div className="empty-output">
                <EmptyState
                  title="Tu borrador aparecerá aquí"
                  description="Elige el tono de tu carta y Astro la personalizará según la oferta analizada."
                >
                  <Astro size="medium" pose="read" />
                </EmptyState>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

function CoverLetterSkeleton() {
  return (
    <div className="letter-loading" aria-busy="true" aria-label="Cargando carta">
      <Skeleton width="44%" height={20} />
      <Skeleton width="90%" height={13} variant="text" />
      <Skeleton width="96%" height={13} variant="text" />
      <Skeleton width="84%" height={13} variant="text" />
      <Skeleton width="92%" height={13} variant="text" />
      <Skeleton width="76%" height={13} variant="text" />
      <Skeleton width="35%" height={13} variant="text" />
    </div>
  )
}
