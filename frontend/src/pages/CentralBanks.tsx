import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart } from '../charts/EChart'
import { lineOption } from '../charts/builders'
import { Loadable, Prov, SkelRows } from '../components/ui'
import { fmtDate, fmtNum } from '../services/format'

export default function CentralBanks() {
  const q = useApi('/central-banks', { refetch: 900_000 })
  return (
    <div className="page">
      <PageHead kicker="Monetary policy" title="Central Bank Monitor" desc="Policy rates fetched live from official data portals (NY Fed, ECB, Bank of England, Bank of Canada) or FRED; meeting schedules verified against official calendars." />
      <Loadable q={q} skeleton={<SkelRows n={12} />}>
        {(d) => (
          <>
            <div className="cards lg" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))' }}>
              {d.banks.map((b: any) => (
                <div className="panel" key={b.id} style={{ padding: 14 }}>
                  <div className="row">
                    <div><div style={{ fontWeight: 600, fontFamily: 'var(--font-display)', fontSize: 15 }}>{b.name}</div><div className="muted xs">{b.rate_name} · {b.currency}</div></div>
                    <span className="spacer" />
                    {b.provenance && <Prov p={b.provenance} />}
                  </div>
                  <div className="row" style={{ alignItems: 'baseline', marginTop: 10, gap: 10 }}>
                    <span className="big-num">{b.rate != null ? `${fmtNum(b.rate, 2)}%` : '—'}</span>
                    {b.target_low != null && <span className="muted small">target {b.target_low}–{b.target_high}%</span>}
                    {b.last_change && <span className={`badge ${b.last_change.bp > 0 ? 'bad' : 'ok'}`}>{b.last_change.bp > 0 ? '+' : ''}{b.last_change.bp} bp on {b.last_change.date}</span>}
                  </div>
                  {b.rate == null && <div className="muted xs" style={{ marginTop: 4 }}>{b.error}</div>}
                  {b.history?.length > 3 && <EChart height={110} deps={[b]} option={() => ({ ...lineOption([{ name: b.short, data: b.history.map((h: any) => [h[0], h[1]]), step: true, area: true }], { yFormat: (v) => `${v.toFixed(2)}%` }), grid: { left: 4, right: 8, top: 10, bottom: 4, containLabel: true } })} />}
                  <div className="row small" style={{ marginTop: 8, flexWrap: 'wrap' }}>
                    <span className="dim">Next decision:</span>
                    <b>{b.next_meeting ? fmtDate(b.next_meeting) : b.meeting_note || '—'}</b>
                    {b.days_to_meeting != null && <span className="badge info">in {b.days_to_meeting} days</span>}
                    <span className="spacer" />
                    <a href={b.statements_url} target="_blank" rel="noreferrer noopener" className="xs">Statements ↗</a>
                    <a href={b.calendar_url} target="_blank" rel="noreferrer noopener" className="xs">Calendar ↗</a>
                  </div>
                </div>
              ))}
            </div>
            <div className="muted xs" style={{ marginTop: 10 }}>{d.note}</div>
          </>
        )}
      </Loadable>
    </div>
  )
}
