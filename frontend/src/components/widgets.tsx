/* Reusable market widgets shared by the dashboard and section pages. */
import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { Download } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { EChart, type EChartHandle, chartColors } from '../charts/EChart'
import { barOption, lineOption, treemapOption } from '../charts/builders'
import { saveBlob } from '../services/api'
import { assetPath, dir, fmtBig, fmtDateTime, fmtNum, fmtPct, fmtPrice, fmtTime, isNum, timeAgo } from '../services/format'
import { AssetLink, Chg, ChgPill, DataTable, Loadable, MarketState, Panel, RangeBar, Seg, Skel, SkelRows, Sparkline, Stat, type Col } from './ui'

export function pngButton(ref: React.RefObject<EChartHandle | null>, name: string) {
  return (
    <button className="icon-btn sm ghost" title="Export chart as PNG" aria-label="Export PNG" onClick={() => {
      const url = ref.current?.png()
      if (!url) return
      fetch(url).then((r) => r.blob()).then((b) => saveBlob(b, `${name}.png`))
    }}><Download size={14} /></button>
  )
}

export function QuoteCard({ c }: { c: any }) {
  const d = dir(c.change_pct)
  return (
    <Link to={assetPath(c.symbol)} className={clsx('kpi', d)}>
      <div className="kpi-top">
        <span className="kpi-name">{c.name}</span>
        <span className="kpi-state">{c.market_state === 'REGULAR' ? <span className="up">● open</span> : c.asset_class === 'crypto' ? '24/7' : c.market_state ? 'closed' : ''}</span>
      </div>
      <div className="row" style={{ alignItems: 'baseline', gap: 8 }}>
        <span className="kpi-price">{c.unavailable ? 'n/a' : fmtPrice(c.price)}</span>
        <ChgPill v={c.change_pct} />
      </div>
      <div className="kpi-spark"><Sparkline data={c.spark} height={38} width={200} /></div>
      <div className="kpi-foot">
        <span>{isNum(c.change) ? `${c.change > 0 ? '+' : ''}${fmtPrice(c.change)}` : ''}</span>
        <span title="Day range">{isNum(c.day_low) && c.day_high > 0 ? `${fmtPrice(c.day_low)} – ${fmtPrice(c.day_high)}` : ''}</span>
      </div>
    </Link>
  )
}

export function OverviewCards() {
  const q = useApi('/markets/overview', { refetch: 60_000 })
  return (
    <Loadable q={q} skeleton={<div className="cards">{Array.from({ length: 10 }).map((_, i) => <Skel key={i} h={128} r={12} />)}</div>}>
      {(d) => <div className="cards">{d.cards.map((c: any) => <QuoteCard key={c.symbol} c={c} />)}</div>}
    </Loadable>
  )
}

export function IndicesTable({ region: initial = 'All' }: { region?: string }) {
  const q = useApi('/markets/indices', { refetch: 60_000 })
  const [region, setRegion] = useState(initial)
  const nav = useNavigate()
  const cols: Col<any>[] = [
    { key: 'name', label: 'Market', render: (r) => <div><div style={{ fontWeight: 600 }}>{r.name}</div><div className="muted xs mono">{r.symbol} · {r.country}</div></div>, value: (r) => r.name },
    { key: 'spark', label: '1D', sortable: false, render: (r) => <div style={{ width: 80 }}><Sparkline data={r.spark} width={80} height={24} /></div> },
    { key: 'price', label: 'Last', num: true, render: (r) => <b>{fmtPrice(r.price)}</b> },
    { key: 'change', label: 'Chg', num: true, render: (r) => <Chg v={r.change} pct={false} /> },
    { key: 'change_pct', label: '%', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
    { key: 'day_high', label: 'High', num: true, render: (r) => fmtPrice(r.day_high || null) },
    { key: 'day_low', label: 'Low', num: true, render: (r) => fmtPrice(r.day_low || null) },
    { key: 'range', label: '52W range', sortable: false, render: (r) => <div style={{ width: 110 }}><RangeBar low={r.year_low} high={r.year_high} value={r.price} /></div> },
    { key: 'volume', label: 'Volume', num: true, render: (r) => fmtBig(r.volume) },
    { key: 'market_time', label: 'Time', num: true, render: (r) => <span className="muted">{fmtTime(r.market_time)}</span> },
  ]
  return (
    <Panel title="Global indices" sub="Delayed per exchange; hover the source badge for provenance" actions={<Seg value={region} options={['All', 'Americas', 'Europe', 'Asia-Pacific']} onChange={setRegion} />}
           prov={q.data?.rows?.[0]?.provenance} flush>
      <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={8} /></div>}>
        {(d) => <DataTable rows={d.rows.filter((r: any) => region === 'All' || r.region === region)} cols={cols} onRow={(r) => nav(assetPath(r.symbol))} maxHeight={470} />}
      </Loadable>
    </Panel>
  )
}

export function Heatmap({ height = 460 }: { height?: number }) {
  const [period, setPeriod] = useState<'1d' | '5d' | '1m' | 'ytd' | '1y'>('1d')
  const [group, setGroup] = useState<'sector' | 'industry' | 'cap'>('sector')
  const q = useApi(`/markets/heatmap?period=${period}&group_by=${group}`, { refetch: 120_000 })
  const nav = useNavigate()
  const ref = useRef<EChartHandle>(null)
  const clamp = { '1d': 3, '5d': 6, '1m': 10, ytd: 30, '1y': 40 }[period]
  return (
    <Panel title="Market heatmap" sub="US large caps · tile size = market cap · color = performance" accent
           actions={<>
             <Seg value={group} options={[['sector', 'Sector'], ['industry', 'Industry'], ['cap', 'Size']]} onChange={setGroup} />
             <Seg value={period} options={[['1d', '1D'], ['5d', '5D'], ['1m', '1M'], ['ytd', 'YTD'], ['1y', '1Y']]} onChange={setPeriod} />
             {pngButton(ref, `heatmap_${period}`)}
           </>} prov={q.data?.provenance}>
      <Loadable q={q} skeleton={<Skel h={height} r={8} />}>
        {(d) => <EChart ref={ref} height={height} deps={[d, period]} option={() => treemapOption(d.tree, clamp, period.toUpperCase())} onClick={(p) => p.data?.perf !== undefined && nav(assetPath(p.name))} />}
      </Loadable>
      <div className="row xs muted" style={{ marginTop: 8, justifyContent: 'center', gap: 4 }}>
        {[-clamp, -clamp / 2, 0, clamp / 2, clamp].map((v) => <span key={v} className="mono" style={{ padding: '2px 8px', borderRadius: 4, color: '#fff', background: v === 0 ? 'rgba(110,120,140,.4)' : v > 0 ? `rgba(22,168,108,${0.3 + v / clamp * 0.6})` : `rgba(211,59,87,${0.3 - v / clamp * 0.6})` }}>{fmtPct(v, 0)}</span>)}
      </div>
    </Panel>
  )
}

export function Movers() {
  const q = useApi('/markets/movers', { refetch: 60_000 })
  const [tab, setTab] = useState<'gainers' | 'losers' | 'unusual_volume'>('gainers')
  const nav = useNavigate()
  return (
    <Panel title="Movers" sub="Tracked US large caps" actions={<Seg value={tab} options={[['gainers', 'Gainers'], ['losers', 'Losers'], ['unusual_volume', 'Volume']]} onChange={setTab} />} flush>
      <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={8} /></div>}>
        {(d) => <DataTable compact rows={d[tab]} onRow={(r) => nav(assetPath(r.symbol))} cols={[
          { key: 'symbol', label: 'Symbol', render: (r) => <div><span className="sym">{r.symbol}</span><div className="muted xs truncate" style={{ maxWidth: 150 }}>{r.name}</div></div> },
          { key: 'price', label: 'Last', num: true, render: (r) => fmtPrice(r.price) },
          { key: 'change_pct', label: '%', num: true, render: (r) => <ChgPill v={r.change_pct} /> },
          { key: 'rvol', label: 'Rel vol', num: true, value: (r) => (r.volume || 0) / (r.avg_volume || 1), render: (r) => fmtNum((r.volume || 0) / (r.avg_volume || 1), 2) + '×' },
        ]} />}
      </Loadable>
    </Panel>
  )
}

export function Breadth() {
  const q = useApi('/markets/breadth', { refetch: 300_000 })
  return (
    <Panel title="Market breadth" sub="Tracked US large caps">
      <Loadable q={q} skeleton={<SkelRows n={5} />}>
        {(d) => {
          const tot = d.advancers + d.decliners + d.unchanged || 1
          return (
            <div className="col" style={{ gap: 12 }}>
              <div>
                <div className="row small" style={{ justifyContent: 'space-between', marginBottom: 5 }}>
                  <span className="up">▲ {d.advancers} advancing</span><span className="muted">{d.unchanged} flat</span><span className="down">{d.decliners} declining ▼</span>
                </div>
                <div className="split-bar"><i style={{ width: `${d.advancers / tot * 100}%`, background: 'var(--up)' }} /><i style={{ width: `${d.unchanged / tot * 100}%`, background: 'var(--text-4)' }} /><i style={{ width: `${d.decliners / tot * 100}%`, background: 'var(--down)' }} /></div>
              </div>
              {[['Above 20-DMA', d.above_20dma_pct], ['Above 50-DMA', d.above_50dma_pct], ['Above 200-DMA', d.above_200dma_pct]].map(([l, v]) => (
                <div key={l as string}>
                  <div className="row small" style={{ justifyContent: 'space-between', marginBottom: 4 }}><span className="dim">{l}</span><span className="mono">{fmtNum(v, 1)}%</span></div>
                  <div className="meter"><i style={{ width: `${v || 0}%` }} /></div>
                </div>
              ))}
              <div className="stats" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <Stat label="52W highs" value={<span className="up">{d.new_highs_52w}</span>} />
                <Stat label="52W lows" value={<span className="down">{d.new_lows_52w}</span>} />
              </div>
              <div className="muted xs">{d.method}</div>
            </div>
          )
        }}
      </Loadable>
    </Panel>
  )
}

export function Volatility() {
  const q = useApi('/markets/volatility', { refetch: 300_000 })
  return (
    <Panel title="Volatility" prov={q.data?.vix?.provenance}>
      <Loadable q={q} skeleton={<SkelRows n={6} />}>
        {(d) => (
          <div className="col" style={{ gap: 10 }}>
            <div className="stats" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              <Stat label="VIX" value={fmtNum(d.vix?.price, 2)} sub={<><Chg v={d.vix?.change_pct} /> · {d.vix_1y_percentile ?? '—'}th pct 1Y</>} />
              <Stat label="MOVE" value={fmtNum(d.move?.price, 1)} sub={<Chg v={d.move?.change_pct} />} />
              <Stat label="VIX − RV20" value={fmtNum(d.variance_risk_premium, 2)} sub="implied − realized" title="Variance risk premium proxy" />
            </div>
            <EChart height={120} deps={[d]} option={() => lineOption([{ name: 'VIX', data: d.vix_history.map((p: any) => [p.t * 1000, p.c]), area: true, color: chartColors().amber }], { yFormat: (v) => v.toFixed(0) })} />
            <table className="t compact">
              <thead><tr><th>Realized vol</th><th className="num">20d</th><th className="num">60d</th><th className="num">1Y</th></tr></thead>
              <tbody>{Object.entries(d.realized).map(([s, r]: any) => (
                <tr key={s}><td><AssetLink symbol={s}>{r.label}</AssetLink></td><td className="num">{fmtNum(r.rv20, 1)}%</td><td className="num">{fmtNum(r.rv60, 1)}%</td><td className="num">{fmtNum(r.rv252, 1)}%</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </Loadable>
    </Panel>
  )
}

export function YieldCurveMini({ height = 220 }: { height?: number }) {
  const q = useApi('/bonds', { refetch: 600_000 })
  return (
    <Panel title="US Treasury curve" sub={q.data?.as_of ? `As of ${q.data.as_of}` : undefined} prov={q.data?.provenance} actions={<Link to="/bonds" className="small">Rates →</Link>}>
      <Loadable q={q} skeleton={<Skel h={height} />}>
        {(d) => d.available ? (
          <>
            <EChart height={height} deps={[d]} option={() => curveOption(d)} />
            <div className="stats" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginTop: 6 }}>
              {Object.entries(d.spreads).slice(0, 3).map(([k, v]: any) => <Stat key={k} label={k} value={<span className={dir(v)}>{v > 0 ? '+' : ''}{fmtNum(v * 100, 0)} bp</span>} />)}
            </div>
          </>
        ) : <div className="muted">{d.reason}</div>}
      </Loadable>
    </Panel>
  )
}

export function curveOption(d: any, showCompare = true) {
  const c = chartColors()
  const pts = (y: any) => d.tenors.filter((t: string) => y && y[t] !== undefined).map((t: string) => [d.tenor_years[t], y[t]])
  const series: any[] = [{ name: `Today (${d.as_of})`, type: 'line', data: pts(d.curve), symbolSize: 6, lineStyle: { width: 2.5, color: c.accent }, itemStyle: { color: c.accent },
    areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: c.accent + '33' }, { offset: 1, color: c.accent + '00' }] } } }]
  if (showCompare) {
    const cols = [c.amber, c.violet, c.text]
    Object.entries(d.compare).forEach(([k, y]: any, i) => { if (y) series.push({ name: `${k} (${d.compare_dates[k]})`, type: 'line', data: pts(y), symbol: 'none', lineStyle: { width: 1.2, type: 'dashed', color: cols[i] }, itemStyle: { color: cols[i] } }) })
  }
  return {
    grid: { left: 6, right: 12, top: 30, bottom: 4, containLabel: true },
    legend: { top: 0, textStyle: { color: c.text2, fontSize: 10.5 }, icon: 'roundRect', itemWidth: 10, itemHeight: 3 },
    tooltip: { trigger: 'axis', valueFormatter: (v: any) => (isNum(v) ? `${v.toFixed(2)}%` : '—') },
    xAxis: { type: 'log', logBase: 2, min: 1 / 12, max: 30, axisLabel: { color: c.text, fontFamily: 'JetBrains Mono', fontSize: 10, formatter: (v: number) => (v < 1 ? `${Math.round(v * 12)}M` : `${v}Y`) }, axisLine: { lineStyle: { color: c.line } }, splitLine: { show: false } },
    yAxis: { type: 'value', scale: true, axisLabel: { color: c.text, fontFamily: 'JetBrains Mono', fontSize: 10, formatter: '{value}%' }, splitLine: { lineStyle: { color: c.grid } } },
    series,
  } as any
}

export function CryptoMini() {
  const q = useApi('/crypto', { refetch: 120_000 })
  const nav = useNavigate()
  return (
    <Panel title="Crypto" prov={q.data?.provenance} actions={<Link to="/crypto" className="small">All →</Link>} flush>
      <Loadable q={q} skeleton={<div style={{ padding: 14 }}><SkelRows n={8} /></div>}>
        {(d) => d.coins.length ? <DataTable compact rows={d.coins.slice(0, 9)} onRow={(r) => nav(assetPath(r.yahoo))} cols={[
          { key: 'name', label: 'Asset', render: (r) => <div className="row" style={{ gap: 8 }}><img src={r.image} alt="" width={18} height={18} style={{ borderRadius: 9 }} loading="lazy" /><span style={{ fontWeight: 600 }}>{r.symbol}</span></div> },
          { key: 'price', label: 'Price', num: true, render: (r) => fmtPrice(r.price) },
          { key: 'change_24h', label: '24h', num: true, render: (r) => <Chg v={r.change_24h} /> },
          { key: 'spark', label: '7D', sortable: false, render: (r) => <div style={{ width: 70 }}><Sparkline data={r.spark} width={70} height={20} fill={false} /></div> },
          { key: 'market_cap', label: 'Mkt cap', num: true, render: (r) => fmtBig(r.market_cap, '$') },
        ]} /> : <div className="muted" style={{ padding: 14 }}>{d.error || 'Crypto data unavailable'}</div>}
      </Loadable>
    </Panel>
  )
}

export function SectorBars() {
  const q = useApi('/markets/sectors', { refetch: 300_000 })
  const [p, setP] = useState<'change_pct' | 'perf_1w' | 'perf_1m' | 'perf_ytd'>('change_pct')
  return (
    <Panel title="Sector performance" sub="SPDR sector ETFs" actions={<Seg value={p} options={[['change_pct', '1D'], ['perf_1w', '1W'], ['perf_1m', '1M'], ['perf_ytd', 'YTD']]} onChange={setP} />}>
      <Loadable q={q} skeleton={<Skel h={300} />}>
        {(d) => {
          const rows = [...d.rows].sort((a: any, b: any) => (b[p] ?? -99) - (a[p] ?? -99))
          return <EChart height={310} deps={[d, p]} option={() => barOption(rows.map((r: any) => r.sector), rows.map((r: any) => r[p]), { horizontal: true, colorBySign: true, format: (v) => `${v > 0 ? '+' : ''}${v.toFixed(2)}%` })} />
        }}
      </Loadable>
    </Panel>
  )
}

export function MarketMovingNews({ limit = 6 }: { limit?: number }) {
  const q = useApi('/news/market-moving', { refetch: 300_000 })
  return (
    <Panel title="Potential market-moving developments" sub="Ranked by an explicit attention score — not a prediction" actions={<Link to="/news" className="small">News →</Link>}>
      <Loadable q={q} skeleton={<SkelRows n={5} />} empty={(d) => !d.items.length}>
        {(d) => (
          <div className="col" style={{ gap: 8 }}>
            {d.items.slice(0, limit).map((c: any) => <ClusterCard key={c.id} c={c} />)}
          </div>
        )}
      </Loadable>
    </Panel>
  )
}

export function ClusterCard({ c }: { c: any }) {
  const [open, setOpen] = useState(false)
  const s = Math.min(1, c.score / 9)
  return (
    <div className="cluster">
      <div className="row" style={{ alignItems: 'flex-start', gap: 10 }}>
        <div className="score-ring" title={`Attention score ${c.score} — ${Object.entries(c.components).map(([k, v]) => `${k}: ${v}`).join(', ')}`}
             style={{ background: `conic-gradient(var(--amber) ${s * 360}deg, var(--panel-3) 0)`, position: 'relative' }}>
          <span style={{ position: 'absolute', inset: 4, borderRadius: '50%', background: 'var(--panel-2)', display: 'grid', placeItems: 'center' }}>{c.score.toFixed(1)}</span>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <a href={c.articles[0]?.url} target="_blank" rel="noreferrer noopener" style={{ color: 'var(--text)', fontWeight: 600, fontSize: 13, lineHeight: 1.35 }}>{c.headline}</a>
          <div className="row xs muted" style={{ marginTop: 4, flexWrap: 'wrap', gap: 6 }}>
            <span className="badge info">{c.category}</span>
            <span>{c.size} report{c.size > 1 ? 's' : ''} · {c.publishers.length} publisher{c.publishers.length > 1 ? 's' : ''}</span>
            <span>{timeAgo(c.last_update)}</span>
            {c.tickers.slice(0, 5).map((t: string) => <AssetLink key={t} symbol={t} className="tag link">{t}{isNum(c.ticker_moves?.[t]) ? ` ${fmtPct(c.ticker_moves[t], 1)}` : ''}</AssetLink>)}
          </div>
          {c.size > 1 && <button className="btn ghost sm" style={{ marginTop: 4, paddingLeft: 0 }} onClick={() => setOpen(!open)}>{open ? 'Hide' : 'Show'} {c.size} publications</button>}
          {open && <div className="col" style={{ gap: 4, marginTop: 2 }}>{c.articles.map((a: any, i: number) => (
            <a key={i} href={a.url} target="_blank" rel="noreferrer noopener" className="small" style={{ color: 'var(--text-2)' }}><b style={{ color: 'var(--text)' }}>{a.publisher}</b> · {a.title} <span className="muted">({fmtDateTime(a.published_at)})</span></a>
          ))}</div>}
        </div>
      </div>
    </div>
  )
}

export function QuoteHeaderStats({ q }: { q: any }) {
  return (
    <div className="stats">
      <Stat label="Open" value={fmtPrice(q.open)} />
      <Stat label="Prev close" value={fmtPrice(q.prev_close)} />
      <Stat label="Day range" value={<span style={{ fontSize: 13 }}>{fmtPrice(q.day_low)} – {fmtPrice(q.day_high)}</span>} />
      <Stat label="52W range" value={<span style={{ fontSize: 13 }}>{fmtPrice(q.year_low)} – {fmtPrice(q.year_high)}</span>} sub={<RangeBar low={q.year_low} high={q.year_high} value={q.price} />} />
      <Stat label="Volume" value={fmtBig(q.volume)} sub={q.avg_volume ? `avg ${fmtBig(q.avg_volume)}` : undefined} />
      <Stat label="Market cap" value={fmtBig(q.market_cap, '$')} />
      {q.pre_price && <Stat label="Pre-market" value={fmtPrice(q.pre_price)} sub={<Chg v={q.pre_change_pct} />} />}
      {q.post_price && <Stat label="After-hours" value={fmtPrice(q.post_price)} sub={<Chg v={q.post_change_pct} />} />}
      <Stat label="State" value={<MarketState state={q.market_state} />} />
    </div>
  )
}
