import type { ReactNode } from 'react'

export function PageHead({ kicker, title, desc, actions }: { kicker?: string; title: string; desc?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        {kicker && <div className="page-kicker">{kicker}</div>}
        <h1 className="page-title">{title}</h1>
        {desc && <div className="page-desc">{desc}</div>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  )
}
