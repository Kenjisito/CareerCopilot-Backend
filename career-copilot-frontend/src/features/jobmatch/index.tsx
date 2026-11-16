import { useEffect, useRef, useState } from "react"
import {
  useAnalyzeJobMatch,
  useExtractJobOffer,
  useJobMatch,
  useJobMatches,
} from "@/features/jobmatch/hooks"
import { fieldLimits, MIN_DESCRIPTION_LENGTH } from "@/features/jobmatch/api"
import type { AnalyzeJobRequest } from "@/features/jobmatch/types"
import { Button, Icon } from "@/shared/ui"
import { ModuleHeader } from "@/shared/ModuleHeader"
import { EmptyState, ErrorState, Skeleton } from "@/shared/components"
import { ApiError } from "@/shared/lib/apiError"

/** Errores de un campo. Acepta varios nombres: los del frontend (JobTitle) y los
 *  que usa el backend FastAPI (nombre, empresa, ofertaTexto). */
function getFieldErrors(
  errors: Record<string, string[]> | undefined,
  ...fields: string[]
): string[] {
  const wanted = fields.map((field) => field.toLowerCase())
  return Object.entries(errors ?? {})
    .filter(([name]) => wanted.includes(name.toLowerCase()))
    .flatMap(([, messages]) => messages)
}

/** A partir de este largo, un texto pegado en la descripción se ordena con Astro automáticamente. */
const AUTO_TIDY_MIN_PASTE = 300

/** Progreso, error o éxito de la lectura de una oferta (desde enlace o texto pegado). */
function ExtractFeedback({
  extract,
  notice,
  pendingLabel = "Astro está leyendo la oferta...",
  onUndo,
}: {
  extract: ReturnType<typeof useExtractJobOffer>
  notice: string | null
  pendingLabel?: string
  onUndo?: () => void
}) {
  if (extract.isPending) {
    return (
      <div className="jobmatch-progress" role="status" aria-live="polite">
        <span>{pendingLabel}</span>
        <span className="jobmatch-progress-track"><i /></span>
      </div>
    )
  }
  if (extract.isError) {
    return (
      <p className="jobmatch-import-error" role="alert">
        {extract.error.message}
        {/* El backend ya explica cómo copiar y pegar en la mayoría de sus errores. */}
        {!/p[ée]ga/i.test(extract.error.message) &&
          " Puedes copiar el texto de la oferta y pegarlo en la descripción."}
      </p>
    )
  }
  if (!notice) return null
  return (
    <p className="jobmatch-import-success" role="status">
      <Icon name="check" size={15} />
      <span>
        {notice}
        {onUndo && (
          <>
            {" "}
            <button type="button" className="jobmatch-link-button" onClick={onUndo}>
              Deshacer
            </button>
          </>
        )}
      </span>
    </p>
  )
}

function isHttpUrl(value: string): boolean {
  const text = value.trim()
  if (!text || /\s/.test(text)) return false
  try {
    const url = new URL(text)
    return url.protocol === "http:" || url.protocol === "https:"
  } catch {
    return false
  }
}

function scoreColor(score: number): "green" | "purple" | "orange" {
  if (score >= 80) return "green"
  return score >= 65 ? "purple" : "orange"
}

function JobMatchSkeleton() {
  return (
    <>
      <ModuleHeader
        title="Encuentra tu mejor match"
        copy="Compara tu perfil con cada vacante y enfoca tu energía donde importa."
      />
      <section className="job-input-card jobmatch-loading-form" aria-busy="true">
        <Skeleton width="40%" height={20} />
        <Skeleton width="80%" height={12} variant="text" />
        <div className="jobmatch-loading-fields">
          <Skeleton width="100%" height={42} />
          <Skeleton width="100%" height={42} />
        </div>
        <Skeleton width="100%" height={150} />
        <Skeleton width={150} height={42} />
      </section>
      <div className="job-results-layout" aria-busy="true" aria-label="Cargando análisis">
        <section className="results-list jobmatch-loading-list">
          <Skeleton width="45%" height={18} />
          <Skeleton width="100%" height={84} />
          <Skeleton width="100%" height={84} />
          <Skeleton width="100%" height={84} />
        </section>
        <aside className="match-detail jobmatch-loading-detail">
          <Skeleton width="72%" height={26} />
          <Skeleton width="100%" height={96} />
          <Skeleton width="100%" height={96} />
          <Skeleton width="100%" height={130} />
        </aside>
      </div>
    </>
  )
}

export function JobMatchModule() {
  const [jobTitle, setJobTitle] = useState("")
  const [company, setCompany] = useState("")
  const [rawDescription, setRawDescription] = useState("")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [offerUrl, setOfferUrl] = useState("")
  const [importNotice, setImportNotice] = useState<string | null>(null)
  // Qué inició la última lectura de oferta: el enlace o un texto pegado (para mostrar
  // el progreso y los mensajes junto al campo correcto).
  const [extractMode, setExtractMode] = useState<"url" | "text" | null>(null)
  const [undoState, setUndoState] = useState<{ jobTitle: string; company: string; rawDescription: string } | null>(null)
  const titleRef = useRef<HTMLInputElement>(null)
  const analysisController = useRef<AbortController | null>(null)
  const resultsQuery = useJobMatches()
  const analyze = useAnalyzeJobMatch()
  const extract = useExtractJobOffer()
  // "Mayor match": la lista se muestra ordenada por puntaje.
  const results = [...(resultsQuery.data ?? [])].sort((a, b) => b.matchScore - a.matchScore)
  const analysisError = analyze.error instanceof ApiError ? analyze.error : undefined
  const titleErrors = getFieldErrors(analysisError?.fieldErrors, "JobTitle", "nombre")
  const companyErrors = getFieldErrors(analysisError?.fieldErrors, "Company", "empresa")
  const descriptionErrors = getFieldErrors(analysisError?.fieldErrors, "RawDescription", "ofertaTexto")
  const descriptionIsUrl = isHttpUrl(rawDescription)
  const busy = analyze.isPending || extract.isPending
  const selectedIdForQuery = selectedId ?? results[0]?.id ?? null
  const selectedQuery = useJobMatch(selectedIdForQuery)
  const selectedSummary = results.find((result) => result.id === selectedIdForQuery)
  const selected = selectedQuery.data ?? selectedSummary

  useEffect(() => () => analysisController.current?.abort(), [])

  const fillFromOffer = (offer: { jobTitle: string; company: string | null; rawDescription: string }) => {
    setJobTitle(offer.jobTitle)
    setCompany(offer.company ?? "")
    setRawDescription(offer.rawDescription)
  }

  const importOffer = (url: string) => {
    if (!isHttpUrl(url) || busy) return
    setImportNotice(null)
    setUndoState(null)
    setExtractMode("url")
    analyze.reset()
    extract.mutate(
      { url },
      {
        onSuccess: (offer) => {
          fillFromOffer(offer)
          setOfferUrl(offer.url)
          const host = new URL(offer.url).hostname.replace(/^www\./, "")
          setImportNotice(
            `Oferta importada desde ${host}${offer.source === "ia" ? " con ayuda de Astro" : ""}. ` +
              "Revisa los datos y corrige lo que haga falta antes de analizar.",
          )
        },
      },
    )
  }

  /** Ordena con Astro una oferta pegada desde cualquier página (menús, avisos y
   *  otras ofertas incluidos): rellena título, empresa y deja solo la oferta. */
  const tidyPastedText = (text: string) => {
    if (busy || text.trim().length < MIN_DESCRIPTION_LENGTH || isHttpUrl(text)) return
    const snapshot = { jobTitle, company, rawDescription: text }
    setImportNotice(null)
    setExtractMode("text")
    analyze.reset()
    extract.mutate(
      { text },
      {
        onSuccess: (offer) => {
          fillFromOffer({
            // Si el usuario ya escribió un título o empresa, se respetan.
            jobTitle: snapshot.jobTitle.trim() || offer.jobTitle,
            company: snapshot.company.trim() || offer.company,
            rawDescription: offer.rawDescription,
          })
          setUndoState(snapshot)
          setImportNotice("Astro ordenó la oferta que pegaste. Revisa los datos antes de analizar.")
        },
      },
    )
  }

  const undoTidy = () => {
    if (!undoState) return
    fillFromOffer(undoState)
    setUndoState(null)
    setImportNotice(null)
  }

  const submitAnalysis = (request: AnalyzeJobRequest) => {
    if (
      analysisController.current ||
      busy ||
      !request.jobTitle.trim() ||
      request.rawDescription.trim().length < MIN_DESCRIPTION_LENGTH
    ) {
      return
    }

    const controller = new AbortController()
    analysisController.current = controller
    analyze.mutate(
      { request, signal: controller.signal },
      {
        onSuccess: (result) => setSelectedId(result.id),
        onSettled: () => {
          if (analysisController.current === controller) analysisController.current = null
        },
      },
    )
  }

  if (resultsQuery.isLoading) return <JobMatchSkeleton />

  if (resultsQuery.isError) {
    return (
      <>
        <ModuleHeader
          title="Encuentra tu mejor match"
          copy="Compara tu perfil con cada vacante y enfoca tu energía donde importa."
        />
        <ErrorState
          message={resultsQuery.error.message}
          onRetry={() => void resultsQuery.refetch()}
          error={resultsQuery.error}
        />
      </>
    )
  }

  const selectedColor = selected ? scoreColor(selected.matchScore) : "purple"

  return (
    <>
      <ModuleHeader
        title="Encuentra tu mejor match"
        copy="Compara tu perfil con cada vacante y enfoca tu energía donde importa."
      />
      <form
        className="job-input-card"
        onSubmit={(event) => {
          event.preventDefault()
          submitAnalysis({ jobTitle, company, rawDescription })
        }}
      >
        <div className="input-title">
          <div className="feature-icon">
            <Icon name="clipboard" />
          </div>
          <div>
            <h3>Analiza una oferta laboral</h3>
            <p>
              Pega el enlace de la oferta o copia su texto desde cualquier sitio. Astro comparará
              sus requisitos con tu perfil.
            </p>
          </div>
        </div>
        <div className="jobmatch-import">
          <label className="jobmatch-field">
            <span>Importar desde un enlace (opcional)</span>
            <div className="jobmatch-import-row">
              <input
                type="url"
                inputMode="url"
                value={offerUrl}
                onChange={(event) => setOfferUrl(event.target.value)}
                onKeyDown={(event) => {
                  // Enter importa en vez de enviar el formulario de análisis.
                  if (event.key === "Enter") {
                    event.preventDefault()
                    importOffer(offerUrl)
                  }
                }}
                placeholder="https://www.linkedin.com/jobs/view/..."
                aria-label="Enlace de la oferta"
                disabled={busy}
              />
              <Button
                variant="secondary"
                icon="download"
                onClick={() => importOffer(offerUrl)}
                disabled={!isHttpUrl(offerUrl) || busy}
              >
                {extract.isPending ? "Leyendo oferta..." : "Importar"}
              </Button>
            </div>
            <span className="jobmatch-field-hint">
              Funciona con LinkedIn, Computrabajo, GetOnBoard y muchos sitios de empresas. ¿Otro sitio
              (Laborum, Indeed…)? Abre la oferta, selecciona todo (Ctrl+A), copia (Ctrl+C) y pégala
              en la descripción: Astro la ordena sola.
            </span>
          </label>
          {extractMode === "url" && <ExtractFeedback extract={extract} notice={importNotice} />}
        </div>
        <div className="jobmatch-fields">
          <label className="jobmatch-field">
            <span>Título del puesto</span>
            <input
              ref={titleRef}
              value={jobTitle}
              onChange={(event) => setJobTitle(event.target.value)}
              placeholder="Ej. Diseñador/a UX"
              maxLength={fieldLimits.jobTitle}
              aria-label="Título del puesto"
              aria-invalid={titleErrors.length > 0}
              aria-describedby={titleErrors.length > 0 ? "job-title-errors" : undefined}
            />
            <span className="jobmatch-char-count">{jobTitle.length} / {fieldLimits.jobTitle}</span>
            {titleErrors.map((message, index) => (
              <span
                className="jobmatch-field-error"
                id={index === 0 ? "job-title-errors" : undefined}
                key={`${index}-${message}`}
              >
                {message}
              </span>
            ))}
          </label>
          <label className="jobmatch-field">
            <span>Empresa (opcional)</span>
            <input
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              placeholder="Nombre de la empresa"
              maxLength={fieldLimits.company}
              aria-label="Empresa"
              aria-invalid={companyErrors.length > 0}
              aria-describedby={companyErrors.length > 0 ? "job-company-errors" : undefined}
            />
            <span className="jobmatch-char-count">{company.length} / {fieldLimits.company}</span>
            {companyErrors.map((message, index) => (
              <span
                className="jobmatch-field-error"
                id={index === 0 ? "job-company-errors" : undefined}
                key={`${index}-${message}`}
              >
                {message}
              </span>
            ))}
          </label>
        </div>
        <label className="jobmatch-field jobmatch-description">
          <span>Descripción de la oferta</span>
          <textarea
            value={rawDescription}
            onChange={(event) => setRawDescription(event.target.value)}
            onPaste={(event) => {
              const pasted = event.clipboardData.getData("text/plain") || event.clipboardData.getData("text")
              if (pasted.trim().length < AUTO_TIDY_MIN_PASTE || isHttpUrl(pasted)) return
              // El texto se pega normalmente y además Astro lo ordena en segundo plano.
              const field = event.currentTarget
              const result =
                field.value.slice(0, field.selectionStart) + pasted + field.value.slice(field.selectionEnd)
              tidyPastedText(result)
            }}
            disabled={extract.isPending && extractMode === "text"}
            placeholder="Pega aquí la oferta copiada desde cualquier página (puedes copiar la página completa con Ctrl+A y Ctrl+C). Astro la ordena sola y completa el título y la empresa."
            rows={5}
            maxLength={fieldLimits.rawDescription}
            aria-label="Descripción de la oferta"
            aria-invalid={descriptionErrors.length > 0}
            aria-describedby={descriptionErrors.length > 0 ? "job-description-errors" : undefined}
          />
          <span
            className="jobmatch-char-count"
            aria-label={
              rawDescription.trim().length <= MIN_DESCRIPTION_LENGTH
                ? `${rawDescription.trim().length} de ${MIN_DESCRIPTION_LENGTH} caracteres mínimos`
                : `${rawDescription.trim().length} de ${fieldLimits.rawDescription} caracteres máximos`
            }
          >
            {rawDescription.trim().length <= MIN_DESCRIPTION_LENGTH
              ? `${rawDescription.trim().length}/${MIN_DESCRIPTION_LENGTH}`
              : `${rawDescription.trim().length} / ${fieldLimits.rawDescription}`}
          </span>
          {descriptionIsUrl ? (
            <span className="jobmatch-field-hint jobmatch-url-hint">
              Pegaste un enlace.{" "}
              <button
                type="button"
                className="jobmatch-link-button"
                onClick={() => {
                  const url = rawDescription.trim()
                  setOfferUrl(url)
                  setRawDescription("")
                  importOffer(url)
                }}
                disabled={busy}
              >
                Importar la oferta desde este enlace
              </button>
            </span>
          ) : rawDescription.trim().length < MIN_DESCRIPTION_LENGTH ? (
            <span className="jobmatch-field-hint">
              Se necesitan al menos {MIN_DESCRIPTION_LENGTH} caracteres para analizar.
            </span>
          ) : rawDescription.length >= fieldLimits.rawDescription ? (
            <span className="jobmatch-field-hint">
              Llegaste al máximo de {fieldLimits.rawDescription.toLocaleString("es-CL")} caracteres:
              deja solo la descripción y los requisitos.
            </span>
          ) : !undoState && !importNotice && !extract.isPending ? (
            <span className="jobmatch-field-hint">
              ¿Pegaste la página completa o con texto de más?{" "}
              <button
                type="button"
                className="jobmatch-link-button"
                onClick={() => tidyPastedText(rawDescription)}
                disabled={busy}
              >
                Ordenar con Astro
              </button>
            </span>
          ) : null}
          {extractMode === "text" && (
            <ExtractFeedback
              extract={extract}
              notice={importNotice}
              pendingLabel="Astro está ordenando la oferta que pegaste..."
              onUndo={undoState ? undoTidy : undefined}
            />
          )}
          {descriptionErrors.map((message, index) => (
            <span
              className="jobmatch-field-error"
              id={index === 0 ? "job-description-errors" : undefined}
              key={`${index}-${message}`}
            >
              {message}
            </span>
          ))}
        </label>
        <div className="input-footer">
          <span>
            <Icon name="spark" size={16} /> Análisis con IA basado en tu CV
          </span>
          <Button
            type="submit"
            icon="arrow"
            disabled={
              !jobTitle.trim() ||
              rawDescription.trim().length < MIN_DESCRIPTION_LENGTH ||
              descriptionIsUrl ||
              busy
            }
          >
            {analyze.isPending ? "Analizando..." : "Analizar JobMatch"}
          </Button>
        </div>
        {analyze.isPending && (
          <div className="jobmatch-progress" role="status" aria-live="polite">
            <span>Astro está analizando la oferta...</span>
            <span className="jobmatch-progress-track"><i /></span>
          </div>
        )}
      </form>
      {analyze.isError && (
        <ErrorState
          title="No se pudo analizar la oferta"
          message={analyze.error.message}
          traceId={
            analysisError && analysisError.status >= 500
              ? analysisError.traceId
              : undefined
          }
          error={analyze.error}
          onRetry={() => {
            const request = analyze.variables?.request
            if (request) submitAnalysis(request)
          }}
        />
      )}
      {results.length === 0 ? (
        analyze.isPending ? null : (
          <EmptyState
            title="Aún no tienes análisis"
            description="Completa los datos de una vacante para descubrir cómo encaja con tu perfil."
            actionLabel="Agregar una oferta"
            onAction={() => titleRef.current?.focus()}
          />
        )
      ) : (
        <div className="job-results-layout">
          <section className="results-list">
            <div className="list-heading">
              <div>
                <h2>Tus rankings</h2>
                <span>{results.length} ofertas analizadas</span>
              </div>
              <span className="filter-button">Mayor match <Icon name="chevron" size={15} /></span>
            </div>
            {results.map((result) => {
              const color = scoreColor(result.matchScore)
              return (
                <button
                  key={result.id}
                  className={`job-row ${selectedIdForQuery === result.id ? "selected" : ""}`}
                  onClick={() => setSelectedId(result.id)}
                  type="button"
                >
                  <div className={`company-logo logo-${color}`}>
                    {(result.company ?? "?").slice(0, 1)}
                  </div>
                  <div className="job-info">
                    <h3>{result.jobTitle}</h3>
                    <p>{result.company ?? "Empresa no especificada"}</p>
                    <div className="mini-progress">
                      <span style={{ width: `${result.matchScore}%` }} />
                    </div>
                  </div>
                  <div className={`match-badge match-${color}`}>
                    <b>{result.matchScore}%</b>
                    <span>Match</span>
                  </div>
                  <Icon name="chevron" size={17} />
                </button>
              )
            })}
          </section>
          {selectedIdForQuery && (
            <aside className="match-detail">
              {selectedQuery.isError ? (
                <ErrorState
                  message={selectedQuery.error.message}
                  onRetry={() => void selectedQuery.refetch()}
                  error={selectedQuery.error}
                />
              ) : selectedQuery.isLoading ? (
                <div className="jobmatch-loading-detail" aria-busy="true" aria-label="Cargando detalle">
                  <Skeleton width="72%" height={26} />
                  <Skeleton width="100%" height={96} />
                  <Skeleton width="100%" height={96} />
                  <Skeleton width="100%" height={130} />
                </div>
              ) : selected ? (
                <>
                  <div className="detail-heading">
                    <div>
                      <h2>{selected.jobTitle}</h2>
                      <p>{selected.company ?? "Empresa no especificada"}</p>
                    </div>
                    <div className={`score-circle score-${selectedColor}`}>
                      <b>{selected.matchScore}%</b>
                      <span>Match</span>
                    </div>
                  </div>
                  <div className="keyword-section">
                    <h3>
                      <span className="dot green" /> Coincidencias{" "}
                      <small>{selected.matchedKeywords.length}</small>
                    </h3>
                    <div className="tags">
                      {selected.matchedKeywords.length === 0 && (
                        <span className="jobmatch-field-hint">Sin coincidencias detectadas con tu perfil.</span>
                      )}
                      {selected.matchedKeywords.map((keyword) => (
                        <span className="tag tag-green" key={keyword}>
                          <Icon name="check" size={13} />
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="keyword-section">
                    <h3>
                      <span className="dot red" /> Oportunidades de mejora{" "}
                      <small>{selected.missingKeywords.length}</small>
                    </h3>
                    <div className="tags">
                      {selected.missingKeywords.length === 0 && (
                        <span className="jobmatch-field-hint">Cumples todos los requisitos detectados.</span>
                      )}
                      {selected.missingKeywords.map((keyword) => (
                        <span className="tag tag-red" key={keyword}>{keyword}</span>
                      ))}
                    </div>
                  </div>
                  <div className="astro-recommendation">
                    <div className="recommendation-title">
                      <span><Icon name="spark" /></span>
                      <div><b>Recomendación de Astro</b></div>
                    </div>
                    <p>{selected.astroAdvice}</p>
                  </div>
                </>
              ) : null}
            </aside>
          )}
        </div>
      )}
    </>
  )
}
