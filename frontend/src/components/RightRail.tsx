import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { assetPath, fmtDuration, fmtPrice, timeAgo } from '../services/format'
import { Chg, Panel, SkelRows, Sparkline, StatusDot } from './ui'

export function WatchlistMini({ height }: { height?: number }) {
  const lists = useApi<any[]>('/watchlists')
  const [wid, setWid] = useState<number | null>(null)
  const id = wid ?? lists.data?.[0]?.id ?? null
  const q = useApi(id ? `/watchlists/${id}` : null, { refetch: 60_000 })
  const nav = useNavigate()
  return (
    <Panel title="Watchlist" actions={
      <select className="input sm" value={id ?? ''} onChange={(e) => setWid(Number(e.target.value))} aria-label="Choose watchlist" style={{ maxWidth: 140 }}>
        {(lists.data || []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
      </select>}>
      <div style={{ maxHeight: height, overflow: 'auto', margin: '0 -14px' }}>
        {q.isLoading ? <div style={{ padding: '0 14px' }}><SkelRows n={6} /></div> : (q.data?.rows || []).map((r: any) => (
          <div key={r.symbol} className="row" style={{ padding: '7px 14px', borderBottom: '1px solid var(--line)', cursor: 'pointer' }}
               onClick={() => nav(assetPath(r.symbol))} role="link" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && nav(assetPath(r.symbol))}>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div className="mono" style={{ fontWeight: 600, fontSize: 12 }}>{r.symbol}</div>
              <div className="muted xs truncate">{r.name}</div>
            </div>
            <div style={{ width: 60 }}><Sparkline data={r.spark} width={60} height={22} fill={false} /></div>
            <div className="right" style={{ minWidth: 78 }}>
              <div className="mono" style={{ fontSize: 12, fontWeight: 600 }}>{r.unavailable ? 'n/a' : fmtPrice(r.price)}</div>
              <Chg v={r.change_pct} className="xs" />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  )
}

export function MarketClock() {
  const q = useApi('/clock', { refetch: 30_000 })
  return (
    <Panel title="Market sessions">
      {(q.data?.sessions || []).map((s: any) => (
        <div className="session" key={s.id}>
          <div className="row" style={{ gap: 8 }}>
            <StatusDot status={s.status} />
            <div>
              <div style={{ fontWeight: 600, fontSize: 12.5 }}>{s.city} <span className="muted xs mono">{s.id}</span></div>
              <div className="muted xs">{s.status === 'open' ? 'Open' : s.status.replace('-', ' ')}{s.next_event ? ` · ${s.next_event} in ${fmtDuration(s.seconds_to_next)}` : ''}</div>
            </div>
          </div>
          <div className="mono small dim" title={`Session ${s.hours} local`}>{s.local_time}</div>
        </div>
      ))}
    </Panel>
  )
}

export function HeadlinesMini({ limit = 8 }: { limit?: number }) {
  const q = useApi('/news?limit=40', { refetch: 300_000 })
  return (
    <Panel title="Latest headlines" actions={<Link to="/news" className="small">All news →</Link>}>
      {q.isLoading ? <SkelRows n={5} /> : (q.data?.items || []).slice(0, limit).map((n: any) => (
        <a key={n.id} href={n.url} target="_blank" rel="noreferrer noopener" style={{ display: 'block', padding: '7px 0', borderBottom: '1px solid var(--line)', color: 'var(--text)', textDecoration: 'none' }}>
          <div style={{ fontSize: 12.5, fontWeight: 500, lineHeight: 1.35 }}>{n.title}</div>
          <div className="muted xs" style={{ marginTop: 3 }}>{n.publisher} · {timeAgo(n.published_at)} · <span style={{ color: 'var(--accent)' }}>{n.category}</span></div>
        </a>
      ))}
    </Panel>
  )
}

export function EconMini() {
  const q = useApi('/calendar/economic?which=this_week&min_importance=3')
  const today = new Date().toISOString().slice(0, 10)
  const rows = (q.data?.rows || []).filter((r: any) => r.date >= today).slice(0, 7)
  return (
    <Panel title="Key events this week" actions={<Link to="/calendar" className="small">Calendar →</Link>}>
      {q.isLoading ? <SkelRows n={4} /> : rows.length ? rows.map((r: any, i: number) => (
        <div key={i} className="row" style={{ padding: '6px 0', borderBottom: '1px solid var(--line)', alignItems: 'flex-start' }}>
          <span className="mono xs muted" style={{ width: 46 }}>{r.date.slice(5)}<br />{r.time_gmt || ''}</span>
          <span style={{ flex: 1, fontSize: 12 }}>{r.event}<div className="muted xs">{r.country}{r.forecast ? ` · fcst ${r.forecast}` : ''}</div></span>
        </div>
      )) : <div className="muted small">No high-importance events remaining this week.</div>}
    </Panel>
  )
}

export function RightRail() {
  return (
    <>
      <WatchlistMini height={360} />
      <MarketClock />
      <HeadlinesMini />
      <EconMini />
    </>
  )
}
