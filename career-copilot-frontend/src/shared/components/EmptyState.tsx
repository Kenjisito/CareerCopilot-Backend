import { useId, type ReactNode } from "react"

type EmptyStateProps = {
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
  children?: ReactNode
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  children,
}: EmptyStateProps) {
  const titleId = useId()

  return (
    <section className="empty-state" aria-labelledby={titleId}>
      <h2 id={titleId}>{title}</h2>
      <p>{description}</p>
      {children}
      {actionLabel && onAction && (
        <button className="btn btn-primary" type="button" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </section>
  )
}
