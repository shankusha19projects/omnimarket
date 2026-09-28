import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { ChevronDown, Command, Moon, PanelLeftClose, PanelLeftOpen, PanelRight, RefreshCw, Search, Settings, Sun, SunMoon } from 'lucide-react'
import { useApp } from '../hooks/AppContext'
import { useApi } from '../hooks/useApi'
import { ALL_NAV, NAV } from './nav'
import { assetPath, fmtPrice, fmtTime, timeAgo } from '../services/format'
import { Chg, Sparkline, StatusDot } from './ui'
import { RightRail } from './RightRail'

export function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden>
      <defs>
        <linearGradient id="bm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#37c8f5" /><stop offset="1" stopColor="#8d8cff" /></linearGradient>
      </defs>
      <rect x="1" y="1" width="30" height="30" rx="8" fill="none" stroke="url(#bm)" strokeWidth="1.5" />
      <circle cx="16" cy="16" r="8.5" fill="none" stroke="url(#bm)" strokeWidth="1.2" opacity=".55" />
      <path d="M6 20.5 L11 15.5 L14.5 18.5 L19.5 11 L26 16" fill="none" stroke="url(#bm)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="19.5" cy="11" r="1.8" fill="#f5b544" />
    </svg>
  )
}

function Clock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => { const i = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(i) }, [])
  return (
    <div className="clock-block" title={Intl.DateTimeFormat().resolvedOptions().timeZone}>
      <span className="t">{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
      <span className="d">{now.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })} · {Intl.DateTimeFormat().resolvedOptions().timeZone.split('/').pop()?.replace('_', ' ')}</span>
    </div>
  )
}

function RefreshControl() {
  const { startRefresh, refreshing, job, setDrawerOpen, currentAsset } = useApp()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])
  const pct = job && job.total ? Math.round((job.completed / job.total) * 100) : 0
  const go = (s: string[], a: string | null = null) => { setOpen(false); startRefresh(s, a).catch(() => undefined) }
  return (
    <div className="refresh-split" ref={ref} style={{ position: 'relative' }}>
      <button className={clsx('refresh-btn', refreshing && 'running')} disabled={refreshing} onClick={() => go(['everything'], currentAsset)}
              title="Fetch the newest data from every configured provider" aria-label="Refresh live data">
        <RefreshCw size={14} className={refreshing ? 'spin' : undefined} />
        {refreshing ? `Refreshing ${pct}%` : 'Refresh live data'}
      </button>
      <button className="refresh-more" aria-label="Selective refresh" onClick={() => setOpen(!open)}><ChevronDown size={14} /></button>
      {open && (
        <div className="menu">
          <button onClick={() => go(['everything'], currentAsset)}>Refresh everything</button>
          <hr />
          <button onClick={() => go(['markets'])}>Refresh markets</button>
          <button onClick={() => go(['news'])}>Refresh news</button>
          <button onClick={() => go(['crypto'])}>Refresh crypto</button>
          <button onClick={() => go(['economics'])}>Refresh economics</button>
          <button onClick={() => go(['portfolio'])}>Refresh portfolio</button>
          <button disabled={!currentAsset} onClick={() => currentAsset && go(['asset'], currentAsset)}>Refresh current asset{currentAsset ? ` (${currentAsset})` : ''}</button>
          <hr />
          <button onClick={() => { setOpen(false); setDrawerOpen(true) }}>Show refresh log…</button>
        </div>
      )}
    </div>
  )
}

function ThemeToggle() {
  const { theme, setTheme } = useApp()
  const next = theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark'
  const Icon = theme === 'dark' ? Moon : theme === 'light' ? Sun : SunMoon
  return <button className="icon-btn" onClick={() => setTheme(next)} title={`Theme: ${theme} (click for ${next})`} aria-label="Toggle theme"><Icon size={16} /></button>
}

function DataStatus() {
  const { lastJob, setDrawerOpen, refreshing } = useApp()
  const q = useApi('/providers/status', { refetch: 60_000 })
  const provs = (q.data?.providers || []).filter((p: any) => p.configured)
  const bad = provs.filter((p: any) => p.status === 'error' || p.status === 'rate_limited').length
  const deg = provs.filter((p: any) => p.status === 'degraded').length
  const state = refreshing ? 'pre-market' : bad ? 'error' : deg ? 'degraded' : 'online'
  const label = refreshing ? 'Updating' : bad ? `${bad} source${bad > 1 ? 's' : ''} down` : deg ? 'Degraded' : 'Data OK'
  return (
    <button className="btn ghost sm" onClick={() => setDrawerOpen(true)} title={lastJob?.finished_at ? `Last refresh ${fmtTime(lastJob.finished_at, true)}` : 'No refresh yet'}>
      <StatusDot status={state} /> <span className="small">{label}</span>
    </button>
  )
}

function UsMarket() {
  const q = useApi('/clock', { refetch: 30_000 })
  const ny = q.data?.sessions?.find((s: any) => s.id === 'NYSE')
  if (!ny) return null
  const lbl = ny.status === 'open' ? 'US open' : ny.status === 'pre-market' ? 'US pre-market' : ny.status === 'after-hours' ? 'US after-hours' : 'US closed'
  return <span className={clsx('badge', ny.status === 'open' ? 'ok live' : ny.status === 'closed' || ny.status === 'holiday' ? '' : 'warn')} title={ny.next_event ? `${ny.next_event} in ${Math.round((ny.seconds_to_next || 0) / 60)} min` : ''}>{lbl}</span>
}

export function TopBar() {
  const { setPaletteOpen } = useApp()
  const loc = useLocation()
  return (
    <header className="topbar">
      <Link to="/" className="brand" aria-label="OmniMarket home">
        <BrandMark />
        <div><div className="brand-name">OMNIMARKET</div><div className="brand-sub">Intelligence Terminal</div></div>
      </Link>
      <button className="search-trigger" onClick={() => setPaletteOpen(true)} aria-label="Search (Ctrl+K)">
        <Search size={14} /><span>Search stocks, crypto, macro…</span><span className="kbd">Ctrl K</span>
      </button>
      <nav className="quicknav" aria-label="Primary">
        {ALL_NAV.filter((n) => n.quick).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => clsx(isActive && 'active')}>{n.label}</NavLink>
        ))}
      </nav>
      <div className="top-right">
        <UsMarket />
        <DataStatus />
        <Clock />
        <RefreshControl />
        <ThemeToggle />
        <Link to="/settings" className="icon-btn" aria-label="Settings" title="Settings"><Settings size={16} /></Link>
      </div>
      <span className="sr-only">{loc.pathname}</span>
    </header>
  )
}

export function TickerStrip() {
  const q = useApi('/markets/ticker', { refetch: 60_000 })
  const items: any[] = q.data?.items || []
  if (!items.length) return <div className="ticker"><div className="row" style={{ height: '100%', padding: '0 14px' }}><span className="muted small">Loading global markets…</span></div></div>
  const loop = [...items, ...items]
  return (
    <div className="ticker" aria-label="Global market ticker">
      <div className="ticker-track">
        {loop.map((it, i) => (
          <Link key={i} to={assetPath(it.symbol)} className="tick" aria-hidden={i >= items.length}>
            <span className="n">{shortName(it.name)}</span>
            <span className="p">{it.unavailable ? 'n/a' : fmtPrice(it.price)}</span>
            <Chg v={it.change_pct} />
            <span style={{ width: 54, display: 'inline-block' }}><Sparkline data={it.spark} width={54} height={18} fill={false} /></span>
          </Link>
        ))}
      </div>
    </div>
  )
}

function shortName(n: string) {
  return (n || '').replace('CBOE Volatility (VIX)', 'VIX').replace('Dow Jones Industrial', 'Dow Jones').replace('US 10-Year Yield', 'US 10Y').replace('US Dollar Index (DXY)', 'DXY').replace(' Crude Oil', '').replace('Natural Gas (Henry Hub)', 'Nat Gas')
}

export function SideNav() {
  const { navCollapsed, setNavCollapsed, railOpen, setRailOpen } = useApp()
  return (
    <nav className="sidenav" aria-label="Sections">
      {NAV.map((g) => (
        <div className="nav-group" key={g.group}>
          <div className="nav-group-title">{g.group}</div>
          {g.items.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => clsx('nav-item', isActive && 'active')} title={n.label}>
              <n.icon size={16} /><span className="nav-label">{n.label}</span>{n.badge && <span className="nav-badge">{n.badge}</span>}
            </NavLink>
          ))}
        </div>
      ))}
      <div className="nav-footer">
        <button className="icon-btn sm ghost" onClick={() => setNavCollapsed(!navCollapsed)} aria-label="Collapse navigation">
          {navCollapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
        </button>
        <button className="icon-btn sm ghost" onClick={() => setRailOpen(!railOpen)} aria-label="Toggle right rail" title="Toggle watchlist / news rail"><PanelRight size={15} /></button>
        <span className="nav-footer-text"><Command size={11} style={{ verticalAlign: -1 }} /> K to search</span>
      </div>
    </nav>
  )
}

export function StatusBar() {
  const { lastJob, job } = useApp()
  const prov = useApi('/providers/status', { refetch: 60_000 })
  const provs = (prov.data?.providers || []).filter((p: any) => p.configured)
  const online = provs.filter((p: any) => p.status === 'online').length
  const j = job?.status === 'running' ? job : lastJob
  return (
    <footer className="statusbar">
      <span className="item"><StatusDot status={online ? 'online' : 'idle'} /> {online}/{provs.length} providers online</span>
      <span className="sep" />
      <span className="item">Last refresh: {j?.finished_at ? `${fmtTime(j.finished_at, true)} (${timeAgo(j.finished_at)})` : j?.status === 'running' ? 'in progress…' : 'never — using cached / on-demand data'}</span>
      {j?.summary && Object.keys(j.summary).length > 0 && <span className="item">{Object.entries(j.summary).map(([k, v]) => `${v} ${k}`).join(' · ')}</span>}
      <span className="right">
        <span>Data may be delayed · provenance on every figure</span>
        <span>OmniMarket v1.0 · localhost</span>
      </span>
    </footer>
  )
}

export function Shell({ children }: { children: ReactNode }) {
  const { navCollapsed, railOpen } = useApp()
  return (
    <div className={clsx('app', navCollapsed && 'nav-collapsed', !railOpen && 'no-rail')}>
      <TopBar />
      <TickerStrip />
      <SideNav />
      <main className="main" id="main">{children}</main>
      <aside className="rail" aria-label="Watchlist, news and calendar"><RightRail /></aside>
      <StatusBar />
    </div>
  )
}
