import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { X } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart } from '../charts/EChart'
import { lineOption, matrixOption } from '../charts/builders'
import { AssetLink, Chg, Loadable, Panel, Seg, Skel, SkelRows, Tabs } from '../components/ui'
import { fmtBig, fmtNum, fmtPrice, fmtRatioPct, fmtX } from '../services/format'

export default function Analytics() {
  const [params] = useSearchParams()
  const [tab, setTab] = useState<'compare' | 'correlation'>('compare')
  return (
    <div className="page">
      <PageHead kicker="Analytics" title="Compare & Correlate" desc="Side-by-side comparison of up to five assets across performance, valuation, growth, profitability, balance sheet, volatility and technicals — plus cross-asset correlation." />
      <Tabs value={tab} options={[['compare', 'Comparison tool'], ['correlation', 'Correlation tool']]} onChange={setTab} />
      {tab === 'compare' ? <Compare initial={(params.get('symbols') || 'AAPL,MSFT,NVDA,^GSPC').split(',')} /> : <Correlation />}
    </div>
  )
}

function SymbolPicker({ symbols, onChange, max }: { symbols: string[]; onChange: (s: string[]) => void; max: number }) {
  const [v, setV] = useState('')
  return (
    <div className="row wrap">
      {symbols.map((s) => <span key={s} className="chip on">{s}<button onClick={() => onChange(symbols.filter((x) => x !== s))} style={{ border: 'none', background: 'none', color: 'inherit', padding: 0, display: 'grid' }} aria-label={`Remove ${s}`}><X size={11} /></button></span>)}
      {symbols.length < max && <form onSubmit={(e) => { e.preventDefault(); if (v.trim()) { onChange([...symbols, v.trim().toUpperCase()]); setV('') } }}>
        <input className="input sm mono" placeholder="Add symbol (e.g. BTC-USD)" value={v} onChange={(e) => setV(e.target.value)} style={{ width: 180 }} />
      </form>}
    </div>
  )
}

const ROWS: [string, string, (v: any) => string][] = [
  ['price', 'Price', fmtPrice], ['change_pct', '1D %', (v) => fmtNum(v, 2) + '%'], ['market_cap', 'Market cap', (v) => fmtBig(v, '$')],
  ['perf_1m', '1M %', (v) => fmtNum(v, 1) + '%'], ['perf_3m', '3M %', (v) => fmtNum(v, 1) + '%'], ['perf_ytd', 'YTD %', (v) => fmtNum(v, 1) + '%'], ['perf_1y', '1Y %', (v) => fmtNum(v, 1) + '%'],
  ['volatility_1y', 'Volatility (1Y ann.)', (v) => fmtNum(v, 1) + '%'], ['max_drawdown_1y', 'Max drawdown (1Y)', (v) => fmtNum(v, 1) + '%'], ['rsi14', 'RSI 14', (v) => fmtNum(v, 0)],
  ['pe', 'P/E', fmtX], ['forward_pe', 'Forward P/E', fmtX], ['ps', 'P/S', fmtX], ['ev_ebitda', 'EV/EBITDA', fmtX], ['fcf_yield', 'FCF yield', (v) => fmtRatioPct(v, 1)],
  ['revenue_growth', 'Revenue growth', (v) => fmtRatioPct(v, 1)], ['eps_growth', 'EPS growth', (v) => fmtRatioPct(v, 1)],
  ['gross_margin', 'Gross margin', (v) => fmtRatioPct(v, 1)], ['operating_margin', 'Operating margin', (v) => fmtRatioPct(v, 1)], ['net_margin', 'Net margin', (v) => fmtRatioPct(v, 1)],
  ['roe', 'ROE', (v) => fmtRatioPct(v, 1)], ['roic', 'ROIC', (v) => fmtRatioPct(v, 1)], ['debt_to_equity', 'Debt / equity', fmtX], ['current_ratio', 'Current ratio', fmtX],
]

function Compare({ initial }: { initial: string[] }) {
  const [symbols, setSymbols] = useState(initial.slice(0, 5))
  const [range, setRange] = useState('1y')
  const q = useApi(symbols.length ? `/compare?symbols=${encodeURIComponent(symbols.join(','))}&range=${range}` : null)
  return (
    <div className="grid">
      <div className="c-12"><Panel title="Assets (max 5)" actions={<Seg value={range} options={[['3mo', '3M'], ['6mo', '6M'], ['ytd', 'YTD'], ['1y', '1Y'], ['3y', '3Y'], ['5y', '5Y']]} onChange={setRange} />}><SymbolPicker symbols={symbols} onChange={setSymbols} max={5} /></Panel></div>
      <div className="c-12">
        <Panel title="Relative performance" sub="Rebased to 0% at the start of the period">
          <Loadable q={q} skeleton={<Skel h={340} />}>
            {(d) => <EChart height={340} deps={[d]} option={() => lineOption(Object.entries(d.series).map(([s, pts]: any) => ({ name: s, data: pts.map((p: any) => [p.t * 1000, p.v]) })), { yFormat: (v) => `${v.toFixed(0)}%`, zoom: true, markZero: true })} />}
          </Loadable>
        </Panel>
      </div>
      <div className="c-12">
        <Panel title="Side-by-side metrics" flush>
          <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={12} /></div>}>
            {(d) => (
              <div className="table-wrap">
                <table className="t">
                  <thead><tr><th>Metric</th>{d.rows.map((r: any) => <th key={r.symbol} className="num"><AssetLink symbol={r.symbol}>{r.symbol}</AssetLink><div className="muted xs" style={{ textTransform: 'none', letterSpacing: 0 }}>{r.asset_class}</div></th>)}</tr></thead>
                  <tbody>{ROWS.filter(([k]) => d.rows.some((r: any) => r[k] != null)).map(([k, l, f]) => {
                    const vals = d.rows.map((r: any) => r[k]).filter((v: any) => typeof v === 'number')
                    const best = ['max_drawdown_1y', 'volatility_1y', 'pe', 'forward_pe', 'ps', 'ev_ebitda', 'debt_to_equity'].includes(k) ? Math.min(...vals) : Math.max(...vals)
                    return <tr key={k}><td className="dim">{l}</td>{d.rows.map((r: any) => <td key={r.symbol} className="num" style={{ fontWeight: r[k] === best && vals.length > 1 && k !== 'price' ? 700 : 400, color: r[k] === best && vals.length > 1 && k !== 'price' ? 'var(--accent)' : undefined }}>{r[k] == null ? '—' : f(r[k])}</td>)}</tr>
                  })}</tbody>
                </table>
              </div>
            )}
          </Loadable>
          <div className="muted xs" style={{ padding: '6px 12px' }}>Highlighted = most favorable value in the row (lowest for multiples, volatility, drawdown and leverage). Equity fundamentals from SEC filings; not meaningful for crypto/commodities.</div>
        </Panel>
      </div>
    </div>
  )
}

function Correlation() {
  const [symbols, setSymbols] = useState(['^GSPC', '^NDX', 'TLT', 'GC=F', 'CL=F', 'DX-Y.NYB', 'BTC-USD', 'EURUSD=X', 'HG=F', 'XLE'])
  const [range, setRange] = useState('1y')
  const [pair, setPair] = useState<[string, string]>(['BTC-USD', '^NDX'])
  const m = useApi(`/correlation?symbols=${encodeURIComponent(symbols.join(','))}&range=${range}`)
  const presets = useApi('/correlation/presets')
  const p = useApi(`/correlation/pair?a=${encodeURIComponent(pair[0])}&b=${encodeURIComponent(pair[1])}&range=2y&window=60`)
  return (
    <div className="grid">
      <div className="c-12"><Panel title="Universe (max 12)" actions={<Seg value={range} options={[['3mo', '3M'], ['6mo', '6M'], ['1y', '1Y'], ['3y', '3Y']]} onChange={setRange} />}><SymbolPicker symbols={symbols} onChange={setSymbols} max={12} /></Panel></div>
      <div className="c-7">
        <Panel title="Correlation matrix" sub={m.data ? `${m.data.method} ${m.data.observations} obs · ${m.data.start} → ${m.data.end}` : undefined}>
          <Loadable q={m} skeleton={<Skel h={460} />}>
            {(d) => d.matrix?.length ? <EChart height={470} deps={[d]} option={() => matrixOption(d.keys, d.matrix)} onClick={(e) => setPair([d.keys[e.value[1]], d.keys[e.value[0]]])} /> : <div className="muted">{d.error}</div>}
          </Loadable>
          <div className="muted xs">Click a cell to chart the rolling correlation of that pair.</div>
        </Panel>
      </div>
      <div className="c-5 col">
        <Panel title="Classic relationships" sub="1Y full-period and latest 60-day correlation">
          <Loadable q={presets} skeleton={<SkelRows n={6} />}>
            {(d) => <table className="t compact"><thead><tr><th>Pair</th><th className="num">1Y</th><th className="num">60D</th></tr></thead><tbody>
              {d.pairs.map((x: any) => <tr key={x.label} className="clickable" onClick={() => setPair([x.a, x.b])}><td>{x.label}</td><td className="num">{fmtNum(x.corr_1y, 2)}</td><td className="num"><Chg v={x.latest_60d} pct={false} /></td></tr>)}
            </tbody></table>}
          </Loadable>
        </Panel>
        <Panel title={`Rolling 60-day correlation: ${pair[0]} vs ${pair[1]}`}>
          <Loadable q={p} skeleton={<Skel h={220} />}>
            {(d) => <EChart height={230} deps={[d]} option={() => lineOption([{ name: 'ρ (60d)', data: d.rolling.map((r: any) => [r.date, r.corr]), area: true }], { yFormat: (v) => v.toFixed(2), markZero: true })} />}
          </Loadable>
        </Panel>
      </div>
    </div>
  )
}
