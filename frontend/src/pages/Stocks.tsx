import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { usePostApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { Heatmap, Movers } from '../components/widgets'
import { ChgPill, DataTable, Loadable, Panel, Seg, SkelRows } from '../components/ui'
import { assetPath, fmtBig, fmtNum, fmtPrice, fmtX } from '../services/format'

const CAPS: [string, string, number, number][] = [['all', 'All', 0, Infinity], ['mega', 'Mega (>$200B)', 2e11, Infinity], ['large', 'Large ($10–200B)', 1e10, 2e11], ['mid', 'Mid ($2–10B)', 2e9, 1e10], ['small', 'Small ($300M–2B)', 3e8, 2e9], ['micro', 'Micro (<$300M)', 0, 3e8]]

export default function Stocks() {
  const [universe, setUniverse] = useState<'all' | 'international' | 'critical_minerals' | 'reits'>('all')
  const [cap, setCap] = useState('all')
  const [sector, setSector] = useState('All')
  const [filter, setFilter] = useState('')
  const q = usePostApi('/screener', { universe, filters: [], sort: 'market_cap', limit: 1000 }, { refetch: 120_000 })
  const nav = useNavigate()
  const rows = useMemo(() => {
    const [, , lo, hi] = CAPS.find((c) => c[0] === cap)!
    return (q.data?.rows || []).filter((r: any) => (sector === 'All' || r.sector === sector) && (cap === 'all' || ((r.market_cap || 0) >= lo && (r.market_cap || 0) < hi)))
  }, [q.data, cap, sector])
  const sectors = ['All', ...Array.from(new Set((q.data?.rows || []).map((r: any) => r.sector).filter(Boolean))).sort() as string[]]
  return (
    <div className="page">
      <PageHead kicker="Equities" title="Stocks" desc="US large caps, international equities & ADRs, critical-minerals and REIT universes. Search any listed ticker with Ctrl+K — coverage is not limited to this list." />
      <div className="grid">
        <div className="c-8"><Heatmap height={380} /></div>
        <div className="c-4"><Movers /></div>
        <div className="c-12">
          <Panel title="Equity universe" flush actions={<>
            <div className="row" style={{ position: 'relative' }}><Search size={13} style={{ position: 'absolute', left: 8, color: 'var(--text-3)' }} /><input className="input sm" style={{ paddingLeft: 26, width: 180 }} placeholder="Filter ticker, name, industry" value={filter} onChange={(e) => setFilter(e.target.value)} /></div>
            <select className="input sm" value={sector} onChange={(e) => setSector(e.target.value)} aria-label="Sector">{sectors.map((s) => <option key={s}>{s}</option>)}</select>
            <select className="input sm" value={cap} onChange={(e) => setCap(e.target.value)} aria-label="Market cap">{CAPS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
            <Seg value={universe} options={[['all', 'All equities'], ['international', 'International / ADR'], ['critical_minerals', 'Critical minerals'], ['reits', 'REITs']]} onChange={setUniverse} />
          </>}>
            <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={12} /></div>}>
              {() => <DataTable rows={rows} filter={filter} onRow={(r) => nav(assetPath(r.symbol))} pageSize={40} initialSort="market_cap" cols={[
                { key: 'symbol', label: 'Symbol', render: (r) => <span className="sym">{r.symbol}</span> },
                { key: 'name', label: 'Company', render: (r) => <span className="nm" style={{ display: 'inline-block' }}>{r.name}</span> },
                { key: 'sector', label: 'Sector', render: (r) => <span className="muted">{r.sector}</span> },
                { key: 'industry', label: 'Industry', render: (r) => <span className="muted truncate" style={{ display: 'inline-block', maxWidth: 180 }}>{r.industry}</span> },
                { key: 'price', label: 'Price', num: true, render: (r) => fmtPrice(r.price) },
                { key: 'change_pct', label: '1D', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
                { key: 'perf_1m', label: '1M', num: true, render: (r) => <ChgPill v={r.perf_1m} digits={1} /> },
                { key: 'perf_ytd', label: 'YTD', num: true, render: (r) => <ChgPill v={r.perf_ytd} digits={1} /> },
                { key: 'market_cap', label: 'Mkt cap', num: true, render: (r) => fmtBig(r.market_cap, '$') },
                { key: 'pe', label: 'P/E', num: true, render: (r) => fmtX(r.pe) },
                { key: 'forward_pe', label: 'Fwd P/E', num: true, render: (r) => fmtX(r.forward_pe) },
                { key: 'dividend_yield', label: 'Div %', num: true, render: (r) => fmtNum(r.dividend_yield, 2) },
                { key: 'rsi14', label: 'RSI', num: true, render: (r) => fmtNum(r.rsi14, 0) },
                { key: 'year_high_dist', label: 'vs 52W high', num: true, render: (r) => <span className="muted">{fmtNum(r.year_high_dist, 1)}%</span> },
                { key: 'volume', label: 'Volume', num: true, render: (r) => fmtBig(r.volume) },
              ]} />}
            </Loadable>
          </Panel>
        </div>
      </div>
    </div>
  )
}
