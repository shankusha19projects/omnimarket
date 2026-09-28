import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart } from '../charts/EChart'
import { barOption, donutOption, treemapOption } from '../charts/builders'
import { Chg, ChgPill, DataTable, Loadable, Notice, Panel, Seg, Skel, SkelRows, Sparkline, Stat } from '../components/ui'
import { assetPath, fmtBig, fmtNum, fmtPrice } from '../services/format'

export default function Crypto() {
  const q = useApi('/crypto', { refetch: 90_000 })
  const [cat, setCat] = useState('All')
  const [hp, setHp] = useState<'change_24h' | 'change_7d' | 'change_30d'>('change_24h')
  const nav = useNavigate()
  return (
    <div className="page">
      <PageHead kicker="Digital assets" title="Crypto" desc="Top 100 by market cap from CoinGecko — Layer-1, Layer-2, DeFi, stablecoins, AI and infrastructure tokens. 24/7 markets; prices are aggregates across venues." />
      <Loadable q={q} skeleton={<SkelRows n={14} />}>
        {(d) => {
          if (!d.coins.length) return <Notice kind="bad">{d.error || 'Crypto data unavailable'}</Notice>
          const g = d.global || {}
          const dom = Object.entries(g.dominance || {}).sort((a: any, b: any) => b[1] - a[1]).slice(0, 6).map(([k, v]: any) => ({ name: k.toUpperCase(), value: +v.toFixed(2) }))
          const cats = ['All', ...Array.from(new Set(d.coins.map((c: any) => c.category))) as string[]]
          const rows = d.coins.filter((c: any) => cat === 'All' || c.category === cat)
          const tree = Object.values(d.coins.filter((c: any) => c.category !== 'Stablecoin').slice(0, 60).reduce((acc: any, c: any) => {
            (acc[c.category] ||= { name: c.category, children: [] }).children.push({ name: c.symbol, value: c.market_cap, perf: c[hp], label: c.name, price: fmtPrice(c.price) })
            return acc
          }, {}))
          return (
            <div className="grid">
              <div className="c-12"><div className="stats">
                <Stat label="Total market cap" value={fmtBig(g.total_market_cap, '$')} sub={<Chg v={g.market_cap_change_24h} />} />
                <Stat label="24h volume" value={fmtBig(g.total_volume, '$')} />
                <Stat label="BTC dominance" value={`${fmtNum(g.dominance?.btc, 1)}%`} />
                <Stat label="ETH dominance" value={`${fmtNum(g.dominance?.eth, 1)}%`} />
                <Stat label="BTC YTD" value={<Chg v={d.majors?.['BTC-USD']?.perf_ytd} digits={1} />} sub={`RV30 ${fmtNum(d.majors?.['BTC-USD']?.rv30, 0)}%`} />
                <Stat label="ETH YTD" value={<Chg v={d.majors?.['ETH-USD']?.perf_ytd} digits={1} />} sub={`RV30 ${fmtNum(d.majors?.['ETH-USD']?.rv30, 0)}%`} />
                <Stat label="Active assets" value={g.active_cryptocurrencies?.toLocaleString() || '—'} />
              </div></div>
              <div className="c-8">
                <Panel title="Crypto heatmap" sub="Ex-stablecoins · size = market cap" prov={d.provenance} actions={<Seg value={hp} options={[['change_24h', '24H'], ['change_7d', '7D'], ['change_30d', '30D']]} onChange={setHp} />}>
                  <EChart height={400} deps={[d, hp]} option={() => treemapOption(tree as any[], hp === 'change_24h' ? 6 : hp === 'change_7d' ? 15 : 30, hp.replace('change_', '').toUpperCase())}
                          onClick={(p) => p.data?.perf !== undefined && nav(assetPath(`${p.name}-USD`))} />
                </Panel>
              </div>
              <div className="c-4 col">
                <Panel title="Market dominance"><EChart height={180} deps={[d]} option={() => donutOption(dom, (v) => `${v}%`)} /></Panel>
                <Panel title="Category performance (24h, cap-weighted)">
                  <EChart height={200} deps={[d]} option={() => barOption(d.categories.map((c: any) => c.category), d.categories.map((c: any) => c.change_24h), { horizontal: true, colorBySign: true, format: (v) => `${v.toFixed(2)}%` })} />
                </Panel>
              </div>
              <div className="c-12">
                <Panel title="Top 100" flush actions={<Seg value={cat} options={cats} onChange={setCat} />}>
                  <DataTable rows={rows} onRow={(r) => nav(assetPath(r.yahoo))} pageSize={50} initialSort="market_cap" cols={[
                    { key: 'rank', label: '#', num: true, render: (r) => <span className="muted">{r.rank}</span> },
                    { key: 'name', label: 'Asset', render: (r) => <div className="row" style={{ gap: 8 }}><img src={r.image} width={20} height={20} alt="" style={{ borderRadius: 10 }} loading="lazy" /><b>{r.name}</b><span className="muted mono xs">{r.symbol}</span></div> },
                    { key: 'category', label: 'Category', render: (r) => <span className="badge">{r.category}</span> },
                    { key: 'price', label: 'Price', num: true, render: (r) => <b>${fmtPrice(r.price)}</b> },
                    { key: 'change_1h', label: '1h', num: true, render: (r) => <Chg v={r.change_1h} /> },
                    { key: 'change_24h', label: '24h', num: true, render: (r) => <ChgPill v={r.change_24h} /> },
                    { key: 'change_7d', label: '7d', num: true, render: (r) => <ChgPill v={r.change_7d} /> },
                    { key: 'change_30d', label: '30d', num: true, render: (r) => <ChgPill v={r.change_30d} digits={1} /> },
                    { key: 'change_1y', label: '1y', num: true, render: (r) => <ChgPill v={r.change_1y} digits={0} /> },
                    { key: 'market_cap', label: 'Market cap', num: true, render: (r) => fmtBig(r.market_cap, '$') },
                    { key: 'fdv', label: 'FDV', num: true, render: (r) => fmtBig(r.fdv, '$') },
                    { key: 'volume', label: 'Volume 24h', num: true, render: (r) => fmtBig(r.volume, '$') },
                    { key: 'circulating_supply', label: 'Circulating', num: true, render: (r) => fmtBig(r.circulating_supply) },
                    { key: 'max_supply', label: 'Max supply', num: true, render: (r) => (r.max_supply ? fmtBig(r.max_supply) : '∞') },
                    { key: 'spark', label: '7D', sortable: false, render: (r) => <div style={{ width: 100 }}><Sparkline data={r.spark} width={100} height={26} /></div> },
                  ]} />
                </Panel>
              </div>
            </div>
          )
        }}
      </Loadable>
      <div style={{ height: 1 }}><Skel h={0} /></div>
    </div>
  )
}
