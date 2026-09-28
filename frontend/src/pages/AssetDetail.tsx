import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import type { IChartApi } from 'lightweight-charts'
import { Bot, Download, ExternalLink, FileText, Plus, Printer, RefreshCw, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useApi } from '../hooks/useApi'
import { useApp } from '../hooks/AppContext'
import { api, exportJson, exportRowsCsv, saveBlob } from '../services/api'
import { PriceChart, type Overlay } from '../charts/PriceChart'
import { EChart, chartColors } from '../charts/EChart'
import { barOption, donutOption, lineOption } from '../charts/builders'
import { QuoteHeaderStats } from '../components/widgets'
import { AssetLink, Chg, ChgPill, DataTable, Empty, ErrorState, Loadable, MarketState, Notice, Panel, Prov, Seg, Skel, SkelRows, Stat, Tabs } from '../components/ui'
import { assetPath, fmtBig, fmtDate, fmtDateTime, fmtNum, fmtPct, fmtPrice, fmtRatioPct, fmtX, isNum, timeAgo } from '../services/format'

type Tab = 'overview' | 'financials' | 'fundamentals' | 'analysis' | 'valuation' | 'filings' | 'news' | 'timeline' | 'profile' | 'holdings'
const RANGES: [string, string][] = [['1d', '1D'], ['5d', '5D'], ['1mo', '1M'], ['3mo', '3M'], ['6mo', '6M'], ['ytd', 'YTD'], ['1y', '1Y'], ['3y', '3Y'], ['5y', '5Y'], ['max', 'MAX']]
const OVERLAYS: [Overlay, string][] = [['volume', 'Volume'], ['sma20', 'SMA 20'], ['sma50', 'SMA 50'], ['sma200', 'SMA 200'], ['ema12', 'EMA 12'], ['ema26', 'EMA 26'], ['bb', 'Bollinger'], ['rsi', 'RSI'], ['macd', 'MACD']]

export default function AssetDetail() {
  const { symbol: raw = '' } = useParams()
  const symbol = decodeURIComponent(raw)
  const { setCurrentAsset, startRefresh } = useApp()
  useEffect(() => { setCurrentAsset(symbol); return () => setCurrentAsset(null) }, [symbol, setCurrentAsset])
  const q = useApi(`/assets/${encodeURIComponent(symbol)}`, { refetch: 45_000 })
  const [tab, setTab] = useState<Tab>('overview')
  useEffect(() => setTab('overview'), [symbol])
  const asset = q.data?.asset
  const quote = q.data?.quote
  const cls = asset?.asset_class
  const isEquity = cls === 'equity'

  if (q.error && !q.data) return <div className="page"><ErrorState error={q.error} retry={() => q.refetch()} /></div>
  const tabs: [Tab, string][] = [['overview', 'Overview']]
  if (isEquity) tabs.push(['financials', 'Financials'], ['fundamentals', 'Fundamentals'], ['analysis', 'Analysis'], ['valuation', 'Valuation'], ['filings', 'SEC filings'])
  if (cls === 'etf') tabs.push(['holdings', 'Holdings & exposure'])
  tabs.push(['news', 'News'])
  if (isEquity) tabs.push(['timeline', 'Timeline'], ['profile', 'Company'])

  return (
    <div className="page">
      <div className="page-head" style={{ alignItems: 'center' }}>
        <div style={{ minWidth: 0 }}>
          <div className="page-kicker">{asset ? `${asset.asset_class}${asset.sector ? ` · ${asset.sector}` : ''}${asset.industry ? ` · ${asset.industry}` : ''}` : 'Loading'}</div>
          <div className="row" style={{ gap: 12, alignItems: 'baseline', flexWrap: 'wrap' }}>
            <h1 className="page-title">{asset?.name || symbol}</h1>
            <span className="mono muted" style={{ fontSize: 14 }}>{symbol}</span>
            {quote?.exchange && <span className="badge">{quote.exchange}</span>}
            <MarketState state={quote?.market_state} />
          </div>
        </div>
        <div className="row" style={{ gap: 14, alignItems: 'baseline', marginLeft: 20 }}>
          {q.isLoading ? <Skel h={34} w={200} /> : quote?.unavailable ? <Notice kind="warn">Quote unavailable: {quote?.provenance?.error}</Notice> : <>
            <span className="big-num">{fmtPrice(quote?.price)}</span>
            <span className="col" style={{ gap: 2 }}>
              <Chg v={quote?.change} pct={false} className="small" />
              <ChgPill v={quote?.change_pct} />
            </span>
            <span className="muted xs">{quote?.currency}<br />{quote?.market_time ? fmtDateTime(quote.market_time) : ''}</span>
          </>}
        </div>
        <div className="page-actions">
          {quote?.provenance && <Prov p={quote.provenance} />}
          <AddToWatchlist symbol={symbol} />
          <Link className="btn" to={`/advisor?q=${encodeURIComponent(`Analyze ${symbol}`)}`}><Bot size={14} /> Ask advisor</Link>
          <Link className="btn" to={`/analytics?symbols=${encodeURIComponent(symbol)},^GSPC`}>Compare</Link>
          <button className="btn" onClick={() => startRefresh(['asset'], symbol)} title="Refresh this asset from providers"><RefreshCw size={14} /></button>
        </div>
      </div>
      <Tabs value={tab} options={tabs} onChange={setTab} />
      {tab === 'overview' && <Overview symbol={symbol} quote={quote} asset={asset} />}
      {tab === 'financials' && <Financials symbol={symbol} />}
      {tab === 'fundamentals' && <Fundamentals symbol={symbol} />}
      {tab === 'analysis' && <Analysis symbol={symbol} />}
      {tab === 'valuation' && <Valuation symbol={symbol} />}
      {tab === 'filings' && <Filings symbol={symbol} name={asset?.name} />}
      {tab === 'news' && <AssetNews symbol={symbol} />}
      {tab === 'timeline' && <Timeline symbol={symbol} />}
      {tab === 'profile' && <Profile symbol={symbol} />}
      {tab === 'holdings' && <Holdings symbol={symbol} />}
    </div>
  )
}

function AddToWatchlist({ symbol }: { symbol: string }) {
  const lists = useApi<any[]>('/watchlists')
  const [open, setOpen] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  return (
    <div style={{ position: 'relative' }}>
      <button className="btn" onClick={() => setOpen(!open)}><Plus size={14} /> {msg || 'Watchlist'}</button>
      {open && <div className="menu">{(lists.data || []).map((l) => (
        <button key={l.id} onClick={async () => { await api.post(`/watchlists/${l.id}/items`, { symbol }); setOpen(false); setMsg(`Added to ${l.name}`); lists.refetch() }}>
          {l.symbols.includes(symbol) ? '✓ ' : ''}{l.name}
        </button>
      ))}</div>}
    </div>
  )
}

/* ---------------- Overview: chart + stats + technicals ---------------- */
function Overview({ symbol, quote, asset }: { symbol: string; quote: any; asset: any }) {
  const [range, setRange] = useState('1y')
  const [type, setType] = useState<'candle' | 'ohlc' | 'line'>('candle')
  const [ov, setOv] = useState<Overlay[]>(['volume', 'sma50', 'sma200'])
  const h = useApi(`/assets/${encodeURIComponent(symbol)}/history?range=${range}`, { refetch: range === '1d' ? 60_000 : undefined })
  const tech = useApi(`/assets/${encodeURIComponent(symbol)}/technicals`)
  const chartRef = useRef<IChartApi | null>(null)
  const curve = useApi(asset?.asset_class === 'commodity' ? `/assets/${encodeURIComponent(symbol)}/curve` : null)
  const toggle = (o: Overlay) => setOv(ov.includes(o) ? ov.filter((x) => x !== o) : [...ov, o])
  const data = h.data
  const bars = useMemo(() => data?.bars || [], [data])
  return (
    <div className="grid">
      <div className="c-9" style={{ minWidth: 0 }}>
        <Panel title="Price chart" accent prov={data?.provenance} actions={<>
          <Seg value={type} options={[['candle', 'Candles'], ['ohlc', 'OHLC'], ['line', 'Line']]} onChange={setType} />
          <Seg value={range} options={RANGES} onChange={setRange} />
          <button className="icon-btn sm ghost" title="Export PNG" onClick={() => { const c = chartRef.current?.takeScreenshot(); c?.toBlob((b) => b && saveBlob(b, `${symbol}_${range}.png`)) }}><Download size={14} /></button>
          <button className="icon-btn sm ghost" title="Export CSV" onClick={() => exportRowsCsv(bars.map((b: any) => ({ date: new Date(b.t * 1000).toISOString(), open: b.o, high: b.h, low: b.l, close: b.c, volume: b.v })), `${symbol}_${range}.csv`)}><FileText size={14} /></button>
        </>}>
          <div className="chip-row" style={{ marginBottom: 8 }}>
            {OVERLAYS.map(([k, l]) => <button key={k} className={`chip ${ov.includes(k) ? 'on' : ''}`} onClick={() => toggle(k)}>{l}</button>)}
          </div>
          {h.isLoading ? <Skel h={520} /> : h.error ? <ErrorState error={h.error} retry={() => h.refetch()} /> : bars.length ? (
            <PriceChart bars={bars} indicators={data?.indicators} type={type} overlays={ov} height={ov.includes('rsi') || ov.includes('macd') ? 600 : 500}
                        intraday={range === '1d' || range === '5d' || range === '1mo'} onReady={(c) => { chartRef.current = c }} />
          ) : <Empty title="No price history for this range" />}
          {bars.length > 1 && <div className="row small muted" style={{ marginTop: 8, flexWrap: 'wrap' }}>
            <span>Period return: <Chg v={(bars[bars.length - 1].c / bars[0].c - 1) * 100} /></span>
            <span>High {fmtPrice(Math.max(...bars.map((b: any) => b.h ?? b.c)))}</span>
            <span>Low {fmtPrice(Math.min(...bars.map((b: any) => b.l ?? b.c)))}</span>
            <span>{bars.length} bars · zoom with wheel, drag to pan</span>
          </div>}
        </Panel>
      </div>
      <div className="c-3 col" style={{ minWidth: 0 }}>
        <Panel title="Quote">{quote ? <QuoteHeaderStats q={quote} /> : <SkelRows />}</Panel>
        <Panel title="Technical picture" prov={tech.data?.provenance}>
          <Loadable q={tech} skeleton={<SkelRows n={6} />}>
            {(t) => t.available ? (
              <div className="col" style={{ gap: 8 }}>
                <div className="stats" style={{ gridTemplateColumns: '1fr 1fr' }}>
                  <Stat label="RSI 14" value={<span className={t.rsi14 >= 70 ? 'down' : t.rsi14 <= 30 ? 'up' : ''}>{fmtNum(t.rsi14, 1)}</span>} />
                  <Stat label="RV 20d" value={`${fmtNum(t.realized_vol_20d, 1)}%`} />
                  <Stat label="vs 50-DMA" value={<Chg v={(t.price / t.sma50 - 1) * 100} digits={1} />} />
                  <Stat label="vs 200-DMA" value={<Chg v={t.sma200 ? (t.price / t.sma200 - 1) * 100 : null} digits={1} />} />
                  <Stat label="MACD" value={fmtNum(t.macd, 2)} sub={`signal ${fmtNum(t.macd_signal, 2)}`} />
                  <Stat label="ATR 14" value={fmtPrice(t.atr14)} />
                </div>
                {t.interpretation.map((s: string, i: number) => <p key={i} className="small dim" style={{ lineHeight: 1.5 }}>{s}</p>)}
              </div>
            ) : <div className="muted small">{t.reason}</div>}
          </Loadable>
        </Panel>
      </div>
      {curve.data?.available && (
        <div className="c-6">
          <Panel title={`${curve.data.name} futures curve`} sub={curve.data.shape} prov={curve.data.provenance}>
            <EChart height={240} deps={[curve.data]} option={() => lineOption([{ name: 'Settlement', data: curve.data.points.map((p: any) => [p.label, p.price]), area: true }], { timeAxis: false })} />
          </Panel>
        </div>
      )}
      <div className="c-12"><AssetNews symbol={symbol} compact /></div>
    </div>
  )
}

/* ---------------- Financial statements ---------------- */
function Financials({ symbol }: { symbol: string }) {
  const q = useApi(`/assets/${encodeURIComponent(symbol)}/statements`)
  const [stmt, setStmt] = useState<'income' | 'balance' | 'cashflow'>('income')
  const [period, setPeriod] = useState<'annual' | 'quarterly' | 'ttm'>('annual')
  return (
    <Loadable q={q} skeleton={<Skel h={500} />}>
      {(d) => {
        if (!d.available) return <Notice kind="warn">{d.reason}</Notice>
        const keys: string[] = d.layout[stmt]
        const cols: any[] = period === 'ttm' ? [{ period_end: `TTM to ${d.ttm.period_end || '—'}`, ...d.ttm }] : d[period]
        const chartKey = stmt === 'income' ? 'revenue' : stmt === 'balance' ? 'total_assets' : 'free_cash_flow'
        const series = [...(period === 'ttm' ? d.annual : d[period])].reverse()
        return (
          <div className="grid">
            <div className="c-12">
              <Panel title={`${d.entity || symbol} — ${stmt === 'income' ? 'Income statement' : stmt === 'balance' ? 'Balance sheet' : 'Cash flow'}`} prov={d.provenance}
                     sub={`SEC EDGAR XBRL · CIK ${d.cik} · values in USD${period === 'quarterly' ? ' · Q4 derived as FY − Q1..Q3 where needed' : ''}`}
                     actions={<>
                       <Seg value={stmt} options={[['income', 'Income'], ['balance', 'Balance sheet'], ['cashflow', 'Cash flow']]} onChange={setStmt} />
                       <Seg value={period} options={[['annual', 'Annual'], ['quarterly', 'Quarterly'], ['ttm', 'TTM']]} onChange={setPeriod} />
                       <button className="icon-btn sm ghost" title="Export CSV" onClick={() => exportRowsCsv(keys.map((k) => ({ item: d.labels[k] || k, ...Object.fromEntries(cols.map((c) => [c.period_end, c[k]])) })), `${symbol}_${stmt}_${period}.csv`)}><FileText size={14} /></button>
                     </>} flush>
                <div className="table-wrap">
                  <table className="t">
                    <thead><tr><th>Item</th>{cols.map((c) => <th key={c.period_end} className="num">{c.fiscal_year && period === 'annual' ? `FY${c.fiscal_year}` : c.period_end}</th>)}</tr></thead>
                    <tbody>{keys.map((k) => (
                      <tr key={k}><td style={{ fontWeight: ['revenue', 'net_income', 'operating_income', 'free_cash_flow', 'total_assets', 'equity'].includes(k) ? 600 : 400 }}>{d.labels[k] || k}</td>
                        {cols.map((c) => <td key={c.period_end} className="num">{k.startsWith('eps') ? fmtNum(c[k], 2) : k.includes('shares') ? fmtBig(c[k]) : fmtBig(c[k])}</td>)}</tr>
                    ))}</tbody>
                  </table>
                </div>
              </Panel>
            </div>
            <div className="c-6"><Panel title={`${d.labels[chartKey]} trend`}><EChart height={260} deps={[d, period, stmt]} option={() => barOption(series.map((r: any) => r.period_end.slice(0, 7)), series.map((r: any) => r[chartKey] ?? null), { format: (v) => fmtBig(v), colorBySign: chartKey === 'free_cash_flow' })} /></Panel></div>
            <div className="c-6"><Panel title="Margins">
              <EChart height={260} deps={[d, period]} option={() => lineOption(['gross_profit', 'operating_income', 'net_income'].map((k) => ({
                name: d.labels[k].replace(' income', ' margin').replace('Gross profit', 'Gross margin'), data: series.filter((r: any) => r.revenue).map((r: any) => [r.period_end.slice(0, 7), r[k] != null ? (r[k] / r.revenue) * 100 : null]) as any,
              })), { timeAxis: false, yFormat: (v) => `${v.toFixed(0)}%` })} />
            </Panel></div>
          </div>
        )
      }}
    </Loadable>
  )
}

/* ---------------- Fundamentals ---------------- */
function fmtMetric(m: any) {
  if (!m || m.value === null || m.value === undefined) return '—'
  switch (m.kind) {
    case 'money': return fmtBig(m.value, '$')
    case 'pct': return fmtRatioPct(m.value, 1)
    case 'multiple': return fmtX(m.value)
    case 'per_share': return `$${fmtNum(m.value, 2)}`
    case 'count': return fmtBig(m.value)
    default: return fmtNum(m.value, 2)
  }
}

function Fundamentals({ symbol }: { symbol: string }) {
  const q = useApi(`/assets/${encodeURIComponent(symbol)}/fundamentals`)
  return (
    <Loadable q={q} skeleton={<SkelRows n={14} />}>
      {(d) => (
        <div className="grid">
          {!d.sec_available && <div className="c-12"><Notice kind="warn">SEC XBRL statements unavailable for this issuer; metrics fall back to the Yahoo-compatible provider where possible.</Notice></div>}
          {Object.entries(d.groups).map(([g, keys]: any) => (
            <div className="c-6" key={g}>
              <Panel title={g} prov={g === 'Valuation' ? d.quote_provenance : d.statements_provenance}>
                <div className="metric-grid" style={{ gridTemplateColumns: '1fr' }}>
                  {keys.map((k: string) => {
                    const m = d.metrics[k]
                    return (
                      <div className="metric" key={k} title={m?.formula}>
                        <span className="k">{labelFor(k)}</span>
                        <span><span className="v">{fmtMetric(m)}</span>{m?.source && <span className="src">{m.source.includes('SEC') ? 'SEC' : 'YF'}</span>}</span>
                      </div>
                    )
                  })}
                </div>
              </Panel>
            </div>
          ))}
          <div className="c-12 muted xs">Hover a metric for its formula. “SEC” = computed locally from SEC XBRL filings; “YF” = Yahoo-compatible key statistics. TTM = trailing four reported quarters.</div>
        </div>
      )}
    </Loadable>
  )
}

const LABELS: Record<string, string> = {
  market_cap: 'Market cap', enterprise_value: 'Enterprise value', revenue: 'Revenue', ebitda: 'EBITDA', operating_income: 'Operating income', net_income: 'Net income', eps: 'EPS (diluted)',
  free_cash_flow: 'Free cash flow', cash: 'Cash & ST investments', debt: 'Total debt', net_debt: 'Net debt', pe: 'P/E (TTM)', forward_pe: 'Forward P/E', peg: 'PEG', ps: 'P/S', pb: 'P/B',
  ev_sales: 'EV/Sales', ev_ebitda: 'EV/EBITDA', fcf_yield: 'FCF yield', dividend_yield: 'Dividend yield', gross_margin: 'Gross margin', operating_margin: 'Operating margin',
  net_margin: 'Net margin', fcf_margin: 'FCF margin', roa: 'ROA', roe: 'ROE', roic: 'ROIC', cash_conversion: 'Cash conversion (OCF/NI)', revenue_growth: 'Revenue growth (FY)',
  eps_growth: 'EPS growth (FY)', fcf_growth: 'FCF growth (FY)', revenue_cagr_3y: 'Revenue CAGR 3Y', eps_cagr_3y: 'EPS CAGR 3Y', fcf_cagr_3y: 'FCF CAGR 3Y', current_ratio: 'Current ratio',
  quick_ratio: 'Quick ratio', debt_to_equity: 'Debt / equity', net_debt_to_ebitda: 'Net debt / EBITDA', interest_coverage: 'Interest coverage', beta: 'Beta (5Y)',
  short_percent_float: 'Short % of float', held_institutions: 'Institutional ownership', held_insiders: 'Insider ownership', shares_outstanding: 'Shares outstanding',
}
const labelFor = (k: string) => LABELS[k] || k

/* ---------------- Analysis report ---------------- */
function Analysis({ symbol }: { symbol: string }) {
  const q = useApi(`/assets/${encodeURIComponent(symbol)}/analysis`, { staleTime: 300_000 })
  return (
    <Loadable q={q} skeleton={<SkelRows n={16} />}>
      {(r) => (
        <div className="grid" id="report" style={{ gridAutoFlow: "row dense" }}>
          <div className="c-12">
            <Notice kind="info">
              <b>{r.engine}.</b> Facts are sourced from retrieved data; interpretations are hedged. For narrative synthesis, open the <Link to={`/advisor?q=${encodeURIComponent(`Analyze ${symbol}`)}`}>AI advisor</Link>.
              <span className="row" style={{ marginTop: 6, gap: 6 }}>
                <button className="btn sm" onClick={() => window.print()}><Printer size={12} /> Print report</button>
                <button className="btn sm" onClick={() => exportJson(r, `${symbol}_analysis.json`)}><Download size={12} /> JSON</button>
                <span className="muted xs">Generated {fmtDateTime(r.generated_at)}</span>
              </span>
            </Notice>
          </div>
          {r.sections.map((s: any) => (
            <div className={s.facts.join(' ').length > 600 ? 'c-12' : 'c-6'} key={s.title}>
              <Panel title={s.title}>
                <ul style={{ margin: 0, paddingLeft: 18 }} className="small">{s.facts.map((f: string, i: number) => <li key={i} style={{ margin: '4px 0', lineHeight: 1.55 }}>{/^https?:/.test(f) ? <a href={f}>{f}</a> : f}</li>)}</ul>
                {s.interpretation.length > 0 && <div style={{ marginTop: 10, padding: '8px 10px', borderLeft: '2px solid var(--violet)', background: 'var(--panel-2)', borderRadius: '0 6px 6px 0' }}>
                  <div className="upper" style={{ color: 'var(--violet)', marginBottom: 4 }}>Interpretation</div>
                  {s.interpretation.map((t: string, i: number) => <p key={i} className="small dim" style={{ margin: '3px 0', lineHeight: 1.55 }}>{t}</p>)}
                </div>}
                {s.sources.filter(Boolean).length > 0 && <div className="xs muted" style={{ marginTop: 8 }}>Sources: {s.sources.filter(Boolean).map((u: string, i: number) => /^https?:/.test(u) ? <a key={i} href={u} target="_blank" rel="noreferrer noopener" style={{ marginRight: 8 }}>[{i + 1}]</a> : <span key={i} style={{ marginRight: 8 }}>{u}</span>)}</div>}
              </Panel>
            </div>
          ))}
          <div className="c-12"><Scenarios s={r.scenarios} /></div>
          {r.data_errors?.length > 0 && <div className="c-12"><Notice kind="warn">Data gaps: {r.data_errors.join('; ')}</Notice></div>}
          <div className="c-12 muted xs">{r.disclaimer}</div>
        </div>
      )}
    </Loadable>
  )
}

function Scenarios({ s }: { s: any }) {
  if (!s?.available) return <Panel title="Scenario analysis"><div className="muted">{s?.reason || 'Unavailable'}</div></Panel>
  return (
    <Panel title="Scenario analysis" sub={s.note}>
      <div className="grid">
        {(['bull', 'base', 'bear'] as const).map((k) => {
          const c = s.cases[k]
          return (
            <div className="c-4" key={k}>
              <div className={`scenario ${k}`}>
                <div className="row"><b style={{ textTransform: 'capitalize' }}>{k} scenario</b><span className="spacer" /><span className="mono">{fmtPrice(c.value_per_share)}</span><Chg v={c.vs_price_pct} digits={0} /></div>
                <p className="small dim" style={{ margin: '6px 0 10px', lineHeight: 1.5 }}>{c.narrative}</p>
                <div className="metric-grid" style={{ gridTemplateColumns: '1fr' }}>
                  {Object.entries(c.assumptions).map(([ak, av]: any) => <div className="metric" key={ak}><span className="k">{ak.replace(/_/g, ' ')}</span><span className="v">{fmtRatioPct(av, 1)}</span></div>)}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </Panel>
  )
}

/* ---------------- Valuation: DCF + sensitivity + comps ---------------- */
function Valuation({ symbol }: { symbol: string }) {
  const base = useApi(`/assets/${encodeURIComponent(symbol)}/valuation`, { staleTime: 600_000 })
  const comps = useApi(`/assets/${encodeURIComponent(symbol)}/comparables`, { staleTime: 600_000 })
  const [inputs, setInputs] = useState<any>(null)
  const [res, setRes] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => { if (base.data?.available) { setInputs(base.data.inputs); setRes(base.data) } }, [base.data])
  const run = async () => {
    setBusy(true)
    try { setRes(await api.post('/valuation/dcf', { symbol, ...inputs })) } finally { setBusy(false) }
  }
  if (base.isLoading) return <SkelRows n={12} />
  if (base.error) return <ErrorState error={base.error} />
  if (!base.data?.available) return <Notice kind="warn">{base.data?.reason}</Notice>
  const fields: [string, string, 'pct' | 'num' | 'money'][] = [['revenue_growth', 'Revenue growth (stage 1)', 'pct'], ['growth_years', 'Explicit years', 'num'], ['operating_margin', 'Operating margin', 'pct'],
    ['tax_rate', 'Tax rate', 'pct'], ['reinvestment_rate', 'Reinvestment rate', 'pct'], ['wacc', 'WACC', 'pct'], ['terminal_growth', 'Terminal growth', 'pct'], ['shares', 'Share count', 'money'], ['net_debt', 'Net debt ($)', 'money']]
  return (
    <div className="grid">
      <div className="c-4">
        <Panel title="DCF assumptions" sub="Edit and re-run. Defaults derived from SEC filings." prov={base.data.provenance}>
          <div className="col" style={{ gap: 8 }}>
            {inputs && fields.map(([k, l, kind]) => (
              <label className="field" key={k}>{l}
                <input className="input mono" type="number" step={kind === 'pct' ? 0.5 : kind === 'num' ? 1 : 1e6}
                       value={kind === 'pct' ? +(inputs[k] * 100).toFixed(3) : inputs[k] ?? ''}
                       onChange={(e) => setInputs({ ...inputs, [k]: kind === 'pct' ? Number(e.target.value) / 100 : Number(e.target.value) })} />
              </label>
            ))}
            <button className="btn primary" onClick={run} disabled={busy}>{busy ? 'Running…' : 'Run DCF'}</button>
            <div className="muted xs">{base.data.notes?.[0] || 'NOPAT = revenue × margin × (1 − tax); FCFF = NOPAT × (1 − reinvestment). Gordon-growth terminal value.'}</div>
          </div>
        </Panel>
      </div>
      <div className="c-8 col">
        {res?.available && <>
          <Panel title="DCF output" sub={res.disclaimer} accent>
            <div className="stats">
              <Stat label="Value / share" value={fmtPrice(res.result.per_share)} sub={<>vs price {fmtPrice(res.price)}</>} />
              <Stat label="Implied vs price" value={<Chg v={res.upside_pct} digits={1} />} />
              <Stat label="Enterprise value" value={fmtBig(res.result.enterprise_value, '$')} />
              <Stat label="Equity value" value={fmtBig(res.result.equity_value, '$')} />
              <Stat label="Terminal % of EV" value={fmtRatioPct(res.result.terminal_share_of_ev, 0)} />
              <Stat label="Reverse DCF growth" value={isNum(res.reverse_dcf_growth) ? fmtRatioPct(res.reverse_dcf_growth, 1) : 'n/a'} sub="growth priced in" />
            </div>
            <div className="table-wrap" style={{ marginTop: 10 }}>
              <table className="t compact">
                <thead><tr><th>Year</th><th className="num">Growth</th><th className="num">Revenue</th><th className="num">NOPAT</th><th className="num">FCFF</th><th className="num">PV</th></tr></thead>
                <tbody>{res.result.rows.map((r: any) => <tr key={r.year}><td>Y{r.year}</td><td className="num">{fmtRatioPct(r.growth, 1)}</td><td className="num">{fmtBig(r.revenue)}</td><td className="num">{fmtBig(r.nopat)}</td><td className="num">{fmtBig(r.fcff)}</td><td className="num">{fmtBig(r.pv)}</td></tr>)}</tbody>
              </table>
            </div>
          </Panel>
          <Panel title="Sensitivity — value per share" sub="WACC (rows) × terminal growth (columns)">
            <div className="table-wrap">
              <table className="t compact sens">
                <thead><tr><th>WACC \ g</th>{res.sensitivity.terminal_growth.map((g: number) => <th key={g} className="num">{fmtRatioPct(g, 1)}</th>)}</tr></thead>
                <tbody>{res.sensitivity.grid.map((row: any[], i: number) => (
                  <tr key={i}><td className="mono">{fmtRatioPct(res.sensitivity.wacc[i], 1)}</td>
                    {row.map((v, j) => <td key={j} className={`num ${i === 2 && j === 2 ? 'hl' : ''}`} style={{ color: isNum(v) && res.price ? (v > res.price ? 'var(--up)' : 'var(--down)') : undefined }}>{fmtPrice(v)}</td>)}</tr>
                ))}</tbody>
              </table>
            </div>
          </Panel>
        </>}
      </div>
      <div className="c-6">
        <Panel title="Comparable valuation" sub={comps.data?.method} flush>
          <Loadable q={comps} skeleton={<div style={{ padding: 14 }}><SkelRows /></div>}>
            {(c) => <>
              <DataTable compact rows={[{ symbol, name: 'Target', ...c.target }, ...c.peers]} cols={[
                { key: 'symbol', label: 'Company', render: (r) => <span><AssetLink symbol={r.symbol} className="sym">{r.symbol}</AssetLink> <span className="muted xs">{r.name}</span></span> },
                { key: 'market_cap', label: 'Mkt cap', num: true, render: (r) => fmtBig(r.market_cap, '$') },
                { key: 'pe', label: 'P/E', num: true, render: (r) => fmtX(r.pe) }, { key: 'forward_pe', label: 'Fwd P/E', num: true, render: (r) => fmtX(r.forward_pe) },
                { key: 'pb', label: 'P/B', num: true, render: (r) => fmtX(r.pb) },
              ]} />
              <div style={{ padding: 12 }} className="col">
                {Object.entries(c.implied || {}).map(([k, v]: any) => <div key={k} className="metric"><span className="k">Peer median {k.toUpperCase()} {fmtX(v.peer_median)} × target {k === 'pe' ? 'EPS' : 'book/share'}</span><span className="v">{fmtPrice(v.implied_price)}</span></div>)}
              </div>
            </>}
          </Loadable>
        </Panel>
      </div>
      <div className="c-6">
        <Panel title="Historical P/E at fiscal year-end" sub="FY-end close ÷ diluted EPS (SEC)">
          <Loadable q={comps} skeleton={<Skel h={240} />}>
            {(c) => c.historical?.length ? <EChart height={250} deps={[c]} option={() => barOption(c.historical.map((h: any) => h.period_end.slice(0, 4)), c.historical.map((h: any) => h.pe), { format: (v) => `${v.toFixed(1)}×`, color: chartColors().violet })} /> : <Empty title="Not enough history" />}
          </Loadable>
        </Panel>
      </div>
    </div>
  )
}

/* ---------------- SEC filings with AI summary ---------------- */
function Filings({ symbol, name }: { symbol: string; name?: string }) {
  const q = useApi(`/assets/${encodeURIComponent(symbol)}/filings`)
  const [form, setForm] = useState('Key')
  const [sum, setSum] = useState<Record<string, any>>({})
  const summarize = async (f: any) => {
    setSum({ ...sum, [f.accession]: { loading: true } })
    try {
      const r = await api.post(`/assets/${encodeURIComponent(symbol)}/filings/summarize`, { url: f.url, form: f.form, company: name || symbol })
      setSum((s) => ({ ...s, [f.accession]: r }))
    } catch (e: any) { setSum((s) => ({ ...s, [f.accession]: { error: e.message } })) }
  }
  return (
    <Panel title="SEC EDGAR filings" prov={q.data?.provenance} actions={<Seg value={form} options={['Key', '10-K', '10-Q', '8-K', 'DEF 14A', '4', 'All']} onChange={setForm} />} flush>
      <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={10} /></div>}>
        {(d) => {
          if (!d.available) return <div style={{ padding: 14 }}><Notice kind="warn">{d.reason}</Notice></div>
          const rows = d.filings.filter((f: any) => form === 'All' || (form === 'Key' ? f.form !== '4' : f.form === form || f.form.startsWith(form)))
          return (
            <div className="table-wrap max-h" style={{ maxHeight: 720 }}>
              <table className="t">
                <thead><tr><th>Form</th><th>Filed</th><th>Period</th><th>Description</th><th></th></tr></thead>
                <tbody>{rows.slice(0, 80).map((f: any) => (
                  <Fragment key={f.accession}>
                    <tr>
                      <td><span className="badge info">{f.form}</span></td><td className="mono">{f.filed}</td><td className="mono muted">{f.report_date || '—'}</td>
                      <td className="truncate" style={{ maxWidth: 420 }}>{f.description || '—'}</td>
                      <td className="right nowrap">
                        <a className="btn sm ghost" href={f.url} target="_blank" rel="noreferrer noopener"><ExternalLink size={12} /> Document</a>
                        <a className="btn sm ghost" href={f.index_url} target="_blank" rel="noreferrer noopener">Index</a>
                        {f.form !== '4' && <button className="btn sm" onClick={() => summarize(f)} disabled={sum[f.accession]?.loading}><Sparkles size={12} /> {sum[f.accession]?.loading ? 'Summarizing…' : 'AI summary'}</button>}
                      </td>
                    </tr>
                    {sum[f.accession] && !sum[f.accession].loading && (
                      <tr><td colSpan={5} style={{ whiteSpace: 'normal', background: 'var(--panel-2)' }}>
                        {sum[f.accession].error ? <span className="down">{sum[f.accession].error}</span> : sum[f.accession].summary
                          ? <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{sum[f.accession].summary}</ReactMarkdown><div className="xs muted">Source: <a href={sum[f.accession].source_url} target="_blank" rel="noreferrer noopener">{sum[f.accession].source_url}</a> · {sum[f.accession].provider}/{sum[f.accession].model}</div></div>
                          : <Notice>{sum[f.accession].note}</Notice>}
                      </td></tr>
                    )}
                  </Fragment>
                ))}</tbody>
              </table>
            </div>
          )
        }}
      </Loadable>
    </Panel>
  )
}

/* ---------------- News / timeline / profile / holdings ---------------- */
export function AssetNews({ symbol, compact }: { symbol: string; compact?: boolean }) {
  const q = useApi(`/assets/${encodeURIComponent(symbol)}/news`, { refetch: 300_000 })
  return (
    <Panel title="News" prov={q.data?.provenance}>
      <Loadable q={q} skeleton={<SkelRows n={6} />} empty={(d) => !d.items.length}>
        {(d) => <div style={compact ? { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', columnGap: 24 } : undefined}>
          {d.items.slice(0, compact ? 8 : 40).map((n: any) => (
            <article className="news-item" key={n.id}>
              {n.thumbnail && <img className="thumb" src={n.thumbnail} alt="" loading="lazy" referrerPolicy="no-referrer" />}
              <div style={{ minWidth: 0 }}>
                <a className="hl" href={n.url} target="_blank" rel="noreferrer noopener">{n.title}</a>
                <div className="meta"><b>{n.publisher}</b><span>{fmtDateTime(n.published_at)} · {timeAgo(n.published_at)}</span>{n.tickers?.slice(0, 4).map((t: string) => <AssetLink key={t} symbol={t} className="tag link">{t}</AssetLink>)}</div>
              </div>
            </article>
          ))}
        </div>}
      </Loadable>
    </Panel>
  )
}

function Timeline({ symbol }: { symbol: string }) {
  const q = useApi(`/assets/${encodeURIComponent(symbol)}/timeline`)
  const colors: Record<string, string> = { earnings: 'var(--amber)', filing: 'var(--accent)', dividend: 'var(--up)', split: 'var(--violet)', news: 'var(--text-3)' }
  const [f, setF] = useState('all')
  return (
    <Panel title="Event timeline" sub="SEC filings, earnings reports, dividends, splits and news" actions={<Seg value={f} options={['all', 'earnings', 'filing', 'dividend', 'news']} onChange={setF} />}>
      <Loadable q={q} skeleton={<SkelRows n={10} />}>
        {(d) => <div className="timeline">{d.events.filter((e: any) => f === 'all' || e.type === f).map((e: any, i: number) => (
          <div className="tl-item" key={i} style={{ ['--tl' as any]: colors[e.type] }}>
            <div className="row small"><span className="mono muted" style={{ width: 90 }}>{e.date}</span><span className="badge" style={{ color: colors[e.type] }}>{e.type}</span>
              {e.url ? <a href={e.url} target="_blank" rel="noreferrer noopener">{e.title}</a> : <span>{e.title}</span>}<span className="muted xs" style={{ marginLeft: 'auto' }}>{e.source}</span></div>
          </div>
        ))}</div>}
      </Loadable>
    </Panel>
  )
}

function Profile({ symbol }: { symbol: string }) {
  const q = useApi(`/assets/${encodeURIComponent(symbol)}/profile`)
  const nav = useNavigate()
  return (
    <Loadable q={q} skeleton={<SkelRows n={10} />}>
      {(d) => {
        const p = d.profile || {}, s = d.sec || {}
        return (
          <div className="grid">
            <div className="c-8"><Panel title="Business description" prov={d.profile_provenance}><p style={{ lineHeight: 1.65 }} className="dim">{p.description || 'No description available from configured providers.'}</p></Panel></div>
            <div className="c-4"><Panel title="Company facts">
              <div className="metric-grid" style={{ gridTemplateColumns: '1fr' }}>
                {[['Sector', p.sector], ['Industry', p.industry], ['SIC', s.sic_description], ['Headquarters', s.headquarters || [p.city, p.state, p.country].filter(Boolean).join(', ')], ['Employees', p.employees?.toLocaleString()],
                  ['Exchange', s.exchanges?.join(', ')], ['CIK', s.cik], ['Fiscal year end', s.fiscal_year_end ? `${s.fiscal_year_end.slice(0, 2)}/${s.fiscal_year_end.slice(2)}` : null], ['Incorporated', s.state_of_incorporation],
                  ['Filer category', s.category], ['Earliest recent filing', s.first_filing], ['Website', p.website]].map(([k, v]) => (
                  <div className="metric" key={k as string}><span className="k">{k}</span><span className="v" style={{ fontFamily: 'var(--font-ui)', fontWeight: 500, textAlign: 'right' }}>{k === 'Website' && v ? <a href={v as string} target="_blank" rel="noreferrer noopener">{(v as string).replace(/^https?:\/\//, '')}</a> : v || '—'}</span></div>
                ))}
              </div>
            </Panel></div>
            <div className="c-6"><Panel title="Management" sub="Provider-reported officers">
              {(p.officers || []).length ? <table className="t compact"><tbody>{p.officers.map((o: any) => <tr key={o.name}><td style={{ fontWeight: 600 }}>{o.name}</td><td className="muted" style={{ whiteSpace: 'normal' }}>{o.title}</td></tr>)}</tbody></table> : <Empty title="No officer data" />}
            </Panel></div>
            <div className="c-6"><Panel title="Competitors (tracked universe)" sub="Same industry, then same sector">
              {(d.peers || []).length ? <table className="t compact"><tbody>{d.peers.map((o: any) => <tr key={o.symbol} className="clickable" onClick={() => nav(assetPath(o.symbol))}><td className="sym">{o.symbol}</td><td>{o.name}</td><td className="muted">{o.industry}</td></tr>)}</tbody></table> : <Empty />}
            </Panel></div>
            <div className="c-12 muted xs">Supplier relationships, revenue segments and geographic exposure require segment-level XBRL or licensed datasets; see the latest 10-K (Filings tab) for company-reported segment detail.</div>
            {s.former_names?.length > 0 && <div className="c-12 muted xs">Former names: {s.former_names.join('; ')}</div>}
          </div>
        )
      }}
    </Loadable>
  )
}

function Holdings({ symbol }: { symbol: string }) {
  const q = useApi(`/assets/${encodeURIComponent(symbol)}/profile`)
  return (
    <Loadable q={q} skeleton={<SkelRows n={10} />}>
      {(d) => {
        const f = d.fund
        if (!f) return <Notice kind="warn">{d.fund_error || 'Fund data unavailable.'}</Notice>
        return (
          <div className="grid">
            <div className="c-12"><Panel title="Fund profile" prov={d.fund_provenance}>
              <div className="stats">
                <Stat label="Family" value={<span style={{ fontSize: 13 }}>{f.family || '—'}</span>} /><Stat label="Category" value={<span style={{ fontSize: 13 }}>{f.category || '—'}</span>} />
                <Stat label="AUM" value={fmtBig(f.total_assets, '$')} /><Stat label="NAV" value={fmtPrice(f.nav)} /><Stat label="Expense ratio" value={fmtRatioPct(f.expense_ratio, 2)} />
                <Stat label="Yield" value={fmtRatioPct(f.yield, 2)} /><Stat label="YTD return" value={fmtRatioPct(f.ytd_return, 1)} /><Stat label="3Y avg return" value={fmtRatioPct(f.three_year_return, 1)} />
                <Stat label="Turnover" value={fmtRatioPct(f.turnover, 0)} />
              </div>
            </Panel></div>
            <div className="c-6"><Panel title="Top holdings" flush>
              <DataTable compact rows={f.holdings} cols={[{ key: 'symbol', label: 'Symbol', render: (r) => r.symbol ? <AssetLink symbol={r.symbol} className="sym">{r.symbol}</AssetLink> : '—' },
                { key: 'name', label: 'Name' }, { key: 'weight', label: 'Weight', num: true, render: (r) => fmtRatioPct(r.weight, 2) }]} initialSort="weight" />
            </Panel></div>
            <div className="c-6"><Panel title="Sector exposure">
              {f.sector_weights?.length ? <EChart height={320} deps={[f]} option={() => donutOption(f.sector_weights.filter((s: any) => s.weight > 0).map((s: any) => ({ name: s.sector, value: +(s.weight * 100).toFixed(2) })), (v) => `${v.toFixed(1)}%`)} /> : <Empty title="No sector breakdown" />}
            </Panel></div>
          </div>
        )
      }}
    </Loadable>
  )
}

export { fmtPct, fmtDate }
