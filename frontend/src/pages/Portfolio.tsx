import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { api, exportRowsCsv } from '../services/api'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart } from '../charts/EChart'
import { donutOption } from '../charts/builders'
import { Chg, ChgPill, DataTable, Empty, Loadable, Notice, Panel, SkelRows, Stat } from '../components/ui'
import { assetPath, fmtBig, fmtDate, fmtNum, fmtPrice } from '../services/format'

const blank = { symbol: '', quantity: '', purchase_price: '', purchase_date: '', notes: '' }

export default function Portfolio() {
  const q = useApi('/portfolio', { refetch: 60_000 })
  const [form, setForm] = useState<any>(blank)
  const [editId, setEditId] = useState<number | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const nav = useNavigate()
  const save = async () => {
    setErr(null)
    const body = { ...form, quantity: Number(form.quantity), purchase_price: Number(form.purchase_price), purchase_date: form.purchase_date || null, notes: form.notes || null }
    if (!body.symbol || !body.quantity) { setErr('Symbol and quantity are required.'); return }
    try {
      if (editId) await api.put(`/portfolio/positions/${editId}`, body)
      else await api.post('/portfolio/positions', body)
      setForm(blank); setEditId(null); q.refetch()
    } catch (e: any) { setErr(e.message) }
  }
  return (
    <div className="page">
      <PageHead kicker="Workspace" title="Portfolio" desc="Manually tracked positions valued with live quotes: P&L, allocation, sector / geographic / asset-class exposure and concentration. Research tracker only — no orders are ever placed." />
      <div className="grid">
        <div className="c-12">
          <Panel title={editId ? 'Edit position' : 'Add position'}>
            <div className="row wrap" style={{ alignItems: 'flex-end' }}>
              {[['symbol', 'Symbol', 'AAPL', 120], ['quantity', 'Quantity', '10', 110], ['purchase_price', 'Purchase price', '150.00', 130], ['purchase_date', 'Purchase date', '', 150], ['notes', 'Notes', 'thesis, account…', 260]].map(([k, l, ph, w]) => (
                <label className="field" key={k as string}>{l}<input className="input" type={k === 'purchase_date' ? 'date' : k === 'quantity' || k === 'purchase_price' ? 'number' : 'text'} step="any" placeholder={ph as string} style={{ width: w as number }} value={form[k as string]} onChange={(e) => setForm({ ...form, [k as string]: e.target.value })} /></label>
              ))}
              <button className="btn primary" onClick={save}><Plus size={14} /> {editId ? 'Update' : 'Add'}</button>
              {editId && <button className="btn ghost" onClick={() => { setEditId(null); setForm(blank) }}>Cancel</button>}
              {err && <span className="down small">{err}</span>}
            </div>
          </Panel>
        </div>
        <Loadable q={q} skeleton={<div className="c-12"><SkelRows n={8} /></div>}>
          {(d) => !d.positions.length ? <div className="c-12"><Panel><Empty title="No positions yet">{d.note}</Empty></Panel></div> : (
            <>
              <div className="c-12"><div className="stats">
                <Stat label="Market value" value={fmtBig(d.totals.market_value, '$')} />
                <Stat label="Cost basis" value={fmtBig(d.totals.cost_basis, '$')} />
                <Stat label="Unrealized P&L" value={<span className={d.totals.unrealized_pl >= 0 ? 'up' : 'down'}>{d.totals.unrealized_pl >= 0 ? '+' : ''}{fmtBig(d.totals.unrealized_pl, '$')}</span>} sub={<Chg v={d.totals.unrealized_pct} />} />
                <Stat label="Today" value={<span className={d.totals.day_pl >= 0 ? 'up' : 'down'}>{d.totals.day_pl >= 0 ? '+' : ''}{fmtBig(d.totals.day_pl, '$')}</span>} />
                <Stat label="Positions" value={d.totals.positions} />
                <Stat label="Effective N" value={fmtNum(d.concentration.effective_positions, 1)} sub={`HHI ${fmtNum(d.concentration.hhi, 3)}`} title={d.concentration.method} />
                <Stat label="Largest weight" value={`${fmtNum(d.concentration.largest_weight, 1)}%`} />
              </div></div>
              {d.concentration.largest_weight > 25 && <div className="c-12"><Notice kind="warn">Concentration: the largest position is {fmtNum(d.concentration.largest_weight, 1)}% of the portfolio.</Notice></div>}
              <div className="c-12">
                <Panel title="Positions" flush actions={<button className="btn sm" onClick={() => exportRowsCsv(d.positions, 'portfolio.csv')}>Export CSV</button>}>
                  <DataTable rows={d.positions} onRow={(r) => nav(assetPath(r.symbol))} initialSort="market_value" rowKey={(r) => String(r.id)} cols={[
                    { key: 'symbol', label: 'Symbol', render: (r) => <div><span className="sym">{r.symbol}</span><div className="muted xs">{r.name}</div></div> },
                    { key: 'sector', label: 'Sector', render: (r) => <span className="muted">{r.sector}</span> },
                    { key: 'quantity', label: 'Qty', num: true, render: (r) => fmtNum(r.quantity, r.quantity % 1 ? 4 : 0) },
                    { key: 'purchase_price', label: 'Cost / sh', num: true, render: (r) => fmtPrice(r.purchase_price) },
                    { key: 'price', label: 'Last', num: true, render: (r) => fmtPrice(r.price) },
                    { key: 'change_pct', label: '1D', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
                    { key: 'market_value', label: 'Value', num: true, render: (r) => fmtBig(r.market_value, '$') },
                    { key: 'unrealized_pl', label: 'P&L', num: true, render: (r) => <Chg v={r.unrealized_pl} pct={false} /> },
                    { key: 'unrealized_pct', label: 'Return', num: true, render: (r) => <ChgPill v={r.unrealized_pct} /> },
                    { key: 'weight', label: 'Weight', num: true, render: (r) => `${fmtNum(r.weight, 1)}%` },
                    { key: 'purchase_date', label: 'Bought', render: (r) => <span className="muted">{r.purchase_date ? fmtDate(r.purchase_date) : '—'}</span> },
                    { key: 'actions', label: '', sortable: false, render: (r) => <span className="row" style={{ gap: 2 }} onClick={(e) => e.stopPropagation()}>
                      <button className="icon-btn sm ghost" aria-label="Edit" onClick={() => { setEditId(r.id); setForm({ symbol: r.symbol, quantity: r.quantity, purchase_price: r.purchase_price, purchase_date: r.purchase_date || '', notes: r.notes || '' }) }}><Pencil size={12} /></button>
                      <button className="icon-btn sm ghost" aria-label="Delete" onClick={async () => { if (confirm(`Remove ${r.symbol}?`)) { await api.del(`/portfolio/positions/${r.id}`); q.refetch() } }}><Trash2 size={12} /></button></span> },
                  ]} />
                </Panel>
              </div>
              {(['sector', 'country', 'asset_class'] as const).map((k) => (
                <div className="c-4" key={k}><Panel title={`${k === 'asset_class' ? 'Asset class' : k === 'country' ? 'Geographic' : 'Sector'} exposure`}>
                  <EChart height={240} deps={[d]} option={() => donutOption(d.exposure[k].map((e: any) => ({ name: e.name, value: +e.value.toFixed(2) })), (v) => fmtBig(v, '$'))} />
                </Panel></div>
              ))}
            </>
          )}
        </Loadable>
      </div>
    </div>
  )
}
