"""Earnings and economic calendars (Nasdaq public calendar API; Finnhub when configured)."""
from __future__ import annotations

import html
import re
from datetime import date
from typing import Any

from backend.utils import http

NASDAQ_HEADERS = {"Accept": "application/json, text/plain, */*", "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}


def _money(s: Any) -> float | None:
    if s in (None, "", "N/A", "&nbsp;"):
        return None
    txt = str(s).replace("$", "").replace(",", "").strip()
    neg = txt.startswith("(") and txt.endswith(")")
    txt = txt.strip("()")
    try:
        v = float(txt)
    except ValueError:
        return None
    return -v if neg else v


def _clean(s: Any) -> str | None:
    if s is None:
        return None
    t = html.unescape(str(s)).replace("\xa0", " ").strip()
    t = re.sub(r"<[^>]+>", " ", t)
    return t or None


class NasdaqCalendarProvider:
    name = "nasdaq"
    label = "Nasdaq public calendars"
    homepage = "https://www.nasdaq.com/market-activity/earnings"

    async def earnings(self, day: date) -> list[dict[str, Any]]:
        d = await http.get_json(self.name, "https://api.nasdaq.com/api/calendar/earnings", params={"date": day.isoformat()}, headers=NASDAQ_HEADERS)
        rows = ((d or {}).get("data") or {}).get("rows") or []
        timing = {"time-pre-market": "Before open", "time-after-hours": "After close", "time-not-supplied": "Not supplied"}
        return [{
            "date": day.isoformat(), "symbol": r.get("symbol"), "company": r.get("name"),
            "timing": timing.get(r.get("time"), r.get("time")), "market_cap": _money(r.get("marketCap")),
            "fiscal_quarter": r.get("fiscalQuarterEnding"), "eps_forecast": _money(r.get("epsForecast")),
            "num_estimates": _money(r.get("noOfEsts")), "last_year_eps": _money(r.get("lastYearEPS")),
            "last_year_date": r.get("lastYearRptDt"),
            "eps_actual": _money(r.get("eps")), "surprise_pct": _money(r.get("surprise")),
        } for r in rows]

    async def economic(self, day: date) -> list[dict[str, Any]]:
        d = await http.get_json(self.name, "https://api.nasdaq.com/api/calendar/economicevents", params={"date": day.isoformat()}, headers=NASDAQ_HEADERS)
        rows = ((d or {}).get("data") or {}).get("rows") or []
        return [{
            "date": day.isoformat(), "time_gmt": _clean(r.get("gmt")), "country": _clean(r.get("country")),
            "event": _clean(r.get("eventName")), "actual": _clean(r.get("actual")), "forecast": _clean(r.get("consensus")),
            "previous": _clean(r.get("previous")),
        } for r in rows]
