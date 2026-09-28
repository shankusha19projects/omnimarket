import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart } from '../charts/EChart'
import { barOption, donutOption } from '../charts/builders'
import { AssetLink, ChgPill, DataTable, Loadable, Panel, SkelRows } from '../components/ui'
import { assetPath, fmtBig, fmtPrice } from '../services/format'

const FLAGS: Record<string, string> = { US: 'United States', AU: 'Australia', CA: 'Canada', CL: 'Chile', GB: 'United Kingdom', BR: 'Brazil', BE: 'Belgium' }

export default function RareEarths() {
  const q = useApi('/rare-earths', { refetch: 180_000 })
  const [mineral, setMineral] = useState<string | null>(null)
  const nav = useNavigate()
  return (
    <div className="page">
      <PageHead kicker="Strategic materials" title="Rare Earths & Critical Minerals" desc="Lithium, cobalt, nickel, graphite, uranium, rare-earth elements (NdPr, Dy, Tb), scandium, gallium, germanium, antimony and copper — the companies and ETFs across mining, refining, magnets, recycling and nuclear fuel." />
      <Loadable q={q} skeleton={<SkelRows n={14} />}>
        {(d) => {
          const rows = d.companies.filter((c: any) => !mineral || c.minerals.some((m: string) => mineral.toLowerCase().includes(m.toLowerCase()) || m.toLowerCase().includes(mineral.split(' ')[0].toLowerCase())))
          return (
            <div className="grid">
              <div className="c-12">
                <div className="cards">{d.etfs.map((e: any) => (
                  <div className="kpi" key={e.symbol} onClick={() => nav(assetPath(e.symbol))}>
                    <div className="kpi-top"><span className="kpi-name">{e.symbol}</span><span className="kpi-state">ETF</span></div>
                    <div className="muted xs truncate">{e.name}</div>
                    <div className="row" style={{ alignItems: 'baseline', gap: 8 }}><span className="kpi-price" style={{ fontSize: 18 }}>{fmtPrice(e.price)}</span><ChgPill v={e.change_pct} /></div>
                    <div className="kpi-foot"><span>YTD {e.perf_ytd != null ? `${e.perf_ytd.toFixed(1)}%` : '—'}</span><span>1Y {e.perf_1y != null ? `${e.perf_1y.toFixed(1)}%` : '—'}</span></div>
                  </div>
                ))}</div>
              </div>
              <div className="c-8">
                <Panel title="Company tracker" sub={mineral ? `Filtered: ${mineral}` : 'Click a mineral card to filter'} flush actions={mineral && <button className="btn sm" onClick={() => setMineral(null)}>Clear filter</button>}>
                  <DataTable rows={rows} onRow={(r) => nav(assetPath(r.symbol))} initialSort="market_cap" cols={[
                    { key: 'symbol', label: 'Company', render: (r) => <div><span className="sym">{r.symbol}</span> <span className="muted xs">{r.name}</span></div> },
                    { key: 'minerals', label: 'Exposure', sortable: false, render: (r) => <div className="chip-row" style={{ gap: 3 }}>{r.minerals.map((m: string) => <span key={m} className="tag">{m}</span>)}</div> },
                    { key: 'segment', label: 'Value chain', render: (r) => <span className="muted small">{r.segment}</span> },
                    { key: 'country', label: 'HQ', render: (r) => <span title={FLAGS[r.country]}>{r.country}</span> },
                    { key: 'price', label: 'Price', num: true, render: (r) => fmtPrice(r.price) },
                    { key: 'change_pct', label: '1D', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
                    { key: 'perf_ytd', label: 'YTD', num: true, render: (r) => <ChgPill v={r.perf_ytd} digits={1} /> },
                    { key: 'perf_1y', label: '1Y', num: true, render: (r) => <ChgPill v={r.perf_1y} digits={0} /> },
                    { key: 'market_cap', label: 'Mkt cap', num: true, render: (r) => fmtBig(r.market_cap, '$') },
                  ]} />
                </Panel>
              </div>
              <div className="c-4 col">
                <Panel title="Tracked market cap by HQ country"><EChart height={220} deps={[d]} option={() => donutOption(Object.entries(d.exposure_by_hq_country).map(([k, v]: any) => ({ name: FLAGS[k] || k, value: v })), (v) => fmtBig(v, '$'))} /></Panel>
                <Panel title="Coverage by mineral (# companies)"><EChart height={260} deps={[d]} option={() => { const e = Object.entries(d.coverage_by_mineral).sort((a: any, b: any) => b[1] - a[1]); return barOption(e.map((x) => x[0]), e.map((x: any) => x[1]), { horizontal: true }) }} /></Panel>
              </div>
              <div className="c-12">
                <Panel title="Supply-chain primer" sub={d.note}>
                  <div className="cards lg">{Object.entries(d.minerals).map(([m, txt]: any) => (
                    <div key={m} className="stat" style={{ cursor: 'pointer', outline: mineral === m ? '1px solid var(--accent)' : undefined }} onClick={() => setMineral(mineral === m ? null : m)}>
                      <div className="l" style={{ color: 'var(--amber)' }}>{m}</div>
                      <div className="small dim" style={{ lineHeight: 1.5, marginTop: 3 }}>{txt}</div>
                    </div>
                  ))}</div>
                  <div className="row xs muted" style={{ marginTop: 10, flexWrap: 'wrap' }}>Quantified production & reserve shares: {d.sources.map(([n, u]: any) => <a key={u} href={u} target="_blank" rel="noreferrer noopener">{n} ↗</a>)}</div>
                </Panel>
              </div>
              <div className="c-12 muted xs">Related commodities: <AssetLink symbol="HG=F">Copper</AssetLink> · <AssetLink symbol="URA">Uranium (URA)</AssetLink> · <AssetLink symbol="LIT">Lithium (LIT)</AssetLink></div>
            </div>
          )
        }}
      </Loadable>
    </div>
  )
}
