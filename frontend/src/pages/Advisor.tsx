import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, Globe, Loader2, MessageSquarePlus, Send, Sparkles } from 'lucide-react'
import { api } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Notice, Panel } from '../components/ui'
import { timeAgo } from '../services/format'

type Msg = { role: 'user' | 'assistant'; content: string; meta?: any }
const PROMPTS = ['Analyze NVDA', 'Why did gold move today?', 'What is the yield curve telling us?', 'Compare MSFT and GOOGL valuation', 'How exposed are REITs to higher rates?', 'What is happening in uranium?']
const DISCLAIMER = 'Research and analytical information only. Market data may be delayed or incomplete. This application does not execute trades and is not a substitute for personalized professional financial, tax, or legal advice.'

export default function Advisor() {
  const [params, setParams] = useSearchParams()
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [conv, setConv] = useState<string | null>(null)
  const [web, setWeb] = useState(false)
  const settings = useApi('/settings')
  const convs = useApi<any[]>('/advisor/conversations')
  const endRef = useRef<HTMLDivElement>(null)
  const ai = settings.data?.ai

  const send = async (text = input) => {
    if (!text.trim() || busy) return
    const history = msgs.map(({ role, content }) => ({ role, content: content.slice(0, 12000) }))
    setMsgs((m) => [...m, { role: 'user', content: text }])
    setInput(''); setBusy(true)
    try {
      const r = await api.post('/advisor/chat', { message: text, history, conversation: conv, use_web_research: web })
      setConv(r.conversation)
      setMsgs((m) => [...m, { role: 'assistant', content: r.answer, meta: r }])
      convs.refetch()
    } catch (e: any) {
      setMsgs((m) => [...m, { role: 'assistant', content: `> ⚠ ${e.message}` }])
    } finally { setBusy(false) }
  }

  useEffect(() => {
    const q = params.get('q')
    if (q) { setParams({}, { replace: true }); send(q) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  const load = async (c: string) => {
    const rows = await api.get<any[]>(`/advisor/conversations/${c}`)
    setConv(c)
    setMsgs(rows.map((r) => ({ role: r.role, content: r.content, meta: r.meta })))
  }

  return (
    <div className="page" style={{ maxWidth: 1500 }}>
      <div className="grid">
        <div className="c-9 col" style={{ minHeight: 'calc(100vh - 170px)' }}>
          <div className="page-head" style={{ marginBottom: 4 }}>
            <div>
              <div className="page-kicker">Ask the financial research advisor</div>
              <h1 className="page-title">AI Research Advisor</h1>
              <div className="page-desc">Every answer is grounded in structured context assembled from live providers — quotes, SEC statements, filings, technicals, macro and news — and cites its sources.</div>
            </div>
            <div className="page-actions">
              <span className={`badge ${ai?.active ? 'ok' : 'warn'}`}><Sparkles size={11} /> {ai?.active ? `${ai.active} · ${ai.model}` : 'Offline analyst mode'}</span>
              <button className="btn" onClick={() => { setMsgs([]); setConv(null) }}><MessageSquarePlus size={14} /> New chat</button>
            </div>
          </div>
          {ai && !ai.active && <Notice kind="warn">No AI provider configured — the advisor returns structured data briefs instead of narrative analysis. Add an Anthropic (recommended), OpenAI or local Ollama provider in <Link to="/settings">Settings → AI</Link>.</Notice>}
          <div className="panel" style={{ flex: 1, padding: '6px 18px', overflowY: 'auto', minHeight: 420 }}>
            {!msgs.length && (
              <div className="empty" style={{ padding: '60px 20px' }}>
                <div style={{ width: 54, height: 54, borderRadius: 14, background: 'linear-gradient(135deg, var(--accent), var(--violet))', display: 'grid', placeItems: 'center' }}><Bot size={28} color="#051019" /></div>
                <div className="ttl" style={{ fontSize: 16 }}>What would you like to research?</div>
                <div className="small" style={{ maxWidth: 560 }}>Ask about a company, sector, macro event or market move. The advisor separates facts from interpretation, flags stale data and never invents prices or estimates.</div>
                <div className="chip-row" style={{ justifyContent: 'center', marginTop: 10 }}>{PROMPTS.map((p) => <button key={p} className="chip" onClick={() => send(p)}>{p}</button>)}</div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div className={`chat-msg ${m.role}`} key={i}>
                <div className="avatar">{m.role === 'user' ? 'You' : <Bot size={16} />}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  {m.role === 'user' ? <div style={{ fontWeight: 500, paddingTop: 5 }}>{m.content}</div> : <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: (p) => <a {...p} target="_blank" rel="noreferrer noopener" /> }}>{m.content}</ReactMarkdown></div>}
                  {m.meta?.meta && <div className="row xs muted" style={{ marginTop: 6, flexWrap: 'wrap' }}>
                    <span className="badge">{m.meta.meta.provider}{m.meta.meta.model ? ` · ${m.meta.meta.model}` : ''}</span>
                    {m.meta.intent && <span className="badge">intent: {m.meta.intent}</span>}
                    {m.meta.entities?.map((e: string) => <Link key={e} to={`/asset/${encodeURIComponent(e)}`} className="tag link">{e}</Link>)}
                    {m.meta.elapsed && <span>{m.meta.elapsed}s</span>}
                    {m.meta.meta.usage && <span>{m.meta.meta.usage.input_tokens?.toLocaleString()} in / {m.meta.meta.usage.output_tokens?.toLocaleString()} out tokens</span>}
                  </div>}
                  {m.meta?.sources?.length > 0 && (
                    <details style={{ marginTop: 6 }}><summary className="xs muted" style={{ cursor: 'pointer' }}>{m.meta.sources.length} context sources</summary>
                      <ul className="xs" style={{ margin: '4px 0', paddingLeft: 16 }}>{m.meta.sources.map((s: any, j: number) => <li key={j}>{s.url ? <a href={s.url} target="_blank" rel="noreferrer noopener">{s.label}</a> : s.label}</li>)}</ul>
                    </details>
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="chat-msg assistant"><div className="avatar"><Bot size={16} /></div><div className="row muted small" style={{ paddingTop: 6 }}><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Assembling context from providers and analyzing…</div></div>}
            <div ref={endRef} />
          </div>
          <form className="panel" style={{ padding: 10 }} onSubmit={(e) => { e.preventDefault(); send() }}>
            <div className="row" style={{ alignItems: 'flex-end' }}>
              <textarea className="input" rows={2} style={{ flex: 1, resize: 'none' }} placeholder="Ask e.g. “Analyze NVDA” or “Why did gold move today?”  (Enter to send, Shift+Enter for newline)"
                        value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} aria-label="Message" />
              <div className="col" style={{ gap: 6 }}>
                <label className="check xs" title="Add web research via TinyFish (or public-source fallback)"><input type="checkbox" checked={web} onChange={(e) => setWeb(e.target.checked)} /><Globe size={12} /> Web research</label>
                <button className="btn primary" disabled={busy || !input.trim()}><Send size={14} /> Send</button>
              </div>
            </div>
          </form>
          <div className="muted xs" style={{ textAlign: 'center' }}>{DISCLAIMER}</div>
        </div>
        <div className="c-3 col">
          <Panel title="Conversations">
            {(convs.data || []).length ? (convs.data || []).map((c) => (
              <button key={c.conversation} className="btn ghost" style={{ width: '100%', justifyContent: 'flex-start', height: 'auto', padding: '7px 8px', whiteSpace: 'normal', textAlign: 'left', background: conv === c.conversation ? 'var(--panel-2)' : undefined }} onClick={() => load(c.conversation)}>
                <div style={{ minWidth: 0 }}><div className="small truncate" style={{ maxWidth: 230 }}>{c.title}</div><div className="muted xs">{timeAgo(c.updated)}</div></div>
              </button>
            )) : <span className="muted small">No conversations yet.</span>}
          </Panel>
          <Panel title="How answers are built">
            <ol className="small dim" style={{ paddingLeft: 18, margin: 0, lineHeight: 1.6 }}>
              <li>Entities (tickers, commodities, themes) are detected in your question.</li>
              <li>The backend assembles quotes, SEC XBRL statements, filings, technicals, macro snapshot and news — each tagged with provider and retrieval time.</li>
              <li>Optional web research via TinyFish (or public sources).</li>
              <li>The model receives only this structured context with strict grounding rules — no guessed prices, estimates or citations.</li>
            </ol>
          </Panel>
        </div>
      </div>
    </div>
  )
}
