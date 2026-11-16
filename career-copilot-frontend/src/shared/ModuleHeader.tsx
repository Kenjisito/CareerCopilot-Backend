import type { ReactNode } from "react"

export function ModuleHeader({
  title,
  copy,
  children,
}: {
  title: string
  copy: string
  children?: ReactNode
}) {
  return (
    <header className="module-hero">
      <span className="module-hero-stars" aria-hidden="true">
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
      <div className="module-hero-copy">
        <h1>{title}</h1>
        <p>{copy}</p>
      </div>
      {children && <div className="module-hero-actions">{children}</div>}
    </header>
  )
}
