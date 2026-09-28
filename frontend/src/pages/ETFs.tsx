import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { ChgPill, DataTable, Loadable, Panel, Seg, SkelRows } from '../components/ui'
import { assetPath, fmtBig, fmtPrice, fmtRatioPct } from '../services/format'

export default function ETFs() {
  const q = useApi('/etfs', { refetch: 120_000 })
  const [group, setGroup] = useState('All')
  const nav = useNavigate()
  return (
    <div className="page">
      <PageHead kicker="Funds" title="ETFs" desc="Broad market, sector, factor, thematic, international, commodity, fixed income, leveraged and inverse funds. Open any fund for holdings, sector exposure, NAV, AUM and expense ratio." />
      <Loadable q={q} skeleton={<SkelRows n={14} />}>
        {(d) => {
          const groups = Object.keys(d.groups)
          const rows = (group === 'All' ? groups : [group]).flatMap((g) => d.groups[g].map((r: any) => ({ ...r, category: g })))
          return (
            <Panel title="Fund monitor" flush prov={rows[0]?.provenance} actions={<Seg value={group} options={['All', ...groups]} onChange={setGroup} />}>
              <DataTable rows={rows} onRow={(r) => nav(assetPath(r.symbol))} cols={[
                { key: 'symbol', label: 'Symbol', render: (r) => <span className="sym">{r.symbol}</span> },
                { key: 'name', label: 'Fund' },
                { key: 'category', label: 'Category', render: (r) => <span className="badge">{r.category}</span> },
                { key: 'price', label: 'Price', num: true, render: (r) => fmtPrice(r.price) },
                { key: 'change_pct', label: '1D', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
                { key: 'ytd_return', label: 'YTD', num: true, render: (r) => <ChgPill v={r.ytd_return} digits={1} /> },
                { key: 'perf_1y', label: '52W', num: true, render: (r) => <ChgPill v={r.perf_1y} digits={1} /> },
                { key: 'aum', label: 'AUM', num: true, render: (r) => fmtBig(r.aum, '$') },
                { key: 'expense_ratio', label: 'Expense', num: true, render: (r) => (r.expense_ratio != null ? `${r.expense_ratio.toFixed(2)}%` : '—') },
                { key: 'yield', label: 'Yield', num: true, render: (r) => fmtRatioPct(r.yield, 2) },
                { key: 'volume', label: 'Volume', num: true, render: (r) => fmtBig(r.volume) },
              ]} />
            </Panel>
          )
        }}
      </Loadable>
    </div>
  )
}
