import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, CircleDashed, Clock3, KeyRound, Loader2, Search, X, XCircle } from 'lucide-react'
import { useApp } from '../hooks/AppContext'
import { api } from '../services/api'
import { assetPath, fmtTime } from '../services/format'
import { ALL_NAV } from './nav'
import { BrandMark } from './Shell'

/* ---------------- Ctrl+K command palette ---------------- */
export function CommandPalette() {
  const { paletteOpen, setPaletteOpen } = useApp()
  const [q, setQ] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [idx, setIdx] = useState(0)
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPaletteOpen(true) }
      if (e.key === '/' && !(e.target as HTMLElement).closest('input,textarea,select')) { e.preventDefault(); setPaletteOpen(true) }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [setPaletteOpen])

  useEffect(() => { if (paletteOpen) { setQ(''); setResults([]); setIdx(0); setTimeout(() => inputRef.current?.focus(), 10) } }, [paletteOpen])

  useEffect(() => {
    if (!q.trim()) { setResults([]); return }
    setLoading(true)
    const t = setTimeout(() => {
      api.get(`/assets/search?q=${encodeURIComponent(q.trim())}`).then((r) => { setResults(r.results || []); setIdx(0) }).catch(() => setResults([])).finally(() => setLoading(false))
    }, 160)
    return () => clearTimeout(t)
  }, [q])

  const pages = useMemo(() => ALL_NAV.filter((n) => q && n.label.toLowerCase().includes(q.toLowerCase())).map((n) => ({ type: 'page', symbol: n.to, name: n.label, detail: 'Go to page' })), [q])
  const all = [...pages, ...results]

  const open = (r: any) => {
    setPaletteOpen(false)
    if (r.type === 'page') nav(r.symbol)
    else if (r.type === 'article') window.open(r.symbol, '_blank', 'noopener')
    else if (r.type === 'indicator') nav('/economics')
    else if (r.type === 'sector' || r.type === 'theme') nav('/sectors')
    else nav(assetPath(r.symbol))
  }

  if (!paletteOpen) return null
  const groups: Record<string, string> = { page: 'Navigate', equity: 'Stocks', etf: 'ETFs', index: 'Indices', crypto: 'Crypto', commodity: 'Commodities & futures', fx: 'Currencies', rate: 'Rates', fund: 'Funds', indicator: 'Economic indicators', sector: 'Sectors', theme: 'Themes', article: 'Articles', other: 'Other' }
  let lastType = ''
  return (
    <div className="overlay" onMouseDown={() => setPaletteOpen(false)}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label="Search">
        <div style={{ position: 'relative', borderBottom: '1px solid var(--line)' }}>
          <Search size={17} style={{ position: 'absolute', left: 16, top: 17, color: 'var(--text-3)' }} />
          <input ref={inputRef} className="palette-input" placeholder="Search tickers, companies, crypto, commodities, indicators, articles…" value={q}
                 onChange={(e) => setQ(e.target.value)}
                 onKeyDown={(e) => {
                   if (e.key === 'ArrowDown') { e.preventDefault(); setIdx(Math.min(idx + 1, all.length - 1)) }
                   if (e.key === 'ArrowUp') { e.preventDefault(); setIdx(Math.max(idx - 1, 0)) }
                   if (e.key === 'Enter') { if (all[idx]) open(all[idx]); else if (q.trim()) { setPaletteOpen(false); nav(assetPath(q.trim().toUpperCase())) } }
                   if (e.key === 'Escape') setPaletteOpen(false)
                 }} aria-label="Search query" />
          {loading && <Loader2 size={15} className="spin" style={{ position: 'absolute', right: 16, top: 18, color: 'var(--text-3)', animation: 'spin 1s linear infinite' }} />}
        </div>
        <div className="palette-list">
          {!q && <div className="muted small" style={{ padding: 16 }}>Type a ticker (NVDA, BTC-USD, GC=F, EURUSD=X), a company, sector, theme or indicator. <span className="kbd">↑</span> <span className="kbd">↓</span> to move, <span className="kbd">Enter</span> to open.</div>}
          {q && !all.length && !loading && <div className="muted small" style={{ padding: 16 }}>No matches. Press Enter to open “{q.toUpperCase()}” directly.</div>}
          {all.map((r, i) => {
            const header = r.type !== lastType ? <div className="palette-group">{groups[r.type] || r.type}</div> : null
            lastType = r.type
            return (
              <div key={`${r.type}${r.symbol}${i}`}>
                {header}
                <div className={clsx('palette-item', i === idx && 'on')} onMouseEnter={() => setIdx(i)} onClick={() => open(r)}>
                  <span className="sym">{r.type === 'article' || r.type === 'page' ? '' : r.symbol}</span>
                  <span className="truncate">{r.name}</span>
                  <span className="desc">{r.exchange ? `${r.exchange} · ` : ''}{r.detail}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/* ---------------- Refresh center drawer ---------------- */
const ICON: Record<string, any> = { ok: CheckCircle2, stale: Clock3, partial: AlertTriangle, failed: XCircle, rate_limited: AlertTriangle, running: Loader2, queued: CircleDashed }
const COLOR: Record<string, string> = { ok: 'var(--up)', stale: 'var(--amber)', partial: 'var(--amber)', failed: 'var(--down)', rate_limited: 'var(--amber)', running: 'var(--accent)', queued: 'var(--text-4)' }

export function RefreshDrawer() {
  const { drawerOpen, setDrawerOpen, job, lastJob, startRefresh, refreshing } = useApp()
  if (!drawerOpen) return null
  const j = job || lastJob
  const pct = j && j.total ? Math.round((j.completed / j.total) * 100) : 0
  return (
    <div className="drawer" role="dialog" aria-label="Refresh status">
      <div className="modal-head">
        <div>
          <div style={{ fontWeight: 600 }}>{j ? (j.status === 'running' ? 'Refreshing live data…' : 'Refresh summary') : 'Refresh center'}</div>
          <div className="muted xs">{j ? `Started ${fmtTime(j.started_at, true)}${j.finished_at ? ` · completed ${fmtTime(j.finished_at, true)} (${(j.finished_at - j.started_at).toFixed(1)}s)` : ''}` : 'No refresh has run in this session.'}</div>
        </div>
        <button className="icon-btn sm ghost" style={{ marginLeft: 'auto' }} onClick={() => setDrawerOpen(false)} aria-label="Close"><X size={15} /></button>
      </div>
      {j && <div style={{ padding: '10px 14px 8px' }}>
        <div className="progress"><i style={{ width: `${pct}%` }} /></div>
        <div className="row small muted" style={{ marginTop: 7, flexWrap: 'wrap' }}>
          <span>{j.completed}/{j.total} datasets</span>
          {Object.entries(j.summary || {}).map(([k, v]) => <span key={k} style={{ color: COLOR[k] }}>{v as number} {k.replace('_', ' ')}</span>)}
          {j.status !== 'running' && <span className={clsx('badge', j.status === 'completed' ? 'ok' : j.status === 'failed' ? 'bad' : 'warn')} style={{ marginLeft: 'auto' }}>{j.status.replace(/_/g, ' ')}</span>}
        </div>
        {j.note && <div className="muted xs" style={{ marginTop: 4 }}>{j.note}</div>}
      </div>}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {(j?.datasets || []).map((d: any) => {
          const I = ICON[d.status] || CircleDashed
          return (
            <div className="ds-row" key={d.key}>
              <I size={15} color={COLOR[d.status]} style={d.status === 'running' ? { animation: 'spin 1s linear infinite' } : undefined} />
              <span>{d.label}</span>
              <span className="muted xs mono">{d.provider || ''}{d.finished_at && d.started_at ? ` · ${(d.finished_at - d.started_at).toFixed(1)}s` : ''}</span>
              {d.message && <span className="msg" style={{ color: d.status === 'failed' ? 'var(--down)' : undefined }}>{d.message}</span>}
            </div>
          )
        })}
        {!j && <div className="muted small" style={{ padding: 16 }}>Click <b>Refresh live data</b> to fetch the newest quotes, yields, crypto, macro series and news from every configured provider. Results, failures and stale sources will be listed here.</div>}
      </div>
      <div className="modal-foot">
        <span className="muted xs" style={{ marginRight: 'auto' }}>Failed sources keep serving the last good cached value, labeled stale.</span>
        <button className="btn sm primary" disabled={refreshing} onClick={() => startRefresh(['everything'])}>Refresh everything</button>
      </div>
    </div>
  )
}

/* ---------------- First-run setup wizard ---------------- */
export function SetupWizard() {
  const { setupOpen, setSetupOpen } = useApp()
  const [data, setData] = useState<any>(null)
  const [keys, setKeys] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { if (setupOpen) api.get('/setup').then(setData).catch(() => undefined) }, [setupOpen])
  if (!setupOpen) return null
  const finish = async () => {
    setSaving(true); setErr(null)
    try {
      const secrets = Object.fromEntries(Object.entries(keys).filter(([, v]) => v.trim()))
      await api.put('/settings', { preferences: { setup_complete: true }, secrets })
      setSetupOpen(false)
    } catch (e: any) { setErr(e.message) } finally { setSaving(false) }
  }
  return (
    <div className="overlay">
      <div className="modal wide" role="dialog" aria-label="Welcome">
        <div className="modal-head" style={{ padding: '18px 20px' }}>
          <BrandMark />
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600 }}>Welcome to OmniMarket Intelligence</div>
            <div className="muted small">Keyless public sources are already live. Connect optional providers now or later in Settings → Data Providers.</div>
          </div>
        </div>
        <div className="modal-body" style={{ display: 'grid', gap: 8 }}>
          {(data?.checks || []).map((c: any) => (
            <div key={c.id} className="row" style={{ padding: '10px 12px', border: '1px solid var(--line)', borderRadius: 8, background: 'var(--panel-2)', alignItems: 'center' }}>
              {c.ready ? <CheckCircle2 size={17} color="var(--up)" /> : <CircleDashed size={17} color="var(--text-4)" />}
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{c.label}</div>
                <div className="muted xs">{c.note}</div>
              </div>
              {c.key && !c.ready && (
                <div className="row" style={{ gap: 6 }}>
                  <KeyRound size={13} color="var(--text-3)" />
                  <input className="input sm" type="password" autoComplete="off" placeholder={c.key} value={keys[c.key] || ''} onChange={(e) => setKeys({ ...keys, [c.key]: e.target.value })} style={{ width: 230 }} aria-label={c.key} />
                </div>
              )}
              {c.ready && <span className="badge ok">Connected</span>}
            </div>
          ))}
          <div className="muted xs" style={{ marginTop: 6 }}>Keys are written only to the local <span className="mono">.env</span> file by the backend. They are never stored in the browser or returned by the API.</div>
          {err && <div className="notice bad">{err}</div>}
        </div>
        <div className="modal-foot">
          <button className="btn ghost" onClick={() => { api.put('/settings', { preferences: { setup_complete: true } }).catch(() => undefined); setSetupOpen(false) }}>Skip for now</button>
          <button className="btn primary" disabled={saving} onClick={finish}>{saving ? 'Saving…' : 'Continue'}</button>
        </div>
      </div>
    </div>
  )
}
