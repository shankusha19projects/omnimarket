import type { EChartsOption } from 'echarts'
import { chartColors } from './EChart'
import { heatColor, isNum } from '../services/format'

const axisCommon = () => {
  const c = chartColors()
  return {
    axisLine: { lineStyle: { color: c.line } },
    axisTick: { show: false },
    axisLabel: { color: c.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5 },
    splitLine: { lineStyle: { color: c.grid } },
  }
}

/** Market heatmap treemap: size = market cap, color = performance. */
export function treemapOption(tree: any[], clamp = 3, perfLabel = '1D'): EChartsOption {
  const c = chartColors()
  const decorate = (n: any): any => n.children
    ? { name: n.name, children: n.children.map(decorate) }
    : { name: n.name, value: n.value, perf: n.perf, label_: n.label, price: n.price, itemStyle: { color: heatColor(n.perf, clamp), borderColor: c.bg } }
  return {
    tooltip: {
      formatter: (p: any) => {
        const d = p.data || {}
        if (d.perf === undefined) return `<b>${p.name}</b>`
        const perf = isNum(d.perf) ? `${d.perf > 0 ? '+' : ''}${d.perf.toFixed(2)}%` : 'n/a'
        return `<div style="font-family:JetBrains Mono,monospace"><b>${p.name}</b> · ${d.label_ || ''}<br/>${perfLabel}: <b>${perf}</b><br/>Mkt cap: $${(d.value / 1e9).toFixed(1)}B${d.price ? `<br/>Last: ${d.price}` : ''}</div>`
      },
    },
    series: [{
      type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, width: '100%', height: '100%', top: 0, left: 0, right: 0, bottom: 0,
      data: tree.map(decorate),
      levels: [
        { itemStyle: { borderColor: c.bg, borderWidth: 3, gapWidth: 3 }, upperLabel: { show: true, height: 20, color: c.text2, fontSize: 10.5, fontWeight: 600, backgroundColor: 'transparent', fontFamily: 'IBM Plex Sans' } },
        { itemStyle: { borderColor: c.bg, borderWidth: 1, gapWidth: 1 }, upperLabel: { show: false } },
        { itemStyle: { borderColor: c.bg, borderWidth: 1, gapWidth: 1 } },
      ],
      label: {
        show: true, fontFamily: 'JetBrains Mono, monospace', color: '#fff', overflow: 'truncate',
        formatter: (p: any) => {
          const d = p.data || {}
          if (!isNum(d.perf)) return p.name
          return `{s|${p.name}}\n{v|${d.perf > 0 ? '+' : ''}${d.perf.toFixed(2)}%}`
        },
        rich: { s: { fontSize: 12, fontWeight: 700, color: '#fff', lineHeight: 16 }, v: { fontSize: 10.5, color: 'rgba(255,255,255,.88)' } },
      },
      upperLabel: { show: true, height: 20 },
    } as any],
  }
}

export function lineOption(series: { name: string; data: [number | string, number | null][]; color?: string; area?: boolean; step?: boolean; dashed?: boolean }[],
  opts: { yFormat?: (v: number) => string; timeAxis?: boolean; zoom?: boolean; yName?: string; markZero?: boolean } = {}): EChartsOption {
  const c = chartColors()
  const ax = axisCommon()
  return {
    grid: { left: 8, right: 14, top: 26, bottom: opts.zoom ? 46 : 8, containLabel: true },
    legend: series.length > 1 ? { top: 0, right: 0, textStyle: { color: c.text2, fontSize: 11 }, icon: 'roundRect', itemWidth: 10, itemHeight: 3 } : undefined,
    tooltip: { trigger: 'axis', valueFormatter: (v: any) => (isNum(v) ? (opts.yFormat ? opts.yFormat(v) : v.toLocaleString()) : '—') as string },
    xAxis: { type: opts.timeAxis === false ? 'category' : 'time', ...ax, splitLine: { show: false } },
    yAxis: { type: 'value', scale: true, name: opts.yName, nameTextStyle: { color: c.text, fontSize: 10 }, ...ax, axisLabel: { ...ax.axisLabel, formatter: opts.yFormat as any } },
    dataZoom: opts.zoom ? [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 6, borderColor: c.line, fillerColor: 'rgba(55,200,245,.12)', textStyle: { color: c.text } }] : undefined,
    series: series.map((s, i) => ({
      name: s.name, type: 'line', data: s.data, showSymbol: false, smooth: false, step: s.step ? 'end' : undefined,
      lineStyle: { width: 1.7, color: s.color || c.series[i % c.series.length], type: s.dashed ? 'dashed' : 'solid' },
      itemStyle: { color: s.color || c.series[i % c.series.length] },
      areaStyle: s.area ? { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: (s.color || c.accent) + '44' }, { offset: 1, color: (s.color || c.accent) + '00' }] } } : undefined,
      markLine: opts.markZero && i === 0 ? { silent: true, symbol: 'none', lineStyle: { color: c.line, type: 'dashed' }, data: [{ yAxis: 0 }], label: { show: false } } : undefined,
    })) as any,
  }
}

export function barOption(labels: string[], values: (number | null)[], opts: { horizontal?: boolean; format?: (v: number) => string; colorBySign?: boolean; color?: string } = {}): EChartsOption {
  const c = chartColors()
  const ax = axisCommon()
  const data = values.map((v) => ({ value: v, itemStyle: { color: opts.colorBySign ? (isNum(v) && v >= 0 ? c.up : c.down) : opts.color || c.accent, borderRadius: opts.horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0] } }))
  const cat = { type: 'category' as const, data: labels, ...ax, splitLine: { show: false }, axisLabel: { ...ax.axisLabel, fontFamily: 'IBM Plex Sans', fontSize: 11, color: c.text2 } }
  const val = { type: 'value' as const, ...ax, axisLabel: { ...ax.axisLabel, show: !opts.horizontal, formatter: opts.format as any }, splitLine: { show: !opts.horizontal, lineStyle: ax.splitLine.lineStyle } }
  return {
    grid: { left: 8, right: opts.horizontal ? 52 : 16, top: 12, bottom: 6, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v: any) => (isNum(v) ? (opts.format ? opts.format(v) : String(v)) : '—') as string },
    xAxis: opts.horizontal ? val : cat,
    yAxis: opts.horizontal ? { ...cat, inverse: true } : val,
    series: [{ type: 'bar', data, barMaxWidth: 22, label: { show: !!opts.horizontal, position: 'right', color: c.text2, fontFamily: 'JetBrains Mono', fontSize: 10.5, formatter: (p: any) => (isNum(p.value) ? (opts.format ? opts.format(p.value) : p.value) : '') } }] as any,
  }
}

export function donutOption(items: { name: string; value: number }[], format?: (v: number) => string): EChartsOption {
  const c = chartColors()
  return {
    tooltip: { trigger: 'item', valueFormatter: (v: any) => (format && isNum(v) ? format(v) : String(v)) as string },
    legend: { orient: 'vertical', right: 0, top: 'middle', textStyle: { color: c.text2, fontSize: 11 }, icon: 'circle', itemWidth: 8, itemHeight: 8, type: 'scroll' },
    series: [{ type: 'pie', radius: ['52%', '78%'], center: ['32%', '50%'], avoidLabelOverlap: true, label: { show: false },
      itemStyle: { borderColor: c.panel, borderWidth: 2, borderRadius: 4 }, data: items }],
  }
}

export function matrixOption(keys: string[], matrix: (number | null)[][]): EChartsOption {
  const c = chartColors()
  const data: [number, number, number | null][] = []
  matrix.forEach((row, i) => row.forEach((v, j) => data.push([j, i, v])))
  return {
    grid: { left: 8, right: 70, top: 8, bottom: 8, containLabel: true },
    tooltip: { formatter: (p: any) => `${keys[p.value[1]]} × ${keys[p.value[0]]}<br/><b>ρ = ${isNum(p.value[2]) ? p.value[2].toFixed(3) : 'n/a'}</b>` },
    xAxis: { type: 'category', data: keys, axisLabel: { color: c.text2, fontFamily: 'JetBrains Mono', fontSize: 10.5, rotate: 30 }, axisLine: { show: false }, axisTick: { show: false }, splitArea: { show: false } },
    yAxis: { type: 'category', data: keys, axisLabel: { color: c.text2, fontFamily: 'JetBrains Mono', fontSize: 10.5 }, axisLine: { show: false }, axisTick: { show: false } },
    visualMap: { min: -1, max: 1, calculable: true, orient: 'vertical', right: 0, top: 'center', itemHeight: 160, textStyle: { color: c.text },
      inRange: { color: ['#d33b57', '#5a2233', c.panel2, '#155e45', '#16a86c'] } },
    series: [{ type: 'heatmap', data, label: { show: true, color: c.textMain, fontFamily: 'JetBrains Mono', fontSize: 10.5, formatter: (p: any) => (isNum(p.value[2]) ? p.value[2].toFixed(2) : '') },
      itemStyle: { borderColor: c.panel, borderWidth: 2, borderRadius: 3 } }] as any,
  }
}
