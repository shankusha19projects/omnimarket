"""Yahoo Finance-compatible provider (public chart / quote / search endpoints).

Data is typically delayed (exchange-dependent, commonly 15 min for equities
outside the US and real-time-ish for US via Nasdaq). Delay information from the
`exchangeDataDelayedBy` field is surfaced to the UI.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from backend.models.schemas import Bar, NewsItem, Quote
from backend.providers.base import MarketDataProvider
from backend.utils import http
from backend.utils.http import ProviderError

Q1 = "https://query1.finance.yahoo.com"
Q2 = "https://query2.finance.yahoo.com"

RANGE_INTERVAL = {
    "1d": ("1d", "5m"), "5d": ("5d", "15m"), "1mo": ("1mo", "60m"), "3mo": ("3mo", "1d"),
    "6mo": ("6mo", "1d"), "ytd": ("ytd", "1d"), "1y": ("1y", "1d"), "3y": ("3y", "1d"),
    "5y": ("5y", "1wk"), "10y": ("10y", "1wk"), "max": ("max", "1mo"),
}


def _raw(v: Any) -> Any:
    if isinstance(v, dict):
        return v.get("raw")
    return v


class YahooProvider(MarketDataProvider):
    name = "yahoo"
    label = "Yahoo-compatible (public endpoints)"
    homepage = "https://finance.yahoo.com"

    def __init__(self) -> None:
        self._crumb: str | None = None
        self._crumb_at = 0.0
        self._crumb_lock = asyncio.Lock()

    # ---- crumb/session handling -------------------------------------------------
    async def _get_crumb(self, force: bool = False) -> str:
        async with self._crumb_lock:
            if self._crumb and not force and time.time() - self._crumb_at < 3600:
                return self._crumb
            try:
                await http.client().get("https://fc.yahoo.com", timeout=10)
            except Exception:
                pass  # the cookie is set even on the 404 page; failures are tolerated
            crumb = await http.get_text(self.name, f"{Q1}/v1/test/getcrumb", timeout=10)
            if not crumb or "<" in crumb or len(crumb) > 40:
                raise ProviderError(self.name, "could not obtain session crumb")
            self._crumb, self._crumb_at = crumb.strip(), time.time()
            return self._crumb

    async def _crumbed(self, url: str, params: dict[str, Any]) -> Any:
        for attempt in range(2):
            crumb = await self._get_crumb(force=attempt > 0)
            try:
                return await http.get_json(self.name, url, params={**params, "crumb": crumb}, retries=0)
            except ProviderError as exc:
                if exc.status in (401, 403) and attempt == 0:
                    continue
                raise
        raise ProviderError(self.name, "authorization failed")

    # ---- quotes -----------------------------------------------------------------
    @staticmethod
    def _to_quote(r: dict[str, Any]) -> Quote:
        price = r.get("regularMarketPrice")
        return Quote(
            symbol=r.get("symbol"),
            name=r.get("longName") or r.get("shortName") or r.get("symbol"),
            price=price,
            change=r.get("regularMarketChange"),
            change_pct=r.get("regularMarketChangePercent"),
            prev_close=r.get("regularMarketPreviousClose"),
            open=r.get("regularMarketOpen"),
            day_high=r.get("regularMarketDayHigh"),
            day_low=r.get("regularMarketDayLow"),
            year_high=r.get("fiftyTwoWeekHigh"),
            year_low=r.get("fiftyTwoWeekLow"),
            volume=r.get("regularMarketVolume"),
            avg_volume=r.get("averageDailyVolume3Month"),
            market_cap=r.get("marketCap") or r.get("netAssets"),
            currency=r.get("currency"),
            exchange=r.get("fullExchangeName") or r.get("exchange"),
            market_state=r.get("marketState"),
            pre_price=r.get("preMarketPrice"),
            pre_change_pct=r.get("preMarketChangePercent"),
            post_price=r.get("postMarketPrice"),
            post_change_pct=r.get("postMarketChangePercent"),
            market_time=r.get("regularMarketTime"),
            quote_type=r.get("quoteType"),
            extra={k: r.get(k) for k in (
                "trailingPE", "forwardPE", "priceToBook", "epsTrailingTwelveMonths", "epsForward", "sharesOutstanding",
                "dividendYield", "trailingAnnualDividendYield", "fiftyDayAverage", "twoHundredDayAverage", "bookValue",
                "exchangeDataDelayedBy", "netExpenseRatio", "ytdReturn", "fiftyTwoWeekChangePercent", "averageAnalystRating",
                "earningsTimestamp", "exchangeTimezoneName", "financialCurrency", "priceEpsCurrentYear",
            ) if r.get(k) is not None},
        )

    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        out: dict[str, Quote] = {}
        chunks = [symbols[i:i + 60] for i in range(0, len(symbols), 60)]
        for chunk in chunks:
            try:
                data = await self._crumbed(f"{Q1}/v7/finance/quote", {"symbols": ",".join(chunk)})
                for r in data.get("quoteResponse", {}).get("result", []):
                    q = self._to_quote(r)
                    out[q.symbol] = q
            except ProviderError:
                # Fallback: per-symbol chart meta (no crumb needed).
                results = await asyncio.gather(*(self._quote_from_chart(s) for s in chunk), return_exceptions=True)
                for s, res in zip(chunk, results):
                    if isinstance(res, Quote):
                        out[s] = res
                if not out:
                    raise
        return out

    async def _quote_from_chart(self, symbol: str) -> Quote:
        bars, meta = await self.get_history(symbol, "5d", "1d")
        price = meta.get("regularMarketPrice")
        prev = meta.get("previousClose")
        if prev is None and len(bars) >= 2:
            prev = bars[-2].c
        change = price - prev if price is not None and prev else None
        return Quote(
            symbol=symbol, name=meta.get("longName") or meta.get("shortName") or symbol, price=price,
            change=change, change_pct=(change / prev * 100) if change is not None and prev else None, prev_close=prev,
            day_high=meta.get("regularMarketDayHigh"), day_low=meta.get("regularMarketDayLow"),
            year_high=meta.get("fiftyTwoWeekHigh"), year_low=meta.get("fiftyTwoWeekLow"),
            volume=meta.get("regularMarketVolume"), currency=meta.get("currency"), exchange=meta.get("fullExchangeName"),
            market_time=meta.get("regularMarketTime"), quote_type=meta.get("instrumentType"),
        )

    # ---- history ----------------------------------------------------------------
    async def get_history(self, symbol: str, range_: str = "1y", interval: str | None = None) -> tuple[list[Bar], dict[str, Any]]:
        rng, default_interval = RANGE_INTERVAL.get(range_, (range_, "1d"))
        params: dict[str, Any] = {"interval": interval or default_interval, "includePrePost": "false", "events": "div,splits"}
        if rng == "3y":
            now = int(time.time())
            params.update(period1=now - 3 * 365 * 86400, period2=now)
        else:
            params["range"] = rng
        data = await http.get_json(self.name, f"{Q1}/v8/finance/chart/{symbol}", params=params)
        result = (data.get("chart") or {}).get("result")
        if not result:
            err = (data.get("chart") or {}).get("error") or {}
            raise ProviderError(self.name, err.get("description") or f"no chart data for {symbol}")
        res = result[0]
        ts = res.get("timestamp") or []
        q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
        bars: list[Bar] = []
        for i, t in enumerate(ts):
            c = (q.get("close") or [None])[i] if i < len(q.get("close") or []) else None
            if c is None:
                continue
            bars.append(Bar(t=int(t), o=q["open"][i], h=q["high"][i], l=q["low"][i], c=c, v=(q.get("volume") or [None] * len(ts))[i]))
        meta = res.get("meta") or {}
        events = res.get("events") or {}
        meta["dividends"] = [{"t": int(k), "amount": v.get("amount")} for k, v in (events.get("dividends") or {}).items()]
        meta["splits"] = [{"t": int(k), "ratio": f"{v.get('numerator')}:{v.get('denominator')}"} for k, v in (events.get("splits") or {}).items()]
        return bars, meta

    async def get_daily_closes(self, symbols: list[str], range_: str = "1y") -> dict[str, list[Bar]]:
        """Batched daily closes via the spark endpoint (20 symbols per request)."""
        out: dict[str, list[Bar]] = {}
        for i in range(0, len(symbols), 20):
            chunk = symbols[i:i + 20]
            data = await http.get_json(self.name, f"{Q1}/v8/finance/spark",
                                       params={"symbols": ",".join(chunk), "range": range_, "interval": "1d"})
            for sym, v in (data or {}).items():
                ts, cl = v.get("timestamp") or [], v.get("close") or []
                out[sym] = [Bar(t=int(t), c=c) for t, c in zip(ts, cl) if c is not None]
        return out

    async def get_sparks(self, symbols: list[str], range_: str = "1d", interval: str = "15m") -> dict[str, list[float]]:
        out: dict[str, list[float]] = {}
        for i in range(0, len(symbols), 20):
            chunk = symbols[i:i + 20]
            data = await http.get_json(self.name, f"{Q1}/v8/finance/spark",
                                       params={"symbols": ",".join(chunk), "range": range_, "interval": interval})
            for sym, v in (data or {}).items():
                closes = [c for c in (v.get("close") or []) if c is not None]
                out[sym] = [round(c, 6) for c in closes]
        return out

    # ---- fundamentals / profile -------------------------------------------------
    async def get_summary(self, symbol: str, modules: list[str]) -> dict[str, Any]:
        data = await self._crumbed(f"{Q1}/v10/finance/quoteSummary/{symbol}", {"modules": ",".join(modules)})
        result = (data.get("quoteSummary") or {}).get("result")
        if not result:
            raise ProviderError(self.name, f"no summary for {symbol}")
        return result[0]

    async def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        s = await self.get_summary(symbol, ["financialData", "defaultKeyStatistics", "summaryDetail", "calendarEvents"])
        fd, ks, sd = s.get("financialData", {}), s.get("defaultKeyStatistics", {}), s.get("summaryDetail", {})
        pick = lambda d, k: _raw(d.get(k))  # noqa: E731
        return {
            "total_revenue": pick(fd, "totalRevenue"), "ebitda": pick(fd, "ebitda"), "free_cash_flow": pick(fd, "freeCashflow"),
            "operating_cash_flow": pick(fd, "operatingCashflow"), "total_cash": pick(fd, "totalCash"), "total_debt": pick(fd, "totalDebt"),
            "gross_margin": pick(fd, "grossMargins"), "operating_margin": pick(fd, "operatingMargins"), "net_margin": pick(fd, "profitMargins"),
            "roe": pick(fd, "returnOnEquity"), "roa": pick(fd, "returnOnAssets"), "current_ratio": pick(fd, "currentRatio"),
            "quick_ratio": pick(fd, "quickRatio"), "debt_to_equity": (pick(fd, "debtToEquity") or 0) / 100 if pick(fd, "debtToEquity") is not None else None,
            "revenue_growth": pick(fd, "revenueGrowth"), "earnings_growth": pick(fd, "earningsGrowth"),
            "enterprise_value": pick(ks, "enterpriseValue"), "ev_to_ebitda": pick(ks, "enterpriseToEbitda"), "ev_to_revenue": pick(ks, "enterpriseToRevenue"),
            "forward_pe": pick(ks, "forwardPE") or pick(sd, "forwardPE"), "trailing_pe": pick(sd, "trailingPE"), "peg": pick(ks, "pegRatio"),
            "price_to_book": pick(ks, "priceToBook"), "price_to_sales": pick(sd, "priceToSalesTrailing12Months"),
            "shares_outstanding": pick(ks, "sharesOutstanding"), "beta": pick(sd, "beta") or pick(ks, "beta"),
            "dividend_yield": pick(sd, "dividendYield"), "payout_ratio": pick(sd, "payoutRatio"), "trailing_eps": pick(ks, "trailingEps"),
            "forward_eps": pick(ks, "forwardEps"), "short_percent_float": pick(ks, "shortPercentOfFloat"),
            "held_insiders": pick(ks, "heldPercentInsiders"), "held_institutions": pick(ks, "heldPercentInstitutions"),
            "earnings_dates": [_raw(x) for x in ((s.get("calendarEvents") or {}).get("earnings") or {}).get("earningsDate", [])],
            "ex_dividend_date": _raw((s.get("calendarEvents") or {}).get("exDividendDate")),
        }

    async def get_company_profile(self, symbol: str) -> dict[str, Any]:
        s = await self.get_summary(symbol, ["assetProfile", "summaryProfile"])
        p = s.get("assetProfile") or s.get("summaryProfile") or {}
        return {
            "description": p.get("longBusinessSummary"), "sector": p.get("sectorDisp") or p.get("sector"),
            "industry": p.get("industryDisp") or p.get("industry"), "website": p.get("website"), "ir_website": p.get("irWebsite"),
            "employees": p.get("fullTimeEmployees"), "city": p.get("city"), "state": p.get("state"), "country": p.get("country"),
            "phone": p.get("phone"),
            "officers": [{"name": o.get("name"), "title": o.get("title"), "age": o.get("age")} for o in (p.get("companyOfficers") or [])[:8]],
        }

    async def get_fund_profile(self, symbol: str) -> dict[str, Any]:
        s = await self.get_summary(symbol, ["topHoldings", "fundProfile", "summaryDetail", "defaultKeyStatistics"])
        th, fp, sd, ks = s.get("topHoldings", {}), s.get("fundProfile", {}), s.get("summaryDetail", {}), s.get("defaultKeyStatistics", {})
        fees = fp.get("feesExpensesInvestment") or {}
        sectors = []
        for entry in th.get("sectorWeightings") or []:
            for k, v in entry.items():
                sectors.append({"sector": k.replace("_", " ").title(), "weight": _raw(v)})
        return {
            "family": fp.get("family"), "category": fp.get("categoryName"), "legal_type": fp.get("legalType"),
            "expense_ratio": _raw(fees.get("annualReportExpenseRatio")) or _raw(ks.get("annualReportExpenseRatio")),
            "turnover": _raw(fees.get("annualHoldingsTurnover")),
            "total_assets": _raw(sd.get("totalAssets")) or _raw(ks.get("totalAssets")), "nav": _raw(sd.get("navPrice")),
            "yield": _raw(sd.get("yield")) or _raw(ks.get("yield")), "ytd_return": _raw(ks.get("ytdReturn")),
            "three_year_return": _raw(ks.get("threeYearAverageReturn")), "five_year_return": _raw(ks.get("fiveYearAverageReturn")),
            "holdings": [{"symbol": h.get("symbol"), "name": h.get("holdingName"), "weight": _raw(h.get("holdingPercent"))} for h in th.get("holdings") or []],
            "sector_weights": sorted(sectors, key=lambda x: -(x["weight"] or 0)),
            "asset_allocation": {"stocks": _raw(th.get("stockPosition")), "bonds": _raw(th.get("bondPosition")), "cash": _raw(th.get("cashPosition")), "other": _raw(th.get("otherPosition"))},
        }

    # ---- search / news ----------------------------------------------------------
    async def search(self, q: str, quotes: int = 10, news: int = 0) -> dict[str, Any]:
        data = await http.get_json(self.name, f"{Q2}/v1/finance/search",
                                   params={"q": q, "quotesCount": quotes, "newsCount": news, "enableFuzzyQuery": "false"})
        return data

    async def news_for(self, q: str, count: int = 12) -> list[NewsItem]:
        data = await self.search(q, quotes=0, news=count)
        items: list[NewsItem] = []
        now = time.time()
        for n in data.get("news") or []:
            thumb = None
            res = ((n.get("thumbnail") or {}).get("resolutions") or [])
            if res:
                thumb = sorted(res, key=lambda r: r.get("width", 0))[0].get("url")
            items.append(NewsItem(
                id=f"yh:{n.get('uuid')}", title=n.get("title", ""), url=n.get("link", ""), publisher=n.get("publisher", "Unknown"),
                published_at=n.get("providerPublishTime"), retrieved_at=now, tickers=n.get("relatedTickers") or [],
                thumbnail=thumb, source_feed="yahoo-search",
            ))
        return items

    async def futures_contract(self, symbol: str) -> Quote | None:
        try:
            return await self._quote_from_chart(symbol)
        except ProviderError:
            return None
