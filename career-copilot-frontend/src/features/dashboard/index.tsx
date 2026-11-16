import { lazy, Suspense, useState } from "react"
import type { ApplicationStatus, JobAnalysisResponse } from "@/features/jobmatch/types"
import { useJobMatches } from "@/features/jobmatch/hooks"
import { useProfile } from "@/features/profile"
import { moduleMeta } from "@/features/dashboard/config"
import { EmptyState, ErrorState, Skeleton } from "@/shared/components"
import { ModuleHeader } from "@/shared/ModuleHeader"
import { ModuleSkeleton } from "@/shared/Skeleton"
import { Astro, Brand, Button, Icon } from "@/shared/ui"
import type { Module } from "@/shared/types"
import type { Profile } from "@/shared/types/api"

const CvModule = lazy(() => import("@/features/cv").then((module) => ({ default: module.CvModule })))
const JobMatchModule = lazy(() => import("@/features/jobmatch").then((module) => ({ default: module.JobMatchModule })))
const LettersModule = lazy(() => import("@/features/letters").then((module) => ({ default: module.LettersModule })))
const CoachModule = lazy(() => import("@/features/coach").then((module) => ({ default: module.CoachModule })))
const TrackerModule = lazy(() => import("@/features/tracker").then((module) => ({ default: module.TrackerModule })))

const statusLabels: Record<ApplicationStatus, string> = {
  Saved: "Guardadas",
  Applied: "Enviadas",
  Interview: "Entrevistas",
  Offer: "Ofertas",
  Rejected: "No seleccionadas",
}

function initials(name?: string): string {
  const words = name?.trim().split(/\s+/).filter(Boolean) ?? []
  return words.slice(0, 2).map((word) => word[0].toLocaleUpperCase("es-CL")).join("")
}

function DashboardOverview({
  profile,
  setActive,
}: {
  profile: Profile
  setActive: (module: Module) => void
}) {
  const analysesQuery = useJobMatches()
  const analyses = analysesQuery.data ?? []
  const averageMatch = analyses.length
    ? Math.round(analyses.reduce((total, analysis) => total + analysis.matchScore, 0) / analyses.length)
    : null
  const statusCounts = (Object.keys(statusLabels) as ApplicationStatus[]).map((status) => ({
    status,
    count: analyses.filter((analysis) => analysis.status === status).length,
  }))

  return (
    <>
      <ModuleHeader
        title={`Hola, ${profile.full_name}`}
        copy="Aquí tienes un resumen actualizado de tu búsqueda profesional."
      >
        <Button icon="arrow" onClick={() => setActive("tracker")}>Ver Tracker</Button>
      </ModuleHeader>
      {analysesQuery.isLoading ? (
        <DashboardOverviewSkeleton />
      ) : analysesQuery.isError ? (
        <ErrorState
          message={analysesQuery.error.message}
          onRetry={() => void analysesQuery.refetch()}
          error={analysesQuery.error}
        />
      ) : (
        <>
          <div className="dashboard-metrics-grid">
            <article className="stat-card">
              <div className="feature-icon"><Icon name="document" /></div>
              <div><b>{profile.experiences.length}</b><span>Experiencias en tu perfil</span></div>
            </article>
            <article className="stat-card">
              <div className="feature-icon"><Icon name="spark" /></div>
              <div><b>{profile.skills.length}</b><span>Habilidades registradas</span></div>
            </article>
            <article className="stat-card">
              <div className="feature-icon"><Icon name="target" /></div>
              <div><b>{averageMatch == null ? "—" : `${averageMatch}%`}</b><span>Match promedio</span></div>
            </article>
            <article className="stat-card">
              <div className="feature-icon"><Icon name="clipboard" /></div>
              <div><b>{analyses.length}</b><span>Ofertas analizadas</span></div>
            </article>
          </div>
          <section className="dashboard-status-panel">
            <div className="list-heading">
              <div>
                <h2>Postulaciones por estado</h2>
                <span>Estados recibidos desde tus análisis</span>
              </div>
            </div>
            <div className="dashboard-status-grid">
              {statusCounts.map(({ status, count }) => (
                <div className={`dashboard-status-item status-${status}`} key={status}>
                  <b>{count}</b>
                  <span>{statusLabels[status]}</span>
                </div>
              ))}
            </div>
          </section>
          <section className="dashboard-recent-panel">
            <div className="list-heading">
              <div>
                <h2>Últimas ofertas analizadas</h2>
                <span>{analyses.length} en total</span>
              </div>
              {analyses.length > 0 && (
                <Button variant="secondary" onClick={() => setActive("jobmatch")}>Ver JobMatch</Button>
              )}
            </div>
            {analyses.length === 0 ? (
              <EmptyState
                title="Aún no tienes análisis"
                description="Analiza una oferta para ver aquí tus oportunidades recientes y métricas de compatibilidad."
                actionLabel="Analizar una oferta"
                onAction={() => setActive("jobmatch")}
              />
            ) : (
              <div className="dashboard-recent-list">
                {analyses.slice(0, 5).map((analysis: JobAnalysisResponse) => (
                  <button
                    className="dashboard-analysis-row"
                    key={analysis.id}
                    type="button"
                    onClick={() => setActive("jobmatch")}
                  >
                    <span className="company-logo logo-purple">{(analysis.company ?? "?").slice(0, 1)}</span>
                    <span className="dashboard-analysis-info">
                      <b>{analysis.jobTitle}</b>
                      <small>{analysis.company ?? "Empresa no especificada"}</small>
                    </span>
                    <span className="dashboard-analysis-score">{analysis.matchScore}%</span>
                    <Icon name="chevron" size={16} />
                  </button>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </>
  )
}

function DashboardOverviewSkeleton() {
  return (
    <div className="dashboard-overview-skeleton" aria-busy="true" aria-label="Cargando métricas">
      <div className="dashboard-metrics-grid">
        {[1, 2, 3, 4].map((item) => (
          <div className="stat-card" key={item}>
            <Skeleton width={45} height={45} />
            <div><Skeleton width={45} height={22} /><Skeleton width={105} height={10} /></div>
          </div>
        ))}
      </div>
      <section className="dashboard-status-panel">
        <div className="list-heading"><Skeleton width="35%" height={20} /></div>
        <div className="dashboard-status-grid">
          {[1, 2, 3, 4, 5].map((item) => <Skeleton height={66} key={item} />)}
        </div>
      </section>
      <section className="dashboard-recent-panel">
        <div className="list-heading"><Skeleton width="38%" height={20} /></div>
        {[1, 2, 3].map((item) => <Skeleton className="dashboard-recent-skeleton" height={66} key={item} />)}
      </section>
    </div>
  )
}

export function Sidebar({
  active,
  setActive,
  open,
  close,
}: {
  active: Module
  setActive: (m: Module) => void
  open: boolean
  close: () => void
}) {
  const profile = useProfile()
  return (
    <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
      <div className="sidebar-brand">
        <Brand light />
        <button className="mobile-close" onClick={close}>
          <Icon name="x" />
        </button>
      </div>
      <nav>
        {(Object.keys(moduleMeta) as Module[]).map((key) => (
          <button
            key={key}
            className={active === key ? "active" : ""}
            onClick={() => {
              setActive(key)
              close()
            }}
          >
            <Icon name={moduleMeta[key].icon} />
            <span>{moduleMeta[key].label}</span>
            {key === "coach" && (
              <span className="sidebar-ai-badge" title="Inteligencia artificial">
                <Icon name="spark" size={14} />
                <span className="sr-only">IA</span>
              </span>
            )}
          </button>
        ))}
      </nav>
      <span className="sidebar-stars" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
      </span>
      <div className="sidebar-astro">
        <Astro size="small" pose="peek" />
        <div>
          <b>Astro está online</b>
          <span>Listo para ayudarte</span>
        </div>
      </div>
      <div className="sidebar-profile">
        <div className="user-avatar">{initials(profile.data?.full_name)}</div>
        <div>
          <b>{profile.data?.full_name ?? "Tu perfil"}</b>
          <span>Perfil profesional</span>
        </div>
        <Icon name="chevron" size={16} />
      </div>
    </aside>
  )
}

export function Dashboard({ onHome }: { onHome: () => void }) {
  const [active, setActive] = useState<Module>("overview")
  const [menuOpen, setMenuOpen] = useState(false)
  const profile = useProfile()

  if (profile.isLoading) return <ModuleSkeleton />

  if (profile.isError || !profile.data) {
    return (
      <main className="dashboard-state">
        <ErrorState
          message={profile.error?.message ?? "No se pudo cargar tu perfil."}
          onRetry={() => void profile.refetch()}
          error={profile.error}
        />
      </main>
    )
  }

  const profileIncomplete = !profile.data.full_name.trim()

  return (
    <div className="dashboard">
      <Sidebar
        active={active}
        setActive={setActive}
        open={menuOpen}
        close={() => setMenuOpen(false)}
      />
      <div className="dashboard-shell">
        <header className="dashboard-header">
          <button className="menu-button" onClick={() => setMenuOpen(true)}>
            <Icon name="menu" />
          </button>
          <div className="dashboard-header-title">
            <span className="breadcrumb">
              Career Copilot <span aria-hidden="true">/</span> {moduleMeta[active].label}
            </span>
          </div>
          <div className="header-actions">
            <button className="icon-button">
              <Icon name="search" />
            </button>
            <button className="notification-button" aria-label="Notificaciones">
              <Icon name="bell" />
              <span />
            </button>
            <button className="home-link" onClick={onHome}>
              Salir
            </button>
          </div>
        </header>
        <main className="dashboard-main">
          {profileIncomplete && active !== "cv" ? (
            <EmptyState
              title="Completa tu perfil para continuar"
              description="Agrega tu CV para que Astro pueda personalizar tus oportunidades y prácticas."
              actionLabel="Completar con mi CV"
              onAction={() => setActive("cv")}
            />
          ) : (
            <Suspense fallback={<ModuleSkeleton />}>
              {active === "overview" && <DashboardOverview profile={profile.data} setActive={setActive} />}
              {active === "cv" && <CvModule />}
              {active === "jobmatch" && <JobMatchModule />}
              {active === "letters" && <LettersModule setActive={setActive} />}
              {active === "coach" && <CoachModule setActive={setActive} />}
              {active === "tracker" && <TrackerModule setActive={setActive} />}
            </Suspense>
          )}
        </main>
      </div>
    </div>
  )
}
