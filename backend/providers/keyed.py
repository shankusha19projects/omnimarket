"""Optional keyed providers. They activate automatically when their API key is set in `.env`
and serve as fallbacks in the quote chain (or primary sources where noted)."""
from __future__ import annotations

import time
from typing import Any

from backend.config import env
from backend.models.schemas import Bar, NewsItem, Quote
from backend.providers.base import MarketDataProvider, NewsProvider
from backend.providers.rss import item_id, strip_html
from backend.utils import http
from backend.utils.http import ProviderError


class _KeyedQuoteProvider(MarketDataProvider):
    async def get_history(self, symbol: str, range_: str, interval: str) -> tuple[list[Bar], dict[str, Any]]:
        raise ProviderError(self.name, "history not implemented for this provider; Yahoo-compatible provider is used")

    def _key(self) -> str:
        key = env(self.requires_key or "")
        if not key:
            raise ProviderError(self.name, f"{self.requires_key} not configured")
        return key


class FinnhubProvider(_KeyedQuoteProvider, NewsProvider):
    name, label, requires_key, homepage = "finnhub", "Finnhub", "FINNHUB_API_KEY", "https://finnhub.io"

    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        out = {}
        for s in symbols[:30]:
            d = await http.get_json(self.name, "https://finnhub.io/api/v1/quote", params={"symbol": s, "token": self._key()})
            if d.get("c"):
                out[s] = Quote(symbol=s, price=d["c"], change=d.get("d"), change_pct=d.get("dp"), prev_close=d.get("pc"),
                               open=d.get("o"), day_high=d.get("h"), day_low=d.get("l"), market_time=d.get("t"))
        return out

    async def get_news(self, query: str | None = None, limit: int = 50) -> list[NewsItem]:
        today = time.strftime("%Y-%m-%d")
        week = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 7 * 86400))
        if query:
            d = await http.get_json(self.name, "https://finnhub.io/api/v1/company-news", params={"symbol": query, "from": week, "to": today, "token": self._key()})
        else:
            d = await http.get_json(self.name, "https://finnhub.io/api/v1/news", params={"category": "general", "token": self._key()})
        now = time.time()
        return [NewsItem(id=item_id(n.get("url", ""), n.get("headline", "")), title=n.get("headline", ""), url=n.get("url", ""),
                         publisher=n.get("source") or "Finnhub", published_at=n.get("datetime"), retrieved_at=now,
                         summary=strip_html(n.get("summary")), tickers=[t for t in (n.get("related") or "").split(",") if t],
                         thumbnail=n.get("image") or None, source_feed="finnhub") for n in (d or [])[:limit] if n.get("url")]


class FMPProvider(_KeyedQuoteProvider):
    name, label, requires_key, homepage = "fmp", "Financial Modeling Prep", "FMP_API_KEY", "https://financialmodelingprep.com"

    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        d = await http.get_json(self.name, f"https://financialmodelingprep.com/api/v3/quote/{','.join(symbols[:50])}", params={"apikey": self._key()})
        return {r["symbol"]: Quote(symbol=r["symbol"], name=r.get("name"), price=r.get("price"), change=r.get("change"),
                                   change_pct=r.get("changesPercentage"), prev_close=r.get("previousClose"), open=r.get("open"),
                                   day_high=r.get("dayHigh"), day_low=r.get("dayLow"), year_high=r.get("yearHigh"), year_low=r.get("yearLow"),
                                   volume=r.get("volume"), avg_volume=r.get("avgVolume"), market_cap=r.get("marketCap"),
                                   exchange=r.get("exchange"), market_time=r.get("timestamp")) for r in d or []}


class PolygonProvider(_KeyedQuoteProvider):
    name, label, requires_key, homepage = "polygon", "Polygon.io", "POLYGON_API_KEY", "https://polygon.io"

    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        out = {}
        for s in symbols[:5]:  # free tier: 5 req/min
            d = await http.get_json(self.name, f"https://api.polygon.io/v2/aggs/ticker/{s}/prev", params={"apiKey": self._key()})
            for r in d.get("results") or []:
                out[s] = Quote(symbol=s, price=r.get("c"), open=r.get("o"), day_high=r.get("h"), day_low=r.get("l"),
                               volume=r.get("v"), market_time=(r.get("t") or 0) / 1000, extra={"note": "previous session close"})
        return out


class AlphaVantageProvider(_KeyedQuoteProvider):
    name, label, requires_key, homepage = "alphavantage", "Alpha Vantage", "ALPHA_VANTAGE_API_KEY", "https://www.alphavantage.co"

    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        out = {}
        for s in symbols[:5]:  # free tier: 25 req/day
            d = await http.get_json(self.name, "https://www.alphavantage.co/query", params={"function": "GLOBAL_QUOTE", "symbol": s, "apikey": self._key()})
            g = d.get("Global Quote") or {}
            if not g:
                if d.get("Note") or d.get("Information"):
                    raise ProviderError(self.name, "rate limited (daily quota)", 429)
                continue
            f = lambda k: float(g[k]) if g.get(k) not in (None, "") else None  # noqa: E731
            out[s] = Quote(symbol=s, price=f("05. price"), change=f("09. change"),
                           change_pct=float(g.get("10. change percent", "0").rstrip("%") or 0), prev_close=f("08. previous close"),
                           open=f("02. open"), day_high=f("03. high"), day_low=f("04. low"), volume=f("06. volume"))
        return out


class NewsAPIProvider(NewsProvider):
    name, label, requires_key, homepage = "newsapi", "NewsAPI.org", "NEWS_API_KEY", "https://newsapi.org"

    async def get_news(self, query: str | None = None, limit: int = 50) -> list[NewsItem]:
        key = env("NEWS_API_KEY")
        if not key:
            raise ProviderError(self.name, "NEWS_API_KEY not configured")
        if query:
            d = await http.get_json(self.name, "https://newsapi.org/v2/everything", params={"q": query, "language": "en", "sortBy": "publishedAt", "pageSize": limit}, headers={"X-Api-Key": key})
        else:
            d = await http.get_json(self.name, "https://newsapi.org/v2/top-headlines", params={"category": "business", "language": "en", "pageSize": limit}, headers={"X-Api-Key": key})
        now = time.time()
        from backend.providers.rss import _parse_date
        return [NewsItem(id=item_id(a.get("url", ""), a.get("title", "")), title=a.get("title", ""), url=a.get("url", ""),
                         publisher=(a.get("source") or {}).get("name") or "NewsAPI", published_at=_parse_date(a.get("publishedAt")),
                         retrieved_at=now, summary=strip_html(a.get("description")), thumbnail=a.get("urlToImage"), source_feed="newsapi")
                for a in d.get("articles", []) if a.get("url")]
