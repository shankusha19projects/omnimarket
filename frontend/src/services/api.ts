/* Typed-ish API client. All calls go to the local FastAPI backend via the Vite proxy. */

export class ApiError extends Error {
  status: number
  provider?: string
  constructor(message: string, status: number, provider?: string) {
    super(message)
    this.status = status
    this.provider = provider
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('Backend unreachable — is the API server running on localhost:8000?', 0)
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    let provider: string | undefined
    try {
      const j = await res.json()
      msg = j.detail && typeof j.detail === 'string' ? j.detail : j.error || JSON.stringify(j.detail) || msg
      provider = j.provider
    } catch { /* non-JSON error */ }
    throw new ApiError(msg, res.status, provider)
  }
  return res.json() as Promise<T>
}

export const api = {
  get: <T = any>(p: string) => request<T>('GET', p),
  post: <T = any>(p: string, b?: unknown) => request<T>('POST', p, b ?? {}),
  put: <T = any>(p: string, b?: unknown) => request<T>('PUT', p, b ?? {}),
  del: <T = any>(p: string) => request<T>('DELETE', p),
}

export const enc = (s: string) => encodeURIComponent(s)

export async function downloadCsv(path: string, body: unknown, filename: string) {
  const res = await fetch(`/api${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!res.ok) throw new ApiError(`Export failed (HTTP ${res.status})`, res.status)
  const blob = await res.blob()
  saveBlob(blob, filename)
}

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function exportJson(data: unknown, filename: string) {
  saveBlob(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }), filename)
}

export function exportRowsCsv(rows: Record<string, any>[], filename: string) {
  if (!rows.length) return
  const cols = Object.keys(rows[0]).filter((k) => typeof rows[0][k] !== 'object' || rows[0][k] === null)
  const esc = (v: any) => (v === null || v === undefined ? '' : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v))
  const csv = [cols.join(','), ...rows.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\n')
  saveBlob(new Blob([csv], { type: 'text/csv' }), filename)
}
