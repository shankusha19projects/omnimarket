"""Provider registry: single place where concrete vendors are instantiated and ordered."""
from __future__ import annotations

from backend.providers.calendars import NasdaqCalendarProvider
from backend.providers.coingecko import CoinGeckoProvider
from backend.providers.keyed import AlphaVantageProvider, FinnhubProvider, FMPProvider, NewsAPIProvider, PolygonProvider
from backend.providers.macro import BLSProvider, CentralBankRates, FREDProvider, TreasuryProvider, WorldBankProvider
from backend.providers.rss import RSSProvider
from backend.providers.sec import SECProvider
from backend.providers.yahoo import YahooProvider

yahoo = YahooProvider()
sec = SECProvider()
coingecko = CoinGeckoProvider()
treasury = TreasuryProvider()
fred = FREDProvider()
bls = BLSProvider()
worldbank = WorldBankProvider()
central_banks = CentralBankRates()
nasdaq = NasdaqCalendarProvider()
rss = RSSProvider()
finnhub = FinnhubProvider()
fmp = FMPProvider()
polygon = PolygonProvider()
alphavantage = AlphaVantageProvider()
newsapi = NewsAPIProvider()

# Ordered fallback chain for equity quotes. Keyed providers join when configured.
QUOTE_CHAIN = [yahoo, fmp, finnhub, polygon, alphavantage]

# Metadata for the Provider Health dashboard: (health_key, label, requires_key, homepage, kind)
CATALOG = [
    ("yahoo", "Yahoo-compatible", None, "https://finance.yahoo.com", "Quotes, history, fundamentals, search"),
    ("sec", "SEC EDGAR", None, "https://www.sec.gov/edgar", "Filings, XBRL financial statements"),
    ("coingecko", "CoinGecko", None, "https://www.coingecko.com/en/api", "Crypto markets"),
    ("treasury", "U.S. Treasury", None, "https://home.treasury.gov", "Daily yield curves (nominal & real)"),
    ("bls", "BLS Public API", None, "https://www.bls.gov/developers/", "CPI, jobs, wages (keyless v1)"),
    ("fred", "FRED", "FRED_API_KEY", "https://fred.stlouisfed.org", "800k+ US & intl. economic series"),
    ("worldbank", "World Bank", None, "https://data.worldbank.org", "International macro"),
    ("nyfed", "NY Fed Markets", None, "https://markets.newyorkfed.org", "Fed funds (EFFR)"),
    ("ecb", "ECB Data Portal", None, "https://data.ecb.europa.eu", "ECB policy rates"),
    ("boe", "Bank of England IADB", None, "https://www.bankofengland.co.uk/boeapps/database", "Bank Rate"),
    ("boc", "Bank of Canada Valet", None, "https://www.bankofcanada.ca/valet/docs", "Policy rate"),
    ("nasdaq", "Nasdaq calendars", None, "https://www.nasdaq.com", "Earnings & economic calendar"),
    ("rss", "Publisher RSS feeds", None, None, "News headlines"),
    ("finnhub", "Finnhub", "FINNHUB_API_KEY", "https://finnhub.io", "Quotes, company news"),
    ("fmp", "Financial Modeling Prep", "FMP_API_KEY", "https://financialmodelingprep.com", "Quotes"),
    ("polygon", "Polygon.io", "POLYGON_API_KEY", "https://polygon.io", "Previous-session aggregates"),
    ("alphavantage", "Alpha Vantage", "ALPHA_VANTAGE_API_KEY", "https://www.alphavantage.co", "Quotes"),
    ("newsapi", "NewsAPI.org", "NEWS_API_KEY", "https://newsapi.org", "News search"),
    ("tinyfish", "TinyFish Web Agent", "TINYFISH_API_KEY", "https://www.tinyfish.ai", "Web search, fetch & agentic research"),
    ("anthropic", "Anthropic (Claude)", "ANTHROPIC_API_KEY", "https://console.anthropic.com", "AI advisor"),
    ("openai", "OpenAI", "OPENAI_API_KEY", "https://platform.openai.com", "AI advisor"),
    ("ollama", "Ollama (local)", None, "https://ollama.com", "Local AI advisor"),
]
