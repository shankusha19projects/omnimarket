import { useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { AlertTriangle, ChevronDown, ChevronUp, Database, Inbox, Info } from 'lucide-react'
import { arrow, assetPath, dir, fmtDateTime, fmtPct, fmtPrice, isNum, timeAgo } from '../services/format'

/* ---------- Panel ---------- */
export function Panel({ title, sub, actions, children, className, flush, foot, prov, accent, style, id }: {
  title?: ReactNode; sub?: ReactNode; actions?: ReactNode; children?: ReactNode; className?: string; flush?: boolean; foot?: ReactNode
  prov?: any; accent?: boolean; style?: CSSProperties; id?: string
}) {
  return (
    <section className={clsx('panel', accent && 'accent-top', className)} style={style} id={id}>
      {(title || actions || prov) && (
        <header className="panel-head">
          <div style={{ minWidth: 0 }}>
            {title && <h2 className="panel-title"><span className="dot" />{title}</h2>}
            {sub && <div className="panel-sub">{sub}</div>}
          </div>
          <div className="panel-actions">
            {actions}
            {prov && <Prov p={prov} />}
          </div>
        </header>
      )}
      <div className={clsx('panel-body', flush && 'flush')}>{children}</div>
      {foot && <footer className="panel-foot">{foot}</footer>}
    </section>
  )
}

/* ---------- Direction-aware numbers (never color-only: arrow + sign) ---------- */
export function Chg({ v, pct = true, digits = 2, className }: { v: unknown; pct?: boolean; digits?: number; className?: string }) {
  const d = dir(v)
  return (
    <span className={clsx('chg', d, className)} aria-label={isNum(v) ? `${d === 'up' ? 'up' : d === 'down' ? 'down' : 'unchanged'} ${Math.abs(v as number).toFixed(digits)}${pct ? ' percent' : ''}` : 'not available'}>
      {isNum(v) && <span style={{ fontSize: '0.7em' }}>{arrow(v)}</span>}
      {pct ? fmtPct(v, digits) : isNum(v) ? `${(v as number) > 0 ? '+' : ''}${fmtPrice(v, { max: Math.abs(v as number) >= 0.01 ? digits : 6, min: Math.abs(v as number) >= 0.01 ? digits : 2 })}` : '—'}
    </span>
  )
}

export function ChgPill({ v, digits = 2 }: { v: unknown; digits?: number }) {
  const d = dir(v)
  return <span className={clsx('chg-pill', d)}>{isNum(v) && <span style={{ fontSize: '0.75em' }}>{arrow(v)}</span>}{fmtPct(v, digits)}</span>
}

/* ---------- Sparkline (SVG) ---------- */
export function Sparkline({ data, width = 120, height = 32, color, fill = true, className, baseline }: {
  data?: number[]; width?: number; height?: number; color?: string; fill?: boolean; className?: string; baseline?: number
}) {
  const pts = (data || []).filter(isNum)
  if (pts.length < 2) return <svg width={width} height={height} className={className} aria-hidden />
  const min = Math.min(...pts, baseline ?? Infinity), max = Math.max(...pts, baseline ?? -Infinity)
  const span = max - min || 1
  const x = (i: number) => (i / (pts.length - 1)) * width
  const y = (v: number) => height - 2 - ((v - min) / span) * (height - 4)
  const d = pts.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('')
  const up = pts[pts.length - 1] >= (baseline ?? pts[0])
  const c = color || (up ? 'var(--up)' : 'var(--down)')
  const gid = `g${Math.round(Math.random() * 1e9)}`
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className={className} aria-hidden>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={c} stopOpacity="0.28" />
          <stop offset="100%" stopColor={c} stopOpacity="0" />
        </linearGradient>
      </defs>
      {baseline !== undefined && <line x1="0" x2={width} y1={y(baseline)} y2={y(baseline)} stroke="var(--line-3)" strokeDasharray="2 3" strokeWidth="1" />}
      {fill && <path d={`${d}L${width},${height}L0,${height}Z`} fill={`url(#${gid})`} />}
      <path d={d} fill="none" stroke={c} strokeWidth="1.5" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  )
}

/* ---------- Provenance badge (source, provider, retrieved, delay, cache) ---------- */
export function Prov({ p, label }: { p: any; label?: string }) {
  if (!p) return null
  const status = p.cache_status
  const cls = status === 'stale' || status === 'unavailable' ? 'bad' : status === 'live' ? 'ok' : ''
  return (
    <span className="prov">
      <button className="prov-trigger" type="button" aria-label="Data provenance">
        <Database size={10} />
        {label || p.provider || 'source'}
        {status && <span className={clsx('status-dot', cls === 'ok' ? 'ok' : cls === 'bad' ? 'bad' : 'idle')} style={{ width: 5, height: 5 }} />}
      </button>
      <span className="prov-pop" role="tooltip">
        <dl>
          <dt>Provider</dt><dd>{p.provider || '—'}</dd>
          {p.source_url && <><dt>Source</dt><dd><a href={p.source_url} target="_blank" rel="noreferrer noopener">{shortUrl(p.source_url)}</a></dd></>}
          <dt>Retrieved</dt><dd>{p.retrieved_at ? `${fmtDateTime(p.retrieved_at)} (${timeAgo(p.retrieved_at)})` : '—'}</dd>
          {p.market_time && <><dt>Market time</dt><dd>{fmtDateTime(p.market_time)}</dd></>}
          {p.delay && <><dt>Delay</dt><dd>{p.delay}</dd></>}
          <dt>Cache</dt><dd>{status || '—'}{p.ttl_seconds ? ` · TTL ${p.ttl_seconds}s` : ''}</dd>
          {p.note && <><dt>Note</dt><dd>{p.note}</dd></>}
          {p.error && <><dt>Error</dt><dd style={{ color: 'var(--down)' }}>{p.error}</dd></>}
        </dl>
      </span>
    </span>
  )
}

function shortUrl(u: string) {
  try {
    const x = new URL(u)
    return x.host + (x.pathname.length > 26 ? x.pathname.slice(0, 26) + '…' : x.pathname)
  } catch { return u }
}

/* ---------- Loading / empty / error ---------- */
export function Skel({ h = 14, w = '100%', r, style }: { h?: number; w?: number | string; r?: number; style?: CSSProperties }) {
  return <div className="skel" style={{ height: h, width: w, borderRadius: r, ...style }} />
}

export function SkelRows({ n = 6, h = 16 }: { n?: number; h?: number }) {
  return <div className="col" style={{ gap: 9, padding: '8px 0' }}>{Array.from({ length: n }).map((_, i) => <Skel key={i} h={h} w={`${88 - (i % 3) * 9}%`} />)}</div>
}

export function Empty({ title = 'Nothing here yet', children, icon }: { title?: string; children?: ReactNode; icon?: ReactNode }) {
  return <div className="empty">{icon || <Inbox size={22} />}<div className="ttl">{title}</div>{children && <div className="small">{children}</div>}</div>
}

export function ErrorState({ error, retry }: { error: any; retry?: () => void }) {
  return (
    <div className="err" role="alert">
      <AlertTriangle size={22} color="var(--down)" />
      <div className="ttl">Data temporarily unavailable</div>
      <div className="small" style={{ maxWidth: 440 }}>{String(error?.message || error || 'Unknown error')}</div>
      {retry && <button className="btn sm" onClick={retry}>Retry</button>}
    </div>
  )
}

/** Renders children when a query has data, skeleton while loading, error state otherwise. */
export function Loadable<T>({ q, children, skeleton, empty }: { q: { data?: T; isLoading: boolean; error: any; refetch: () => any }; children: (d: T) => ReactNode; skeleton?: ReactNode; empty?: (d: T) => boolean }) {
  if (q.isLoading) return <>{skeleton ?? <SkelRows />}</>
  if (q.error && !q.data) return <ErrorState error={q.error} retry={() => q.refetch()} />
  if (!q.data) return <Empty />
  if (empty && empty(q.data)) return <Empty />
  return <>{children(q.data)}</>
}

export function Notice({ kind = 'info', children }: { kind?: 'info' | 'warn' | 'bad'; children: ReactNode }) {
  return <div className={clsx('notice', kind)}>{kind === 'bad' ? <AlertTriangle size={15} /> : <Info size={15} />}<div>{children}</div></div>
}

/* ---------- Controls ---------- */
export function Seg<T extends string>({ value, options, onChange, size }: { value: T; options: (T | [T, string])[]; onChange: (v: T) => void; size?: 'sm' }) {
  return (
    <div className="seg" role="tablist" style={size === 'sm' ? { transform: 'scale(.95)', transformOrigin: 'right' } : undefined}>
      {options.map((o) => {
        const [v, l] = Array.isArray(o) ? o : [o, o]
        return <button key={v} role="tab" aria-selected={value === v} className={clsx(value === v && 'on')} onClick={() => onChange(v)}>{l}</button>
      })}
    </div>
  )
}

export function Tabs<T extends string>({ value, options, onChange }: { value: T; options: [T, ReactNode][]; onChange: (v: T) => void }) {
  return (
    <div className="tabs" role="tablist">
      {options.map(([v, l]) => <button key={v} role="tab" aria-selected={value === v} className={clsx(value === v && 'on')} onClick={() => onChange(v)}>{l}</button>)}
    </div>
  )
}

export function Stat({ label, value, sub, className, title }: { label: ReactNode; value: ReactNode; sub?: ReactNode; className?: string; title?: string }) {
  return <div className={clsx('stat', className)} title={title}><div className="l">{label}</div><div className="v">{value}</div>{sub && <div className="s">{sub}</div>}</div>
}

export function RangeBar({ low, high, value }: { low?: number; high?: number; value?: number }) {
  if (!isNum(low) || !isNum(high) || !isNum(value) || high <= low) return <span className="muted">—</span>
  const pct = Math.max(0, Math.min(100, ((value - low) / (high - low)) * 100))
  return (
    <div className="range-bar" title={`${fmtPrice(low)} – ${fmtPrice(high)}`}>
      <div className="fill" style={{ width: '100%' }} />
      <div className="mark" style={{ left: `calc(${pct}% - 1px)` }} />
    </div>
  )
}

export function AssetLink({ symbol, children, className }: { symbol: string; children?: ReactNode; className?: string }) {
  return <Link to={assetPath(symbol)} className={className} onClick={(e) => e.stopPropagation()}>{children ?? symbol}</Link>
}

export function Logo({ symbol, img }: { symbol: string; img?: string }) {
  return <span className="logo-sq">{img ? <img src={img} alt="" loading="lazy" /> : symbol.replace(/[^A-Z0-9]/gi, '').slice(0, 3)}</span>
}

/* ---------- Data table: sortable, sticky header, filter, pagination ---------- */
export type Col<T> = {
  key: string
  label: ReactNode
  num?: boolean
  render?: (r: T) => ReactNode
  value?: (r: T) => any
  sortable?: boolean
  width?: number | string
  title?: string
}

export function DataTable<T extends Record<string, any>>({ rows, cols, onRow, initialSort, initialDesc = true, maxHeight, pageSize, compact, filter, rowKey, empty }: {
  rows: T[]; cols: Col<T>[]; onRow?: (r: T) => void; initialSort?: string; initialDesc?: boolean; maxHeight?: number; pageSize?: number
  compact?: boolean; filter?: string; rowKey?: (r: T, i: number) => string; empty?: ReactNode
}) {
  const [sort, setSort] = useState<string | undefined>(initialSort)
  const [desc, setDesc] = useState(initialDesc)
  const [page, setPage] = useState(0)
  const sorted = useMemo(() => {
    let out = rows
    if (filter) {
      const f = filter.toLowerCase()
      out = out.filter((r) => Object.values(r).some((v) => typeof v === 'string' && v.toLowerCase().includes(f)))
    }
    if (!sort) return out
    const col = cols.find((c) => c.key === sort)
    const get = col?.value || ((r: T) => r[sort])
    return [...out].sort((a, b) => {
      const va = get(a), vb = get(b)
      if (va === null || va === undefined) return 1
      if (vb === null || vb === undefined) return -1
      const c = typeof va === 'string' ? va.localeCompare(vb) : va - vb
      return desc ? -c : c
    })
  }, [rows, sort, desc, cols, filter])
  const pages = pageSize ? Math.max(1, Math.ceil(sorted.length / pageSize)) : 1
  const view = pageSize ? sorted.slice(page * pageSize, (page + 1) * pageSize) : sorted
  return (
    <>
      <div className="table-wrap" style={maxHeight ? { maxHeight } : undefined}>
        <table className={clsx('t', compact && 'compact')}>
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c.key} className={clsx(c.num && 'num', c.sortable !== false && 'sortable')} style={{ width: c.width }} title={c.title}
                    onClick={() => { if (c.sortable === false) return; if (sort === c.key) setDesc(!desc); else { setSort(c.key); setDesc(true) } }}
                    aria-sort={sort === c.key ? (desc ? 'descending' : 'ascending') : 'none'}>
                  {c.label}{sort === c.key && <span className="sort-ind">{desc ? <ChevronDown size={10} /> : <ChevronUp size={10} />}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.map((r, i) => (
              <tr key={rowKey ? rowKey(r, i) : (r.symbol ?? r.id ?? i)} className={clsx(onRow && 'clickable')} onClick={onRow ? () => onRow(r) : undefined}
                  tabIndex={onRow ? 0 : undefined} onKeyDown={onRow ? (e) => { if (e.key === 'Enter') onRow(r) } : undefined}>
                {cols.map((c) => <td key={c.key} className={clsx(c.num && 'num')}>{c.render ? c.render(r) : r[c.key] ?? '—'}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
        {!view.length && (empty ?? <Empty title="No rows" />)}
      </div>
      {pageSize && pages > 1 && (
        <div className="row" style={{ justifyContent: 'flex-end', padding: '8px 10px', gap: 6 }}>
          <span className="muted small">{sorted.length} rows · page {page + 1}/{pages}</span>
          <button className="btn sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Prev</button>
          <button className="btn sm" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      )}
    </>
  )
}

export function StatusDot({ status }: { status?: string }) {
  const cls = status === 'online' || status === 'ok' || status === 'open' ? 'ok' : status === 'degraded' || status === 'rate_limited' || status === 'stale' || status === 'partial' || status === 'pre-market' || status === 'after-hours' || status === 'lunch' ? 'warn' : status === 'error' || status === 'failed' ? 'bad' : 'idle'
  return <span className={clsx('status-dot', cls, (status === 'open' || status === 'online') && 'pulse')} />
}

export function MarketState({ state }: { state?: string }) {
  if (!state) return null
  const s = state.toUpperCase()
  const label = s === 'REGULAR' ? 'Open' : s === 'PRE' || s === 'PREPRE' ? 'Pre-market' : s === 'POST' || s === 'POSTPOST' ? 'After-hours' : 'Closed'
  return <span className={clsx('badge', s === 'REGULAR' ? 'ok live' : s.startsWith('PRE') || s.startsWith('POST') ? 'warn' : '')}>{label}</span>
}
