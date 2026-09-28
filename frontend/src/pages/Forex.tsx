import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart } from '../charts/EChart'
import { barOption } from '../charts/builders'
import { ChgPill, DataTable, Loadable, Panel, Seg, Skel, SkelRows, Sparkline } from '../components/ui'
import { assetPath, fmtNum, fmtPrice } from '../services/format'

export default function Forex() {
  const q = useApi('/forex', { refetch: 90_000 })
  const cb = useApi('/central-banks')
  const [p, setP] = useState<'change_pct' | 'perf_1m' | 'perf_ytd'>('change_pct')
  const nav = useNavigate()
  return (
    <div className="page">
      <PageHead kicker="Currencies" title="Forex" desc="Major and emerging-market pairs with realized volatility, plus policy-rate context from central-bank data portals." />
      <Loadable q={q} skeleton={<SkelRows n={14} />}>
        {(d) => (
          <div className="grid">
            <div className="c-8">
              <Panel title="Spot monitor" flush prov={d.rows[0]?.provenance}>
                <DataTable rows={d.rows} onRow={(r) => nav(assetPath(r.symbol))} cols={[
                  { key: 'name', label: 'Pair', render: (r) => <b className="mono">{r.name}</b> },
                  { key: 'spark', label: '5D', sortable: false, render: (r) => <div style={{ width: 90 }}><Sparkline data={r.spark} width={90} height={24} /></div> },
                  { key: 'price', label: 'Spot', num: true, render: (r) => <b>{fmtPrice(r.price, { min: 4, max: 4 })}</b> },
                  { key: 'change_pct', label: '1D', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
                  { key: 'perf_1m', label: '1M', num: true, render: (r) => <ChgPill v={r.perf_1m} /> },
                  { key: 'perf_ytd', label: 'YTD', num: true, render: (r) => <ChgPill v={r.perf_ytd} digits={1} /> },
                  { key: 'perf_1y', label: '1Y', num: true, render: (r) => <ChgPill v={r.perf_1y} digits={1} /> },
                  { key: 'rv20', label: 'RV 20d', num: true, render: (r) => `${fmtNum(r.rv20, 1)}%` },
                  { key: 'rv60', label: 'RV 60d', num: true, render: (r) => `${fmtNum(r.rv60, 1)}%` },
                ]} />
              </Panel>
            </div>
            <div className="c-4 col">
              <Panel title="Relative moves" actions={<Seg value={p} options={[['change_pct', '1D'], ['perf_1m', '1M'], ['perf_ytd', 'YTD']]} onChange={setP} />}>
                <EChart height={380} deps={[d, p]} option={() => barOption(d.rows.map((r: any) => r.name), d.rows.map((r: any) => r[p]), { horizontal: true, colorBySign: true, format: (v) => `${v.toFixed(2)}%` })} />
              </Panel>
              <Panel title="Interest-rate context" sub="Policy rates (live where available)">
                <Loadable q={cb} skeleton={<Skel h={160} />}>
                  {(c) => {
                    const fed = c.banks.find((b: any) => b.id === 'fed')?.rate
                    return <table className="t compact"><thead><tr><th>Bank</th><th className="num">Rate</th><th className="num">vs Fed</th><th>As of</th></tr></thead><tbody>{c.banks.map((b: any) => (
                      <tr key={b.id}><td><b>{b.short}</b> <span className="muted xs">{b.currency}</span></td>
                        <td className="num">{b.rate != null ? `${fmtNum(b.rate, 2)}%` : <span className="muted xs">n/a</span>}</td>
                        <td className="num">{b.rate != null && fed != null && b.id !== 'fed' ? `${b.rate - fed > 0 ? '+' : ''}${fmtNum((b.rate - fed) * 100, 0)} bp` : '—'}</td>
                        <td className="muted xs">{b.rate_date || ''}</td></tr>
                    ))}</tbody></table>
                  }}
                </Loadable>
                <div className="muted xs" style={{ marginTop: 6 }}>Policy-rate differentials versus the Fed are a first-order driver of carry and USD crosses. Rates without a keyless source need FRED_API_KEY.</div>
              </Panel>
            </div>
          </div>
        )}
      </Loadable>
    </div>
  )
}
