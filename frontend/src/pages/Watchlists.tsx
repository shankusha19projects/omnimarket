import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowDown, ArrowUp, Pencil, Plus, Trash2, X } from 'lucide-react'
import { api } from '../services/api'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { Chg, ChgPill, DataTable, Empty, Loadable, Panel, SkelRows, Sparkline } from '../components/ui'
import { assetPath, fmtPrice } from '../services/format'

export default function Watchlists() {
  const lists = useApi<any[]>('/watchlists')
  const [active, setActive] = useState<number | null>(null)
  useEffect(() => { if (!active && lists.data?.length) setActive(lists.data[0].id) }, [lists.data, active])
  const wl = useApi(active ? `/watchlists/${active}` : null, { refetch: 45_000 })
  const [newName, setNewName] = useState('')
  const [add, setAdd] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const nav = useNavigate()
  const refresh = () => { lists.refetch(); wl.refetch() }
  const addSymbol = async () => {
    if (!add.trim() || !active) return
    setErr(null)
    try { await api.post(`/watchlists/${active}/items`, { symbol: add.trim() }); setAdd(''); refresh() } catch (e: any) { setErr(e.message) }
  }
  const move = async (sym: string, d: -1 | 1) => {
    const syms = (wl.data?.rows || []).map((r: any) => r.symbol)
    const i = syms.indexOf(sym), j = i + d
    if (j < 0 || j >= syms.length) return
    ;[syms[i], syms[j]] = [syms[j], syms[i]]
    await api.put(`/watchlists/${active}/order`, syms)
    wl.refetch()
  }
  return (
    <div className="page">
      <PageHead kicker="Workspace" title="Watchlists" desc="Multiple persistent watchlists stored in local SQLite. Mix stocks, ETFs, indices, futures, FX and crypto." />
      <div className="grid">
        <div className="c-3">
          <Panel title="Lists">
            {(lists.data || []).map((l) => (
              <div key={l.id} className="row" style={{ padding: '3px 0' }}>
                <button className="btn ghost" style={{ flex: 1, justifyContent: 'space-between', background: active === l.id ? 'var(--panel-2)' : undefined }} onClick={() => setActive(l.id)}>
                  <span>{l.name}</span><span className="muted xs">{l.symbols.length}</span>
                </button>
                <button className="icon-btn sm ghost" aria-label="Rename" onClick={async () => { const n = prompt('Rename watchlist', l.name); if (n) { await api.put(`/watchlists/${l.id}`, { name: n }); refresh() } }}><Pencil size={12} /></button>
                <button className="icon-btn sm ghost" aria-label="Delete" onClick={async () => { if (confirm(`Delete "${l.name}"?`)) { await api.del(`/watchlists/${l.id}`); setActive(null); refresh() } }}><Trash2 size={12} /></button>
              </div>
            ))}
            <form className="row" style={{ marginTop: 8 }} onSubmit={async (e) => { e.preventDefault(); if (!newName.trim()) return; try { const r = await api.post('/watchlists', { name: newName }); setNewName(''); setActive(r.id); refresh() } catch (x: any) { setErr(x.message) } }}>
              <input className="input sm" placeholder="New watchlist" value={newName} onChange={(e) => setNewName(e.target.value)} style={{ flex: 1 }} />
              <button className="btn sm"><Plus size={12} /></button>
            </form>
          </Panel>
        </div>
        <div className="c-9">
          <Panel title={wl.data?.name || 'Watchlist'} flush actions={
            <form className="row" onSubmit={(e) => { e.preventDefault(); addSymbol() }}>
              <input className="input sm mono" placeholder="Add symbol (NVDA, GC=F, BTC-USD…)" value={add} onChange={(e) => setAdd(e.target.value)} style={{ width: 230 }} />
              <button className="btn sm primary"><Plus size={12} /> Add</button>
              {err && <span className="down xs">{err}</span>}
            </form>}>
            <Loadable q={wl} skeleton={<div style={{ padding: 14 }}><SkelRows n={8} /></div>}>
              {(d) => d.rows.length ? <DataTable rows={d.rows} onRow={(r) => nav(assetPath(r.symbol))} cols={[
                { key: 'symbol', label: 'Symbol', render: (r) => <span className="sym">{r.symbol}</span> },
                { key: 'name', label: 'Name', render: (r) => <span className="nm" style={{ display: 'inline-block' }}>{r.name}</span> },
                { key: 'asset_class', label: 'Class', render: (r) => <span className="badge">{r.asset_class}</span> },
                { key: 'spark', label: '1D', sortable: false, render: (r) => <div style={{ width: 100 }}><Sparkline data={r.spark} width={100} height={24} /></div> },
                { key: 'price', label: 'Last', num: true, render: (r) => (r.unavailable ? <span className="muted">n/a</span> : <b>{fmtPrice(r.price)}</b>) },
                { key: 'change', label: 'Chg', num: true, render: (r) => <Chg v={r.change} pct={false} /> },
                { key: 'change_pct', label: '%', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
                { key: 'x', label: '', sortable: false, render: (r) => <span className="row" style={{ gap: 2 }} onClick={(e) => e.stopPropagation()}>
                  <button className="icon-btn sm ghost" aria-label="Move up" onClick={() => move(r.symbol, -1)}><ArrowUp size={12} /></button>
                  <button className="icon-btn sm ghost" aria-label="Move down" onClick={() => move(r.symbol, 1)}><ArrowDown size={12} /></button>
                  <button className="icon-btn sm ghost" aria-label="Remove" onClick={async () => { await api.del(`/watchlists/${active}/items/${encodeURIComponent(r.symbol)}`); refresh() }}><X size={12} /></button></span> },
              ]} /> : <Empty title="Empty watchlist">Add a symbol above.</Empty>}
            </Loadable>
          </Panel>
        </div>
      </div>
    </div>
  )
}
