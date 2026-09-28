import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart } from '../charts/EChart'
import { barOption } from '../charts/builders'
import { IndicatorGrid } from './Economics'
import { ChgPill, DataTable, Loadable, Notice, Panel, Seg, SkelRows } from '../components/ui'
import { assetPath, fmtBig, fmtPrice, fmtRatioPct, fmtX } from '../services/format'

export default function RealEstate() {
  const q = useApi('/real-estate', { refetch: 1_800_000 })
  const [seg, setSeg] = useState('All')
  const nav = useNavigate()
  return (
    <div className="page">
      <PageHead kicker="Property" title="Real Estate" desc="Housing macro (mortgage rates, Case-Shiller, FHFA, starts, permits, inventory, rents) and a REIT screener across residential, office, industrial, retail, hospitality, data centers and more." />
      <Loadable q={q} skeleton={<SkelRows n={14} />}>
        {(d) => {
          const r = d.reits
          const segs = ['All', ...Array.from(new Set(r.rows.map((x: any) => x.segment))) as string[]]
          return (
            <div className="grid">
              {!d.fred_configured && <div className="c-12"><Notice kind="warn">Housing series come from FRED. Add a free FRED_API_KEY in <Link to="/settings">Settings</Link> to populate them; rent CPI is available keyless via BLS.</Notice></div>}
              <div className="c-12"><IndicatorGrid rows={d.indicators} /></div>
              <div className="c-4"><Panel title="REIT segments — average YTD">
                <EChart height={330} deps={[r]} option={() => barOption(r.segments.map((s: any) => s.segment), r.segments.map((s: any) => s.avg_ytd), { horizontal: true, colorBySign: true, format: (v) => `${v.toFixed(1)}%` })} />
              </Panel></div>
              <div className="c-8"><Panel title="REIT screener" flush actions={<Seg value={seg} options={segs} onChange={setSeg} />}>
                <DataTable rows={r.rows.filter((x: any) => seg === 'All' || x.segment === seg)} onRow={(x) => nav(assetPath(x.symbol))} initialSort="market_cap" cols={[
                  { key: 'symbol', label: 'REIT', render: (x) => <div><span className="sym">{x.symbol}</span> <span className="muted xs">{x.name}</span></div> },
                  { key: 'segment', label: 'Segment', render: (x) => <span className="badge">{x.segment}</span> },
                  { key: 'price', label: 'Price', num: true, render: (x) => fmtPrice(x.price) },
                  { key: 'change_pct', label: '1D', num: true, render: (x) => <ChgPill v={x.change_pct} /> },
                  { key: 'perf_ytd', label: 'YTD', num: true, render: (x) => <ChgPill v={x.perf_ytd} digits={1} /> },
                  { key: 'perf_1y', label: '1Y', num: true, render: (x) => <ChgPill v={x.perf_1y} digits={1} /> },
                  { key: 'dividend_yield', label: 'Div yield', num: true, render: (x) => fmtRatioPct(x.dividend_yield, 2) },
                  { key: 'pb', label: 'P/B', num: true, render: (x) => fmtX(x.pb) },
                  { key: 'market_cap', label: 'Mkt cap', num: true, render: (x) => fmtBig(x.market_cap, '$') },
                ]} />
              </Panel></div>
            </div>
          )
        }}
      </Loadable>
    </div>
  )
}
