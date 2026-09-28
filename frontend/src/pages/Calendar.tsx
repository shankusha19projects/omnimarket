import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { Chg, DataTable, Loadable, Notice, Panel, Seg, SkelRows, Tabs } from '../components/ui'
import { assetPath, fmtBig, fmtDate, fmtNum } from '../services/format'

type Which = 'today' | 'tomorrow' | 'this_week' | 'next_week'
const WHICH: [Which, string][] = [['today', 'Today'], ['tomorrow', 'Tomorrow'], ['this_week', 'This week'], ['next_week', 'Next week']]

export default function CalendarPage() {
  const [tab, setTab] = useState<'econ' | 'earnings'>('econ')
  const [which, setWhich] = useState<Which>('this_week')
  return (
    <div className="page">
      <PageHead kicker="Schedule" title="Calendar" desc="Economic releases (CPI, payrolls, GDP, PMI, retail sales, housing, auctions) with forecast/actual, central-bank decisions, and the earnings center."
                actions={<Seg value={which} options={WHICH} onChange={setWhich} />} />
      <Tabs value={tab} options={[['econ', 'Economic calendar'], ['earnings', 'Earnings center']]} onChange={setTab} />
      {tab === 'econ' ? <Econ which={which} /> : <Earnings which={which} />}
    </div>
  )
}

function Econ({ which }: { which: Which }) {
  const [imp, setImp] = useState<'1' | '2' | '3'>('2')
  const q = useApi(`/calendar/economic?which=${which}&min_importance=${imp}`)
  const [country, setCountry] = useState('All')
  return (
    <Panel title="Economic calendar" sub={q.data?.note} prov={q.data?.provenance} flush actions={<>
      <select className="input sm" value={country} onChange={(e) => setCountry(e.target.value)} aria-label="Country">{['All', ...Array.from(new Set((q.data?.rows || []).map((r: any) => r.country))) as string[]].map((c) => <option key={c}>{c}</option>)}</select>
      <Seg value={imp} options={[['1', 'All'], ['2', '★★+'], ['3', '★★★']]} onChange={setImp} />
    </>}>
      <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={12} /></div>}>
        {(d) => <>
          {d.errors?.length > 0 && <div style={{ padding: 10 }}><Notice kind="warn">Some days failed to load: {d.errors[0]}</Notice></div>}
          <DataTable rows={d.rows.filter((r: any) => country === 'All' || r.country === country)} initialSort="date" initialDesc={false} rowKey={(r, i) => `${r.date}${r.event}${i}`} cols={[
            { key: 'date', label: 'Date', value: (r) => `${r.date} ${r.time_gmt || ''}`, render: (r) => <span className="mono">{fmtDate(r.date)}</span> },
            { key: 'time_gmt', label: 'Time (GMT)', render: (r) => <span className="mono muted">{r.time_gmt || '—'}</span> },
            { key: 'country', label: 'Country' },
            { key: 'event', label: 'Event', render: (r) => <span style={{ fontWeight: r.importance === 3 ? 600 : 400, whiteSpace: 'normal' }}>{r.event}</span> },
            { key: 'importance', label: 'Impact', num: true, render: (r) => <span style={{ color: r.importance === 3 ? 'var(--down)' : r.importance === 2 ? 'var(--amber)' : 'var(--text-4)', letterSpacing: 1 }}>{'★'.repeat(r.importance)}{'☆'.repeat(3 - r.importance)}</span> },
            { key: 'actual', label: 'Actual', num: true, render: (r) => <b>{r.actual || '—'}</b> },
            { key: 'forecast', label: 'Forecast', num: true, render: (r) => r.forecast || '—' },
            { key: 'previous', label: 'Previous', num: true, render: (r) => <span className="muted">{r.previous || '—'}</span> },
          ]} />
        </>}
      </Loadable>
    </Panel>
  )
}

function Earnings({ which }: { which: Which }) {
  const [minCap, setMinCap] = useState('1e9')
  const q = useApi(`/calendar/earnings?which=${which}&min_cap=${minCap}`)
  const nav = useNavigate()
  return (
    <Panel title="Earnings center" sub={q.data?.note} prov={q.data?.provenance} flush actions={<Seg value={minCap} options={[['0', 'All caps'], ['1e9', '>$1B'], ['1e10', '>$10B'], ['1e11', '>$100B']]} onChange={setMinCap} />}>
      <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={12} /></div>}>
        {(d) => <DataTable rows={d.rows} onRow={(r) => nav(assetPath(r.symbol))} initialSort="market_cap" pageSize={50} rowKey={(r, i) => `${r.date}${r.symbol}${i}`} cols={[
          { key: 'date', label: 'Date', render: (r) => <span className="mono">{fmtDate(r.date)}</span> },
          { key: 'symbol', label: 'Ticker', render: (r) => <span className="sym">{r.symbol}</span> },
          { key: 'company', label: 'Company', render: (r) => <span className="nm" style={{ display: 'inline-block' }}>{r.company}</span> },
          { key: 'timing', label: 'Timing', render: (r) => <span className="badge">{r.timing}</span> },
          { key: 'market_cap', label: 'Mkt cap', num: true, render: (r) => fmtBig(r.market_cap, '$') },
          { key: 'fiscal_quarter', label: 'Quarter', render: (r) => <span className="muted">{r.fiscal_quarter}</span> },
          { key: 'eps_forecast', label: 'EPS est.', num: true, render: (r) => (r.eps_forecast != null ? `$${fmtNum(r.eps_forecast, 2)}` : '—') },
          { key: 'num_estimates', label: '# est', num: true, render: (r) => r.num_estimates ?? '—' },
          { key: 'last_year_eps', label: 'Prior-yr EPS', num: true, render: (r) => (r.last_year_eps != null ? `$${fmtNum(r.last_year_eps, 2)}` : '—') },
          { key: 'eps_actual', label: 'Reported', num: true, render: (r) => (r.eps_actual != null ? <b>${fmtNum(r.eps_actual, 2)}</b> : '—') },
          { key: 'surprise_pct', label: 'Surprise', num: true, render: (r) => <Chg v={r.surprise_pct} digits={1} /> },
          { key: 'price_reaction_pct', label: 'Price reaction', num: true, render: (r) => <Chg v={r.price_reaction_pct} /> },
        ]} />}
      </Loadable>
    </Panel>
  )
}
