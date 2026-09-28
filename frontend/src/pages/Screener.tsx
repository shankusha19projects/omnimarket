import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Download, Loader2, Plus, Save, Trash2, X } from 'lucide-react'
import { api, downloadCsv } from '../services/api'
import { useApi, usePostApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { ChgPill, DataTable, Loadable, Notice, Panel, Seg, SkelRows } from '../components/ui'
import { assetPath, fmtBig, fmtNum, fmtPrice, fmtX } from '../services/format'

type F = { field: string; op: string; value: any; value2?: any }
const PRESETS: Record<string, F[]> = {
  'Quality growth': [{ field: 'roe', op: 'gt', value: 15 }, { field: 'revenue_growth', op: 'gt', value: 8 }, { field: 'operating_margin', op: 'gt', value: 15 }],
  'Value': [{ field: 'pe', op: 'between', value: 0.1, value2: 15 }, { field: 'pb', op: 'lt', value: 3 }],
  'Dividend payers': [{ field: 'dividend_yield', op: 'gt', value: 2.5 }],
  'Oversold (RSI<35)': [{ field: 'rsi14', op: 'lt', value: 35 }],
  'Momentum': [{ field: 'pct_vs_sma200', op: 'gt', value: 10 }, { field: 'perf_1m', op: 'gt', value: 3 }],
  'Mega caps': [{ field: 'market_cap', op: 'gt', value: 2e11 }],
}

export default function Screener() {
  const [filters, setFilters] = useState<F[]>([{ field: 'market_cap', op: 'gt', value: 1e10 }])
  const [universe, setUniverse] = useState('all')
  const [sort, setSort] = useState('market_cap')
  const [applied, setApplied] = useState<any>({ filters, universe, sort, desc: true, limit: 500 })
  const q = usePostApi('/screener', applied)
  const saved = useApi<any[]>('/screener/saved')
  const [loadingF, setLoadingF] = useState(false)
  const nav = useNavigate()
  const fields: Record<string, string> = q.data?.fields || {}
  const run = (f = filters, u = universe) => setApplied({ filters: f.filter((x) => x.field && (x.value !== '' || x.op === 'contains')), universe: u, sort, desc: true, limit: 500 })
  const upd = (i: number, patch: Partial<F>) => setFilters(filters.map((f, j) => (j === i ? { ...f, ...patch } : f)))
  const textField = (f: string) => ['sector', 'industry', 'country', 'symbol', 'name', 'group'].includes(f)
  return (
    <div className="page">
      <PageHead kicker="Discovery" title="Stock Screener" desc="AND-combined filters over valuation, growth, profitability, leverage and technical fields. Save screens and export results to CSV."
                actions={<Seg value={universe} options={[['all', 'All equities'], ['international', 'International'], ['critical_minerals', 'Critical minerals'], ['reits', 'REITs']]} onChange={(u) => { setUniverse(u); run(filters, u) }} />} />
      <div className="grid">
        <div className="c-3 col">
          <Panel title="Filters" actions={<button className="btn sm" onClick={() => setFilters([...filters, { field: 'pe', op: 'lt', value: 25 }])}><Plus size={12} /> Add</button>}>
            <div className="col" style={{ gap: 8 }}>
              {filters.map((f, i) => (
                <div key={i} className="col" style={{ gap: 4, padding: 8, border: '1px solid var(--line)', borderRadius: 8, background: 'var(--panel-2)' }}>
                  <div className="row" style={{ gap: 4 }}>
                    <select className="input sm" style={{ flex: 1 }} value={f.field} onChange={(e) => upd(i, { field: e.target.value, op: textField(e.target.value) ? 'contains' : 'gt' })} aria-label="Field">
                      {Object.entries(fields).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                    </select>
                    <button className="icon-btn sm ghost" onClick={() => setFilters(filters.filter((_, j) => j !== i))} aria-label="Remove filter"><X size={12} /></button>
                  </div>
                  <div className="row" style={{ gap: 4 }}>
                    <select className="input sm" value={f.op} onChange={(e) => upd(i, { op: e.target.value })} aria-label="Operator">
                      {(textField(f.field) ? [['contains', 'contains'], ['eq', '=']] : [['gt', '>'], ['gte', '≥'], ['lt', '<'], ['lte', '≤'], ['between', 'between']]).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                    </select>
                    <input className="input sm mono" style={{ flex: 1, minWidth: 0 }} value={f.value ?? ''} onChange={(e) => upd(i, { value: textField(f.field) ? e.target.value : e.target.value === '' ? '' : Number(e.target.value) })} aria-label="Value" />
                    {f.op === 'between' && <input className="input sm mono" style={{ flex: 1, minWidth: 0 }} value={f.value2 ?? ''} onChange={(e) => upd(i, { value2: Number(e.target.value) })} aria-label="Upper value" />}
                  </div>
                </div>
              ))}
              <select className="input sm" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort by">{Object.entries(fields).map(([k, l]) => <option key={k} value={k}>Sort: {l}</option>)}</select>
              <button className="btn primary" onClick={() => run()}>Run screen</button>
              <div className="muted xs">Percent fields use whole numbers (e.g. 15 = 15%). Market cap in dollars (1e10 = $10B).</div>
            </div>
          </Panel>
          <Panel title="Presets">
            <div className="chip-row">{Object.entries(PRESETS).map(([k, v]) => <button key={k} className="chip" onClick={() => { setFilters(v); run(v) }}>{k}</button>)}</div>
          </Panel>
          <Panel title="Saved screens" actions={<button className="btn sm" onClick={async () => { const name = prompt('Name this screen'); if (name) { await api.post('/screener/saved', { name, request: { filters, universe, sort, desc: true, limit: 500 } }); saved.refetch() } }}><Save size={12} /> Save</button>}>
            {(saved.data || []).length ? (saved.data || []).map((s) => (
              <div key={s.id} className="row small" style={{ padding: '4px 0' }}>
                <button className="btn ghost sm" style={{ flex: 1, justifyContent: 'flex-start' }} onClick={() => { setFilters(s.request.filters); setUniverse(s.request.universe); setApplied(s.request) }}>{s.name}</button>
                <button className="icon-btn sm ghost" onClick={async () => { await api.del(`/screener/saved/${s.id}`); saved.refetch() }} aria-label="Delete"><Trash2 size={12} /></button>
              </div>
            )) : <span className="muted small">None yet.</span>}
          </Panel>
        </div>
        <div className="c-9">
          <Panel title="Results" sub={q.data ? `${q.data.matched} of ${q.data.total} match · fundamentals coverage ${q.data.fundamentals_coverage}` : undefined} flush actions={<>
            <button className="btn sm" disabled={loadingF} onClick={async () => { setLoadingF(true); try { await api.post(`/screener/fundamentals?universe=${universe}`); q.refetch() } finally { setLoadingF(false) } }}>
              {loadingF ? <><Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> Loading…</> : 'Load fundamentals'}</button>
            <button className="btn sm" onClick={() => downloadCsv('/screener/export', applied, 'screen.csv')}><Download size={12} /> CSV</button>
          </>}>
            {q.data?.note && <div style={{ padding: '0 12px 8px' }}><Notice>{q.data.note}</Notice></div>}
            <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={14} /></div>}>
              {(d) => <DataTable rows={d.rows} onRow={(r) => nav(assetPath(r.symbol))} pageSize={50} initialSort={sort} cols={[
                { key: 'symbol', label: 'Symbol', render: (r) => <span className="sym">{r.symbol}</span> },
                { key: 'name', label: 'Name', render: (r) => <span className="nm" style={{ display: 'inline-block', maxWidth: 180 }}>{r.name}</span> },
                { key: 'sector', label: 'Sector', render: (r) => <span className="muted">{r.sector}</span> },
                { key: 'price', label: 'Price', num: true, render: (r) => fmtPrice(r.price) },
                { key: 'change_pct', label: '1D', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
                { key: 'market_cap', label: 'Mkt cap', num: true, render: (r) => fmtBig(r.market_cap, '$') },
                { key: 'pe', label: 'P/E', num: true, render: (r) => fmtX(r.pe) },
                { key: 'forward_pe', label: 'Fwd', num: true, render: (r) => fmtX(r.forward_pe) },
                { key: 'ev_ebitda', label: 'EV/EBITDA', num: true, render: (r) => fmtX(r.ev_ebitda) },
                { key: 'revenue_growth', label: 'Rev g', num: true, render: (r) => (r.revenue_growth != null ? `${fmtNum(r.revenue_growth, 1)}%` : '—') },
                { key: 'operating_margin', label: 'Op m', num: true, render: (r) => (r.operating_margin != null ? `${fmtNum(r.operating_margin, 1)}%` : '—') },
                { key: 'roe', label: 'ROE', num: true, render: (r) => (r.roe != null ? `${fmtNum(r.roe, 1)}%` : '—') },
                { key: 'debt_to_equity', label: 'D/E', num: true, render: (r) => fmtNum(r.debt_to_equity, 2) },
                { key: 'dividend_yield', label: 'Div', num: true, render: (r) => (r.dividend_yield != null ? `${fmtNum(r.dividend_yield, 2)}%` : '—') },
                { key: 'rsi14', label: 'RSI', num: true, render: (r) => fmtNum(r.rsi14, 0) },
                { key: 'pct_vs_sma200', label: 'vs 200D', num: true, render: (r) => <ChgPill v={r.pct_vs_sma200} digits={1} /> },
                { key: 'perf_ytd', label: 'YTD', num: true, render: (r) => <ChgPill v={r.perf_ytd} digits={1} /> },
              ]} />}
            </Loadable>
          </Panel>
        </div>
      </div>
    </div>
  )
}
