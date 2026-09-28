import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart } from '../charts/EChart'
import { lineOption } from '../charts/builders'
import { QuoteCard } from '../components/widgets'
import { ChgPill, DataTable, Loadable, Notice, Panel, Seg, Skel, SkelRows } from '../components/ui'
import { assetPath, fmtNum, fmtPrice } from '../services/format'

const CURVES: [string, string][] = [['CL=F', 'WTI'], ['NG=F', 'Nat gas'], ['GC=F', 'Gold'], ['HG=F', 'Copper'], ['ZC=F', 'Corn']]

export default function Commodities() {
  const q = useApi('/commodities', { refetch: 90_000 })
  const [curve, setCurve] = useState('CL=F')
  const c = useApi(`/assets/${encodeURIComponent(curve)}/curve`)
  const nav = useNavigate()
  return (
    <div className="page">
      <PageHead kicker="Real assets" title="Commodities" desc="Front-month futures across energy, metals and agriculture (CME/ICE via Yahoo-compatible feed; typically delayed). Futures curves built from individual contract months." />
      <Loadable q={q} skeleton={<SkelRows n={14} />}>
        {(d) => (
          <div className="grid">
            <div className="c-12"><div className="cards">{['Energy', 'Metals'].flatMap((g) => d.groups[g].slice(0, 4)).map((r: any) => <QuoteCard key={r.symbol} c={r} />)}</div></div>
            {Object.entries(d.groups).map(([g, rows]: any) => (
              <div className="c-12" key={g}>
                <Panel title={g} flush prov={rows[0]?.provenance}>
                  <DataTable rows={rows} onRow={(r) => nav(assetPath(r.symbol))} cols={[
                    { key: 'name', label: 'Contract', render: (r) => <div><b>{r.name}</b> <span className="muted mono xs">{r.symbol}</span></div> },
                    { key: 'unit', label: 'Unit', render: (r) => <span className="muted">{r.unit}</span> },
                    { key: 'price', label: 'Last', num: true, render: (r) => <b>{fmtPrice(r.price)}</b> },
                    { key: 'change_pct', label: '1D', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
                    { key: 'perf_1w', label: '1W', num: true, render: (r) => <ChgPill v={r.perf_1w} digits={1} /> },
                    { key: 'perf_1m', label: '1M', num: true, render: (r) => <ChgPill v={r.perf_1m} digits={1} /> },
                    { key: 'perf_ytd', label: 'YTD', num: true, render: (r) => <ChgPill v={r.perf_ytd} digits={1} /> },
                    { key: 'perf_1y', label: '1Y', num: true, render: (r) => <ChgPill v={r.perf_1y} digits={1} /> },
                    { key: 'rv20', label: 'RV 20d', num: true, render: (r) => `${fmtNum(r.rv20, 1)}%` },
                    { key: 'range', label: 'Day range', num: true, render: (r) => <span className="muted">{fmtPrice(r.day_low)} – {fmtPrice(r.day_high)}</span> },
                  ]} />
                </Panel>
              </div>
            ))}
            <div className="c-8">
              <Panel title="Futures curve" sub={c.data?.available ? `${c.data.name}: ${c.data.shape}` : undefined} prov={c.data?.provenance} actions={<Seg value={curve} options={CURVES} onChange={setCurve} />}>
                <Loadable q={c} skeleton={<Skel h={260} />}>
                  {(cd) => cd.available ? <EChart height={270} deps={[cd]} option={() => lineOption([{ name: cd.name, data: cd.points.map((p: any) => [p.label, p.price]), area: true }], { timeAxis: false })} /> : <Notice kind="warn">{cd.reason}</Notice>}
                </Loadable>
              </Panel>
            </div>
            <div className="c-4">
              <Panel title="Not covered by free data">
                <div className="col" style={{ gap: 8 }}>{d.unavailable.map((u: any) => <Notice key={u.name} kind="warn"><b>{u.name}:</b> {u.reason}</Notice>)}</div>
              </Panel>
            </div>
          </div>
        )}
      </Loadable>
    </div>
  )
}
