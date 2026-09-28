import { useState } from 'react'
import { Check, ExternalLink, KeyRound, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import { useApi } from '../hooks/useApi'
import { useApp, type ThemeMode } from '../hooks/AppContext'
import { PageHead } from '../components/PageHead'
import { DataTable, Loadable, Notice, Panel, Seg, SkelRows, StatusDot, Tabs } from '../components/ui'
import { fmtDateTime, timeAgo } from '../services/format'

export default function Settings() {
  const [tab, setTab] = useState<'providers' | 'keys' | 'ai' | 'prefs' | 'cache'>('providers')
  return (
    <div className="page">
      <PageHead kicker="Configuration" title="Settings" desc="Provider health, API keys (stored only in the backend's .env), AI provider, preferences and cache policy." />
      <Tabs value={tab} options={[['providers', 'Provider health'], ['keys', 'Data providers & keys'], ['ai', 'AI & research agents'], ['prefs', 'Preferences'], ['cache', 'Cache & refresh']]} onChange={setTab} />
      {tab === 'providers' && <Providers />}
      {tab === 'keys' && <Keys />}
      {tab === 'ai' && <AI />}
      {tab === 'prefs' && <Prefs />}
      {tab === 'cache' && <Cache />}
    </div>
  )
}

function Providers() {
  const q = useApi('/providers/status', { refetch: 20_000 })
  return (
    <Panel title="Provider health" sub="Live request/success/failure tracking for every data source" flush>
      <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={14} /></div>}>
        {(d) => <DataTable rows={d.providers} initialSort="requests" cols={[
          { key: 'label', label: 'Provider', render: (r) => <div><b>{r.label}</b><div className="muted xs">{r.purpose}</div></div> },
          { key: 'status', label: 'Status', render: (r) => <span className="row" style={{ gap: 6 }}><StatusDot status={r.status} /><span className="small">{r.status.replace('_', ' ')}</span></span> },
          { key: 'requires_key', label: 'Key', render: (r) => r.requires_key ? <span className={`badge ${r.configured ? 'ok' : ''}`}>{r.configured ? 'configured' : r.requires_key}</span> : <span className="muted xs">keyless</span> },
          { key: 'last_request', label: 'Latest request', render: (r) => <span className="muted small">{r.last_request ? timeAgo(r.last_request) : '—'}</span> },
          { key: 'last_success', label: 'Latest success', render: (r) => <span className="small">{r.last_success ? fmtDateTime(r.last_success) : '—'}</span> },
          { key: 'last_failure', label: 'Latest failure', render: (r) => <span className="small" title={r.last_error || ''}>{r.last_failure ? <span className="down">{fmtDateTime(r.last_failure)}</span> : '—'}{r.last_error && <div className="muted xs truncate" style={{ maxWidth: 260 }}>{r.last_error}</div>}</span> },
          { key: 'requests', label: 'Requests', num: true },
          { key: 'failures', label: 'Failures', num: true },
          { key: 'quota', label: 'Quota', render: (r) => <span className="muted xs">{r.quota || 'unknown'}</span> },
          { key: 'homepage', label: '', sortable: false, render: (r) => r.homepage ? <a href={r.homepage} target="_blank" rel="noreferrer noopener" aria-label="Provider site"><ExternalLink size={12} /></a> : null },
        ]} />}
      </Loadable>
    </Panel>
  )
}

function Keys() {
  const q = useApi('/settings')
  const [vals, setVals] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState<string | null>(null)
  const save = async (secrets: Record<string, string | null>) => {
    setMsg(null)
    try { await api.put('/settings', { secrets }); setVals({}); setMsg('Saved to .env — takes effect immediately.'); q.refetch() } catch (e: any) { setMsg(e.message) }
  }
  return (
    <Loadable q={q} skeleton={<SkelRows n={10} />}>
      {(d) => (
        <div className="grid">
          <div className="c-12"><Notice kind="info">Keys are sent once to the local backend, written to <span className="mono">.env</span> and never returned to the browser — only a “configured” flag is exposed. Keyless public sources (Yahoo-compatible, SEC, Treasury, BLS, CoinGecko, central banks, Nasdaq calendars, RSS) work without any keys.</Notice></div>
          {Array.from(new Set(d.secrets.map((s: any) => s.group))).map((g: any) => (
            <div className="c-6" key={g}>
              <Panel title={g}>
                {d.secrets.filter((s: any) => s.group === g).map((s: any) => (
                  <div key={s.key} className="row" style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
                    <KeyRound size={14} color={s.configured ? 'var(--up)' : 'var(--text-4)'} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600 }}>{s.label} {s.configured && <span className="badge ok"><Check size={10} /> configured</span>}</div>
                      <div className="muted xs mono">{s.key} · <a href={s.url} target="_blank" rel="noreferrer noopener">get a key ↗</a></div>
                    </div>
                    <input className="input sm" type="password" autoComplete="off" placeholder={s.configured ? '•••••••• (replace)' : 'paste key'} value={vals[s.key] || ''} onChange={(e) => setVals({ ...vals, [s.key]: e.target.value })} style={{ width: 200 }} aria-label={s.key} />
                    <button className="btn sm" disabled={!vals[s.key]} onClick={() => save({ [s.key]: vals[s.key] })}>Save</button>
                    {s.configured && <button className="icon-btn sm ghost" aria-label="Remove key" onClick={() => confirm(`Remove ${s.key}?`) && save({ [s.key]: null })}><Trash2 size={12} /></button>}
                  </div>
                ))}
              </Panel>
            </div>
          ))}
          <div className="c-12">
            <Panel title="SEC fair-access identity">
              <SecUA initial={d.env.SEC_USER_AGENT} />
            </Panel>
          </div>
          {msg && <div className="c-12"><Notice>{msg}</Notice></div>}
        </div>
      )}
    </Loadable>
  )
}

function SecUA({ initial }: { initial: string }) {
  const [v, setV] = useState(initial)
  const [ok, setOk] = useState(false)
  return (
    <div className="row">
      <input className="input" style={{ flex: 1 }} value={v} onChange={(e) => setV(e.target.value)} aria-label="SEC user agent" />
      <button className="btn" onClick={async () => { await api.put('/settings', { env: { SEC_USER_AGENT: v } }); setOk(true) }}>{ok ? 'Saved' : 'Save'}</button>
      <span className="muted xs" style={{ maxWidth: 360 }}>The SEC asks automated clients to identify themselves (name + email) in the User-Agent.</span>
    </div>
  )
}

function AI() {
  const q = useApi('/settings')
  const [prov, setProv] = useState<string | null>(null)
  const [model, setModel] = useState<string | null>(null)
  const [ollama, setOllama] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  return (
    <Loadable q={q} skeleton={<SkelRows />}>
      {(d) => {
        const p = prov ?? d.ai.configured_choice
        return (
          <div className="grid">
            <div className="c-6">
              <Panel title="AI provider" sub={d.ai.active ? `Active: ${d.ai.active} · ${d.ai.model}` : 'No provider active — offline analyst mode'}>
                <div className="col" style={{ gap: 10 }}>
                  <Seg value={p} options={[['auto', 'Auto'], ['anthropic', 'Anthropic'], ['openai', 'OpenAI'], ['ollama', 'Ollama'], ['none', 'Off']]} onChange={setProv} />
                  <label className="field">Model override (blank = provider default)
                    <input className="input mono" placeholder={d.ai.providers.find((x: any) => x.id === (p === 'auto' ? d.ai.active || 'anthropic' : p))?.default_model || ''} value={model ?? d.env.AI_MODEL ?? ''} onChange={(e) => setModel(e.target.value)} />
                  </label>
                  {p === 'ollama' && <label className="field">Ollama base URL<input className="input mono" value={ollama ?? d.env.OLLAMA_BASE_URL ?? ''} onChange={(e) => setOllama(e.target.value)} /></label>}
                  <table className="t compact"><tbody>{d.ai.providers.map((x: any) => <tr key={x.id}><td>{x.id}</td><td className="mono muted">{x.default_model}</td><td>{x.available ? <span className="badge ok">ready</span> : <span className="badge">not configured</span>}</td></tr>)}</tbody></table>
                  <button className="btn primary" onClick={async () => {
                    try { await api.put('/settings', { env: { AI_PROVIDER: p, AI_MODEL: model ?? d.env.AI_MODEL ?? '', ...(ollama !== null ? { OLLAMA_BASE_URL: ollama } : {}) } }); setMsg('Saved.'); q.refetch() } catch (e: any) { setMsg(e.message) }
                  }}>Save AI settings</button>
                  {msg && <span className="small muted">{msg}</span>}
                  <div className="muted xs">Anthropic uses the official SDK with <span className="mono">claude-opus-5</span> by default, adaptive thinking and server-side refusal fallbacks. API keys are set under “Data providers &amp; keys”.</div>
                </div>
              </Panel>
            </div>
            <div className="c-6">
              <Panel title="Web research agents">
                {d.agents.map((a: any) => (
                  <div key={a.id} className="row" style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
                    <StatusDot status={a.available ? 'online' : 'idle'} />
                    <div style={{ flex: 1 }}><b>{a.label}</b>{a.note && <div className="muted xs">{a.note}</div>}</div>
                    <span className={`badge ${a.available ? 'ok' : ''}`}>{a.available ? 'available' : 'not configured'}</span>
                  </div>
                ))}
                <div className="muted xs" style={{ marginTop: 8 }}>The TinyFish adapter uses the official REST endpoints (Search, Fetch, Agent), is rate-limited and cached, records source URL and retrieval time for every result, and never attempts to bypass logins, paywalls, CAPTCHAs or robots rules.</div>
              </Panel>
            </div>
          </div>
        )
      }}
    </Loadable>
  )
}

function Prefs() {
  const { theme, setTheme, setSetupOpen } = useApp()
  const q = useApi('/settings')
  const lists = useApi<any[]>('/watchlists')
  const [saved, setSaved] = useState(false)
  const set = async (prefs: Record<string, unknown>) => { await api.put('/settings', { preferences: prefs }); setSaved(true); q.refetch(); setTimeout(() => setSaved(false), 1500) }
  return (
    <Loadable q={q} skeleton={<SkelRows />}>
      {(d) => {
        const p = d.preferences
        return (
          <Panel title="Preferences" actions={saved && <span className="badge ok">Saved</span>}>
            <div className="col" style={{ gap: 14, maxWidth: 560 }}>
              <label className="field">Theme<Seg value={theme} options={[['dark', 'Dark'], ['light', 'Light'], ['system', 'System']]} onChange={(t) => setTheme(t as ThemeMode)} /></label>
              <label className="field">Default watchlist<select className="input" value={p.default_watchlist ?? ''} onChange={(e) => set({ default_watchlist: Number(e.target.value) })}>{(lists.data || []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
              <label className="field">Default market<select className="input" value={p.default_market} onChange={(e) => set({ default_market: e.target.value })}>{['US', 'Europe', 'Asia-Pacific', 'Global'].map((m) => <option key={m}>{m}</option>)}</select></label>
              <label className="field">Display currency<select className="input" value={p.currency} onChange={(e) => set({ currency: e.target.value })}>{['USD', 'EUR', 'GBP', 'JPY', 'INR'].map((m) => <option key={m}>{m}</option>)}</select></label>
              <label className="field">Timezone<select className="input" value={p.timezone} onChange={(e) => set({ timezone: e.target.value })}>{['local', 'America/New_York', 'Europe/London', 'Asia/Tokyo', 'Asia/Kolkata', 'UTC'].map((m) => <option key={m}>{m}</option>)}</select></label>
              <label className="field">Widget auto-refresh (seconds)<input className="input" type="number" min={15} value={p.auto_refresh_seconds} onChange={(e) => set({ auto_refresh_seconds: Number(e.target.value) })} /></label>
              <button className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => setSetupOpen(true)}>Re-run setup wizard</button>
              <div className="muted xs">Values are stored in the SQLite user_preferences table. Display currency conversion applies to portfolio totals in a future release; quotes are always shown in their native currency.</div>
            </div>
          </Panel>
        )
      }}
    </Loadable>
  )
}

function Cache() {
  const q = useApi('/settings')
  const r = useApi('/refresh/last')
  return (
    <div className="grid">
      <div className="c-6"><Panel title="Cache policy (config/app.json)" sub="TTL in seconds per data class">
        <Loadable q={q} skeleton={<SkelRows />}>{(d) => <table className="t compact"><tbody>{Object.entries(d.cache_ttl_seconds).map(([k, v]: any) => <tr key={k}><td className="mono">{k}</td><td className="num">{v}s</td><td className="muted xs">{v >= 3600 ? `${(v / 3600).toFixed(1)}h` : `${(v / 60).toFixed(1)}m`}</td></tr>)}</tbody></table>}</Loadable>
        <div className="muted xs" style={{ marginTop: 6 }}>Stale entries are served (and labeled stale) when a provider fails. Edit config/app.json and restart to change TTLs and per-host rate limits.</div>
      </Panel></div>
      <div className="c-6"><Panel title="Refresh history">
        <Loadable q={r} skeleton={<SkelRows />}>{(d) => <table className="t compact"><thead><tr><th>Started</th><th>Scope</th><th>Status</th><th className="num">Duration</th></tr></thead><tbody>
          {d.history.map((h: any) => <tr key={h.id}><td>{fmtDateTime(h.started_at)}</td><td className="mono xs">{h.scope}</td><td><span className={`badge ${h.status === 'completed' ? 'ok' : h.status === 'running' ? 'info' : 'warn'}`}>{h.status}</span></td><td className="num">{h.finished_at ? `${(h.finished_at - h.started_at).toFixed(1)}s` : '—'}</td></tr>)}
        </tbody></table>}</Loadable>
      </Panel></div>
    </div>
  )
}
