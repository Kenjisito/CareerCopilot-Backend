import type { CSSProperties } from "react"

type SkeletonProps = {
  width?: CSSProperties["width"]
  height?: CSSProperties["height"]
  variant?: "text" | "circle" | "rect"
  className?: string
}

export function Skeleton({
  width,
  height,
  variant = "rect",
  className = "",
}: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={`skeleton skeleton-${variant} ${className}`.trim()}
      style={{ width, height }}
    />
  )
}

export function AppSkeleton() {
  return (
    <main className="app-skeleton" aria-busy="true" aria-label="Preparando la página">
      <div className="app-skeleton-header">
        <Skeleton width={158} height={36} />
        <Skeleton width={112} height={36} />
      </div>
      <div className="app-skeleton-content">
        <Skeleton width="34%" height={14} variant="text" />
        <Skeleton width="72%" height={38} />
        <Skeleton width="54%" height={18} variant="text" />
        <div className="app-skeleton-grid">
          <Skeleton height={150} />
          <Skeleton height={150} />
        </div>
        <Skeleton width="100%" height={190} />
      </div>
    </main>
  )
}

export function ModuleSkeleton() {
  return (
    <section className="module-skeleton" aria-busy="true" aria-label="Preparando el módulo">
      <div className="module-skeleton-hero">
        <div>
          <Skeleton width="min(340px, 72vw)" height={32} />
          <Skeleton width="min(280px, 65vw)" height={12} variant="text" />
        </div>
        <Skeleton width={150} height={42} />
      </div>
      <div className="module-skeleton-grid">
        <div className="module-skeleton-card">
          <Skeleton width="40%" height={18} />
          <Skeleton width="92%" height={12} variant="text" />
          <Skeleton width="100%" height={48} />
          <Skeleton width="100%" height={48} />
        </div>
        <div className="module-skeleton-card">
          <Skeleton width="52%" height={18} />
          <Skeleton width="84%" height={12} variant="text" />
          <Skeleton width="100%" height={94} />
        </div>
      </div>
    </section>
  )
}
