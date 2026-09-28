import { useState } from 'react'
import { Search } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { ClusterCard } from '../components/widgets'
import { AssetLink, Loadable, Panel, Seg, SkelRows, StatusDot } from '../components/ui'
import { fmtDateTime, timeAgo } from '../services/format'

export default function News() {
  const [cat, setCat] = useState('All')
  const [q, setQ] = useState('')
  const [view, setView] = useState<'clusters' | 'stream'>('clusters')
  const [term, setTerm] = useState('')
  const stream = useApi(`/news?limit=200${cat !== 'All' ? `&category=${encodeURIComponent(cat)}` : ''}${term ? `&q=${encodeURIComponent(term)}` : ''}`, { refetch: 300_000 })
  const clusters = useApi(view === 'clusters' ? '/news/clusters?hours=48' : null, { refetch: 300_000 })
  const cats: string[] = stream.data?.categories || ['All']
  return (
    <div className="page">
      <PageHead kicker="Intelligence" title="News Intelligence" desc="Aggregated publisher feeds, deduplicated into event clusters and ranked by an explicit, auditable attention score. Only headlines, metadata and short excerpts are shown — follow links for full articles."
                actions={<Seg value={view} options={[['clusters', 'Event clusters'], ['stream', 'Live stream']]} onChange={setView} />} />
      <div className="row wrap" style={{ marginBottom: 12 }}>
        <div className="chip-row" style={{ flex: 1 }}>{cats.map((c) => <button key={c} className={`chip ${cat === c ? 'on' : ''}`} onClick={() => setCat(c)}>{c}</button>)}</div>
        <form className="row" onSubmit={(e) => { e.preventDefault(); setTerm(q) }} style={{ position: 'relative' }}>
          <Search size={13} style={{ position: 'absolute', left: 9, color: 'var(--text-3)' }} />
          <input className="input" style={{ paddingLeft: 28, width: 240 }} placeholder="Search headlines or tickers" value={q} onChange={(e) => setQ(e.target.value)} />
        </form>
      </div>
      <div className="grid">
        <div className="c-8">
          {view === 'clusters' ? (
            <Panel title="Event clusters · last 48h" sub="Multiple publications about the same event are merged. Score components are shown on hover.">
              <Loadable q={clusters} skeleton={<SkelRows n={10} />} empty={(d) => !d.clusters.length}>
                {(d) => <div className="col" style={{ gap: 8 }}>{d.clusters.filter((c: any) => cat === 'All' || c.category === cat).filter((c: any) => !term || c.headline.toLowerCase().includes(term.toLowerCase()) || c.tickers.includes(term.toUpperCase())).map((c: any) => <ClusterCard key={c.id} c={c} />)}</div>}
              </Loadable>
            </Panel>
          ) : (
            <Panel title="Live stream" sub={stream.data?.last_refresh ? `Feeds refreshed ${timeAgo(stream.data.last_refresh)}` : undefined} prov={stream.data?.provenance}>
              <Loadable q={stream} skeleton={<SkelRows n={12} />} empty={(d) => !d.items.length}>
                {(d) => <div>{d.items.map((n: any) => (
                  <article className="news-item" key={n.id}>
                    {n.thumbnail && <img className="thumb" src={n.thumbnail} alt="" loading="lazy" referrerPolicy="no-referrer" />}
                    <div style={{ minWidth: 0 }}>
                      <a className="hl" href={n.url} target="_blank" rel="noreferrer noopener">{n.title}</a>
                      {n.summary && <div className="sum">{n.summary}</div>}
                      <div className="meta"><b>{n.publisher}</b><span>{fmtDateTime(n.published_at)} · {timeAgo(n.published_at)}</span><span className="badge info">{n.category}</span>
                        {n.tickers.slice(0, 5).map((t: string) => <AssetLink key={t} symbol={t} className="tag link">{t}</AssetLink>)}
                        <span className="muted xs">retrieved {timeAgo(n.retrieved_at)}</span></div>
                    </div>
                  </article>
                ))}</div>}
              </Loadable>
            </Panel>
          )}
        </div>
        <div className="c-4 col">
          <Panel title="Feed health" sub="Publisher RSS sources">
            {(stream.data?.feed_status || []).map((f: any) => (
              <div className="row small" key={f.feed} style={{ padding: '4px 0', borderBottom: '1px solid var(--line)' }}>
                <StatusDot status={f.ok ? 'online' : 'error'} /><span style={{ flex: 1 }}>{f.publisher} <span className="muted xs mono">{f.feed}</span></span>
                <span className="muted xs">{f.ok ? `${f.count} items` : f.error}</span>
              </div>
            ))}
          </Panel>
          <Panel title="Scoring method">
            <pre className="xs muted" style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-num)', margin: 0, lineHeight: 1.5 }}>{(clusters.data?.method || '').trim()}</pre>
          </Panel>
        </div>
      </div>
    </div>
  )
}
