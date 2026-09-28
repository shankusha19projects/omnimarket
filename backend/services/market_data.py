"""Quotes, history and sparklines with caching, provenance and provider fallback."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from backend.cache import store
from backend.cache.store import Fetched
from backend.config import ttl
from backend.models.schemas import Quote
from backend.providers import registry
from backend.utils.http import ProviderError

YAHOO_QUOTE_URL = "https://finance.yahoo.com/quote/{s}"


def delay_label(q: dict[str, Any]) -> str:
    d = (q.get("extra") or {}).get("exchangeDataDelayedBy")
    qt = (q.get("quote_type") or "").upper()
    if qt == "CRYPTOCURRENCY":
        return "24/7 aggregate (near real-time)"
    if d is None:
        return "Delay unknown (provider did not report)"
    return "Real-time / near real-time (provider-reported)" if int(d) == 0 else f"Delayed ~{int(d)} min"


def _quote_payload(sym: str, c: store.Cached) -> dict[str, Any]:
    q = dict(c.value)
    prov = c.provenance()
    prov["delay"] = delay_label(q)
    prov["source_url"] = prov.get("source_url") or YAHOO_QUOTE_URL.format(s=sym)
    q["provenance"] = prov
    return q


async def quotes(symbols: list[str], force: bool = False) -> dict[str, dict[str, Any]]:
    """Bulk quotes keyed by provider symbol. Unavailable symbols map to an explicit error record."""
    symbols = list(dict.fromkeys(s for s in symbols if s))
    if not symbols:
        return {}

    async def fetch_many(missing: list[str]) -> dict[str, Any]:
        got = await registry.yahoo.get_quotes(missing)
        result = {s: q.model_dump() for s, q in got.items()}
        # Keyed fallbacks for anything Yahoo could not supply.
        rest = [s for s in missing if s not in result]
        for prov in registry.QUOTE_CHAIN[1:]:
            if not rest or not prov.configured():
                continue
            try:
                extra = await prov.get_quotes(rest)
            except ProviderError:
                continue
            for s, q in extra.items():
                d = q.model_dump()
                d["extra"] = {**d.get("extra", {}), "provider_override": prov.name}
                result[s] = d
            rest = [s for s in rest if s not in result]
        return result

    got, error = await store.bulk_cached(
        "quote", symbols, ttl("quote"), fetch_many, "yahoo",
        source_url=lambda s: YAHOO_QUOTE_URL.format(s=s), market_time=lambda v: v.get("market_time"), force=force,
    )
    out: dict[str, dict[str, Any]] = {}
    for s in symbols:
        if s in got:
            payload = _quote_payload(s, got[s])
            override = (payload.get("extra") or {}).get("provider_override")
            if override:
                payload["provenance"]["provider"] = override
            out[s] = payload
        else:
            out[s] = {"symbol": s, "price": None, "unavailable": True,
                      "provenance": {"provider": "yahoo", "cache_status": "unavailable", "error": error or "no data returned"}}
    return out


async def quote(symbol: str, force: bool = False) -> dict[str, Any]:
    return (await quotes([symbol], force=force))[symbol]


def _history_ttl(range_: str) -> int:
    return ttl("history_intraday") if range_ in ("1d", "5d") else ttl("history_daily")


async def history(symbol: str, range_: str = "1y", interval: str | None = None, force: bool = False) -> dict[str, Any]:
    key = f"hist:{symbol}:{range_}:{interval or ''}"

    async def fetch() -> Fetched:
        bars, meta = await registry.yahoo.get_history(symbol, range_, interval)
        return Fetched({"bars": [b.model_dump() for b in bars], "meta": {k: meta.get(k) for k in (
            "currency", "exchangeName", "instrumentType", "regularMarketPrice", "chartPreviousClose", "previousClose",
            "exchangeTimezoneName", "dataGranularity", "range", "longName", "shortName", "dividends", "splits",
            "fiftyTwoWeekHigh", "fiftyTwoWeekLow")}},
            "yahoo", f"https://finance.yahoo.com/quote/{symbol}/chart", meta.get("regularMarketTime"))

    c = await store.cached(key, _history_ttl(range_), fetch, force=force)
    return {**c.value, "symbol": symbol, "range": range_, "provenance": c.provenance()}


async def sparks(symbols: list[str], range_: str = "1d", interval: str = "15m", force: bool = False) -> dict[str, list[float]]:
    symbols = list(dict.fromkeys(symbols))

    async def fetch_many(missing: list[str]) -> dict[str, Any]:
        return await registry.yahoo.get_sparks(missing, range_, interval)

    got, _ = await store.bulk_cached(f"spark:{range_}", symbols, ttl("history_intraday"), fetch_many, "yahoo", force=force)
    return {s: got[s].value for s in symbols if s in got}


async def daily_closes(symbols: list[str], range_: str = "1y", force: bool = False) -> dict[str, list[dict]]:
    """Daily closes for many symbols: batched spark requests, falling back to per-symbol history."""
    symbols = list(dict.fromkeys(symbols))

    async def fetch_many(missing: list[str]) -> dict[str, Any]:
        got = await registry.yahoo.get_daily_closes(missing, range_)
        return {s: [b.model_dump(exclude_none=True) for b in bars] for s, bars in got.items() if bars}

    got, _ = await store.bulk_cached(f"closes:{range_}", symbols, ttl("history_daily"), fetch_many, "yahoo", force=force)
    out = {s: got[s].value for s in symbols if s in got}
    missing = [s for s in symbols if s not in out]
    if missing:
        out.update(await _daily_closes_slow(missing, range_))
    return out


async def _daily_closes_slow(symbols: list[str], range_: str) -> dict[str, list[dict]]:
    sem = asyncio.Semaphore(6)

    async def one(s: str) -> tuple[str, list[dict]]:
        async with sem:
            try:
                h = await history(s, range_)
                return s, h["bars"]
            except ProviderError:
                return s, []

    results = await asyncio.gather(*(one(s) for s in symbols))
    return {s: b for s, b in results}


def perf_from_bars(bars: list[dict]) -> dict[str, float | None]:
    """1W/1M/3M/YTD/1Y performance from daily bars."""
    if not bars:
        return {}
    closes = [b["c"] for b in bars]
    times = [b["t"] for b in bars]
    last = closes[-1]

    def back(days: int) -> float | None:
        target = times[-1] - days * 86400
        for i in range(len(times) - 1, -1, -1):
            if times[i] <= target:
                return (last / closes[i] - 1) * 100 if closes[i] else None
        return None

    year = time.gmtime(times[-1]).tm_year
    ytd_base = next((closes[i - 1] for i in range(1, len(times)) if time.gmtime(times[i]).tm_year == year and time.gmtime(times[i - 1]).tm_year < year), None)
    return {"perf_1w": back(7), "perf_1m": back(30), "perf_3m": back(91), "perf_6m": back(182),
            "perf_ytd": (last / ytd_base - 1) * 100 if ytd_base else None, "perf_1y": back(365)}


def quote_obj(d: dict[str, Any]) -> Quote:
    return Quote(**{k: v for k, v in d.items() if k in Quote.model_fields})
