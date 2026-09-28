import { useEffect, useState, type ReactNode } from 'react'
import { ArrowDown, ArrowUp, Eye, EyeOff, LayoutGrid, RotateCcw, X } from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../hooks/AppContext'
import { Breadth, CryptoMini, Heatmap, IndicesTable, MarketMovingNews, Movers, OverviewCards, SectorBars, Volatility, YieldCurveMini } from '../components/widgets'
import { EconMini, HeadlinesMini, MarketClock, WatchlistMini } from '../components/RightRail'

/* Widget registry: id → (title, grid span, render). Order/visibility is user-configurable and persisted. */
const WIDGETS: Record<string, { title: string; span: string; render: () => ReactNode }> = {
  overview: { title: 'Market overview cards', span: 'c-12', render: () => <OverviewCards /> },
  heatmap: { title: 'Market heatmap', span: 'c-8', render: () => <Heatmap /> },
  movers: { title: 'Movers', span: 'c-4', render: () => <Movers /> },
  indices: { title: 'Global indices', span: 'c-8', render: () => <IndicesTable /> },
  breadth: { title: 'Market breadth', span: 'c-4', render: () => <Breadth /> },
  news: { title: 'Market-moving news', span: 'c-6', render: () => <MarketMovingNews /> },
  volatility: { title: 'Volatility', span: 'c-6', render: () => <Volatility /> },
  yield_curve: { title: 'Yield curve', span: 'c-4', render: () => <YieldCurveMini /> },
  crypto: { title: 'Crypto', span: 'c-4', render: () => <CryptoMini /> },
  sectors: { title: 'Sector performance', span: 'c-4', render: () => <SectorBars /> },
  watchlist: { title: 'Watchlist', span: 'c-4', render: () => <WatchlistMini height={420} /> },
  calendar: { title: 'Economic calendar', span: 'c-4', render: () => <EconMini /> },
  headlines: { title: 'Latest headlines', span: 'c-4', render: () => <HeadlinesMini limit={10} /> },
  clock: { title: 'Market sessions', span: 'c-4', render: () => <MarketClock /> },
}
const DEFAULT_ORDER = ['overview', 'heatmap', 'movers', 'indices', 'breadth', 'news', 'volatility', 'yield_curve', 'crypto', 'sectors', 'calendar', 'clock', 'watchlist', 'headlines']
const DEFAULT_HIDDEN = ['watchlist', 'headlines']

function loadLayout(): { order: string[]; hidden: string[] } {
  try {
    const v = JSON.parse(localStorage.getItem('omni.layout') || 'null')
    if (v?.order) return { order: [...v.order.filter((k: string) => WIDGETS[k]), ...DEFAULT_ORDER.filter((k) => !v.order.includes(k))], hidden: v.hidden || [] }
  } catch { /* ignore */ }
  return { order: DEFAULT_ORDER, hidden: DEFAULT_HIDDEN }
}

export default function Markets() {
  const [layout, setLayout] = useState(loadLayout)
  const [editing, setEditing] = useState(false)
  const [dragKey, setDragKey] = useState<string | null>(null)
  const { lastJob } = useApp()

  useEffect(() => {
    try { localStorage.setItem('omni.layout', JSON.stringify(layout)) } catch { /* ignore */ }
    api.put('/settings', { preferences: { dashboard_layout: layout.order, dashboard_hidden: layout.hidden } }).catch(() => undefined)
  }, [layout])

  const move = (k: string, d: -1 | 1) => {
    const o = [...layout.order]
    const i = o.indexOf(k), j = i + d
    if (j < 0 || j >= o.length) return
    ;[o[i], o[j]] = [o[j], o[i]]
    setLayout({ ...layout, order: o })
  }
  const toggle = (k: string) => setLayout({ ...layout, hidden: layout.hidden.includes(k) ? layout.hidden.filter((x) => x !== k) : [...layout.hidden, k] })
  const drop = (target: string) => {
    if (!dragKey || dragKey === target) return
    const o = layout.order.filter((k) => k !== dragKey)
    o.splice(o.indexOf(target), 0, dragKey)
    setLayout({ ...layout, order: o })
    setDragKey(null)
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-kicker">Global command center</div>
          <h1 className="page-title">Markets</h1>
          <div className="page-desc">Cross-asset overview — equities, rates, FX, commodities and crypto. Every figure carries its source, retrieval time and cache status.</div>
        </div>
        <div className="page-actions">
          {lastJob?.finished_at && <span className="muted small">Last full refresh {new Date(lastJob.finished_at * 1000).toLocaleTimeString()}</span>}
          <button className="btn" onClick={() => setEditing(!editing)}><LayoutGrid size={14} /> {editing ? 'Done' : 'Customize'}</button>
        </div>
      </div>

      {editing && (
        <div className="panel fade-in" style={{ marginBottom: 12 }}>
          <div className="panel-head">
            <h2 className="panel-title"><span className="dot" />Dashboard widgets</h2>
            <span className="panel-sub">Drag cards on the dashboard or use the arrows. Layout is saved locally and to your preferences.</span>
            <div className="panel-actions">
              <button className="btn sm" onClick={() => setLayout({ order: DEFAULT_ORDER, hidden: DEFAULT_HIDDEN })}><RotateCcw size={12} /> Reset</button>
              <button className="icon-btn sm ghost" onClick={() => setEditing(false)} aria-label="Close"><X size={14} /></button>
            </div>
          </div>
          <div className="panel-body" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 6 }}>
            {layout.order.map((k, i) => (
              <div key={k} className="row" style={{ padding: '6px 10px', border: '1px solid var(--line)', borderRadius: 8, background: 'var(--panel-2)', opacity: layout.hidden.includes(k) ? 0.5 : 1 }}>
                <span className="mono xs muted" style={{ width: 16 }}>{i + 1}</span>
                <span style={{ flex: 1 }}>{WIDGETS[k].title}</span>
                <button className="icon-btn sm ghost" onClick={() => move(k, -1)} aria-label="Move up"><ArrowUp size={13} /></button>
                <button className="icon-btn sm ghost" onClick={() => move(k, 1)} aria-label="Move down"><ArrowDown size={13} /></button>
                <button className="icon-btn sm ghost" onClick={() => toggle(k)} aria-label="Toggle visibility">{layout.hidden.includes(k) ? <EyeOff size={13} /> : <Eye size={13} />}</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid">
        {layout.order.filter((k) => !layout.hidden.includes(k)).map((k) => (
          <div key={k} className={`${WIDGETS[k].span} ${dragKey === k ? 'dragging' : ''} ${editing ? 'drop-hint' : ''}`} style={{ minWidth: 0 }}
               draggable={editing} onDragStart={() => setDragKey(k)} onDragOver={(e) => editing && e.preventDefault()} onDrop={() => drop(k)}>
            {WIDGETS[k].render()}
          </div>
        ))}
      </div>
    </div>
  )
}
