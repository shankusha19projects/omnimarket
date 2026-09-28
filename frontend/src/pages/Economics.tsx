import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart } from '../charts/EChart'
import { barOption, lineOption } from '../charts/builders'
import { Chg, Loadable, Notice, Panel, Prov, Seg, SkelRows, Sparkline, Tabs } from '../components/ui'
import { fmtDate, fmtNum } from '../services/format'

export function IndicatorGrid({ rows, onPick, picked }: { rows: any[]; onPick?: (id: string) => void; picked?: string[] }) {
  return (
    <div className="cards lg">
      {rows.map((r: any) => (
        <div key={r.id} className="panel" style={{ padding: 12, cursor: r.available ? 'pointer' : 'default', outline: picked?.includes(r.id) ? '1px solid var(--accent)' : undefined }}
             onClick={() => r.available && onPick?.(r.id)}>
          <div className="row"><span className="small" style={{ fontWeight: 600 }}>{r.name}</span><span className="spacer" />{r.provenance && <Prov p={r.provenance} />}</div>
          {r.available ? <>
            <div className="row" style={{ alignItems: 'baseline', gap: 8, marginTop: 4 }}>
              <span className="mono" style={{ fontSize: 22, fontWeight: 600 }}>{fmtNum(r.latest, r.unit === '%' ? 1 : 0)}{r.unit === '%' ? '%' : r.unit === 'k' ? 'k' : ''}</span>
              <Chg v={r.change} pct={false} digits={r.unit === '%' ? 2 : 0} />
            </div>
            <div className="muted xs">{fmtDate(r.latest_date)} · prev {fmtNum(r.previous, r.unit === '%' ? 1 : 0)}{r.category ? ` · ${r.category}` : ''}</div>
            <div style={{ marginTop: 6 }}><Sparkline data={r.series.slice(-36).map((p: any) => p.value)} height={34} width={220} color="var(--accent)" /></div>
          </> : <div className="muted xs" style={{ marginTop: 6 }}>{r.reason}</div>}
        </div>
      ))}
    </div>
  )
}

export default function Economics() {
  const q = useApi('/economics', { refetch: 3_600_000 })
  const [tab, setTab] = useState<'us' | 'intl'>('us')
  const [picked, setPicked] = useState<string[]>(['cpi_yoy', 'core_cpi_yoy', 'unrate'])
  const [cat, setCat] = useState('All')
  return (
    <div className="page">
      <PageHead kicker="Macro" title="Economic Dashboard" desc="US inflation, labor, growth, housing and sentiment from official sources (BLS keyless; FRED with a free key), plus international comparisons from the World Bank." />
      <Tabs value={tab} options={[['us', 'United States'], ['intl', 'International']]} onChange={setTab} />
      <Loadable q={q} skeleton={<SkelRows n={14} />}>
        {(d) => tab === 'us' ? (
          <div className="col" style={{ gap: 12 }}>
            {d.note && <Notice kind="warn">{d.note} <Link to="/settings">Add key →</Link></Notice>}
            <Panel title="Historical comparison" sub="Click indicator cards below to add/remove series">
              <EChart height={320} deps={[d, picked]} option={() => lineOption(d.us.filter((r: any) => picked.includes(r.id) && r.available).map((r: any) => ({ name: r.name, data: r.series.map((p: any) => [p.date, p.value]) })), { zoom: true })} />
            </Panel>
            <div className="row"><Seg value={cat} options={['All', ...Array.from(new Set(d.us.map((r: any) => r.category))) as string[]]} onChange={setCat} /></div>
            <IndicatorGrid rows={d.us.filter((r: any) => cat === 'All' || r.category === cat)} picked={picked} onPick={(id) => setPicked(picked.includes(id) ? picked.filter((x) => x !== id) : [...picked, id].slice(-5))} />
            <Panel title="Not available from free sources">{d.unavailable.map((u: any) => <div key={u.name} className="small" style={{ padding: '3px 0' }}><b>{u.name}</b> — <span className="muted">{u.reason}</span></div>)}</Panel>
          </div>
        ) : <International d={d.international} />}
      </Loadable>
    </div>
  )
}

function International({ d }: { d: any }) {
  const [ind, setInd] = useState(d.indicators[0]?.id)
  const cur = d.indicators.find((i: any) => i.id === ind)
  const names: Record<string, string> = Object.fromEntries(d.countries)
  const latest = cur?.available ? Object.entries(cur.data).map(([c, pts]: any) => ({ c, name: names[c] || c, v: pts[pts.length - 1]?.[1], y: pts[pts.length - 1]?.[0] })).sort((a, b) => (b.v ?? -99) - (a.v ?? -99)) : []
  return (
    <div className="grid">
      <div className="c-12"><Seg value={ind} options={d.indicators.map((i: any) => [i.id, i.name])} onChange={setInd} /></div>
      {cur?.available ? <>
        <div className="c-5"><Panel title="Latest by country" prov={cur.provenance}>
          <EChart height={400} deps={[cur]} option={() => barOption(latest.map((l) => `${l.name} (${l.y})`), latest.map((l) => l.v ?? null), { horizontal: true, colorBySign: true, format: (v) => `${v.toFixed(1)}%` })} />
        </Panel></div>
        <div className="c-7"><Panel title="History" sub={d.note}>
          <EChart height={400} deps={[cur]} option={() => lineOption(Object.entries(cur.data).map(([c, pts]: any) => ({ name: names[c] || c, data: pts.map((p: any) => [p[0], p[1]]) })), { timeAxis: false, yFormat: (v) => `${v.toFixed(1)}%` })} />
        </Panel></div>
      </> : <div className="c-12"><Notice kind="warn">{cur?.reason}</Notice></div>}
    </div>
  )
}
