import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { SectorBars } from '../components/widgets'
import { AssetLink, Chg, ChgPill, DataTable, Loadable, Panel, SkelRows, Tabs } from '../components/ui'
import { assetPath, fmtBig, fmtNum, fmtX, heatColor } from '../services/format'

export default function Sectors() {
  const [tab, setTab] = useState<'sectors' | 'themes'>('sectors')
  return (
    <div className="page">
      <PageHead kicker="Equity structure" title="Sectors & Themes" desc="GICS-style sectors via SPDR ETFs with constituent breadth, valuation and leaders/laggards — plus configurable thematic baskets (config/themes.json)." />
      <Tabs value={tab} options={[['sectors', 'Sectors'], ['themes', 'Thematic baskets']]} onChange={setTab} />
      {tab === 'sectors' ? <SectorsView /> : <ThemesView />}
    </div>
  )
}

function SectorsView() {
  const q = useApi('/markets/sectors', { refetch: 180_000 })
  const nav = useNavigate()
  return (
    <div className="grid">
      <div className="c-4"><SectorBars /></div>
      <div className="c-8">
        <Panel title="Sector scoreboard" sub={q.data?.method} flush>
          <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={11} /></div>}>
            {(d) => <DataTable rows={d.rows} onRow={(r) => nav(assetPath(r.etf))} initialSort="change_pct" cols={[
              { key: 'sector', label: 'Sector', render: (r) => <div><b>{r.sector}</b> <span className="muted mono xs">{r.etf}</span></div> },
              { key: 'change_pct', label: '1D', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
              { key: 'perf_1w', label: '1W', num: true, render: (r) => <ChgPill v={r.perf_1w} /> },
              { key: 'perf_1m', label: '1M', num: true, render: (r) => <ChgPill v={r.perf_1m} digits={1} /> },
              { key: 'perf_ytd', label: 'YTD', num: true, render: (r) => <ChgPill v={r.perf_ytd} digits={1} /> },
              { key: 'median_pe', label: 'Med P/E', num: true, render: (r) => fmtX(r.median_pe) },
              { key: 'median_forward_pe', label: 'Med fwd P/E', num: true, render: (r) => fmtX(r.median_forward_pe) },
              { key: 'implied_eps_growth', label: 'Impl. EPS g', num: true, render: (r) => <Chg v={r.implied_eps_growth} digits={1} />, title: 'Cap-weighted trailing→forward earnings growth implied by P/E ratios' },
              { key: 'breadth', label: 'Breadth', num: true, value: (r) => r.breadth_up / (r.breadth_total || 1), render: (r) => `${r.breadth_up}/${r.breadth_total}` },
              { key: 'tracked_cap', label: 'Tracked cap', num: true, render: (r) => fmtBig(r.tracked_cap, '$') },
            ]} />}
          </Loadable>
        </Panel>
      </div>
      <div className="c-12">
        <Loadable q={q} skeleton={<SkelRows />}>
          {(d) => <div className="cards lg">{d.rows.map((r: any) => (
            <div className="panel" key={r.sector} style={{ padding: 12 }}>
              <div className="row"><b>{r.sector}</b><span className="spacer" /><ChgPill v={r.change_pct} /></div>
              <div className="upper muted" style={{ marginTop: 8 }}>Leaders</div>
              {r.leaders.map((x: any) => <div className="row small" key={x.symbol} style={{ padding: '2px 0' }}><AssetLink symbol={x.symbol} className="mono">{x.symbol}</AssetLink><span className="muted truncate" style={{ flex: 1 }}>{x.name}</span><Chg v={x.change_pct} /></div>)}
              <div className="upper muted" style={{ marginTop: 6 }}>Laggards</div>
              {r.laggards.map((x: any) => <div className="row small" key={x.symbol} style={{ padding: '2px 0' }}><AssetLink symbol={x.symbol} className="mono">{x.symbol}</AssetLink><span className="muted truncate" style={{ flex: 1 }}>{x.name}</span><Chg v={x.change_pct} /></div>)}
            </div>
          ))}</div>}
        </Loadable>
      </div>
    </div>
  )
}

function ThemesView() {
  const q = useApi('/markets/themes', { refetch: 180_000 })
  const [open, setOpen] = useState<string | null>(null)
  return (
    <Loadable q={q} skeleton={<SkelRows n={12} />}>
      {(d) => (
        <>
          <div className="muted small" style={{ marginBottom: 10 }}>{d.method}</div>
          <div className="cards lg">{d.rows.map((t: any) => (
            <div className="panel" key={t.id} style={{ padding: 12, cursor: 'pointer' }} onClick={() => setOpen(open === t.id ? null : t.id)}>
              <div className="row"><b>{t.name}</b><span className="spacer" /><ChgPill v={t.basket_change_pct} /></div>
              <div className="row xs muted" style={{ marginTop: 4 }}>ETF <AssetLink symbol={t.etf} className="mono">{t.etf}</AssetLink> <Chg v={t.etf_change_pct} /> · {t.coverage}</div>
              <div className="heat-grid" style={{ marginTop: 8, gridTemplateColumns: 'repeat(auto-fill, minmax(62px, 1fr))' }}>
                {t.members.map((m: any) => (
                  <Link key={m.symbol} to={assetPath(m.symbol)} className="heat-tile" style={{ background: heatColor(m.change_pct, 4) }} onClick={(e) => e.stopPropagation()} title={m.name}>
                    <span className="s">{m.symbol}</span><span className="v">{m.change_pct != null ? `${m.change_pct > 0 ? '+' : ''}${fmtNum(m.change_pct, 1)}%` : 'n/a'}</span></Link>
                ))}
              </div>
            </div>
          ))}</div>
        </>
      )}
    </Loadable>
  )
}
