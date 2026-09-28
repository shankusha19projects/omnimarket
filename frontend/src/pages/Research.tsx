import { useState } from 'react'
import { Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, Globe, Loader2, Microscope, Printer, Search } from 'lucide-react'
import { api, exportJson } from '../services/api'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { AssetLink, Chg, ChgPill, Empty, ErrorState, Notice, Panel, Stat } from '../components/ui'
import { fmtBig, fmtDateTime, fmtNum, fmtPrice, timeAgo } from '../services/format'

const EXAMPLES = ['TSLA', 'US semiconductor industry', 'What is happening in copper?', 'Uranium and nuclear power', 'NVDA data center demand', 'Rare earth magnets supply chain']

export default function Research() {
  const [query, setQuery] = useState('')
  const [useWeb, setUseWeb] = useState(true)
  const [busy, setBusy] = useState(false)
  const [ws, setWs] = useState<any>(null)
  const [err, setErr] = useState<any>(null)
  const recent = useApi<any[]>('/research/recent')
  const settings = useApi('/settings')
  const tinyfish = settings.data?.agents?.find((a: any) => a.id === 'tinyfish')
  const run = async (q = query) => {
    if (!q.trim()) return
    setQuery(q); setBusy(true); setErr(null); setWs(null)
    try { setWs(await api.post('/research', { query: q, use_web_agent: useWeb, synthesize: true })); recent.refetch() } catch (e) { setErr(e) } finally { setBusy(false) }
  }
  return (
    <div className="page">
      <PageHead kicker="Research command center" title="Research" desc="Enter a ticker, industry or question. The workspace collects market data, fundamentals, SEC filings (incl. full-text search), macro context and news — optionally via the TinyFish web agent — then synthesizes a sourced brief." />
      <form className="panel" style={{ padding: 14, marginBottom: 12 }} onSubmit={(e) => { e.preventDefault(); run() }}>
        <div className="row">
          <Microscope size={18} color="var(--accent)" />
          <input className="input" style={{ flex: 1, height: 40, fontSize: 14 }} placeholder="e.g. TSLA · US semiconductor industry · What is happening in copper?" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Research query" />
          <label className="check" title={tinyfish?.available ? 'TinyFish Search & Fetch' : 'TinyFish not configured — falls back to keyless public sources'}>
            <input type="checkbox" checked={useWeb} onChange={(e) => setUseWeb(e.target.checked)} /> <Globe size={13} /> Web agent {tinyfish && <span className={`badge ${tinyfish.available ? 'ok' : ''}`}>{tinyfish.available ? 'TinyFish' : 'public fallback'}</span>}
          </label>
          <button className="btn primary" disabled={busy} style={{ height: 40 }}>{busy ? <><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Researching…</> : <><Search size={14} /> Research</>}</button>
        </div>
        <div className="chip-row" style={{ marginTop: 10 }}>{EXAMPLES.map((e) => <button type="button" key={e} className="chip" onClick={() => run(e)}>{e}</button>)}</div>
      </form>
      {busy && <Notice kind="info">Collecting quotes, statements, filings, macro context and web evidence in parallel… deep equity research typically takes 10–40 seconds on first load (cached afterwards).</Notice>}
      {err && <ErrorState error={err} retry={() => run()} />}
      {!ws && !busy && !err && (
        <Panel title="Recent research">
          {(recent.data || []).length ? (recent.data || []).map((r) => <div key={r.id} className="row small" style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}><button className="btn ghost sm" onClick={() => run(r.query)}>{r.query}</button><span className="spacer" /><span className="muted xs">{timeAgo(r.created_at)}</span></div>) : <Empty title="No research yet" icon={<Microscope size={22} />}>Try one of the examples above.</Empty>}
        </Panel>
      )}
      {ws && <Workspace ws={ws} />}
    </div>
  )
}

function Workspace({ ws }: { ws: any }) {
  const c = ws.compact
  return (
    <div className="grid fade-in">
      <div className="c-12 row wrap">
        <span className="muted small">Entities detected:</span>
        {ws.entities.map((s: string) => <AssetLink key={s} symbol={s} className="tag link">{s}</AssetLink>)}
        {ws.themes.map((t: string) => <span key={t} className="badge info">{t}</span>)}
        {ws.sectors.map((t: string) => <span key={t} className="badge">{t}</span>)}
        <span className="spacer" />
        <span className="muted xs">Assembled in {ws.elapsed}s</span>
        <button className="btn sm" onClick={() => window.print()}><Printer size={12} /> Print</button>
        <button className="btn sm" onClick={() => exportJson(ws, `research_${ws.query.replace(/\W+/g, '_')}.json`)}>Export JSON</button>
        {ws.primary && <Link className="btn sm" to={`/advisor?q=${encodeURIComponent(`Analyze ${ws.primary.symbol}`)}`}><Bot size={12} /> Continue in advisor</Link>}
      </div>
      <div className="c-8 col">
        <Panel title="Research brief" sub={ws.synthesis?.provider ? `Synthesized by ${ws.synthesis.provider} / ${ws.synthesis.model} from the sourced context below` : undefined} accent>
          {ws.synthesis?.text ? <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{ws.synthesis.text}</ReactMarkdown></div>
            : <Notice kind="warn">{ws.synthesis?.error ? `AI synthesis failed: ${ws.synthesis.error}` : ws.synthesis?.note || 'No AI provider configured.'} The sourced workspace below is complete; configure an AI provider in <Link to="/settings">Settings</Link> for a narrative brief.</Notice>}
        </Panel>
        {ws.report && (
          <Panel title="Structured analysis (deterministic)" sub={ws.report.engine}>
            {ws.report.sections.slice(0, 10).map((s: any) => (
              <div key={s.title} style={{ marginBottom: 10 }}>
                <div className="upper" style={{ color: 'var(--accent)' }}>{s.title}</div>
                <ul className="small" style={{ margin: '4px 0', paddingLeft: 18 }}>{s.facts.slice(0, 4).map((f: string, i: number) => <li key={i}>{f}</li>)}</ul>
                {s.interpretation.map((t: string, i: number) => <p key={i} className="small dim" style={{ fontStyle: 'italic' }}>{t}</p>)}
              </div>
            ))}
            <Link to={`/asset/${encodeURIComponent(ws.primary.symbol)}`} className="small">Open full analysis, valuation and filings →</Link>
          </Panel>
        )}
        <Panel title="Web & news evidence" sub={`Agent: ${ws.web?.agent || '—'}`}>
          {(ws.web?.notes || []).map((n: string, i: number) => <Notice key={i}>{n}</Notice>)}
          {(ws.web?.errors || []).map((n: string, i: number) => <div key={i} className="down xs">{n}</div>)}
          {(ws.web?.evidence || []).map((e: any, i: number) => (
            <article className="news-item" key={i}>
              <div style={{ minWidth: 0 }}>
                <a className="hl" href={e.url} target="_blank" rel="noreferrer noopener">{e.title}</a>
                {e.snippet && <div className="sum">{e.snippet}</div>}
                <div className="meta"><b>{e.publisher || new URL(e.url).host}</b><span>{e.published || ''}</span><span className="badge">{e.kind}</span><span className="muted xs">retrieved {fmtDateTime(e.retrieved_at)}</span></div>
              </div>
            </article>
          ))}
          {(ws.web_pages?.evidence || []).length > 0 && <div className="upper muted" style={{ marginTop: 10 }}>Fetched pages (TinyFish Fetch)</div>}
          {(ws.web_pages?.evidence || []).map((e: any, i: number) => <div key={i} className="small" style={{ padding: '4px 0' }}><a href={e.url} target="_blank" rel="noreferrer noopener">{e.title}</a> <span className="muted xs">· {(e.snippet || '').length} chars extracted</span></div>)}
        </Panel>
      </div>
      <div className="c-4 col">
        {c?.quote && (
          <Panel title={`${c.asset.name} (${c.asset.symbol})`} sub={c.quote.source}>
            <div className="row" style={{ alignItems: 'baseline', gap: 8 }}><span className="big-num" style={{ fontSize: 24 }}>{fmtPrice(c.quote.price)}</span><ChgPill v={c.quote.change_pct} /></div>
            <div className="stats" style={{ marginTop: 8, gridTemplateColumns: '1fr 1fr' }}>
              {Object.entries(c.performance || {}).map(([k, v]: any) => <Stat key={k} label={k.replace('perf_', '')} value={<Chg v={v} digits={1} />} />)}
            </div>
          </Panel>
        )}
        {ws.theme_rows?.map((t: any) => (
          <Panel key={t.id} title={`Theme: ${t.name}`}>
            {t.members.map((m: any) => <div key={m.symbol} className="row small" style={{ padding: '3px 0' }}><AssetLink symbol={m.symbol} className="mono">{m.symbol}</AssetLink><span className="muted truncate" style={{ flex: 1 }}>{m.name}</span><Chg v={m.change_pct} /></div>)}
          </Panel>
        ))}
        {ws.sector_rows?.map((s: any) => (
          <Panel key={s.sector} title={`Sector: ${s.sector}`}>
            <div className="stats" style={{ gridTemplateColumns: '1fr 1fr' }}><Stat label="1D" value={<Chg v={s.change_pct} />} /><Stat label="YTD" value={<Chg v={s.perf_ytd} digits={1} />} /><Stat label="Median P/E" value={fmtNum(s.median_pe, 1)} /><Stat label="Breadth" value={`${s.breadth_up}/${s.breadth_total}`} /></div>
          </Panel>
        ))}
        <Panel title="Macro context">
          {Object.entries(ws.macro || {}).map(([k, v]: any) => <div className="metric" key={k}><span className="k">{k.replace(/_/g, ' ')}</span><span className="v">{typeof v === 'number' ? (Math.abs(v) > 1000 ? fmtBig(v) : fmtNum(v, 2)) : String(v ?? '—')}</span></div>)}
        </Panel>
        <Panel title="SEC full-text search" sub="EDGAR FTS">
          {ws.filings_search_error && <div className="down xs">{ws.filings_search_error}</div>}
          {(ws.filings_search || []).map((f: any, i: number) => <div key={i} className="small" style={{ padding: '4px 0', borderBottom: '1px solid var(--line)' }}><span className="badge info">{f.form}</span> <a href={f.url} target="_blank" rel="noreferrer noopener">{f.company}</a> <span className="muted xs">{f.filed}</span></div>)}
          {!ws.filings_search?.length && !ws.filings_search_error && <span className="muted small">No matching filings.</span>}
        </Panel>
      </div>
    </div>
  )
}
