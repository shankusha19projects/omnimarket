"""Bonds & rates, central banks, economic indicators, international macro, real-estate macro."""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from backend.cache import store
from backend.cache.store import Fetched
from backend.config import has_secret, load_config, ttl
from backend.providers import registry
from backend.providers.macro import TENOR_YEARS
from backend.services import market_data as md
from backend.utils.http import ProviderError


# ---- Treasury curve ------------------------------------------------------------------
async def _curve_rows(year: int, real: bool = False, force: bool = False) -> tuple[list[dict], dict]:
    async def fetch() -> Fetched:
        rows = await registry.treasury.curve_year(year, real)
        return Fetched(rows, "treasury", registry.treasury.source_url(year))

    c = await store.cached(f"ust:{'real' if real else 'nom'}:{year}", ttl("economic") if year < date.today().year else 3600, fetch, force=force)
    return c.value, c.provenance()


def _nearest(rows: list[dict], days_back: int) -> dict | None:
    if not rows:
        return None
    target = date.fromordinal(date.fromisoformat(rows[-1]["date"]).toordinal() - days_back).isoformat()
    cands = [r for r in rows if r["date"] <= target]
    return cands[-1] if cands else None


async def bonds(force: bool = False) -> dict[str, Any]:
    yr = date.today().year
    cur, prov = await _curve_rows(yr, force=force)
    try:
        prev, _ = await _curve_rows(yr - 1)
    except ProviderError:
        prev = []
    rows = prev + cur
    if not rows:
        return {"available": False, "reason": "Treasury yield curve unavailable."}
    latest = rows[-1]
    compare = {"1W ago": _nearest(rows, 7), "1M ago": _nearest(rows, 30), "1Y ago": _nearest(rows, 365)}
    y = latest["yields"]
    spread = lambda a, b: round(y[a] - y[b], 3) if a in y and b in y else None  # noqa: E731
    hist = [{"date": r["date"], "10Y": r["yields"].get("10Y"), "2Y": r["yields"].get("2Y"), "3M": r["yields"].get("3M"), "30Y": r["yields"].get("30Y"),
             "2s10s": round(r["yields"]["10Y"] - r["yields"]["2Y"], 3) if "10Y" in r["yields"] and "2Y" in r["yields"] else None,
             "3m10y": round(r["yields"]["10Y"] - r["yields"]["3M"], 3) if "10Y" in r["yields"] and "3M" in r["yields"] else None}
            for r in rows]
    real: dict[str, Any] = {}
    try:
        rr, _ = await _curve_rows(yr, real=True)
        if rr:
            real = rr[-1]
    except ProviderError:
        pass
    extras = await _series_block(load_config("economics.json")["rates_extra"])
    proxies = await md.quotes(["LQD", "HYG", "IEF", "TLT", "TIP", "MUB", "EMB", "^MOVE"], force=force)
    tenors = sorted(y, key=lambda k: TENOR_YEARS.get(k, 99))
    return {
        "available": True, "as_of": latest["date"], "tenors": tenors, "tenor_years": {t: TENOR_YEARS.get(t) for t in tenors},
        "curve": y, "compare": {k: (v["yields"] if v else None) for k, v in compare.items()},
        "compare_dates": {k: (v["date"] if v else None) for k, v in compare.items()},
        "spreads": {"10Y-2Y": spread("10Y", "2Y"), "10Y-3M": spread("10Y", "3M"), "30Y-10Y": spread("30Y", "10Y"), "5Y-2Y": spread("5Y", "2Y")},
        "inverted_2s10s": (spread("10Y", "2Y") or 0) < 0, "history": hist[-520:],
        "real_curve": real, "breakeven_10y": round(y["10Y"] - real["yields"]["10Y"], 3) if real and "10Y" in real.get("yields", {}) and "10Y" in y else None,
        "extras": extras, "proxies": {s: md_brief(s, q) for s, q in proxies.items()},
        "provenance": prov,
        "notes": ["Nominal and real (TIPS) par yield curves from the U.S. Treasury daily release.",
                  "Breakeven = nominal 10Y − real 10Y (market-implied average inflation).",
                  "Credit spreads (ICE BofA OAS) require FRED_API_KEY; ETF prices shown as proxies."],
    }


def md_brief(s: str, q: dict) -> dict:
    return {"symbol": s, "name": q.get("name"), "price": q.get("price"), "change_pct": q.get("change_pct"), "provenance": q.get("provenance")}


# ---- Economic series helpers --------------------------------------------------------------
def _transform(pts: list[tuple[str, float]], how: str, freq: str) -> list[tuple[str, float]]:
    if how == "level" or not pts:
        return pts
    lag = {"M": 12, "Q": 4, "W": 52, "D": 252}.get(freq, 12)
    out = []
    for i in range(len(pts)):
        if how == "yoy" and i >= lag and pts[i - lag][1]:
            out.append((pts[i][0], (pts[i][1] / pts[i - lag][1] - 1) * 100))
        elif how == "mom_pct" and i >= 1 and pts[i - 1][1]:
            out.append((pts[i][0], (pts[i][1] / pts[i - 1][1] - 1) * 100))
        elif how == "diff" and i >= 1:
            out.append((pts[i][0], pts[i][1] - pts[i - 1][1]))
    return out


async def _bls_batch(series: list[str], force: bool = False) -> dict[str, list]:
    key = "bls:" + ",".join(sorted(series))

    async def fetch() -> Fetched:
        return Fetched(await registry.bls.get_many(sorted(series)), "bls", "https://www.bls.gov/developers/")

    c = await store.cached(key, 43200, fetch, force=force)  # BLS keyless quota is small: 12h cache
    return c.value


async def _fred(series_id: str, force: bool = False) -> tuple[list, dict]:
    async def fetch() -> Fetched:
        return Fetched(await registry.fred.get_series(series_id, "2012-01-01"), "fred", registry.fred.url(series_id))

    c = await store.cached(f"fred:{series_id}", ttl("economic"), fetch, force=force)
    return c.value, c.provenance()


async def _series_block(inds: list[dict], force: bool = False) -> list[dict[str, Any]]:
    fred_ok = has_secret("FRED_API_KEY")
    bls_ids = [i["bls"] for i in inds if i.get("bls") and not fred_ok]
    bls_data: dict[str, list] = {}
    bls_err = None
    if bls_ids:
        try:
            bls_data = await _bls_batch(bls_ids, force)
        except ProviderError as exc:
            bls_err = exc.message

    async def one(ind: dict) -> dict[str, Any]:
        base = {"id": ind["id"], "name": ind["name"], "category": ind.get("category"), "unit": ind.get("unit"), "freq": ind.get("freq"), "importance": ind.get("importance")}
        pts, prov, err = None, None, None
        if fred_ok and ind.get("fred"):
            try:
                pts, prov = await _fred(ind["fred"], force)
                prov["source_url"] = registry.fred.url(ind["fred"])
            except ProviderError as exc:
                err = exc.message
        if pts is None and ind.get("bls") and ind["bls"] in bls_data:
            pts = bls_data[ind["bls"]]
            prov = {"provider": "bls", "source_url": registry.bls.url(ind["bls"]), "cache_status": "cache"}
        if pts is None:
            reason = err or bls_err or ("Requires FRED_API_KEY (free) — configure in Settings → Data Providers." if ind.get("fred") and not fred_ok else "No source available")
            return {**base, "available": False, "reason": reason, "fred_series": ind.get("fred")}
        series = [(d, v) for d, v in _transform([tuple(p) for p in pts], ind.get("transform", "level"), ind.get("freq", "M"))]
        if not series:
            return {**base, "available": False, "reason": "series empty after transform"}
        last, prev = series[-1], (series[-2] if len(series) > 1 else None)
        return {**base, "available": True, "latest": round(last[1], 3), "latest_date": last[0], "previous": round(prev[1], 3) if prev else None,
                "change": round(last[1] - prev[1], 3) if prev else None, "series": [{"date": d, "value": round(v, 4)} for d, v in series[-160:]],
                "provenance": prov, "transform": ind.get("transform")}

    return list(await asyncio.gather(*(one(i) for i in inds)))


async def economics(force: bool = False) -> dict[str, Any]:
    cfg = load_config("economics.json")
    us = await _series_block(cfg["us"], force)
    intl = await international(force)
    return {"us": us, "international": intl, "unavailable": [{"name": n, "reason": r} for n, r in cfg["unavailable"]],
            "fred_configured": has_secret("FRED_API_KEY"),
            "note": None if has_secret("FRED_API_KEY") else "Running on keyless BLS data only. Add a free FRED_API_KEY to unlock GDP, PCE, housing, claims, sentiment and more."}


async def international(force: bool = False) -> dict[str, Any]:
    cfg = load_config("economics.json")["international"]
    countries = [c for c, _ in cfg["countries"]]

    async def one(ind: str, label: str) -> dict[str, Any]:
        async def fetch() -> Fetched:
            return Fetched(await registry.worldbank.indicator(countries, ind), "worldbank", f"https://data.worldbank.org/indicator/{ind}")
        try:
            c = await store.cached(f"wb:{ind}", 86400, fetch, force=force)
        except ProviderError as exc:
            return {"id": ind, "name": label, "available": False, "reason": exc.message}
        return {"id": ind, "name": label, "available": True, "data": c.value, "provenance": c.provenance()}

    rows = await asyncio.gather(*(one(i, l) for i, l in cfg["indicators"]))
    return {"countries": cfg["countries"], "indicators": list(rows), "note": "World Bank annual data (latest available year per country; typically 1–2 year lag)."}


async def real_estate(force: bool = False) -> dict[str, Any]:
    from backend.services.asset_classes import reits
    cfg = load_config("economics.json")["real_estate"]
    macro_rows = await _series_block(cfg, force)
    r = await reits(force)
    return {"indicators": macro_rows, "reits": r, "fred_configured": has_secret("FRED_API_KEY")}


# ---- Central banks ----------------------------------------------------------------------
async def central_banks(force: bool = False) -> dict[str, Any]:
    cfg = load_config("central_banks.json")["banks"]
    cb = registry.central_banks
    live_map = {"nyfed_effr": cb.nyfed_effr, "ecb_dfr": cb.ecb_dfr, "boe_bank_rate": cb.boe_bank_rate, "boc_valet": cb.boc_valet}
    today = date.today().isoformat()

    async def one(b: dict) -> dict[str, Any]:
        out = {k: b.get(k) for k in ("id", "name", "short", "country", "currency", "rate_name", "calendar_url", "statements_url", "meeting_note")}
        upcoming = [m for m in b.get("meetings", []) if m >= today]
        out["next_meeting"] = upcoming[0] if upcoming else None
        out["days_to_meeting"] = (date.fromisoformat(upcoming[0]) - date.today()).days if upcoming else None
        src = b.get("live_source")
        if src in live_map:
            async def fetch(fn=live_map[src]) -> Fetched:
                d = await fn()
                return Fetched(d, d.get("provider", src), d.get("source_url"))
            try:
                c = await store.cached(f"cb:{b['id']}", ttl("economic"), fetch, force=force)
                out.update({"rate": c.value["value"], "rate_date": c.value["date"], "history": c.value.get("history", []),
                            "target_low": c.value.get("target_low"), "target_high": c.value.get("target_high"), "provenance": c.provenance()})
                hist = c.value.get("history") or []
                changes = [(hist[i][0], hist[i][1] - hist[i - 1][1]) for i in range(1, len(hist)) if hist[i][1] != hist[i - 1][1]]
                if changes:
                    out["last_change"] = {"date": changes[-1][0], "bp": round(changes[-1][1] * 100)}
                return out
            except ProviderError as exc:
                out["error"] = exc.message
        if b.get("fred_series") and has_secret("FRED_API_KEY"):
            try:
                pts, prov = await _fred(b["fred_series"], force)
                if pts:
                    out.update({"rate": pts[-1][1], "rate_date": pts[-1][0], "history": pts[-200:], "provenance": prov})
                    return out
            except ProviderError as exc:
                out["error"] = exc.message
        out.setdefault("error", "No keyless live source; add FRED_API_KEY or check the official site." if b.get("fred_series") else "No machine-readable free source configured; see official site.")
        return out

    rows = await asyncio.gather(*(one(b) for b in cfg))
    return {"banks": list(rows), "note": "Meeting dates from config/central_banks.json (verified against official calendars). Rates fetched live; never hard-coded."}


async def macro_snapshot() -> dict[str, Any]:
    """Compact macro context for reports and the AI advisor."""
    out: dict[str, Any] = {}
    try:
        b = await bonds()
        if b.get("available"):
            out.update({"us10y": b["curve"].get("10Y"), "us2y": b["curve"].get("2Y"), "us3m": b["curve"].get("3M"),
                        "spread_2s10s": b["spreads"]["10Y-2Y"], "curve_as_of": b["as_of"], "breakeven_10y": b.get("breakeven_10y")})
    except ProviderError:
        pass
    qs = await md.quotes(["^VIX", "DX-Y.NYB", "^GSPC", "GC=F", "CL=F", "BTC-USD"])
    out.update({"vix": qs["^VIX"].get("price"), "dxy": qs["DX-Y.NYB"].get("price"), "spx_change_pct": qs["^GSPC"].get("change_pct"),
                "gold": qs["GC=F"].get("price"), "wti": qs["CL=F"].get("price"), "btc": qs["BTC-USD"].get("price")})
    try:
        cb = await central_banks()
        fed = next((x for x in cb["banks"] if x["id"] == "fed"), None)
        if fed and fed.get("rate") is not None:
            out["fed_funds_effective"] = fed["rate"]
            out["fed_target_range"] = f"{fed.get('target_low')}–{fed.get('target_high')}%" if fed.get("target_low") is not None else None
            out["next_fomc"] = fed.get("next_meeting")
    except ProviderError:
        pass
    return out
