# OmniMarket Intelligence Terminal

A local, institutional-style financial intelligence and market-research terminal. FastAPI backend + React/TypeScript frontend, running entirely on `localhost`.

It covers global indices, US and international equities, ETFs, crypto, commodities (with futures curves), FX, Treasury curves, central banks, US and international macro, real estate & REITs, rare earths / critical minerals, sectors and thematic baskets, a deduplicated news engine, earnings and economic calendars, a screener, portfolio and watchlists, compare/correlation/risk tools, SEC filings with XBRL-derived financial statements, DCF/scenario valuation, a Research Command Center with a TinyFish web-agent adapter, and an AI research advisor.

**Provenance comes first.** Every number carries its provider, source URL, retrieval time, market time, delay and cache status (hover any `SOURCE` badge). Nothing is fabricated: when a source fails, the last good value is served and labeled **stale**; when nothing is cached, the UI says **unavailable**.

---

## Quick start

**Windows (one command):**

```powershell
cd C:\myc\INVEST\omnimarket
.\start.bat                       # or: powershell -ExecutionPolicy Bypass -File .\start.ps1
```

**macOS / Linux:** `./start.sh`

The launcher creates the Python venv, installs dependencies, copies `.env.example` → `.env`, starts both servers and opens the browser.

| Service | URL |
|---|---|
| Terminal UI | http://localhost:5173 |
| API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |

### Manual start

```powershell
# Terminal 1 - API
cd C:\myc\INVEST\omnimarket
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Terminal 2 - UI
cd C:\myc\INVEST\omnimarket\frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api to :8000)
```

Single-origin production mode: `npm --prefix frontend run build`, then just run the API — it serves `frontend/dist` at http://localhost:8000.

## Installation

### Python setup
Python 3.11+ (developed on 3.14). Dependencies in `requirements.txt`: FastAPI, Uvicorn, httpx, Pydantic v2, NumPy, python-dotenv, the official `anthropic` SDK, `tzdata` (needed for time zones on Windows) and pytest.

### Node setup
Node 18+ (developed on Node 24). Frontend: React 19, Vite, TypeScript, TanStack Query, React Router, Apache ECharts, TradingView Lightweight Charts, lucide icons, react-markdown. Fonts are bundled locally via `@fontsource` (IBM Plex Sans, JetBrains Mono, Space Grotesk) so the UI works offline.

## Environment variables & API keys

Everything works **without any keys**. Keys unlock more coverage. Set them in **Settings → Data providers & keys** (the backend writes `.env`; values are never returned to the browser) or edit `.env` directly — see `.env.example`.

| Key | What it unlocks | Cost |
|---|---|---|
| `FRED_API_KEY` | GDP, PCE, retail sales, housing, claims, sentiment, credit spreads (OAS), TIPS, mortgage rates, BoJ/RBI/RBA rates | Free — recommended |
| `TINYFISH_API_KEY` | TinyFish Web Agent: web search, page fetch, goal-based browsing for research | Search & Fetch free |
| `ANTHROPIC_API_KEY` | AI advisor, research synthesis, filing summaries (default model `claude-opus-5`) | Paid |
| `OPENAI_API_KEY` / Ollama | Alternative AI providers (`AI_PROVIDER`, `AI_MODEL`, `OLLAMA_BASE_URL`) | — |
| `FINNHUB_API_KEY`, `FMP_API_KEY`, `POLYGON_API_KEY`, `ALPHA_VANTAGE_API_KEY` | Fallback quote providers; Finnhub adds company news | Free tiers |
| `NEWS_API_KEY` | Additional news search | Free tier |
| `SEC_USER_AGENT` | Your name/email for SEC fair-access identification | — |

## Running locally — what to try

* **REFRESH LIVE DATA** (top right) — refreshes every dataset, with a live progress drawer listing each dataset's provider, timing, and ok / stale / partial / failed status. The ▾ menu offers selective refresh (markets, news, crypto, economics, portfolio, current asset).
* **Ctrl+K** — global search across tickers, companies, crypto, futures, FX, indicators, sectors, themes and news headlines. Any Yahoo-compatible ticker works, not just the tracked universe.
* **Asset pages** (`/asset/NVDA`, `/asset/GC=F`, `/asset/BTC-USD`, `/asset/SPY`) — chart (candles/OHLC/line; SMA/EMA/Bollinger/RSI/MACD/volume; PNG & CSV export), SEC statements (annual/quarterly/TTM), fundamentals with formulas, rule-based Analysis report with bull/base/bear scenarios, editable DCF with sensitivity & reverse DCF, comparables, historical P/E, SEC filings with AI summaries, timeline, company profile, ETF holdings, futures curves.
* **Markets** dashboard → **Customize** to reorder (drag or arrows) / hide widgets; layout persists.
* **Research** — "TSLA", "US semiconductor industry", "What is happening in copper?".
* **AI Advisor** — "Analyze NVDA", "Why did gold move today?".

## Architecture

```text
omnimarket/
├── backend/
│   ├── main.py                 FastAPI app (localhost bind, strict CORS, security headers, error handlers, serves built UI)
│   ├── config.py               central config: .env secrets (server-side only) + config/app.json
│   ├── db.py                   SQLite + forward-only migrations (17 tables incl. cache, quotes, watchlists, portfolio, refresh logs)
│   ├── api/routes.py           REST API (OpenAPI at /docs)
│   ├── models/schemas.py       canonical Pydantic models (Asset, Quote, Bar, NewsItem, Filing, requests)
│   ├── providers/              data acquisition layer — one module per vendor, all behind base.py interfaces
│   │   ├── base.py             MarketDataProvider, NewsProvider, EconomicDataProvider, CryptoProvider, FilingsProvider
│   │   ├── yahoo.py            quotes (bulk), history, sparks, key stats, profiles, fund holdings, search, news
│   │   ├── sec.py              EDGAR tickers, filings, full-text search, XBRL company facts → normalized statements
│   │   ├── macro.py            U.S. Treasury curves, FRED, BLS, World Bank, NY Fed / ECB / BoE / BoC policy rates
│   │   ├── coingecko.py, calendars.py (Nasdaq), rss.py, keyed.py (Finnhub/FMP/Polygon/AlphaVantage/NewsAPI)
│   │   └── registry.py         instantiation + fallback chain + provider-health catalog
│   ├── agents/                 WebResearchAgent interface; TinyFishResearchProvider; keyless PublicSourcesAgent fallback
│   ├── ai/providers.py         AIProvider: Anthropic (official SDK), OpenAI, Ollama; offline mode when none configured
│   ├── analytics/              technicals, fundamentals, valuation (DCF/reverse DCF/DDM/comps), correlation,
│   │                           news clustering + market-moving score, screener engine, rule-based report generator
│   ├── research/               context assembly for reports/advisor/research workspace; advisor prompts & guardrails
│   ├── services/               markets, assets, asset classes, macro, news, calendar, user state, analytics, refresh, clock, system
│   ├── cache/store.py          provenance-aware TTL cache (SQLite + memory), single-flight, stale-while-revalidate
│   └── utils/                  rate-limited HTTP client, provider health tracking, structured redacting logs
├── frontend/src/
│   ├── components/             shell (header, ticker, nav, rail, status bar), overlays (Ctrl+K, refresh drawer, setup wizard), UI kit, widgets
│   ├── charts/                 ECharts wrapper + builders (treemap, curves, matrices), Lightweight-Charts price chart
│   ├── pages/                  22 routed pages
│   ├── services/, hooks/, styles/ (Deep Signal design tokens — see docs/DESIGN.md)
├── config/                     universe.json, themes.json, markets.json, central_banks.json, economics.json, news_feeds.json, app.json
├── tests/                      pytest suite (analytics math, cache, normalization, SEC XBRL, refresh, API)
├── data/ cache/ logs/          SQLite DB · cache dir · application/provider/refresh/research/error logs (JSON lines, secrets redacted)
└── start.bat / start.ps1 / start.sh
```

**Canonical asset schema.** Every provider maps into `Asset` (`id` like `equity:US:AAPL`, `index:US:^GSPC`, `commodity:GC=F`, `fx:EURUSD`, `crypto:bitcoin`) with per-provider symbols in `provider_symbols`.

**Real-time model.** Polling (TanStack Query intervals per widget; quotes ~45–60 s). The service layer is async and cache-backed, so adding a WebSocket push channel later only requires a broadcaster on top of `market_data.quotes`.

## Refresh architecture

1. `POST /api/refresh {scopes, asset}` creates a job (scopes: `everything`, `markets`, `news`, `crypto`, `economics`, `portfolio`, `asset`). If one is already running, you attach to it.
2. The orchestrator (`services/refresh.py`) runs datasets concurrently (max 4) with `force=True`, bypassing caches, each with a 150 s timeout.
3. Each result is inspected for provenance: `ok`, `stale` (served from cache because the provider failed), `partial` (some sub-sources unavailable, e.g. FRED key missing), `rate_limited`, `failed` — with message, provider and timing.
4. The UI polls `GET /api/refresh/{id}` (~650 ms) and renders the progress drawer; on completion it invalidates all queries so visible widgets reload.
5. Jobs persist to `refresh_logs`; `GET /api/refresh/last` powers the status bar and Settings → Cache & refresh.

**Caching** (`config/app.json → cache_ttl_seconds`): quotes 45 s, bulk quotes 60 s, intraday history 5 min, daily history 15 min, fundamentals/statements 12 h, profiles 24 h, economic series 6 h (BLS keyless 12 h), news 10 min, filings 45 min, crypto 90 s, calendars 1 h. Expired-but-recent entries are returned instantly (status `revalidating`, true age shown) while a background refresh runs; the Refresh button always forces a synchronous fetch. Per-host rate limits are configured in the same file.

## Data providers

| Source | Used for | Key |
|---|---|---|
| Yahoo-compatible public endpoints | Quotes (bulk), charts, sparklines, key statistics, profiles, ETF holdings, futures contracts, search, news | none |
| SEC EDGAR | Ticker→CIK, filings, full-text search, XBRL company facts → income/balance/cash-flow statements (Q4 derived, TTM) | none (User-Agent) |
| U.S. Treasury | Daily nominal & real par yield curves | none |
| BLS Public API v1 | CPI, core CPI, PPI, unemployment, payrolls, wages, JOLTS, rent CPI | none |
| FRED | 20+ macro, housing, credit and policy-rate series | free key |
| World Bank | International inflation, GDP growth, unemployment, industry | none |
| NY Fed / ECB / BoE / BoC | Policy rates | none |
| CoinGecko | Top-100 crypto, dominance, global stats | none |
| Nasdaq public calendars | Earnings (consensus EPS, timing) & economic events (forecast/actual) | none |
| Publisher RSS (CNBC, MarketWatch, Yahoo, Fed, ECB, SEC, CoinDesk, Cointelegraph, OilPrice, MINING.COM, Seeking Alpha) | News headlines + short excerpts | none |
| TinyFish Web Agent | Web search, page fetch, goal-based browsing (research) | free Search/Fetch |
| Finnhub / FMP / Polygon / Alpha Vantage / NewsAPI | Fallback quotes, company news | optional |

## Adding another provider

1. Create `backend/providers/myvendor.py` implementing the relevant interface from `providers/base.py` (e.g. `MarketDataProvider.get_quotes`). Use `backend.utils.http.get_json(provider_name, url, ...)` so requests are rate-limited and tracked in Provider Health.
2. Read credentials with `backend.config.env("MYVENDOR_API_KEY")`; add the key to `SECRET_KEYS` in `config.py` (it then appears in Settings) and to `.env.example`.
3. Register it in `providers/registry.py` (instance, `QUOTE_CHAIN` position, and a `CATALOG` row).
4. Call it from a service through `cache.store.cached(...)` / `bulk_cached(...)` so results carry provenance.

## Adding a market

* Instruments: add rows to `config/universe.json` (indices, commodities, forex, ETFs, stocks, REITs, critical-minerals companies, ticker strip).
* Thematic baskets: edit `config/themes.json`.
* Exchange sessions/holidays: `config/markets.json`. Central-bank meetings: `config/central_banks.json`.
* Economic indicators: `config/economics.json` (FRED / BLS series IDs and transforms).
* News feeds: `config/news_feeds.json`.

Restart the API after editing config files.

## Testing

```powershell
.venv\Scripts\python -m pytest -q                          # offline suite (24 tests)
$env:OMNI_NETWORK_TESTS=1; .venv\Scripts\python -m pytest  # + live provider test
```

Covers technical indicators, fundamental ratios, DCF/reverse DCF/DDM/comps, correlation, screener filters, news clustering & scoring, cache freshness/stale/SWR/bulk behavior, provenance fields, symbol normalization, SEC XBRL statement building (incl. derived Q4 and TTM), refresh status assessment, and API endpoints (health, settings secrecy, input validation, watchlist CRUD, portfolio math).

## Security

* Server binds to `127.0.0.1`; CORS restricted to the local UI origin; security headers set.
* Secrets live only in `.env` on the backend; `/api/settings` returns only `configured: true/false`.
* Logs redact configured secret values and key-like strings.
* Symbols, query params, request bodies and settings keys are validated (Pydantic + allow-lists); filing summaries only fetch `https://www.sec.gov/` URLs; all SQL is parameterized.
* The research agent never bypasses logins, paywalls, CAPTCHAs or robots rules; blocked pages are reported, not circumvented. Web collection is rate-limited and cached with source URLs and timestamps.
* No trading functionality exists anywhere — the portfolio is a manual tracker.

## Troubleshooting

| Symptom | Fix |
|---|---|
| UI shows "Backend unreachable" | Start the API (port 8000). Check `logs/error.log`. |
| Macro cards say "Requires FRED_API_KEY" | Add a free FRED key in Settings. BLS-backed series work without it. |
| Quotes show `stale` | A provider failed; the last good value is shown with its age. Check Settings → Provider health. |
| Advisor says "offline analyst mode" | Add `ANTHROPIC_API_KEY` (or OpenAI / Ollama) in Settings. |
| `ZoneInfoNotFoundError` on Windows | `pip install tzdata` (included in requirements). |
| Port already in use | Stop the other process or change ports in `start.ps1` / `.env` (`PORT`) and `frontend/vite.config.ts`. |
| Nasdaq calendar / RSS feed failing | These are public endpoints that occasionally throttle; the refresh drawer and News → Feed health show which one. |

## Limitations

* Free public data is typically **delayed** (exchange-dependent; the delay reported by the provider is displayed). This is not a real-time trading feed.
* Yahoo-compatible endpoints are unofficial and may change or throttle; licensed providers (FMP, Polygon, Finnhub) can be configured as fallbacks.
* LME base metals (nickel, zinc, tin), ISM PMIs and Conference Board confidence are proprietary and shown as unavailable.
* SEC statements cover US filers using standard us-gaap tags; foreign filers (20-F/IFRS) and unusual tagging may have gaps. Segment/geographic revenue requires reading the 10-K.
* Market holiday calendars are configured for NYSE, LSE, XETRA and SSE; other exchanges treat only weekends as closed.
* Screener fundamentals (growth, margins, ROE, EV/EBITDA) populate after **Load fundamentals** (cached 12 h) to respect provider rate limits.
* Analysis reports and scenarios are mechanical outputs of stated assumptions — not forecasts, recommendations or price targets.

---

*Research and analytical information only. Market data may be delayed or incomplete. This application does not execute trades and is not a substitute for personalized professional financial, tax, or legal advice.*
