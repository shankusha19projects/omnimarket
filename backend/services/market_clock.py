"""Global market session clock (timezone- and holiday-aware per config/markets.json)."""
from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from backend.config import load_config


def _t(s: str) -> dtime:
    h, m = s.split(":")
    return dtime(int(h), int(m))


def _is_trading_day(ex: dict[str, Any], d: datetime) -> bool:
    return d.weekday() < 5 and d.date().isoformat() not in set(ex.get("holidays", []))


def _session_bounds(ex: dict[str, Any], d: datetime) -> tuple[datetime, datetime]:
    tz = d.tzinfo
    close_s = ex.get("early_close", {}).get(d.date().isoformat(), ex["close"])
    return (datetime.combine(d.date(), _t(ex["open"]), tz), datetime.combine(d.date(), _t(close_s), tz))


def exchange_status(ex: dict[str, Any], now_utc: datetime | None = None) -> dict[str, Any]:
    tz = ZoneInfo(ex["tz"])
    now = (now_utc or datetime.now(ZoneInfo("UTC"))).astimezone(tz)
    status, next_event, next_label = "closed", None, None
    if _is_trading_day(ex, now):
        o, c = _session_bounds(ex, now)
        lunch = ex.get("lunch")
        pre = datetime.combine(now.date(), _t(ex["pre"]), tz) if ex.get("pre") else None
        post = datetime.combine(now.date(), _t(ex["post"]), tz) if ex.get("post") else None
        if o <= now < c:
            if lunch:
                ls, le = (datetime.combine(now.date(), _t(x), tz) for x in lunch)
                if ls <= now < le:
                    status, next_event, next_label = "lunch", le, "reopens"
                else:
                    status, next_event, next_label = "open", (ls if now < ls else c), ("lunch break" if now < ls else "closes")
            else:
                status, next_event, next_label = "open", c, "closes"
        elif pre and pre <= now < o:
            status, next_event, next_label = "pre-market", o, "opens"
        elif post and c <= now < post:
            status, next_event, next_label = "after-hours", None, None
    elif now.date().isoformat() in set(ex.get("holidays", [])):
        status = "holiday"
    if next_event is None:
        d = now
        for _ in range(10):
            if d.date() > now.date() or (d.date() == now.date() and now < _session_bounds(ex, d)[0]):
                if _is_trading_day(ex, d):
                    next_event, next_label = _session_bounds(ex, d)[0], "opens"
                    break
            d = (d + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "id": ex["id"], "city": ex["city"], "tz": ex["tz"], "local_time": now.strftime("%H:%M"), "status": status,
        "next_event": next_label, "next_event_at": next_event.isoformat() if next_event else None,
        "seconds_to_next": int((next_event - now).total_seconds()) if next_event else None,
        "hours": f"{ex['open']}–{ex['close']}", "holiday_calendar": bool(ex.get("holidays")), "calendar_url": ex.get("calendar_url"),
    }


def all_sessions() -> list[dict[str, Any]]:
    return [exchange_status(ex) for ex in load_config("markets.json")["exchanges"]]


def us_status() -> str:
    ex = next(e for e in load_config("markets.json")["exchanges"] if e["id"] == "NYSE")
    return exchange_status(ex)["status"]
