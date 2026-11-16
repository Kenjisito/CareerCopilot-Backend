import { useEffect, useRef, useState } from "react"
import { useAnalyzeJobMatch, useJobMatch, useJobMatches } from "@/features/jobmatch/hooks"
import type { AnalyzeJobRequest } from "@/features/jobmatch/types"
import { Button, Icon } from "@/shared/ui"
import { ModuleHeader } from "@/shared/ModuleHeader"
import { EmptyState, ErrorState, Skeleton } from "@/shared/components"
import { ApiError } from "@/shared/lib/apiError"

function getFieldErrors(
  errors: Record<string, string[]> | undefined,
  field: string,
): string[] {
  const matchingEntry = Object.entries(errors ?? {}).find(
    ([name]) => name.toLowerCase() === field.toLowerCase(),
  )
  return matchingEntry?.[1] ?? []
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
  const titleRef = useRef<HTMLInputElement>(null)
  const analysisController = useRef<AbortController | null>(null)
  const resultsQuery = useJobMatches()
  const analyze = useAnalyzeJobMatch()
  const results = resultsQuery.data ?? []
  const analysisError = analyze.error instanceof ApiError ? analyze.error : undefined
  const titleErrors = getFieldErrors(analysisError?.fieldErrors, "JobTitle")
  const companyErrors = getFieldErrors(analysisError?.fieldErrors, "Company")
  const descriptionErrors = getFieldErrors(analysisError?.fieldErrors, "RawDescription")
  const selectedIdForQuery = selectedId ?? results[0]?.id ?? null
  const selectedQuery = useJobMatch(selectedIdForQuery)
  const selectedSummary = results.find((result) => result.id === selectedIdForQuery)
  const selected = selectedQuery.data ?? selectedSummary

  useEffect(() => () => analysisController.current?.abort(), [])

  const submitAnalysis = (request: AnalyzeJobRequest) => {
    if (
      analysisController.current ||
      analyze.isPending ||
      !request.jobTitle.trim() ||
      request.rawDescription.trim().length < 100
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
            <p>Completa los datos de la vacante y Astro comparará sus requisitos con tu perfil.</p>
          </div>
        </div>
        <div className="jobmatch-fields">
          <label className="jobmatch-field">
            <span>Título del puesto</span>
            <input
              ref={titleRef}
              value={jobTitle}
              onChange={(event) => setJobTitle(event.target.value)}
              placeholder="Ej. Diseñador/a UX"
              maxLength={300}
              aria-label="Título del puesto"
              aria-invalid={titleErrors.length > 0}
              aria-describedby={titleErrors.length > 0 ? "job-title-errors" : undefined}
            />
            <span className="jobmatch-char-count">{jobTitle.length} / 300</span>
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
              maxLength={200}
              aria-label="Empresa"
              aria-invalid={companyErrors.length > 0}
              aria-describedby={companyErrors.length > 0 ? "job-company-errors" : undefined}
            />
            <span className="jobmatch-char-count">{company.length} / 200</span>
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
            placeholder="Pega aquí responsabilidades, requisitos y habilidades..."
            rows={5}
            maxLength={10_000}
            aria-label="Descripción de la oferta"
            aria-invalid={descriptionErrors.length > 0}
            aria-describedby={descriptionErrors.length > 0 ? "job-description-errors" : undefined}
          />
          <span
            className="jobmatch-char-count"
            aria-label={`${rawDescription.trim().length} de 100 caracteres mínimos`}
          >
            {rawDescription.trim().length}/100
          </span>
          {rawDescription.trim().length < 100 && (
            <span className="jobmatch-field-hint">Se necesitan al menos 100 caracteres para analizar.</span>
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
              rawDescription.trim().length < 100 ||
              analyze.isPending
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
