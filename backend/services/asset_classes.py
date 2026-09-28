"""Crypto, commodities, forex, ETFs, rare earths / critical minerals, REITs."""
from __future__ import annotations

import time
from datetime import date
from typing import Any

from backend.analytics import technicals
from backend.cache import store
from backend.cache.store import Fetched
from backend.config import load_config, ttl
from backend.providers import registry
from backend.services import market_data as md
from backend.services import universe
from backend.services.markets import _brief
from backend.utils.http import ProviderError


async def crypto(force: bool = False) -> dict[str, Any]:
    async def fetch_markets() -> Fetched:
        return Fetched(await registry.coingecko.get_markets(100), "coingecko", "https://www.coingecko.com/")

    async def fetch_global() -> Fetched:
        return Fetched(await registry.coingecko.get_global(), "coingecko", "https://www.coingecko.com/en/global-charts")

    out: dict[str, Any] = {}
    try:
        c = await store.cached("crypto:markets", ttl("crypto"), fetch_markets, force=force)
        out["coins"], out["provenance"] = c.value, c.provenance()
    except ProviderError as exc:
        out["coins"], out["error"] = [], f"CoinGecko unavailable: {exc.message}"
    try:
        g = await store.cached("crypto:global", ttl("crypto"), fetch_global, force=force)
        out["global"] = g.value
    except ProviderError:
        out["global"] = {}
    cats: dict[str, dict[str, float]] = {}
    for c in out["coins"]:
        k = cats.setdefault(c["category"], {"market_cap": 0.0, "weighted": 0.0, "count": 0})
        if c.get("market_cap") and c.get("change_24h") is not None:
            k["market_cap"] += c["market_cap"]
            k["weighted"] += c["market_cap"] * c["change_24h"]
            k["count"] += 1
    out["categories"] = sorted([{"category": n, "market_cap": v["market_cap"], "change_24h": v["weighted"] / v["market_cap"] if v["market_cap"] else None, "count": v["count"]}
                                for n, v in cats.items()], key=lambda x: -x["market_cap"])
    # BTC / ETH realized volatility and YTD from Yahoo-compatible daily closes.
    hist = await md.daily_closes(["BTC-USD", "ETH-USD"], "1y")
    out["majors"] = {s: {**md.perf_from_bars(b), "rv30": technicals.realized_vol([x["c"] for x in b], 30, 365)} for s, b in hist.items()}
    return out


async def commodities(force: bool = False) -> dict[str, Any]:
    u = load_config("universe.json")
    syms = [r[0] for g in u["commodities"].values() for r in g]
    qs = await md.quotes(syms, force=force)
    hist = await md.daily_closes(syms, "1y")
    try:
        sp = await md.sparks(syms, "5d", "1h")
    except ProviderError:
        sp = {}
    groups = {}
    for g, rows in u["commodities"].items():
        groups[g] = [{**_brief(s, qs[s]), "unit": unit, "spark": sp.get(s, []), **md.perf_from_bars(hist.get(s, [])),
                      "rv20": technicals.realized_vol([b["c"] for b in hist.get(s, [])], 20)} for s, _, unit in rows]
    return {"groups": groups, "unavailable": [{"name": n, "reason": r} for n, r in u["commodities_unavailable"]]}


def _contract_symbols(spec: dict[str, Any], n: int = 8) -> list[tuple[str, str]]:
    today = date.today()
    out: list[tuple[str, str]] = []
    y, m = today.year, today.month
    codes = "FGHJKMNQUVXZ"
    while len(out) < n:
        m += 1
        if m > 12:
            m, y = 1, y + 1
        code = codes[m - 1]
        if code in spec["months"]:
            out.append((f"{spec['root']}{code}{str(y)[-2:]}{spec['suffix']}", f"{date(y, m, 1):%b %y}"))
    return out


async def futures_curve(symbol: str, force: bool = False) -> dict[str, Any]:
    spec = load_config("universe.json")["futures_curves"].get(symbol)
    if not spec:
        return {"available": False, "reason": "No futures curve configured for this contract."}
    contracts = _contract_symbols(spec)

    async def fetch() -> Fetched:
        qs = await md.quotes([c for c, _ in contracts], force=True)
        pts = [{"contract": c, "label": lbl, "price": qs[c].get("price")} for c, lbl in contracts if qs[c].get("price")]
        if len(pts) < 2:
            raise ProviderError("yahoo", "individual contract quotes unavailable")
        return Fetched(pts, "yahoo", f"https://finance.yahoo.com/quote/{symbol}/futures")

    try:
        c = await store.cached(f"curve:{symbol}", ttl("history_daily"), fetch, force=force)
    except ProviderError as exc:
        return {"available": False, "reason": exc.message}
    pts = c.value
    shape = "contango (deferred > front)" if pts[-1]["price"] > pts[0]["price"] else "backwardation (front > deferred)"
    return {"available": True, "name": spec["name"], "points": pts, "shape": shape, "provenance": c.provenance()}


async def forex(force: bool = False) -> dict[str, Any]:
    u = load_config("universe.json")
    syms = [r[0] for r in u["forex"]]
    qs = await md.quotes(syms, force=force)
    hist = await md.daily_closes(syms, "1y")
    try:
        sp = await md.sparks(syms, "5d", "1h")
    except ProviderError:
        sp = {}
    rows = []
    for s, name, base, quote in u["forex"]:
        closes = [b["c"] for b in hist.get(s, [])]
        rows.append({**_brief(s, qs[s]), "name": name, "base": base, "quote": quote, "spark": sp.get(s, []), **md.perf_from_bars(hist.get(s, [])),
                     "rv20": technicals.realized_vol(closes, 20), "rv60": technicals.realized_vol(closes, 60)})
    return {"rows": rows, "method": "Spot from Yahoo-compatible FX quotes; realized vol = annualized stdev of daily log returns."}


async def etfs(force: bool = False) -> dict[str, Any]:
    u = load_config("universe.json")
    syms = [r[0] for g in u["etfs"].values() for r in g]
    qs = await md.quotes(syms, force=force)
    groups = {}
    for g, rows in u["etfs"].items():
        groups[g] = [{**_brief(s, qs[s]), "name": n, "aum": qs[s].get("market_cap"), "expense_ratio": (qs[s].get("extra") or {}).get("netExpenseRatio"),
                      "ytd_return": (qs[s].get("extra") or {}).get("ytdReturn"), "yield": (qs[s].get("extra") or {}).get("trailingAnnualDividendYield"),
                      "perf_1y": (qs[s].get("extra") or {}).get("fiftyTwoWeekChangePercent")} for s, n in rows]
    return {"groups": groups}


async def rare_earths(force: bool = False) -> dict[str, Any]:
    re_ = load_config("universe.json")["rare_earths"]
    syms = [c[0] for c in re_["companies"]] + [e[0] for e in re_["etfs"]]
    qs = await md.quotes(syms, force=force)
    hist = await md.daily_closes(syms, "1y")
    companies = []
    for sym, name, country, minerals, segment in re_["companies"]:
        q = qs[sym]
        companies.append({**_brief(sym, q), "name": name, "country": country, "minerals": minerals, "segment": segment,
                          "market_cap": q.get("market_cap"), **md.perf_from_bars(hist.get(sym, []))})
    etf_rows = [{**_brief(s, qs[s]), "name": n, **md.perf_from_bars(hist.get(s, []))} for s, n in re_["etfs"]]
    by_country: dict[str, float] = {}
    by_mineral: dict[str, int] = {}
    for c in companies:
        by_country[c["country"]] = by_country.get(c["country"], 0) + (c.get("market_cap") or 0)
        for m in c["minerals"]:
            by_mineral[m] = by_mineral.get(m, 0) + 1
    return {"companies": companies, "etfs": etf_rows, "minerals": re_["minerals"], "sources": re_["sources"],
            "exposure_by_hq_country": by_country, "coverage_by_mineral": by_mineral,
            "note": "Company-to-mineral mapping is a curated reference list (config/universe.json). Supply-chain concentration notes are qualitative; see linked USGS/IEA datasets for quantified shares."}


async def reits(force: bool = False) -> dict[str, Any]:
    rows_cfg = load_config("universe.json")["reits"]
    syms = [r[0] for r in rows_cfg]
    qs = await md.quotes(syms, force=force)
    hist = await md.daily_closes(syms, "1y")
    rows = []
    for s, name, seg in rows_cfg:
        q, ex = qs[s], qs[s].get("extra") or {}
        rows.append({**_brief(s, q), "name": name, "segment": seg, "market_cap": q.get("market_cap"),
                     "dividend_yield": ex.get("trailingAnnualDividendYield"), "pb": ex.get("priceToBook"), **md.perf_from_bars(hist.get(s, []))})
    segs: dict[str, list[float]] = {}
    for r in rows:
        if r.get("perf_ytd") is not None:
            segs.setdefault(r["segment"], []).append(r["perf_ytd"])
    return {"rows": rows, "segments": [{"segment": k, "avg_ytd": sum(v) / len(v), "n": len(v)} for k, v in sorted(segs.items())],
            "retrieved_at": time.time()}
