# MASTER BUILD PROMPT — LOCAL FINANCIAL INTELLIGENCE & MARKET RESEARCH TERMINAL

You are acting as a principal full-stack engineer, quantitative-finance developer, financial-data architect, UI/UX designer, data visualization specialist, web-research engineer, and software architect.

Your task is to DESIGN AND BUILD a complete professional-grade **local financial intelligence web application** that runs on my computer using `localhost`.

Do not create a simple demo, mockup, landing page, or static dashboard.

Build a functional application with a real backend, frontend, data acquisition layer, caching layer, analytics engine, news aggregation layer, search functionality, configurable watchlists, financial charts, market dashboards, and an AI financial research/advisor interface.

The application should feel like a combination of:

- Investing.com
- Bloomberg Terminal
- TradingView
- Yahoo Finance
- Reuters Markets
- MarketWatch
- Finviz
- Koyfin
- Seeking Alpha
- FRED
- CoinMarketCap
- CoinGecko
- Federal Reserve economic dashboards
- institutional investment research terminals

However:

**DO NOT copy Investing.com source code, proprietary assets, copyrighted layouts, trademarks, logos, or exact visual design.**

Instead, create an original institutional-quality financial terminal inspired by the information density, navigation hierarchy, market coverage, usability, and professional appearance of leading financial platforms.

The final application should be extremely polished, modern, responsive, information-rich, and suitable for serious investment research.

---

# 1. PRIMARY OBJECTIVE

Build a localhost application that allows me to monitor, search, analyze, compare, and research virtually every major financial market from one interface.

The user should be able to click a prominent:

**REFRESH LIVE DATA**

button.

When clicked, the backend should retrieve the newest available information from configured data providers, APIs, feeds, or research agents, refresh the relevant cache, recalculate analytics, and update the interface.

The refresh operation must show:

- refresh started
- datasets being updated
- successful sources
- failed sources
- stale sources
- timestamp of last successful update
- market data timestamp
- news timestamp
- source/provider information
- progress indicator
- graceful error handling

Never silently fail.

---

# 2. APPLICATION NAME

Use a professional temporary product name such as:

**OmniMarket Intelligence Terminal**

or

**Global Markets Intelligence Hub**

Make the name configurable in a central configuration file.

---

# 3. CORE TECHNOLOGY ARCHITECTURE

Build this as a proper local full-stack application.

Preferred architecture:

Frontend:
- HTML5
- CSS3
- JavaScript / TypeScript
- React preferred if appropriate
- Vite preferred
- Tailwind CSS or a clean reusable CSS design system
- responsive desktop-first interface

Backend:
- Python
- FastAPI preferred

Alternative:
- Node.js/Express if there is a strong technical reason

Use a clean modular architecture.

Example project structure:

```text
financial-terminal/
│
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── charts/
│   ├── services/
│   ├── styles/
│   └── assets/
│
├── backend/
│   ├── main.py
│   ├── api/
│   ├── services/
│   ├── providers/
│   ├── models/
│   ├── analytics/
│   ├── research/
│   ├── agents/
│   ├── cache/
│   └── utils/
│
├── data/
├── cache/
├── logs/
├── tests/
├── scripts/
├── .env.example
├── requirements.txt
├── package.json
├── README.md
└── start scripts
```

Keep responsibilities separated.

Do not put the whole application into one massive HTML or Python file.

---

# 4. LOCALHOST EXPERIENCE

The project must run locally.

Prefer:

Frontend:

```text
http://localhost:5173
```

Backend:

```text
http://localhost:8000
```

If possible, provide a startup command that launches both.

Examples:

Windows:

```text
start.bat
```

PowerShell:

```text
start.ps1
```

Mac/Linux:

```text
./start.sh
```

Also document manual startup commands.

---

# 5. ZERO-HARDCODED FAKE MARKET DATA

Do not populate the production application with fake prices pretending to be live.

If an API is unavailable:

- mark the information unavailable
- show the last cached value
- display the cache timestamp
- label delayed data
- indicate simulation/demo data explicitly

Never portray fabricated values as live financial information.

---

# 6. DATA ACQUISITION LAYER

Design a provider abstraction so different market-data providers can be swapped in without changing the UI.

Example:

```python
class MarketDataProvider:
    get_quote()
    get_history()
    get_fundamentals()
    get_company_profile()
    get_market_status()
```

Support multiple providers where legally and technically appropriate.

Potential sources can include legitimate APIs, public datasets, RSS feeds, SEC filings, central-bank databases, exchange information, or licensed market-data providers configured by the user.

Examples to consider:

- Yahoo Finance-compatible libraries where permitted
- Alpha Vantage
- Finnhub
- Twelve Data
- Polygon
- Financial Modeling Prep
- Nasdaq Data Link
- SEC EDGAR
- FRED
- Treasury data
- World Bank
- IMF
- ECB
- BLS
- BEA
- EIA
- CoinGecko
- CoinMarketCap when configured
- exchange APIs
- RSS feeds
- official investor-relations pages
- company SEC filings

API credentials must come from environment variables.

Example:

```env
FINNHUB_API_KEY=
ALPHA_VANTAGE_API_KEY=
FMP_API_KEY=
POLYGON_API_KEY=
NEWS_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

Never hard-code secrets.

---

# 7. TINYFISH / WEB RESEARCH AGENT INTEGRATION

Create an optional **Research Agent layer**.

If TinyFish Web Agent or another browser/research-agent integration is available in the execution environment, structure the application so it can be connected through an adapter.

Example interface:

```python
class WebResearchAgent:
    research_company()
    research_sector()
    collect_recent_news()
    research_macro_event()
    investigate_market_move()
    gather_public_filings()
```

Create a provider such as:

```text
TinyFishResearchProvider
```

but isolate it from the rest of the application.

Do not make the application dependent on TinyFish being installed.

If TinyFish is unavailable, gracefully fall back to:

- APIs
- RSS feeds
- SEC
- public datasets
- configured search/research APIs

The system should never break because one agent is unavailable.

IMPORTANT:

Do not bypass:
- authentication
- paywalls
- CAPTCHAs
- robots restrictions
- website protections
- licensing restrictions

Prefer official APIs whenever available.

Rate-limit all web collection.

Cache collected information.

Record source URL and retrieval timestamp.

---

# 8. DATA SOURCE TRANSPARENCY

Every important number should support provenance.

Where practical expose:

```text
Source:
Provider:
Retrieved:
Market timestamp:
Delay:
Cache status:
```

For research/news:

```text
Publisher:
Published:
Retrieved:
URL:
```

This is extremely important.

---

# 9. GLOBAL HEADER

Create a beautiful fixed top navigation bar.

Include:

- application logo/name
- global search
- Markets
- Stocks
- ETFs
- Crypto
- Commodities
- Forex
- Bonds
- Rates
- Real Estate
- Rare Earths
- Economics
- News
- Screener
- Portfolio
- Watchlists
- Calendar
- Research
- AI Advisor
- Settings

Top-right should display:

- current local time
- market status
- data-status indicator
- refresh button
- settings icon

---

# 10. GLOBAL MARKET TICKER

Under the header create a horizontally scrolling market strip.

Display representative instruments such as:

US:
- S&P 500
- Nasdaq 100
- Dow Jones
- Russell 2000
- VIX

Europe:
- FTSE 100
- DAX
- CAC 40
- STOXX Europe 600

Asia:
- Nikkei 225
- Hang Seng
- Shanghai Composite
- Nifty 50
- Sensex

Other:

- Gold
- Silver
- Copper
- WTI
- Brent
- Natural Gas
- Bitcoin
- Ethereum
- US 10Y yield
- DXY
- EUR/USD
- USD/JPY

Show:

- value
- absolute change
- percentage change
- mini sparkline where possible

---

# 11. MAIN MARKET OVERVIEW PAGE

The homepage should resemble a professional financial command center.

Include cards/sections for:

## Global Indices

Table columns:

- market
- last
- change
- %
- day high
- day low
- 52-week range
- volume
- timestamp

## Market Heatmap

Interactive equity heatmap grouped by:

- sector
- industry
- market cap

Size tiles by market cap.

Color based on performance.

Allow:

- 1D
- 5D
- 1M
- YTD
- 1Y

## Market Breadth

Show metrics such as:

- advancers
- decliners
- unchanged
- stocks above 20DMA
- above 50DMA
- above 200DMA
- new highs
- new lows

## Volatility

Track:

- VIX
- MOVE index if data is available
- realized volatility
- historical volatility

---

# 12. STOCKS MODULE

The Stocks section should include:

- US equities
- international equities
- ADRs
- micro cap
- small cap
- mid cap
- large cap
- mega cap

Search by:

- ticker
- company
- industry
- sector
- exchange

Stock detail page must include:

## Quote

- price
- change
- percent change
- premarket
- after-hours
- open
- previous close
- day range
- 52-week range
- volume
- average volume
- market cap

## Chart

Interactive chart supporting:

- 1D
- 5D
- 1M
- 3M
- 6M
- YTD
- 1Y
- 3Y
- 5Y
- MAX

Chart types:

- line
- candlestick
- OHLC

Indicators where technically reasonable:

- SMA
- EMA
- RSI
- MACD
- Bollinger Bands
- volume

## Company Fundamentals

Show:

- revenue
- EBITDA
- operating income
- net income
- EPS
- free cash flow
- cash
- debt
- enterprise value

Valuation:

- P/E
- forward P/E
- PEG
- P/S
- P/B
- EV/Sales
- EV/EBITDA
- FCF yield
- dividend yield

Profitability:

- gross margin
- operating margin
- net margin
- ROA
- ROE
- ROIC

Growth:

- revenue growth
- EPS growth
- FCF growth

Balance-sheet metrics:

- current ratio
- quick ratio
- debt/equity
- interest coverage

---

# 13. FINANCIAL STATEMENTS

Create structured views for:

- Income Statement
- Balance Sheet
- Cash Flow

Allow:

- annual
- quarterly
- TTM

If possible provide 5–10 years of history depending on provider availability.

---

# 14. COMPANY INTELLIGENCE

Create sections for:

- business description
- sector
- industry
- headquarters
- employees
- management
- website
- exchange
- IPO date
- CIK
- competitors
- suppliers if known
- geographic exposure
- revenue segments

---

# 15. SEC FILINGS

Integrate SEC EDGAR where possible.

Display:

- 10-K
- 10-Q
- 8-K
- DEF 14A
- S-1
- Form 4
- 13D
- 13G
- 13F where relevant

Allow user to click through to source documents.

Add an AI summarization option for filings.

Summaries must reference the original filing.

---

# 16. ETFs

Track:

- broad market
- sector
- factor
- thematic
- international
- commodity
- fixed income
- leveraged
- inverse

Show:

- NAV
- AUM
- expense ratio
- holdings
- sector exposure
- geographic exposure
- yield
- performance

---

# 17. CRYPTOCURRENCY

Build a full crypto dashboard.

Support:

- Bitcoin
- Ethereum
- major altcoins
- stablecoins
- DeFi tokens
- Layer-1
- Layer-2
- AI-related tokens
- infrastructure tokens

Metrics where available:

- price
- market cap
- volume
- circulating supply
- max supply
- FDV
- dominance
- 24H
- 7D
- 30D
- YTD

Include crypto market heatmaps.

---

# 18. COMMODITIES

Track:

Energy:
- WTI crude
- Brent
- gasoline
- heating oil
- natural gas

Metals:
- gold
- silver
- copper
- platinum
- palladium
- aluminum
- nickel
- zinc
- tin

Agriculture:
- wheat
- corn
- soybeans
- coffee
- cocoa
- sugar
- cotton
- cattle

Display futures curves when data permits.

---

# 19. RARE EARTH & CRITICAL MINERALS SECTION

Create a specialized section covering industries and companies related to:

- lithium
- cobalt
- nickel
- graphite
- uranium
- rare-earth elements
- neodymium
- praseodymium
- dysprosium
- terbium
- scandium
- gallium
- germanium
- antimony
- copper

Track companies connected to:

- mining
- refining
- processing
- recycling
- battery materials
- magnets
- nuclear fuel
- strategic metals

Include geographic and supply-chain exposure when legitimate data is available.

---

# 20. FOREX

Support major and selected emerging-market currency pairs.

Examples:

- EUR/USD
- GBP/USD
- USD/JPY
- USD/CHF
- AUD/USD
- USD/CAD
- NZD/USD
- USD/INR
- USD/CNY
- USD/MXN
- USD/BRL

Include:

- spot
- daily move
- historical chart
- volatility
- interest-rate context

---

# 21. BONDS & INTEREST RATES

Build an institutional fixed-income dashboard.

US Treasury:

- 1M
- 3M
- 6M
- 1Y
- 2Y
- 3Y
- 5Y
- 7Y
- 10Y
- 20Y
- 30Y

Show yield curve visualization.

Calculate spreads such as:

- 10Y–2Y
- 10Y–3M
- 30Y–10Y

Where data exists also track:

- corporate bonds
- investment grade
- high yield
- municipal bonds
- TIPS
- sovereign debt
- mortgage rates

---

# 22. CENTRAL BANK MONITOR

Create dashboards for:

- Federal Reserve
- ECB
- Bank of England
- Bank of Japan
- Reserve Bank of India
- Bank of Canada
- RBA
- PBOC

Track:

- policy rates
- latest decision
- next scheduled meeting
- recent policy statements
- rate history

---

# 23. ECONOMIC DASHBOARD

Integrate macroeconomic indicators.

US examples:

- CPI
- Core CPI
- PCE
- Core PCE
- unemployment
- nonfarm payrolls
- GDP
- retail sales
- industrial production
- ISM
- consumer confidence
- housing starts
- building permits
- existing-home sales
- new-home sales
- jobless claims
- JOLTS
- wage growth

International:

- inflation
- GDP
- unemployment
- PMI
- industrial output
- policy rates

Allow charts and historical comparison.

---

# 24. REAL ESTATE SECTION

Create a macro real-estate dashboard.

Track available public data such as:

- mortgage rates
- home-price indices
- Case-Shiller
- FHFA indices
- housing starts
- building permits
- home sales
- housing inventory
- rental indicators
- REIT performance

Separate:

- residential
- commercial
- office
- industrial
- multifamily
- retail
- hospitality
- data centers

Also create a REIT screener.

---

# 25. MARKET SECTORS

Track all major equity sectors:

- Technology
- Financials
- Healthcare
- Industrials
- Consumer Discretionary
- Consumer Staples
- Energy
- Materials
- Utilities
- Communication Services
- Real Estate

For every sector show:

- daily performance
- weekly
- monthly
- YTD
- valuation
- earnings growth
- market breadth
- representative ETFs
- leading companies
- lagging companies

---

# 26. THEMATIC MARKETS

Create configurable thematic baskets including:

- Artificial Intelligence
- Semiconductors
- Cloud Computing
- Cybersecurity
- Robotics
- Quantum Computing
- Defense
- Aerospace
- Nuclear
- Uranium
- Clean Energy
- Solar
- Hydrogen
- EVs
- Batteries
- Rare Earths
- Biotech
- Space
- Data Centers
- Infrastructure
- FinTech

Baskets should be configurable through JSON/YAML.

---

# 27. NEWS INTELLIGENCE ENGINE

Create a full financial-news dashboard.

Categories:

- Markets
- Stocks
- Economy
- Federal Reserve
- Crypto
- Commodities
- Technology
- Energy
- Real Estate
- Bonds
- Forex
- M&A
- Earnings
- IPOs
- Regulation
- Geopolitics
- Global Markets

Each story card should show:

- headline
- publisher
- timestamp
- category
- tickers
- thumbnail if legally available
- short generated summary
- source link

Do not reproduce full copyrighted articles.

Only:
- headline
- metadata
- a short summary
- source URL

---

# 28. NEWS DEDUPLICATION

Multiple publications will cover the same story.

Create a deduplication pipeline.

Cluster stories based on:

- title similarity
- named entities
- ticker symbols
- event keywords
- publication timing

Display one event cluster such as:

```text
Federal Reserve leaves rates unchanged

12 publications reporting

Reuters
CNBC
Bloomberg
WSJ
Financial Times
...
```

Do not reproduce copyrighted text.

---

# 29. MARKET-MOVING NEWS

Create an algorithm that attempts to identify potentially significant market stories based on objective indicators including:

- number of sources covering the event
- affected market capitalization
- price reaction
- volatility
- trading volume
- earnings surprises
- macroeconomic relevance

Label the section:

**Potential Market-Moving Developments**

Avoid presenting speculation as fact.

---

# 30. EARNINGS CENTER

Create:

- earnings calendar
- today
- tomorrow
- this week
- next week

Show:

- company
- ticker
- expected EPS
- previous EPS
- expected revenue
- timing
- market cap

After earnings show:

- reported EPS
- surprise
- revenue
- surprise
- share-price reaction

---

# 31. ECONOMIC CALENDAR

Create calendar support for:

- CPI
- GDP
- unemployment
- payrolls
- central-bank meetings
- PMI
- retail sales
- housing
- earnings
- Treasury auctions

Display:

- date
- time
- country
- event
- importance
- previous
- forecast
- actual

---

# 32. GLOBAL SEARCH

The search bar should find:

- companies
- stocks
- ETFs
- crypto assets
- commodities
- currencies
- bonds
- economic indicators
- articles
- sectors
- industries

Implement autocomplete.

Keyboard shortcut:

```text
Ctrl + K
```

or

```text
Cmd + K
```

---

# 33. WATCHLISTS

Allow users to create multiple watchlists.

Examples:

- Portfolio
- AI
- Semiconductor
- Energy
- Rare Earths
- Crypto
- Dividend Stocks
- Real Estate
- Bonds

Watchlists should persist locally.

Use:

- SQLite
or
- browser local storage for simple UI preferences

Use SQLite for important application state.

---

# 34. PORTFOLIO TRACKER

Allow manual portfolio creation.

Fields:

- symbol
- quantity
- purchase price
- purchase date
- notes

Calculate:

- market value
- cost basis
- unrealized gain/loss
- percentage return
- allocation
- sector exposure
- geographic exposure
- concentration

Never execute trades.

This is a research and tracking application only.

---

# 35. SCREENER

Create a stock screener.

Filters:

- market cap
- sector
- industry
- country
- price
- volume
- average volume
- P/E
- forward P/E
- PEG
- price/sales
- price/book
- EV/EBITDA
- dividend yield
- revenue growth
- EPS growth
- ROE
- ROIC
- debt/equity
- gross margin
- operating margin
- RSI
- price relative to moving averages

Allow:

- AND filters
- sorting
- save screener
- export CSV

---

# 36. COMPARISON TOOL

Allow up to 5 assets to be compared.

Comparison dimensions:

- price performance
- valuation
- growth
- profitability
- balance sheet
- volatility
- technical indicators

Support comparison across:

- stocks
- ETFs
- crypto
- commodities

where metrics are meaningful.

---

# 37. TECHNICAL ANALYSIS ENGINE

Calculate indicators locally where historical data exists.

Implement:

- SMA
- EMA
- RSI
- MACD
- Bollinger Bands
- ATR
- stochastic oscillator
- rate of change
- volatility
- volume averages
- relative strength

Do not characterize signals as guaranteed predictions.

Instead display statements such as:

```text
RSI is currently 72, placing the asset in a historically elevated momentum range.
```

---

# 38. FUNDAMENTAL ANALYSIS ENGINE

Build reusable financial analytics.

Examples:

Valuation:

```text
P/E
Forward P/E
PEG
P/S
P/B
EV/EBITDA
EV/Revenue
FCF Yield
Dividend Yield
```

Quality:

```text
ROE
ROA
ROIC
Gross Margin
Operating Margin
Net Margin
FCF Margin
```

Growth:

```text
Revenue CAGR
EPS CAGR
FCF CAGR
```

Financial strength:

```text
Net debt
Net debt/EBITDA
Debt/equity
Current ratio
Interest coverage
```

---

# 39. FINANCIAL ANALYSIS REPORT

Create an **Analysis** tab for each security.

The analysis engine should generate a structured research report using the retrieved data.

Suggested sections:

## Executive Snapshot

## Business Overview

## Recent Price Behavior

## Financial Performance

## Revenue Growth

## Earnings

## Cash Flow

## Balance Sheet

## Valuation

## Profitability

## Competitive Position

## Industry Context

## Macro Sensitivity

## Catalysts

## Risks

## Technical Picture

## Recent News

## SEC Filing Developments

## Key Metrics to Monitor

## Scenario Analysis

Do not reduce complex investment decisions to simplistic:

```text
BUY
SELL
GUARANTEED WINNER
```

Present evidence and scenarios.

---

# 40. SCENARIO ANALYSIS

Create:

### Bull Scenario

What assumptions would cause material upside?

### Base Scenario

What assumptions represent continuation of current fundamentals?

### Bear Scenario

What risks could materially impair performance?

Display assumptions separately.

Do not present any scenario as certain.

---

# 41. VALUATION MODELS

Where enough data exists implement tools for:

- DCF
- reverse DCF
- dividend discount model
- comparable valuation
- historical multiple comparison

Allow the user to modify assumptions.

Example:

```text
Revenue growth
Operating margin
Tax rate
WACC
Terminal growth
Share count
Net debt
```

Display sensitivity tables.

---

# 42. AI FINANCIAL RESEARCH ADVISOR

The final major section should be:

# ASK THE FINANCIAL RESEARCH ADVISOR

Create a sophisticated chat interface.

The AI should behave like an interdisciplinary financial research analyst combining knowledge of:

- equities
- macroeconomics
- accounting
- corporate finance
- valuation
- fixed income
- commodities
- foreign exchange
- cryptocurrency
- real estate
- monetary policy
- banking
- derivatives concepts
- economics
- corporate strategy
- portfolio analytics
- financial history
- market structure

The assistant should be highly analytical, but must not pretend to know facts it cannot verify.

---

# 43. AI ADVISOR CONTEXT

When the user asks:

```text
Analyze NVDA
```

the backend should automatically assemble context from available sources:

- live/latest quote
- historical prices
- financial statements
- valuation metrics
- news
- filings
- sector performance
- relevant macro environment
- technical indicators

Then send this structured context into the configured AI model.

---

# 44. ADVISOR RESPONSE FORMAT

For asset analysis, prefer:

```text
1. Executive Summary
2. Current Market Situation
3. Business Fundamentals
4. Earnings and Cash Flow
5. Valuation
6. Technical Context
7. Macro Context
8. Recent Developments
9. Catalysts
10. Risks
11. Bull Scenario
12. Base Scenario
13. Bear Scenario
14. Metrics to Watch
15. Data Sources
```

For questions such as:

```text
Why did gold move today?
```

use:

```text
1. What happened
2. Most relevant observable drivers
3. Dollar impact
4. Rates impact
5. Inflation expectations
6. Geopolitical developments
7. Technical context
8. Alternative explanations
9. Sources
```

---

# 45. AI RESEARCH GUARDRAILS

The AI advisor must:

- distinguish facts from interpretation
- cite sources when available
- show data timestamps
- identify stale data
- state when data is unavailable
- avoid hallucinating earnings numbers
- avoid hallucinating prices
- avoid invented analyst targets
- avoid fake citations
- avoid certainty about future price movements

Whenever AI analysis uses fetched financial information, pass structured context to the model rather than asking the LLM to guess market data.

---

# 46. DASHBOARD DESIGN

The application should be extremely visually impressive.

Design direction:

- institutional terminal
- premium fintech
- information-dense without clutter
- professional
- responsive
- sharp typography
- dark mode first

Dark theme inspiration:

```text
Background: charcoal / near-black
Panels: slightly lighter
Positive numbers: green
Negative numbers: red
Neutral: gray
Accent: electric blue / cyan
```

But create an original design.

Do not copy Investing.com pixel-for-pixel.

---

# 47. LIGHT MODE

Include:

- Dark mode
- Light mode
- System mode

Persist preference.

---

# 48. CARD SYSTEM

Create consistent cards.

Example:

```text
┌───────────────────────────────────┐
│ S&P 500                    OPEN   │
│ 6,214.32                         │
│ +42.31 (+0.69%)                  │
│ ▁▂▃▄▅▆▅▇                         │
│ Day range: ...                   │
└───────────────────────────────────┘
```

---

# 49. CHARTING

Prefer powerful open-source charting libraries.

Consider:

- Apache ECharts
- Lightweight Charts
- Plotly

Charts should support:

- zoom
- pan
- tooltip
- crosshair
- responsive resizing

Financial charts should look institutional.

---

# 50. DASHBOARD PERSONALIZATION

Allow user to rearrange or configure widgets.

Examples:

```text
Market Overview
Portfolio
Watchlist
News
Crypto
Yield Curve
Economic Calendar
Sector Heatmap
```

Persist layout.

---

# 51. REFRESH SYSTEM

The Refresh button is a major feature.

When clicked:

1. Disable the button temporarily.
2. Display progress.
3. Call the backend `/api/refresh`.
4. Refresh selected sources.
5. Update database/cache.
6. Recalculate analytics.
7. Reload visible widgets.
8. Display completion summary.

Example:

```text
Refreshing markets...

✓ US equities
✓ Treasury yields
✓ Crypto
✓ Commodities
✓ Forex
✓ Economic data
✓ News
⚠ Company fundamentals — provider rate limited

Last completed: 4:42:18 PM
```

---

# 52. SELECTIVE REFRESH

Allow:

```text
Refresh Everything
Refresh Markets
Refresh News
Refresh Crypto
Refresh Economics
Refresh Portfolio
Refresh Current Asset
```

Avoid unnecessary API consumption.

---

# 53. CACHING

Implement intelligent caching.

Examples:

Quotes:
```text
30–60 seconds
```

Company fundamentals:
```text
6–24 hours
```

Economic indicators:
```text
6–24 hours
```

News:
```text
5–15 minutes
```

SEC filings:
```text
30–60 minutes
```

Historical prices:
```text
15 minutes during trading hours
longer when markets are closed
```

Cache policy should be configurable.

---

# 54. SQLITE DATABASE

Use SQLite initially.

Suggested tables:

```text
assets
quotes
price_history
company_profiles
financial_statements
fundamentals
news
news_clusters
economic_indicators
watchlists
watchlist_items
portfolio_positions
research_reports
filings
refresh_logs
provider_status
user_preferences
```

Use migrations if appropriate.

---

# 55. LOGGING

Create structured logs.

Include:

```text
application.log
provider.log
refresh.log
research.log
error.log
```

Do not expose API keys in logs.

---

# 56. PROVIDER HEALTH DASHBOARD

Settings should include:

```text
Provider                 Status
Yahoo-compatible         Online
FRED                      Online
CoinGecko                 Online
SEC                       Online
News Provider             Rate limited
TinyFish                  Not configured
```

Show:

- status
- latest request
- latest success
- latest failure
- remaining quota if known

---

# 57. SETTINGS PAGE

Allow configuration of:

- API keys
- default market
- default watchlist
- refresh intervals
- theme
- AI provider
- AI model
- enabled news providers
- enabled market-data providers
- caching
- timezone
- currency

Secrets should preferably remain in `.env`, not browser storage.

---

# 58. GLOBAL MARKET CLOCK

Show major sessions:

```text
New York
London
Frankfurt
Tokyo
Hong Kong
Shanghai
Mumbai
Sydney
```

Display:

- Open
- Closed
- Pre-market where relevant
- opening countdown
- closing countdown

Calculate correctly based on timezone and market calendar.

---

# 59. PERFORMANCE

Do not download every available dataset on initial startup.

Use lazy loading.

Fetch data only for:

- visible modules
- selected assets
- active watchlists
- background refresh priorities

Use asynchronous backend requests.

Avoid blocking the UI.

---

# 60. ERROR HANDLING

Examples:

```text
Data provider temporarily unavailable.
Displaying cached value from 14:32 ET.
```

Or:

```text
No live quote provider configured.
Configure an API under Settings → Data Providers.
```

The UI should remain functional during partial outages.

---

# 61. SECURITY

Because the application may contain API credentials:

- backend owns credentials
- browser must not receive provider secrets
- use `.env`
- provide `.env.example`
- validate inputs
- sanitize URLs
- protect against injection
- use proper CORS restrictions
- bind server to localhost by default

Do not expose localhost service publicly unless explicitly configured.

---

# 62. TESTING

Create tests for:

- market data adapters
- financial calculations
- caching
- refresh system
- API endpoints
- data normalization
- screener filters

Use unit tests and basic integration tests.

---

# 63. DOCUMENTATION

README must explain:

## Installation

## Python setup

## Node setup

## Environment variables

## API keys

## Running locally

## Refresh architecture

## Data providers

## Adding another provider

## Adding a market

## Troubleshooting

## Architecture

## Limitations

---

# 64. FIRST-RUN EXPERIENCE

If no API keys are configured, the application should still open.

Show a setup wizard:

```text
Welcome to OmniMarket Intelligence

Connect data sources:

[ ] FRED
[ ] SEC
[ ] Crypto provider
[ ] Equity provider
[ ] News provider
[ ] AI provider
[ ] Web Research Agent

Continue
```

Allow users to configure providers later.

---

# 65. RESEARCH COMMAND CENTER

Create a dedicated research page.

User can enter:

```text
TSLA
```

or:

```text
US semiconductor industry
```

or:

```text
What is happening in copper?
```

System should collect:

- market data
- fundamentals
- news
- macro indicators
- industry context
- relevant filings

Then create a structured research workspace.

---

# 66. EVENT TIMELINE

For stocks create a timeline including:

- earnings
- SEC filings
- dividends
- acquisitions
- management changes
- product announcements
- major news

---

# 67. MARKET CORRELATION TOOL

Allow users to compare relationships between:

- stocks
- indexes
- commodities
- bonds
- currencies
- crypto

Calculate historical correlations.

Example:

```text
BTC vs Nasdaq
Gold vs DXY
Oil vs Energy Stocks
10Y Yield vs Tech
Copper vs China Equities
```

---

# 68. RISK DASHBOARD

Create objective risk indicators such as:

- VIX
- credit spreads where available
- yield curve
- dollar index
- commodity volatility
- crypto volatility
- market breadth
- equity drawdowns

Do not invent a proprietary "risk score" unless its formula is explicitly shown.

---

# 69. DATA NORMALIZATION

Different providers use different symbols.

Create an internal canonical asset schema.

Example:

```json
{
  "id": "equity:US:AAPL",
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "asset_class": "equity",
  "exchange": "NASDAQ",
  "currency": "USD",
  "country": "US"
}
```

All providers should map into this schema.

---

# 70. BACKEND ENDPOINTS

Create APIs similar to:

```text
GET /api/markets/overview
GET /api/assets/search?q=
GET /api/assets/{id}
GET /api/assets/{id}/quote
GET /api/assets/{id}/history
GET /api/assets/{id}/fundamentals
GET /api/assets/{id}/news
GET /api/assets/{id}/analysis

GET /api/news
GET /api/economics
GET /api/bonds
GET /api/commodities
GET /api/crypto
GET /api/forex
GET /api/real-estate

POST /api/refresh
POST /api/research
POST /api/advisor/chat

GET /api/providers/status
```

Use OpenAPI docs automatically through FastAPI.

---

# 71. REAL-TIME ARCHITECTURE

Initially use polling.

Architect the system so WebSockets can later be added for:

- live quotes
- breaking news
- market status
- portfolio changes

Do not over-engineer prematurely.

---

# 72. USER EXPERIENCE DETAILS

Include:

- loading skeletons
- hover states
- keyboard navigation
- tooltips
- sortable tables
- resizable sections
- sticky table headers
- pagination
- search filtering
- responsive navigation
- empty states
- data-source badges

---

# 73. ACCESSIBILITY

Follow WCAG best practices.

Do not rely only on green/red.

Use:

- arrows
- plus/minus
- labels
- accessible contrast

---

# 74. EXPORT

Allow exports where appropriate:

- CSV
- JSON
- PNG for charts
- printable research report

Do not illegally redistribute proprietary provider datasets.

---

# 75. FUTURE PLUGIN ARCHITECTURE

Make these capabilities modular:

```text
MarketDataProvider
NewsProvider
EconomicDataProvider
CryptoProvider
FilingsProvider
ResearchAgent
AIProvider
```

The entire application should not depend on one vendor.

---

# 76. CODING STANDARD

Use:

- typed models where possible
- TypeScript preferred frontend
- Python type hints
- Pydantic models
- reusable components
- modular services
- central configuration
- environment variables
- comments for difficult financial calculations

Avoid:

- giant monolithic files
- duplicated functions
- inline CSS everywhere
- fake placeholder functionality
- broken buttons

---

# 77. BUILD STRATEGY

Do not attempt to build every obscure market simultaneously before establishing the architecture.

Build the application in phases while maintaining the full architecture.

### Phase 1

Foundation:

- FastAPI backend
- React frontend
- SQLite
- provider architecture
- market overview
- search
- stocks
- crypto
- commodities
- bonds
- news
- refresh
- watchlists
- advisor shell

### Phase 2

Advanced analytics:

- financial statements
- technical indicators
- screeners
- economic dashboard
- earnings
- SEC
- yield curves
- portfolio analysis

### Phase 3

Research intelligence:

- research agent
- news clustering
- deep company research
- AI advisor context engine
- DCF models
- scenario analysis

### Phase 4

Advanced assets:

- global equities
- rare earths
- real estate
- thematic baskets
- international macro
- expanded fixed income

The codebase should support all phases from the start.

---

# 78. INITIAL DELIVERABLE

Start implementing the actual project.

Do not only describe it.

Your response/work should result in a working repository.

First:

1. Inspect the current working directory.
2. Create the project architecture.
3. Create backend.
4. Create frontend.
5. Add SQLite.
6. Add the provider abstraction.
7. Add at least a few functioning public/free data integrations where practical.
8. Add market dashboard.
9. Add Refresh functionality.
10. Add news.
11. Add asset search.
12. Add detail page.
13. Add AI Advisor infrastructure.
14. Add setup/configuration screen.
15. Add documentation.
16. Run the application.
17. Fix build/runtime errors.
18. Verify all major navigation routes.
19. Run tests.
20. Provide the exact startup command.

Continue implementing rather than stopping after scaffolding.

---

# 79. DEFINITION OF DONE

The first usable release is not complete unless:

- localhost application launches
- dashboard renders correctly
- navigation works
- Refresh button works
- at least one real market data provider works
- stock lookup works
- crypto data works
- news data works
- data timestamps are shown
- cached data works
- errors do not crash the UI
- watchlist persists
- charts work
- dark/light mode works
- backend OpenAPI works
- AI Advisor UI works
- AI provider is configurable
- secrets stay server-side
- README gives exact instructions
- application looks professionally designed

---

# 80. VERY IMPORTANT DESIGN REQUIREMENT

The interface must NOT look like:

- a school project
- Bootstrap defaults
- a generic admin dashboard
- plain white HTML tables
- an AI-generated prototype
- an unfinished developer console

It should look like a premium institutional financial intelligence platform.

Use:

- excellent spacing
- strong typography
- sophisticated information hierarchy
- dense but readable tables
- elegant charts
- polished hover states
- responsive cards
- consistent iconography
- professional skeleton loaders
- subtle animations
- contextual colors
- strong empty/error states

---

# 81. INFORMATION DENSITY

Design primarily for desktop monitors.

Support:

- 1920×1080
- 2560×1440
- ultrawide monitors

The terminal should make intelligent use of horizontal space.

For desktop, support a layout similar to:

```text
┌───────────────────────────────────────────────────────────────────────┐
│ Global Navigation                                    Search | Refresh │
├───────────────────────────────────────────────────────────────────────┤
│ Market Ticker                                                        │
├────────────┬──────────────────────────────────────┬───────────────────┤
│ Navigation │ Main Market Workspace                │ Watchlist         │
│            │                                      │                   │
│            │ Charts                               │ News              │
│            │                                      │                   │
│            │ Tables                               │ Calendar          │
├────────────┴──────────────────────────────────────┴───────────────────┤
│ Market Intelligence / News / Analytics                               │
└───────────────────────────────────────────────────────────────────────┘
```

Mobile can simplify this significantly.

---

# 82. SOURCE PRIORITY

Prefer authoritative or first-party sources.

Priority:

1. Exchange / regulator / government
2. Company filings / investor relations
3. Licensed market-data API
4. Major financial-news organizations
5. Trusted secondary datasets
6. Research-agent/web extraction only when appropriate

Never scrape a website simply because it is easier than using an available official API.

---

# 83. FINANCIAL RESEARCH QUALITY

The analysis should attempt to answer:

```text
What changed?
Why might it matter?
What financial evidence supports it?
What data contradicts the thesis?
What could invalidate the thesis?
What should be monitored next?
```

Avoid shallow language such as:

```text
The stock looks good because revenue increased.
```

Instead analyze relationships between:

- revenue
- margins
- operating leverage
- cash conversion
- capital expenditures
- free cash flow
- dilution
- debt
- valuation
- industry cycle
- rates
- economic environment

---

# 84. DON'T HIDE UNCERTAINTY

Where evidence is mixed, say so.

Example:

```text
Three potential drivers coincide with the move, but available evidence does not establish a single causal explanation.
```

This is preferable to inventing certainty.

---

# 85. FINAL ADVISOR DISCLAIMER

The Advisor page should contain a small professional notice:

```text
Research and analytical information only. Market data may be delayed or incomplete. This application does not execute trades and is not a substitute for personalized professional financial, tax, or legal advice.
```

Do not flood the UI with disclaimers.

---

# 86. OPTIONAL ADVANCED FEATURES

After the core platform works, consider:

- options chains
- implied volatility
- volatility smile
- put/call ratios
- short interest
- institutional ownership
- insider transactions
- analyst estimate trends
- dividend calendars
- IPO calendar
- M&A activity
- congressional trading datasets where legally available
- ETF flows
- dark-pool information only from legitimate providers
- sentiment analytics
- commodity inventories
- shipping data integrations
- economic nowcasting
- factor analytics

These should not delay the stable core release.

---

# 87. PROJECT QUALITY REQUIREMENT

Before declaring completion:

Run the project.

Check the browser.

Look for:

- broken layouts
- console errors
- API failures
- responsive issues
- blank charts
- incorrect timestamps
- broken routes
- refresh failures

Fix them.

Do not tell me:

```text
You can implement this later.
```

Implement as much of the working system as possible now.

When API credentials are required, create the integration and configuration UX even if I have not supplied the credential yet.

---

# 88. START NOW

Proceed as the technical lead.

Start by inspecting the environment and generating the working application architecture.

Then implement the first functional version.

Do not stop after writing a project plan.

Create the files, install/configure dependencies where permitted, run the application, test it, and iterate until the major flows are functional.
