import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import * as echarts from 'echarts'
import { useApp } from '../hooks/AppContext'

export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export function chartColors() {
  return {
    text: cssVar('--chart-text'), text2: cssVar('--text-2'), grid: cssVar('--chart-grid'), line: cssVar('--line-2'),
    up: cssVar('--up'), down: cssVar('--down'), accent: cssVar('--accent'), amber: cssVar('--amber'), violet: cssVar('--violet'),
    panel: cssVar('--panel'), panel2: cssVar('--panel-2'), bg: cssVar('--bg-1'), textMain: cssVar('--text'),
    series: [cssVar('--accent'), cssVar('--amber'), cssVar('--violet'), '#2ec4a6', '#ff7aa2', '#9bd14b', '#f2784b', '#6aa7ff'],
  }
}

export function baseOption(): echarts.EChartsOption {
  const c = chartColors()
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'IBM Plex Sans, sans-serif', color: c.text },
    color: c.series,
    tooltip: {
      backgroundColor: c.panel2, borderColor: c.line, textStyle: { color: c.textMain, fontSize: 12 },
      extraCssText: 'box-shadow: 0 12px 30px -10px rgba(0,0,0,.5); border-radius: 8px;',
    },
    animationDuration: 500,
  }
}

export type EChartHandle = { png: () => string | undefined; instance: () => echarts.ECharts | undefined }

/** Resizing, theme-aware ECharts host. `option` is a function so colors re-resolve on theme change. */
export const EChart = forwardRef<EChartHandle, { option: () => echarts.EChartsOption; height?: number | string; onClick?: (p: any) => void; deps?: unknown[] }>(
  function EChart({ option, height = 300, onClick, deps = [] }, ref) {
    const el = useRef<HTMLDivElement>(null)
    const inst = useRef<echarts.ECharts | undefined>(undefined)
    const { resolvedTheme } = useApp()

    useImperativeHandle(ref, () => ({
      png: () => inst.current?.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: cssVar('--panel') }),
      instance: () => inst.current,
    }))

    useEffect(() => {
      if (!el.current) return
      const chart = echarts.init(el.current, undefined, { renderer: 'canvas' })
      inst.current = chart
      const ro = new ResizeObserver(() => chart.resize())
      ro.observe(el.current)
      return () => { ro.disconnect(); chart.dispose(); inst.current = undefined }
    }, [])

    useEffect(() => {
      const chart = inst.current
      if (!chart) return
      chart.setOption({ ...baseOption(), ...option() }, { notMerge: true })
      chart.off('click')
      if (onClick) chart.on('click', onClick)
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [resolvedTheme, ...deps])

    return <div ref={el} style={{ width: '100%', height }} />
  })
