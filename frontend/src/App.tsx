import { lazy, Suspense, useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { Shell } from './components/Shell'
import { CommandPalette, RefreshDrawer, SetupWizard } from './components/Overlays'
import { SkelRows } from './components/ui'
import Markets from './pages/Markets'

const AssetDetail = lazy(() => import('./pages/AssetDetail'))
const Stocks = lazy(() => import('./pages/Stocks'))
const ETFs = lazy(() => import('./pages/ETFs'))
const Crypto = lazy(() => import('./pages/Crypto'))
const Commodities = lazy(() => import('./pages/Commodities'))
const Forex = lazy(() => import('./pages/Forex'))
const Sectors = lazy(() => import('./pages/Sectors'))
const Bonds = lazy(() => import('./pages/Bonds'))
const CentralBanks = lazy(() => import('./pages/CentralBanks'))
const Economics = lazy(() => import('./pages/Economics'))
const RealEstate = lazy(() => import('./pages/RealEstate'))
const RareEarths = lazy(() => import('./pages/RareEarths'))
const News = lazy(() => import('./pages/News'))
const CalendarPage = lazy(() => import('./pages/Calendar'))
const Research = lazy(() => import('./pages/Research'))
const Advisor = lazy(() => import('./pages/Advisor'))
const Screener = lazy(() => import('./pages/Screener'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Risk = lazy(() => import('./pages/Risk'))
const Portfolio = lazy(() => import('./pages/Portfolio'))
const Watchlists = lazy(() => import('./pages/Watchlists'))
const Settings = lazy(() => import('./pages/Settings'))
const NotFound = lazy(() => import('./pages/NotFound'))

const TITLES: Record<string, string> = { '/': 'Markets' }

export default function App() {
  const loc = useLocation()
  useEffect(() => {
    document.getElementById('main')?.scrollTo({ top: 0 })
    const seg = loc.pathname.split('/')[1]
    const title = TITLES[loc.pathname] || (seg ? decodeURIComponent(loc.pathname.split('/').pop() || seg).replace(/-/g, ' ') : 'Markets')
    document.title = `${title.charAt(0).toUpperCase()}${title.slice(1)} · OmniMarket`
  }, [loc.pathname])
  return (
    <Shell>
      <Suspense fallback={<div className="page"><SkelRows n={10} /></div>}>
        <Routes>
          <Route path="/" element={<Markets />} />
          <Route path="/asset/:symbol" element={<AssetDetail />} />
          <Route path="/stocks" element={<Stocks />} />
          <Route path="/etfs" element={<ETFs />} />
          <Route path="/crypto" element={<Crypto />} />
          <Route path="/commodities" element={<Commodities />} />
          <Route path="/forex" element={<Forex />} />
          <Route path="/sectors" element={<Sectors />} />
          <Route path="/bonds" element={<Bonds />} />
          <Route path="/rates" element={<Bonds />} />
          <Route path="/central-banks" element={<CentralBanks />} />
          <Route path="/economics" element={<Economics />} />
          <Route path="/real-estate" element={<RealEstate />} />
          <Route path="/rare-earths" element={<RareEarths />} />
          <Route path="/news" element={<News />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/research" element={<Research />} />
          <Route path="/advisor" element={<Advisor />} />
          <Route path="/screener" element={<Screener />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/watchlists" element={<Watchlists />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
      <CommandPalette />
      <RefreshDrawer />
      <SetupWizard />
    </Shell>
  )
}
