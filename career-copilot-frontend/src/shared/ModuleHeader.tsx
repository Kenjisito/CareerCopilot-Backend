import { Children, useEffect, useState, type ReactNode } from "react"

function useCompactActions() {
  const [isCompact, setIsCompact] = useState(() =>
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(max-width: 720px)").matches,
  )

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return
    const query = window.matchMedia("(max-width: 720px)")
    const update = (event: MediaQueryListEvent) => setIsCompact(event.matches)
    query.addEventListener("change", update)
    return () => query.removeEventListener("change", update)
  }, [])

  return isCompact
}

export function ModuleHeader({
  title,
  copy,
  children,
}: {
  title: string
  copy: string
  children?: ReactNode
}) {
  const hasMultipleActions = Children.count(children) > 1
  const isCompact = useCompactActions()

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
      {children && (
        hasMultipleActions && isCompact ? (
          <details className="module-hero-actions-mobile">
            <summary>Acciones</summary>
            <div className="module-hero-action-list">{children}</div>
          </details>
        ) : (
          <div className="module-hero-actions">{children}</div>
        )
      )}
    </header>
  )
}
