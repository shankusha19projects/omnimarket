import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart, type EChartHandle } from '../charts/EChart'
import { lineOption } from '../charts/builders'
import { curveOption, pngButton } from '../components/widgets'
import { AssetLink, Chg, Loadable, Notice, Panel, Seg, Skel, SkelRows, Stat } from '../components/ui'
import { dir, fmtNum, fmtPrice } from '../services/format'

export default function Bonds() {
  const q = useApi('/bonds', { refetch: 600_000 })
  const [spread, setSpread] = useState<'2s10s' | '3m10y'>('2s10s')
  const curveRef = useRef<EChartHandle>(null)
  return (
    <div className="page">
      <PageHead kicker="Fixed income" title="Bonds & Rates" desc="U.S. Treasury nominal and real (TIPS) par yield curves from the official daily release, curve spreads, breakevens, credit spreads and fixed-income ETF proxies." />
      <Loadable q={q} skeleton={<SkelRows n={14} />}>
        {(d) => !d.available ? <Notice kind="bad">{d.reason}</Notice> : (
          <div className="grid">
            <div className="c-12"><div className="stats">
              {['3M', '2Y', '5Y', '10Y', '30Y'].map((t) => <Stat key={t} label={`UST ${t}`} value={`${fmtNum(d.curve[t], 2)}%`} sub={d.compare['1W ago']?.[t] != null ? <Chg v={(d.curve[t] - d.compare['1W ago'][t]) * 100} pct={false} digits={0} /> : undefined} title="Change vs one week ago in basis points" />)}
              {Object.entries(d.spreads).map(([k, v]: any) => <Stat key={k} label={k} value={<span className={dir(v)}>{v > 0 ? '+' : ''}{fmtNum(v * 100, 0)} bp</span>} />)}
              <Stat label="10Y breakeven" value={d.breakeven_10y != null ? `${fmtNum(d.breakeven_10y, 2)}%` : '—'} sub="nominal − TIPS" />
              <Stat label="10Y real (TIPS)" value={d.real_curve?.yields?.['10Y'] != null ? `${fmtNum(d.real_curve.yields['10Y'], 2)}%` : '—'} />
            </div></div>
            {d.inverted_2s10s && <div className="c-12"><Notice kind="warn">The 2s10s curve is inverted (10Y below 2Y). Historically inversions have preceded many US recessions, with long and variable lags — it is an observation, not a forecast.</Notice></div>}
            <div className="c-8">
              <Panel title="Treasury yield curve" sub={`Par yields · as of ${d.as_of}`} prov={d.provenance} accent actions={pngButton(curveRef, `yield_curve_${d.as_of}`)}>
                <EChart ref={curveRef} height={360} deps={[d]} option={() => curveOption(d)} />
              </Panel>
            </div>
            <div className="c-4">
              <Panel title="Tenor table" flush>
                <table className="t compact">
                  <thead><tr><th>Tenor</th><th className="num">Today</th><th className="num">1W</th><th className="num">1M</th><th className="num">1Y</th></tr></thead>
                  <tbody>{d.tenors.map((t: string) => (
                    <tr key={t}><td className="mono">{t}</td><td className="num"><b>{fmtNum(d.curve[t], 2)}</b></td>
                      {['1W ago', '1M ago', '1Y ago'].map((k) => { const v = d.compare[k]?.[t]; return <td key={k} className="num">{v != null ? <Chg v={(d.curve[t] - v) * 100} pct={false} digits={0} /> : '—'}</td> })}</tr>
                  ))}</tbody>
                </table>
                <div className="muted xs" style={{ padding: '6px 12px' }}>Changes in basis points.</div>
              </Panel>
            </div>
            <div className="c-8">
              <Panel title="Rates history" sub="Daily, ~2 years">
                <EChart height={300} deps={[d]} option={() => lineOption(['3M', '2Y', '10Y', '30Y'].map((k) => ({ name: k, data: d.history.map((h: any) => [h.date, h[k]]) })), { yFormat: (v) => `${v.toFixed(2)}%`, zoom: true })} />
              </Panel>
            </div>
            <div className="c-4">
              <Panel title="Curve spread" actions={<Seg value={spread} options={[['2s10s', '10Y−2Y'], ['3m10y', '10Y−3M']]} onChange={setSpread} />}>
                <EChart height={300} deps={[d, spread]} option={() => lineOption([{ name: spread, data: d.history.map((h: any) => [h.date, h[spread]]), area: true }], { yFormat: (v) => `${v.toFixed(2)}`, markZero: true })} />
              </Panel>
            </div>
            <div className="c-6">
              <Panel title="Credit, inflation & mortgages" sub="FRED series (require FRED_API_KEY)">
                {d.extras.map((x: any) => (
                  <div className="metric" key={x.id}><span className="k">{x.name}</span>
                    {x.available ? <span className="v">{fmtNum(x.latest, 2)}% <span className="muted xs">{x.latest_date}</span></span> : <span className="muted xs">{x.reason}</span>}</div>
                ))}
                <div className="muted xs" style={{ marginTop: 6 }}>Add a free key in <Link to="/settings">Settings</Link> to populate IG/HY option-adjusted spreads, TIPS and mortgage rates history.</div>
              </Panel>
            </div>
            <div className="c-6">
              <Panel title="Fixed-income ETF proxies" sub="Corporate IG, high yield, munis, TIPS, EM sovereign">
                <table className="t compact"><tbody>{Object.values(d.proxies).map((p: any) => (
                  <tr key={p.symbol}><td><AssetLink symbol={p.symbol} className="sym">{p.symbol}</AssetLink></td><td className="muted">{p.name}</td><td className="num">{fmtPrice(p.price)}</td><td className="num"><Chg v={p.change_pct} /></td></tr>
                ))}</tbody></table>
              </Panel>
            </div>
            <div className="c-12 muted xs">{d.notes.join(' ')}</div>
          </div>
        )}
      </Loadable>
      <Skel h={0} />
    </div>
  )
}
