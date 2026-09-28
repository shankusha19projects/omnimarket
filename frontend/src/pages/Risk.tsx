import { useApi } from '../hooks/useApi'
import { PageHead } from '../components/PageHead'
import { EChart, chartColors } from '../charts/EChart'
import { lineOption } from '../charts/builders'
import { Loadable, Panel, SkelRows } from '../components/ui'
import { YieldCurveMini, Breadth } from '../components/widgets'
import { fmtNum, isNum } from '../services/format'

export default function Risk() {
  const q = useApi('/risk', { refetch: 300_000 })
  return (
    <div className="page">
      <PageHead kicker="Risk" title="Risk Dashboard" desc="Objective cross-asset risk indicators with their reference thresholds and sources. There is deliberately no opaque composite 'risk score'." />
      <Loadable q={q} skeleton={<SkelRows n={16} />}>
        {(d) => (
          <div className="grid">
            <div className="c-12">
              <div className="cards lg">
                {d.indicators.map((i: any) => (
                  <div className="panel" key={i.name} style={{ padding: 13 }}>
                    <div className="upper muted">{i.name}</div>
                    <div className="mono" style={{ fontSize: 24, fontWeight: 600, marginTop: 4 }}>{isNum(i.value) ? `${fmtNum(i.value, Math.abs(i.value) >= 100 ? 1 : 2)}${i.unit === '%' ? '%' : i.unit === 'pp' ? ' pp' : ''}` : i.value ?? '—'}</div>
                    {i.percentile_1y != null && <div className="xs muted">{i.percentile_1y}th percentile of trailing year</div>}
                    <div className="small dim" style={{ marginTop: 6, lineHeight: 1.45 }}>{i.reference}</div>
                    <div className="xs muted" style={{ marginTop: 4 }}>Source: {i.source}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="c-6"><Panel title="VIX — trailing year"><EChart height={260} deps={[d]} option={() => lineOption([{ name: 'VIX', data: (d.vix_history || []).map((p: any) => [p.t * 1000, p.c]), area: true, color: chartColors().amber }], { yFormat: (v) => v.toFixed(0) })} /></Panel></div>
            <div className="c-3"><YieldCurveMini height={200} /></div>
            <div className="c-3"><Breadth /></div>
            <div className="c-12 muted xs">{d.note}</div>
          </div>
        )}
      </Loadable>
    </div>
  )
}
