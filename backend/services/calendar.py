"""Earnings center and economic calendar."""
from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta
from typing import Any

from backend.cache import store
from backend.cache.store import Fetched
from backend.config import load_config, ttl
from backend.providers import registry
from backend.services import market_data as md
from backend.utils.http import ProviderError

IMPORTANT = [("cpi", 3), ("consumer price", 3), ("nonfarm", 3), ("payroll", 3), ("fomc", 3), ("fed interest rate", 3), ("interest rate decision", 3),
             ("gdp", 3), ("unemployment rate", 3), ("pce", 3), ("retail sales", 2), ("pmi", 2), ("ism", 2), ("jobless claims", 2), ("ppi", 2),
             ("housing starts", 2), ("building permits", 2), ("home sales", 2), ("consumer confidence", 2), ("sentiment", 2), ("jolts", 2),
             ("durable goods", 2), ("industrial production", 2), ("auction", 1), ("trade balance", 1)]
MAJOR = {"United States", "Euro Zone", "Eurozone", "United Kingdom", "Japan", "China", "Germany", "Canada", "India", "Australia"}


def _importance(event: str, country: str | None) -> int:
    e = (event or "").lower()
    base = next((w for k, w in IMPORTANT if k in e), 1)
    return base if (country or "") in MAJOR else max(1, base - 1)


def _days(which: str) -> list[date]:
    today = date.today()
    if which == "today":
        return [today]
    if which == "tomorrow":
        return [today + timedelta(days=1)]
    if which == "next_week":
        start = today + timedelta(days=7 - today.weekday())
        return [start + timedelta(days=i) for i in range(5)]
    start = today - timedelta(days=today.weekday())
    return [start + timedelta(days=i) for i in range(5)]  # this_week


async def _earnings_day(d: date, force: bool) -> tuple[list, dict | None, str | None]:
    async def fetch() -> Fetched:
        return Fetched(await registry.nasdaq.earnings(d), "nasdaq", f"https://www.nasdaq.com/market-activity/earnings?date={d.isoformat()}")
    try:
        c = await store.cached(f"earn:{d.isoformat()}", ttl("calendar"), fetch, force=force)
        return c.value, c.provenance(), None
    except ProviderError as exc:
        return [], None, exc.message


async def earnings(which: str = "this_week", min_cap: float = 0, force: bool = False) -> dict[str, Any]:
    days = _days(which)
    res = await asyncio.gather(*(_earnings_day(d, force) for d in days))
    rows = [r for day_rows, _, _ in res for r in day_rows]
    errors = [e for _, _, e in res if e]
    rows = [r for r in rows if (r.get("market_cap") or 0) >= min_cap]
    rows.sort(key=lambda r: (r["date"], -(r.get("market_cap") or 0)))
    # Share-price reaction for already-reported large caps (today and earlier).
    reported = [r["symbol"] for r in rows if r["date"] <= date.today().isoformat() and (r.get("market_cap") or 0) > 2e9][:60]
    if reported:
        qs = await md.quotes(reported)
        for r in rows:
            if r["symbol"] in qs and qs[r["symbol"]].get("change_pct") is not None:
                r["price_reaction_pct"] = qs[r["symbol"]]["change_pct"]
    provs = [p for _, p, _ in res if p]
    return {"which": which, "days": [d.isoformat() for d in days], "rows": rows, "errors": errors,
            "provenance": provs[0] if provs else None, "note": "Consensus EPS from Nasdaq's public calendar. Actual/surprise fill in after companies report."}


async def economic(which: str = "this_week", min_importance: int = 1, force: bool = False) -> dict[str, Any]:
    days = _days(which)

    async def one(d: date) -> tuple[list, str | None]:
        async def fetch() -> Fetched:
            return Fetched(await registry.nasdaq.economic(d), "nasdaq", "https://www.nasdaq.com/market-activity/economic-calendar")
        try:
            c = await store.cached(f"econcal:{d.isoformat()}", ttl("calendar"), fetch, force=force)
            return c.value, None
        except ProviderError as exc:
            return [], exc.message

    res = await asyncio.gather(*(one(d) for d in days))
    rows = []
    for day_rows, _ in res:
        for r in day_rows:
            r["importance"] = _importance(r.get("event") or "", r.get("country"))
            rows.append(r)
    # Central bank meetings from verified config.
    for b in load_config("central_banks.json")["banks"]:
        for m in b.get("meetings", []):
            if days[0].isoformat() <= m <= days[-1].isoformat():
                rows.append({"date": m, "time_gmt": None, "country": b["country"], "event": f"{b['name']} policy decision", "actual": None,
                             "forecast": None, "previous": None, "importance": 3, "source": b["calendar_url"]})
    rows = [r for r in rows if r["importance"] >= min_importance]
    rows.sort(key=lambda r: (r["date"], r.get("time_gmt") or "99:99"))
    return {"which": which, "days": [d.isoformat() for d in days], "rows": rows, "errors": [e for _, e in res if e],
            "provenance": {"provider": "nasdaq", "source_url": "https://www.nasdaq.com/market-activity/economic-calendar", "retrieved_at": time.time()},
            "note": "Times are GMT as published. Importance is a transparent keyword heuristic (3 = high) — see backend/services/calendar.py."}
