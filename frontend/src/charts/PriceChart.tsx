import { useEffect, useRef } from 'react'
import {
  AreaSeries, BarSeries, CandlestickSeries, ColorType, CrosshairMode, HistogramSeries, LineSeries, createChart,
  type IChartApi, type Time, type UTCTimestamp,
} from 'lightweight-charts'
import { useApp } from '../hooks/AppContext'
import { cssVar } from './EChart'

export type Overlay = 'sma20' | 'sma50' | 'sma200' | 'ema12' | 'ema26' | 'bb' | 'volume' | 'rsi' | 'macd'

type Bar = { t: number; o?: number; h?: number; l?: number; c: number; v?: number }

/** Institutional price chart: candles / OHLC / line with overlays and oscillator panes. */
export function PriceChart({ bars, indicators, type, overlays, height = 460, intraday, onReady }: {
  bars: Bar[]; indicators?: Record<string, (number | null)[]>; type: 'candle' | 'ohlc' | 'line'; overlays: Overlay[]
  height?: number; intraday?: boolean; onReady?: (chart: IChartApi) => void
}) {
  const el = useRef<HTMLDivElement>(null)
  const { resolvedTheme } = useApp()

  useEffect(() => {
    if (!el.current || !bars.length) return
    const up = cssVar('--up'), down = cssVar('--down'), accent = cssVar('--accent')
    const chart = createChart(el.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: cssVar('--chart-text'), fontFamily: 'JetBrains Mono, monospace', fontSize: 11,
        panes: { separatorColor: cssVar('--line-2'), separatorHoverColor: cssVar('--accent-soft'), enableResize: true } },
      grid: { vertLines: { color: cssVar('--chart-grid') }, horzLines: { color: cssVar('--chart-grid') } },
      crosshair: { mode: CrosshairMode.Normal, vertLine: { color: cssVar('--line-3'), labelBackgroundColor: cssVar('--panel-3') }, horzLine: { color: cssVar('--line-3'), labelBackgroundColor: cssVar('--panel-3') } },
      rightPriceScale: { borderColor: cssVar('--line'), scaleMargins: { top: 0.08, bottom: overlays.includes('volume') ? 0.22 : 0.06 } },
      timeScale: { borderColor: cssVar('--line'), timeVisible: !!intraday, secondsVisible: false, rightOffset: 4 },
      localization: { priceFormatter: (p: number) => (Math.abs(p) >= 1000 ? p.toLocaleString('en-US', { maximumFractionDigits: 2 }) : p.toPrecision(6).replace(/\.?0+$/, '')) },
    })
    const time = (t: number) => t as UTCTimestamp as Time
    const clean = bars.filter((b) => b.c != null)
    if (type === 'line') {
      const s = chart.addSeries(AreaSeries, { lineColor: accent, topColor: cssVar('--accent-soft'), bottomColor: 'transparent', lineWidth: 2, priceLineColor: accent })
      s.setData(clean.map((b) => ({ time: time(b.t), value: b.c })))
    } else {
      const def = type === 'candle' ? CandlestickSeries : BarSeries
      const s = chart.addSeries(def as typeof CandlestickSeries, type === 'candle'
        ? { upColor: up, downColor: down, borderUpColor: up, borderDownColor: down, wickUpColor: up, wickDownColor: down }
        : ({ upColor: up, downColor: down, thinBars: false } as any))
      s.setData(clean.map((b) => ({ time: time(b.t), open: b.o ?? b.c, high: b.h ?? b.c, low: b.l ?? b.c, close: b.c })))
    }
    const ind = indicators || {}
    const line = (key: string, color: string, width = 1.5, pane = 0, style = 0) => {
      const vals = ind[key]
      if (!vals) return
      const s = chart.addSeries(LineSeries, { color, lineWidth: width as any, lineStyle: style, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }, pane)
      s.setData(clean.map((b, i) => (vals[i] == null ? { time: time(b.t) } : { time: time(b.t), value: vals[i] as number })))
      return s
    }
    if (overlays.includes('sma20')) line('sma20', '#f5b544')
    if (overlays.includes('sma50')) line('sma50', '#8d8cff')
    if (overlays.includes('sma200')) line('sma200', '#ff7aa2')
    if (overlays.includes('ema12')) line('ema12', '#2ec4a6', 1)
    if (overlays.includes('ema26')) line('ema26', '#6aa7ff', 1)
    if (overlays.includes('bb')) { line('bb_upper', cssVar('--text-3'), 1, 0, 2); line('bb_mid', cssVar('--text-4'), 1, 0, 1); line('bb_lower', cssVar('--text-3'), 1, 0, 2) }
    if (overlays.includes('volume')) {
      const v = chart.addSeries(HistogramSeries, { priceScaleId: 'vol', priceFormat: { type: 'volume' }, lastValueVisible: false, priceLineVisible: false })
      chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } })
      v.setData(clean.map((b, i) => ({ time: time(b.t), value: b.v || 0, color: (i && b.c < clean[i - 1].c) ? cssVar('--down-soft') : cssVar('--up-soft') })))
    }
    let pane = 1
    if (overlays.includes('rsi') && ind.rsi14) {
      const s = line('rsi14', '#8d8cff', 1.5, pane)
      s?.createPriceLine({ price: 70, color: cssVar('--down'), lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '' })
      s?.createPriceLine({ price: 30, color: cssVar('--up'), lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '' })
      pane++
    }
    if (overlays.includes('macd') && ind.macd) {
      const h = chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, pane)
      const hist = ind.macd_hist || []
      h.setData(clean.map((b, i) => (hist[i] == null ? { time: time(b.t) } : { time: time(b.t), value: hist[i] as number, color: (hist[i] as number) >= 0 ? cssVar('--up-soft') : cssVar('--down-soft') })))
      line('macd', accent, 1.5, pane)
      line('macd_signal', '#f5b544', 1, pane)
    }
    const panes = chart.panes()
    panes.forEach((p, i) => { if (i > 0) p.setHeight(Math.round(height * 0.18)) })
    chart.timeScale().fitContent()
    onReady?.(chart)
    return () => chart.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bars, indicators, type, overlays.join(','), resolvedTheme, height, intraday])

  return <div ref={el} style={{ width: '100%', height }} />
}
