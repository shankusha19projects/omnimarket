"""Market overview: ticker strip, global indices, heatmap, breadth, volatility, sectors, themes."""
from __future__ import annotations

import math
from typing import Any

from backend.analytics import technicals
from backend.config import load_config
from backend.services import market_data as md
from backend.services import universe


def _brief(sym: str, q: dict[str, Any], asset=None) -> dict[str, Any]:
    a = asset or universe.resolve(sym)
    return {
        "symbol": sym, "id": a.id, "name": a.name if a.name != sym else (q.get("name") or sym), "asset_class": a.asset_class,
        "group": a.group, "price": q.get("price"), "change": q.get("change"), "change_pct": q.get("change_pct"),
        "day_high": q.get("day_high"), "day_low": q.get("day_low"), "year_high": q.get("year_high"), "year_low": q.get("year_low"),
        "volume": q.get("volume"), "market_time": q.get("market_time"), "market_state": q.get("market_state"),
        "currency": q.get("currency") or a.currency, "unit": a.unit, "unavailable": q.get("unavailable", False),
        "provenance": q.get("provenance"),
    }


async def ticker_strip(force: bool = False) -> dict[str, Any]:
    syms = load_config("universe.json")["ticker_strip"]
    qs = await md.quotes(syms, force=force)
    try:
        sp = await md.sparks(syms, force=force)
    except Exception:
        sp = {}
    return {"items": [{**_brief(s, qs[s]), "spark": sp.get(s, [])} for s in syms]}


async def indices(force: bool = False) -> dict[str, Any]:
    idx = universe.by_class("index")
    qs = await md.quotes([a.yahoo for a in idx], force=force)
    try:
        sp = await md.sparks([a.yahoo for a in idx], force=force)
    except Exception:
        sp = {}
    rows = [{**_brief(a.yahoo, qs[a.yahoo], a), "region": a.group, "country": a.country, "spark": sp.get(a.yahoo, [])} for a in idx]
    return {"rows": rows}


async def heatmap(period: str = "1d", group_by: str = "sector", force: bool = False) -> dict[str, Any]:
    """Treemap data: tiles sized by market cap, colored by period performance."""
    stocks = universe.us_stocks()
    syms = [a.yahoo for a in stocks]
    qs = await md.quotes(syms, force=force)
    perf: dict[str, float | None] = {}
    if period != "1d":
        hist = await md.daily_closes(syms, "1y")
        key = {"5d": "perf_1w", "1m": "perf_1m", "ytd": "perf_ytd", "1y": "perf_1y"}.get(period, "perf_1m")
        for s, bars in hist.items():
            perf[s] = md.perf_from_bars(bars).get(key)
    groups: dict[str, dict[str, list]] = {}
    for a in stocks:
        q = qs[a.yahoo]
        cap = q.get("market_cap")
        if not cap:
            continue
        val = q.get("change_pct") if period == "1d" else perf.get(a.yahoo)
        g1 = a.sector if group_by in ("sector", "industry") else ("Mega cap (>$200B)" if cap > 2e11 else "Large cap ($10–200B)" if cap > 1e10 else "Mid cap")
        g2 = a.industry if group_by == "industry" else None
        tile = {"name": a.yahoo, "label": a.name, "value": cap, "perf": val, "price": q.get("price"), "industry": a.industry}
        groups.setdefault(g1, {}).setdefault(g2 or "_", []).append(tile)
    tree = []
    for g1, subs in groups.items():
        if group_by == "industry":
            children = [{"name": g2, "children": tiles} for g2, tiles in subs.items()]
        else:
            children = [t for tiles in subs.values() for t in tiles]
        tree.append({"name": g1, "children": children})
    provs = [q.get("provenance") for q in qs.values() if q.get("provenance")]
    return {"period": period, "group_by": group_by, "tree": tree,
            "provenance": {"provider": "yahoo", "note": f"{len(stocks)} tracked US large caps; performance {'from quotes' if period == '1d' else 'from daily closes'}",
                           "retrieved_at": max((p.get("retrieved_at") or 0) for p in provs) if provs else None}}


async def breadth(force: bool = False) -> dict[str, Any]:
    stocks = universe.us_stocks()
    syms = [a.yahoo for a in stocks]
    qs = await md.quotes(syms, force=force)
    hist = await md.daily_closes(syms, "1y")
    adv = dec = unch = a20 = a50 = a200 = nh = nl = n20 = n50 = n200 = 0
    for s in syms:
        q = qs[s]
        p, ch = q.get("price"), q.get("change_pct")
        if ch is not None:
            adv += ch > 0.02
            dec += ch < -0.02
            unch += -0.02 <= ch <= 0.02
        closes = [b["c"] for b in hist.get(s, [])]
        if p is None or len(closes) < 20:
            continue
        s20 = sum(closes[-20:]) / 20
        n20 += 1
        a20 += p > s20
        if len(closes) >= 50:
            n50 += 1
            a50 += p > sum(closes[-50:]) / 50
        if len(closes) >= 200:
            n200 += 1
            a200 += p > sum(closes[-200:]) / 200
        hi, lo = max(closes[-252:]), min(closes[-252:])
        nh += (q.get("day_high") or p) >= hi * 0.999
        nl += (q.get("day_low") or p) <= lo * 1.001
    pct = lambda a, n: round(a / n * 100, 1) if n else None  # noqa: E731
    return {"universe": f"{len(syms)} tracked US large caps", "advancers": adv, "decliners": dec, "unchanged": unch,
            "above_20dma_pct": pct(a20, n20), "above_50dma_pct": pct(a50, n50), "above_200dma_pct": pct(a200, n200),
            "new_highs_52w": nh, "new_lows_52w": nl,
            "method": "Computed locally from quotes and 1-year daily closes. 52-week high/low within 0.1% of the trailing 252-session extreme."}


async def volatility(force: bool = False) -> dict[str, Any]:
    qs = await md.quotes(["^VIX", "^MOVE", "^GSPC", "^NDX", "GC=F", "CL=F", "BTC-USD", "EURUSD=X"], force=force)
    hist = await md.daily_closes(["^GSPC", "^VIX", "^NDX", "GC=F", "CL=F", "BTC-USD", "EURUSD=X"], "1y")
    vix_closes = [b["c"] for b in hist.get("^VIX", [])]
    vix = qs["^VIX"].get("price")
    pctile = round(sum(1 for v in vix_closes if v <= vix) / len(vix_closes) * 100) if vix and vix_closes else None
    realized = {}
    for s, label in (("^GSPC", "S&P 500"), ("^NDX", "Nasdaq 100"), ("GC=F", "Gold"), ("CL=F", "WTI Crude"), ("BTC-USD", "Bitcoin"), ("EURUSD=X", "EUR/USD")):
        closes = [b["c"] for b in hist.get(s, [])]
        realized[s] = {"label": label, "rv20": technicals.realized_vol(closes, 20, 365 if s == "BTC-USD" else 252),
                       "rv60": technicals.realized_vol(closes, 60, 365 if s == "BTC-USD" else 252),
                       "rv252": technicals.realized_vol(closes, 252, 365 if s == "BTC-USD" else 252)}
    spx_rv20 = realized["^GSPC"]["rv20"]
    return {"vix": _brief("^VIX", qs["^VIX"]), "move": _brief("^MOVE", qs["^MOVE"]), "vix_1y_percentile": pctile,
            "vix_history": [{"t": b["t"], "c": b["c"]} for b in hist.get("^VIX", [])],
            "variance_risk_premium": round(vix - spx_rv20, 2) if vix and spx_rv20 else None, "realized": realized,
            "method": "Realized vol = annualized stdev of daily log returns (252 trading days; 365 for crypto). VRP proxy = VIX − S&P 500 20d realized."}


async def sectors(force: bool = False) -> dict[str, Any]:
    u = load_config("universe.json")
    etfs = [e for _, e in u["sectors"]]
    qs = await md.quotes(etfs, force=force)
    hist = await md.daily_closes(etfs, "1y")
    stocks = universe.us_stocks()
    sq = await md.quotes([a.yahoo for a in stocks], force=force)
    rows = []
    for name, etf in u["sectors"]:
        members = [a for a in stocks if a.sector == name]
        mq = [(a, sq[a.yahoo]) for a in members if sq[a.yahoo].get("change_pct") is not None]
        mq.sort(key=lambda x: x[1]["change_pct"], reverse=True)
        pes = [q.get("extra", {}).get("trailingPE") for _, q in mq if q.get("extra", {}).get("trailingPE")]
        fpes = [q.get("extra", {}).get("forwardPE") for _, q in mq if q.get("extra", {}).get("forwardPE")]
        cap_w = sum(q.get("market_cap") or 0 for _, q in mq)
        eg = None
        if pes and fpes:
            # Implied forward EPS growth from cap-weighted trailing vs forward P/E (price cancels out).
            tw = sum((q.get("market_cap") or 0) / q["extra"]["trailingPE"] for _, q in mq if q.get("extra", {}).get("trailingPE") and q.get("extra", {}).get("forwardPE"))
            fw = sum((q.get("market_cap") or 0) / q["extra"]["forwardPE"] for _, q in mq if q.get("extra", {}).get("trailingPE") and q.get("extra", {}).get("forwardPE"))
            eg = (fw / tw - 1) * 100 if tw else None
        rows.append({
            "sector": name, "etf": etf, **_brief(etf, qs[etf]), **md.perf_from_bars(hist.get(etf, [])),
            "median_pe": sorted(pes)[len(pes) // 2] if pes else None, "median_forward_pe": sorted(fpes)[len(fpes) // 2] if fpes else None,
            "implied_eps_growth": eg, "members": len(members), "tracked_cap": cap_w,
            "breadth_up": sum(1 for _, q in mq if q["change_pct"] > 0), "breadth_total": len(mq),
            "leaders": [{"symbol": a.yahoo, "name": a.name, "change_pct": q["change_pct"]} for a, q in mq[:3]],
            "laggards": [{"symbol": a.yahoo, "name": a.name, "change_pct": q["change_pct"]} for a, q in mq[-3:][::-1]],
        })
    return {"rows": rows, "method": "Sector ETFs (SPDR) for performance; valuation/breadth from tracked large-cap constituents. Implied EPS growth = cap-weighted trailing ÷ forward earnings yield ratio − 1."}


async def themes(force: bool = False) -> dict[str, Any]:
    th = load_config("themes.json")["themes"]
    syms = sorted({s for t in th for s in t["symbols"]} | {t["etf"] for t in th})
    qs = await md.quotes(syms, force=force)
    rows = []
    for t in th:
        members = [{"symbol": s, "name": qs[s].get("name") or s, "change_pct": qs[s].get("change_pct"), "price": qs[s].get("price"),
                    "market_cap": qs[s].get("market_cap")} for s in t["symbols"]]
        chs = [m["change_pct"] for m in members if m["change_pct"] is not None]
        rows.append({**{k: t[k] for k in ("id", "name", "etf")}, "basket_change_pct": sum(chs) / len(chs) if chs else None,
                     "etf_change_pct": qs[t["etf"]].get("change_pct"), "members": members,
                     "coverage": f"{len(chs)}/{len(members)} quotes available"})
    rows.sort(key=lambda r: -(r["basket_change_pct"] if r["basket_change_pct"] is not None else -math.inf))
    return {"rows": rows, "method": "Equal-weighted average of daily % change across basket members (config/themes.json)."}


async def overview(force: bool = False) -> dict[str, Any]:
    idx = await indices(force)
    majors = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX", "^TNX", "DX-Y.NYB", "GC=F", "CL=F", "BTC-USD"]
    qs = await md.quotes(majors, force=force)
    sp = await md.sparks(majors)
    return {"cards": [{**_brief(s, qs[s]), "spark": sp.get(s, [])} for s in majors], "indices": idx["rows"]}
