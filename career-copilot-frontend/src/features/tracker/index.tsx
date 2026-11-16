import { useEffect, useRef, useState } from "react"
import { useJobMatches, useUpdateApplicationStatus } from "@/features/jobmatch/hooks"
import type { ApplicationStatus, JobAnalysisResponse } from "@/features/jobmatch/types"
import { EmptyState, ErrorState, Skeleton } from "@/shared/components"
import { ModuleHeader } from "@/shared/ModuleHeader"
import { Button, Icon } from "@/shared/ui"
import type { Module } from "@/shared/types"

const statuses: ApplicationStatus[] = ["Saved", "Applied", "Interview", "Offer", "Rejected"]
const statusLabels: Record<ApplicationStatus, string> = {
  Saved: "Guardada",
  Applied: "Enviada",
  Interview: "Entrevista",
  Offer: "Oferta",
  Rejected: "No seleccionada",
}

function isApplicationStatus(value: string): value is ApplicationStatus {
  return statuses.includes(value as ApplicationStatus)
}

function TrackerSkeleton() {
  return (
    <>
      <ModuleHeader
        title="Tu búsqueda, bajo control"
        copy="Sigue el progreso de cada oportunidad y celebra cada avance."
      />
      <div className="stats-grid" aria-busy="true">
        {[1, 2, 3].map((item) => (
          <div className="stat-card tracker-stat-skeleton" key={item}>
            <Skeleton width={45} height={45} />
            <div><Skeleton width={50} height={22} /><Skeleton width={92} height={10} /></div>
          </div>
        ))}
      </div>
      <section className="tracker-table" aria-busy="true" aria-label="Cargando postulaciones">
        <div className="list-heading"><Skeleton width="35%" height={20} /><Skeleton width="28%" height={30} /></div>
        {[1, 2, 3, 4].map((item) => (
          <div className="tracker-row tracker-row-skeleton" key={item}>
            <Skeleton width={38} height={38} />
            <Skeleton width="75%" height={34} />
            <Skeleton width={55} height={24} />
            <Skeleton width={100} height={34} />
            <Skeleton width={28} height={28} />
          </div>
        ))}
      </section>
    </>
  )
}

export function TrackerModule({ setActive }: { setActive: (module: Module) => void }) {
  const [filter, setFilter] = useState<ApplicationStatus | "all">("all")
  const [lastUpdate, setLastUpdate] = useState<{ id: string; status: ApplicationStatus } | null>(null)
  const updateController = useRef<AbortController | null>(null)
  const applicationsQuery = useJobMatches()
  const updateStatus = useUpdateApplicationStatus()

  useEffect(() => () => updateController.current?.abort(), [])

  if (applicationsQuery.isLoading) return <TrackerSkeleton />

  if (applicationsQuery.isError) {
    return (
      <>
        <ModuleHeader
          title="Tu búsqueda, bajo control"
          copy="Sigue el progreso de cada oportunidad y celebra cada avance."
        />
        <ErrorState
          message={applicationsQuery.error.message}
          onRetry={() => void applicationsQuery.refetch()}
          error={applicationsQuery.error}
        />
      </>
    )
  }

  const applications: JobAnalysisResponse[] = applicationsQuery.data ?? []
  const filteredApplications = applications.filter((item) => filter === "all" || item.status === filter)
  const activeCount = applications.filter((item) => item.status === "Applied" || item.status === "Interview").length
  const averageMatch = applications.length
    ? Math.round(applications.reduce((total, item) => total + item.matchScore, 0) / applications.length)
    : 0

  const changeStatus = (id: string, status: ApplicationStatus) => {
    if (updateController.current || updateStatus.isPending) return

    const controller = new AbortController()
    updateController.current = controller
    setLastUpdate({ id, status })
    updateStatus.mutate(
      { applicationId: id, request: { status }, signal: controller.signal },
      {
        onSettled: () => {
          if (updateController.current === controller) updateController.current = null
        },
      },
    )
  }

  return (
    <>
      <ModuleHeader
        title="Tu búsqueda, bajo control"
        copy="Sigue el progreso de cada oportunidad y celebra cada avance."
      >
        <Button icon="arrow" onClick={() => setActive("jobmatch")}>
          Buscar ofertas
        </Button>
      </ModuleHeader>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="feature-icon"><Icon name="clipboard" /></div>
          <div><b>{applications.length}</b><span>Postulaciones guardadas</span></div>
        </div>
        <div className="stat-card">
          <div className="feature-icon"><Icon name="spark" /></div>
          <div><b>{activeCount}</b><span>En proceso</span></div>
        </div>
        <div className="stat-card">
          <div className="feature-icon"><Icon name="target" /></div>
          <div><b>{averageMatch}%</b><span>Match promedio</span></div>
        </div>
      </div>
      {updateStatus.isError && (
        <ErrorState
          title="No se pudo actualizar el estado"
          message={updateStatus.error.message}
          error={updateStatus.error}
          onRetry={() => {
            if (lastUpdate) changeStatus(lastUpdate.id, lastUpdate.status)
          }}
        />
      )}
      {applications.length === 0 ? (
        <EmptyState
          title="Aún no tienes postulaciones guardadas"
          description="Analiza una oferta y guarda las oportunidades que quieras seguir."
          actionLabel="Analizar ofertas"
          onAction={() => setActive("jobmatch")}
        />
      ) : (
        <section className="tracker-table" aria-busy={updateStatus.isPending}>
          <div className="list-heading">
            <div>
              <h2>Mis postulaciones</h2>
              <span>{filteredApplications.length} de {applications.length} oportunidades</span>
            </div>
            <div className="tracker-filters" aria-label="Filtrar postulaciones">
              <button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>Todas</button>
              {statuses.map((status) => (
                <button
                  className={filter === status ? "active" : ""}
                  key={status}
                  onClick={() => setFilter(status)}
                >
                  {statusLabels[status]}
                </button>
              ))}
            </div>
          </div>
          {filteredApplications.length === 0 ? (
            <EmptyState
              title="No hay postulaciones en este estado"
              description="Elige otro filtro o actualiza el estado de una oportunidad."
              actionLabel="Ver todas"
              onAction={() => setFilter("all")}
            />
          ) : (
            filteredApplications.map((application) => {
              const status = application.status
              const color = application.matchScore >= 80 ? "green" : application.matchScore >= 65 ? "purple" : "orange"
              return (
                <div className="tracker-row" key={application.id}>
                  <div className={`company-logo logo-${color}`}>{(application.company ?? "?").slice(0, 1)}</div>
                  <div>
                    <b>{application.jobTitle}</b>
                    <span>{application.company ?? "Empresa no especificada"}</span>
                  </div>
                  <span className={`match-pill match-${color}`}>{application.matchScore}% match</span>
                  <label className={`tracker-status status-${status}`}>
                    <span className="sr-only">Estado de {application.jobTitle}</span>
                    <select
                      value={status}
                      disabled={updateStatus.isPending}
                      aria-label={`Estado de ${application.jobTitle}`}
                      onChange={(event) => {
                        const nextStatus = event.currentTarget.value
                        if (isApplicationStatus(nextStatus)) changeStatus(application.id, nextStatus)
                      }}
                    >
                      {statuses.map((option) => (
                        <option value={option} key={option}>{statusLabels[option]}</option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="icon-button"
                    aria-label={`Ver análisis de ${application.jobTitle}`}
                    onClick={() => setActive("jobmatch")}
                  >
                    <Icon name="chevron" size={16} />
                  </button>
                </div>
              )
            })
          )}
        </section>
      )}
    </>
  )
}
