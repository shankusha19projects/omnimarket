import {
  Activity, BarChart3, Bitcoin, Bot, Briefcase, Building2, CalendarDays, CandlestickChart, Coins, Filter, Gauge, Gem, Globe2, Landmark,
  LayoutDashboard, LineChart, ListChecks, Newspaper, Percent, PieChart, Search, Settings, Shapes, TrendingUp, type LucideIcon,
} from 'lucide-react'

export type NavItem = { to: string; label: string; icon: LucideIcon; quick?: boolean; badge?: string }

export const NAV: { group: string; items: NavItem[] }[] = [
  { group: 'Markets', items: [
    { to: '/', label: 'Markets', icon: LayoutDashboard, quick: true },
    { to: '/stocks', label: 'Stocks', icon: CandlestickChart, quick: true },
    { to: '/etfs', label: 'ETFs', icon: PieChart, quick: true },
    { to: '/crypto', label: 'Crypto', icon: Bitcoin, quick: true },
    { to: '/commodities', label: 'Commodities', icon: Coins, quick: true },
    { to: '/forex', label: 'Forex', icon: Globe2, quick: true },
    { to: '/sectors', label: 'Sectors & Themes', icon: Shapes },
  ] },
  { group: 'Macro', items: [
    { to: '/bonds', label: 'Bonds & Rates', icon: Percent, quick: true },
    { to: '/central-banks', label: 'Central Banks', icon: Landmark },
    { to: '/economics', label: 'Economics', icon: BarChart3, quick: true },
    { to: '/real-estate', label: 'Real Estate', icon: Building2, quick: true },
    { to: '/rare-earths', label: 'Rare Earths', icon: Gem, quick: true },
  ] },
  { group: 'Intelligence', items: [
    { to: '/news', label: 'News', icon: Newspaper, quick: true },
    { to: '/calendar', label: 'Calendar', icon: CalendarDays, quick: true },
    { to: '/research', label: 'Research', icon: Search, quick: true },
    { to: '/advisor', label: 'AI Advisor', icon: Bot, quick: true, badge: 'AI' },
  ] },
  { group: 'Tools', items: [
    { to: '/screener', label: 'Screener', icon: Filter, quick: true },
    { to: '/analytics', label: 'Compare & Risk', icon: Activity },
    { to: '/risk', label: 'Risk Dashboard', icon: Gauge },
  ] },
  { group: 'Workspace', items: [
    { to: '/portfolio', label: 'Portfolio', icon: Briefcase, quick: true },
    { to: '/watchlists', label: 'Watchlists', icon: ListChecks, quick: true },
    { to: '/settings', label: 'Settings', icon: Settings, quick: true },
  ] },
]

export const ALL_NAV = NAV.flatMap((g) => g.items)
export { LineChart, TrendingUp }
