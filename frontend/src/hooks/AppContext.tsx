import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'

export type ThemeMode = 'dark' | 'light' | 'system'

type RefreshJob = {
  id: string
  status: string
  scopes: string[]
  asset?: string | null
  started_at: number
  finished_at: number | null
  completed: number
  total: number
  summary: Record<string, number>
  datasets: { key: string; label: string; scope: string; status: string; message: string | null; provider: string | null; started_at: number | null; finished_at: number | null }[]
  note?: string
}

type Ctx = {
  theme: ThemeMode
  resolvedTheme: 'dark' | 'light'
  setTheme: (t: ThemeMode) => void
  job: RefreshJob | null
  lastJob: RefreshJob | null
  refreshing: boolean
  startRefresh: (scopes?: string[], asset?: string | null) => Promise<void>
  drawerOpen: boolean
  setDrawerOpen: (b: boolean) => void
  paletteOpen: boolean
  setPaletteOpen: (b: boolean) => void
  navCollapsed: boolean
  setNavCollapsed: (b: boolean) => void
  railOpen: boolean
  setRailOpen: (b: boolean) => void
  currentAsset: string | null
  setCurrentAsset: (s: string | null) => void
  setupOpen: boolean
  setSetupOpen: (b: boolean) => void
}

const AppCtx = createContext<Ctx | null>(null)

function readLS<T>(k: string, d: T): T {
  try {
    const v = localStorage.getItem(k)
    return v === null ? d : (JSON.parse(v) as T)
  } catch {
    return d
  }
}
function writeLS(k: string, v: unknown) {
  try { localStorage.setItem(k, JSON.stringify(v)) } catch { /* storage unavailable */ }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const [theme, setThemeState] = useState<ThemeMode>(() => readLS('omni.theme', 'dark'))
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches)
  const [job, setJob] = useState<RefreshJob | null>(null)
  const [lastJob, setLastJob] = useState<RefreshJob | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [setupOpen, setSetupOpen] = useState(false)
  const [navCollapsed, setNavCollapsedState] = useState<boolean>(() => readLS('omni.nav', false))
  const [railOpen, setRailOpenState] = useState<boolean>(() => readLS('omni.rail', true))
  const [currentAsset, setCurrentAsset] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const on = (e: MediaQueryListEvent) => setSystemDark(e.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])

  const resolvedTheme: 'dark' | 'light' = theme === 'system' ? (systemDark ? 'dark' : 'light') : theme
  useEffect(() => { document.documentElement.dataset.theme = resolvedTheme }, [resolvedTheme])

  const setTheme = useCallback((t: ThemeMode) => {
    setThemeState(t)
    writeLS('omni.theme', t)
    api.put('/settings', { preferences: { theme: t } }).catch(() => undefined)
  }, [])
  const setNavCollapsed = (b: boolean) => { setNavCollapsedState(b); writeLS('omni.nav', b) }
  const setRailOpen = (b: boolean) => { setRailOpenState(b); writeLS('omni.rail', b) }

  useEffect(() => {
    api.get('/refresh/last').then((r) => r.last && setLastJob(r.last)).catch(() => undefined)
    api.get('/setup').then((s) => { if (!s.setup_complete) setSetupOpen(true) }).catch(() => undefined)
  }, [])

  const poll = useCallback((id: string) => {
    if (pollRef.current) window.clearInterval(pollRef.current)
    pollRef.current = window.setInterval(async () => {
      try {
        const j = await api.get<RefreshJob>(`/refresh/${id}`)
        setJob(j)
        if (j.status !== 'running') {
          if (pollRef.current) window.clearInterval(pollRef.current)
          pollRef.current = null
          setLastJob(j)
          qc.invalidateQueries()
        }
      } catch {
        if (pollRef.current) window.clearInterval(pollRef.current)
        pollRef.current = null
      }
    }, 650)
  }, [qc])

  const startRefresh = useCallback(async (scopes: string[] = ['everything'], asset: string | null = null) => {
    setDrawerOpen(true)
    const j = await api.post<RefreshJob>('/refresh', { scopes, asset })
    setJob(j)
    poll(j.id)
  }, [poll])

  const value = useMemo<Ctx>(() => ({
    theme, resolvedTheme, setTheme, job, lastJob, refreshing: job?.status === 'running', startRefresh, drawerOpen, setDrawerOpen,
    paletteOpen, setPaletteOpen, navCollapsed, setNavCollapsed, railOpen, setRailOpen, currentAsset, setCurrentAsset, setupOpen, setSetupOpen,
  }), [theme, resolvedTheme, setTheme, job, lastJob, startRefresh, drawerOpen, paletteOpen, navCollapsed, railOpen, currentAsset, setupOpen])

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>
}

export function useApp() {
  const c = useContext(AppCtx)
  if (!c) throw new Error('useApp outside provider')
  return c
}
