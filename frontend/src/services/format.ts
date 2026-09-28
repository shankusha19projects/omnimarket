/* Number, time and direction formatting used across the terminal. */

export const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)

export function fmtPrice(v: unknown, opts: { min?: number; max?: number } = {}): string {
  if (!isNum(v)) return '—'
  const a = Math.abs(v)
  const max = opts.max ?? (a >= 1000 ? 2 : a >= 10 ? 2 : a >= 1 ? 4 : a >= 0.01 ? 5 : 8)
  const min = opts.min ?? Math.min(2, max)
  return v.toLocaleString('en-US', { minimumFractionDigits: min, maximumFractionDigits: max })
}

export function fmtNum(v: unknown, digits = 2): string {
  if (!isNum(v)) return '—'
  return v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function fmtInt(v: unknown): string {
  if (!isNum(v)) return '—'
  return Math.round(v).toLocaleString('en-US')
}

export function fmtPct(v: unknown, digits = 2, signed = true): string {
  if (!isNum(v)) return '—'
  const s = v.toFixed(digits)
  return `${signed && v > 0 ? '+' : ''}${s}%`
}

/** Ratio (0.123) → "12.3%" */
export function fmtRatioPct(v: unknown, digits = 1, signed = false): string {
  if (!isNum(v)) return '—'
  return fmtPct(v * 100, digits, signed)
}

export function fmtBig(v: unknown, prefix = ''): string {
  if (!isNum(v)) return '—'
  const a = Math.abs(v)
  const sign = v < 0 ? '-' : ''
  const units: [number, string][] = [[1e12, 'T'], [1e9, 'B'], [1e6, 'M'], [1e3, 'K']]
  for (const [d, u] of units) if (a >= d) return `${sign}${prefix}${(a / d).toFixed(a / d >= 100 ? 1 : 2)}${u}`
  return `${sign}${prefix}${a.toFixed(0)}`
}

export function fmtX(v: unknown, digits = 1): string {
  return isNum(v) ? `${v.toFixed(digits)}×` : '—'
}

export function dir(v: unknown): 'up' | 'down' | 'flat' {
  if (!isNum(v) || Math.abs(v) < 1e-9) return 'flat'
  return v > 0 ? 'up' : 'down'
}

export function arrow(v: unknown): string {
  const d = dir(v)
  return d === 'up' ? '▲' : d === 'down' ? '▼' : '■'
}

export function fmtTime(ts: unknown, withSeconds = false): string {
  if (!isNum(ts) || ts <= 0) return '—'
  return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: withSeconds ? '2-digit' : undefined })
}

export function fmtDateTime(ts: unknown): string {
  if (!isNum(ts) || ts <= 0) return '—'
  return new Date(ts * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function fmtDate(s: unknown): string {
  if (typeof s === 'number') return new Date(s * 1000).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' })
  if (typeof s !== 'string' || !s) return '—'
  const d = new Date(s.length === 10 ? `${s}T12:00:00` : s)
  return isNaN(d.getTime()) ? s : d.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' })
}

export function timeAgo(ts: unknown): string {
  if (!isNum(ts) || ts <= 0) return '—'
  const s = Date.now() / 1000 - ts
  if (s < 45) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  return `${Math.round(s / 86400)}d ago`
}

export function fmtDuration(sec: unknown): string {
  if (!isNum(sec)) return '—'
  const s = Math.max(0, Math.round(sec))
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60)
  if (d) return `${d}d ${h}h`
  if (h) return `${h}h ${m}m`
  return `${m}m ${s % 60}s`
}

/** Color for performance heatmaps (diverging, clamped). */
export function heatColor(v: unknown, clamp = 3): string {
  if (!isNum(v)) return 'rgba(110,120,140,0.35)'
  const t = Math.max(-1, Math.min(1, v / clamp))
  if (t >= 0) {
    const a = 0.18 + t * 0.72
    return `rgba(22, 168, 108, ${a.toFixed(3)})`
  }
  const a = 0.18 + -t * 0.72
  return `rgba(211, 59, 87, ${a.toFixed(3)})`
}

export function assetPath(symbol: string): string {
  return `/asset/${encodeURIComponent(symbol)}`
}
