"""Watchlists, portfolio, saved screens and the screener universe (SQLite-backed)."""
from __future__ import annotations

import json
import math
import time
from typing import Any

from backend import db
from backend.analytics import screener, technicals
from backend.models.schemas import PositionIn, ScreenRequest
from backend.services import market_data as md
from backend.services import universe

DEFAULT_WATCHLISTS = {
    "Core": ["^GSPC", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "BTC-USD", "GC=F"],
    "AI & Semis": ["NVDA", "AMD", "AVGO", "TSM", "ASML", "MU", "SMH"],
    "Energy": ["XOM", "CVX", "COP", "CL=F", "NG=F", "XLE"],
    "Rare Earths": ["MP", "LYSDY", "UUUU", "ALB", "REMX", "LIT"],
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Dividend": ["KO", "PEP", "PG", "JNJ", "O", "SCHD"],
    "Bonds & Rates": ["^TNX", "^IRX", "TLT", "IEF", "LQD", "HYG"],
}


def seed_defaults() -> None:
    if db.query("SELECT COUNT(*) AS n FROM watchlists")[0]["n"]:
        return
    for pos, (name, syms) in enumerate(DEFAULT_WATCHLISTS.items()):
        wid = db.execute("INSERT INTO watchlists (name, position, created_at) VALUES (?, ?, ?)", (name, pos, time.time()))
        for i, s in enumerate(syms):
            db.execute("INSERT OR IGNORE INTO watchlist_items (watchlist_id, symbol, added_at, position) VALUES (?,?,?,?)", (wid, s, time.time(), i))


# ---- watchlists ---------------------------------------------------------------------------
def list_watchlists() -> list[dict[str, Any]]:
    lists = db.query("SELECT * FROM watchlists ORDER BY position, id")
    for w in lists:
        w["symbols"] = [r["symbol"] for r in db.query("SELECT symbol FROM watchlist_items WHERE watchlist_id = ? ORDER BY position, added_at", (w["id"],))]
    return lists


async def watchlist_quotes(wid: int) -> dict[str, Any]:
    w = db.query("SELECT * FROM watchlists WHERE id = ?", (wid,))
    if not w:
        raise KeyError("watchlist not found")
    syms = [r["symbol"] for r in db.query("SELECT symbol FROM watchlist_items WHERE watchlist_id = ? ORDER BY position, added_at", (wid,))]
    qs = await md.quotes(syms)
    try:
        sp = await md.sparks(syms)
    except Exception:
        sp = {}
    rows = []
    for s in syms:
        q = qs[s]
        a = universe.resolve(s)
        rows.append({"symbol": s, "name": a.name if a.name != a.symbol else (q.get("name") or s), "asset_class": a.asset_class, "price": q.get("price"),
                     "change": q.get("change"), "change_pct": q.get("change_pct"), "market_state": q.get("market_state"), "spark": sp.get(s, []),
                     "unavailable": q.get("unavailable", False), "provenance": q.get("provenance")})
    return {**w[0], "rows": rows}


def create_watchlist(name: str) -> dict[str, Any]:
    pos = db.query("SELECT COALESCE(MAX(position), 0) + 1 AS p FROM watchlists")[0]["p"]
    wid = db.execute("INSERT INTO watchlists (name, position, created_at) VALUES (?, ?, ?)", (name.strip(), pos, time.time()))
    return {"id": wid, "name": name.strip()}


def rename_watchlist(wid: int, name: str) -> None:
    db.execute("UPDATE watchlists SET name = ? WHERE id = ?", (name.strip(), wid))


def delete_watchlist(wid: int) -> None:
    db.execute("DELETE FROM watchlist_items WHERE watchlist_id = ?", (wid,))
    db.execute("DELETE FROM watchlists WHERE id = ?", (wid,))


def add_item(wid: int, symbol: str) -> None:
    pos = db.query("SELECT COALESCE(MAX(position), 0) + 1 AS p FROM watchlist_items WHERE watchlist_id = ?", (wid,))[0]["p"]
    db.execute("INSERT OR IGNORE INTO watchlist_items (watchlist_id, symbol, added_at, position) VALUES (?,?,?,?)", (wid, symbol.strip().upper() if "=" not in symbol else symbol.strip(), time.time(), pos))


def remove_item(wid: int, symbol: str) -> None:
    db.execute("DELETE FROM watchlist_items WHERE watchlist_id = ? AND symbol = ?", (wid, symbol))


def reorder(wid: int, symbols: list[str]) -> None:
    for i, s in enumerate(symbols):
        db.execute("UPDATE watchlist_items SET position = ? WHERE watchlist_id = ? AND symbol = ?", (i, wid, s))


# ---- portfolio ------------------------------------------------------------------------------
def add_position(p: PositionIn) -> int:
    return db.execute("INSERT INTO portfolio_positions (symbol, quantity, purchase_price, purchase_date, notes, created_at) VALUES (?,?,?,?,?,?)",
                      (p.symbol.strip().upper() if "=" not in p.symbol else p.symbol.strip(), p.quantity, p.purchase_price, p.purchase_date, p.notes, time.time()))


def update_position(pid: int, p: PositionIn) -> None:
    db.execute("UPDATE portfolio_positions SET symbol=?, quantity=?, purchase_price=?, purchase_date=?, notes=? WHERE id=?",
               (p.symbol.strip().upper(), p.quantity, p.purchase_price, p.purchase_date, p.notes, pid))


def delete_position(pid: int) -> None:
    db.execute("DELETE FROM portfolio_positions WHERE id = ?", (pid,))


async def portfolio(force: bool = False) -> dict[str, Any]:
    pos = db.query("SELECT * FROM portfolio_positions ORDER BY id")
    if not pos:
        return {"positions": [], "totals": None, "note": "Add positions to begin tracking. This is a research tracker — it never executes trades."}
    syms = sorted({p["symbol"] for p in pos})
    qs = await md.quotes(syms, force=force)
    rows, total_mv, total_cost, day_pl = [], 0.0, 0.0, 0.0
    for p in pos:
        q = qs[p["symbol"]]
        a = universe.resolve(p["symbol"])
        price = q.get("price")
        mv = price * p["quantity"] if price is not None else None
        cost = p["purchase_price"] * p["quantity"]
        if mv is not None:
            total_mv += mv
            day_pl += (q.get("change") or 0) * p["quantity"]
        total_cost += cost
        rows.append({**p, "name": a.name if a.name != a.symbol else (q.get("name") or p["symbol"]), "asset_class": a.asset_class,
                     "sector": a.sector or {"crypto": "Crypto", "commodity": "Commodities", "etf": "ETF / Fund", "fx": "Currency"}.get(a.asset_class, "Other"),
                     "country": a.country or ("Global" if a.asset_class in ("crypto", "commodity") else "US"), "price": price, "change_pct": q.get("change_pct"),
                     "market_value": mv, "cost_basis": cost, "unrealized_pl": (mv - cost) if mv is not None else None,
                     "unrealized_pct": ((mv / cost - 1) * 100) if mv is not None and cost else None, "provenance": q.get("provenance")})
    for r in rows:
        r["weight"] = (r["market_value"] / total_mv * 100) if r["market_value"] and total_mv else None

    def expo(key: str) -> list[dict[str, Any]]:
        agg: dict[str, float] = {}
        for r in rows:
            if r["market_value"]:
                agg[r[key]] = agg.get(r[key], 0) + r["market_value"]
        return sorted(({"name": k, "value": v, "weight": v / total_mv * 100} for k, v in agg.items()), key=lambda x: -x["value"])

    weights = [r["weight"] / 100 for r in rows if r.get("weight")]
    hhi = sum(w * w for w in weights)
    return {"positions": rows,
            "totals": {"market_value": total_mv, "cost_basis": total_cost, "unrealized_pl": total_mv - total_cost,
                       "unrealized_pct": (total_mv / total_cost - 1) * 100 if total_cost else None, "day_pl": day_pl, "positions": len(rows)},
            "exposure": {"sector": expo("sector"), "country": expo("country"), "asset_class": expo("asset_class")},
            "concentration": {"hhi": round(hhi, 4), "effective_positions": round(1 / hhi, 1) if hhi else None,
                              "largest_weight": max(weights) * 100 if weights else None,
                              "method": "Herfindahl-Hirschman index of position weights; effective N = 1/HHI."},
            "note": "Research tracker only. No orders are ever placed."}


# ---- screener ---------------------------------------------------------------------------------
async def screener_universe(which: str = "all", force: bool = False) -> list[dict[str, Any]]:
    if which == "reits":
        assets = [a for a in universe.all_assets() if a.group == "REIT"]
    elif which == "critical_minerals":
        assets = [a for a in universe.all_assets() if a.group == "Critical Minerals"]
    elif which == "international":
        assets = [a for a in universe.all_assets() if a.group == "International"]
    else:
        assets = [a for a in universe.all_assets() if a.asset_class == "equity"]
    syms = [a.yahoo for a in assets]
    qs = await md.quotes(syms, force=force)
    hist = await md.daily_closes(syms, "1y")
    rows = []
    for a in assets:
        q, ex = qs[a.yahoo], (qs[a.yahoo].get("extra") or {})
        bars = hist.get(a.yahoo, [])
        closes = [b["c"] for b in bars]
        r = technicals.rsi(closes) if len(closes) > 15 else None
        rsi_v = float(r[-1]) if r is not None and not math.isnan(r[-1]) else None
        price = q.get("price")
        s50, s200 = ex.get("fiftyDayAverage"), ex.get("twoHundredDayAverage")
        perf = md.perf_from_bars(bars)
        row = {"symbol": a.yahoo, "name": q.get("name") or a.name, "sector": a.sector, "industry": a.industry, "country": a.country or "US",
               "group": a.group, "price": price, "change_pct": q.get("change_pct"), "market_cap": q.get("market_cap"), "volume": q.get("volume"),
               "avg_volume": q.get("avg_volume"), "pe": ex.get("trailingPE"), "forward_pe": ex.get("forwardPE"), "pb": ex.get("priceToBook"),
               "dividend_yield": (ex.get("trailingAnnualDividendYield") or 0) * 100 if ex.get("trailingAnnualDividendYield") is not None else None,
               "rsi14": rsi_v, "pct_vs_sma50": (price / s50 - 1) * 100 if price and s50 else None,
               "pct_vs_sma200": (price / s200 - 1) * 100 if price and s200 else None,
               "year_high_dist": (price / q["year_high"] - 1) * 100 if price and q.get("year_high") else None,
               "perf_1m": perf.get("perf_1m"), "perf_ytd": perf.get("perf_ytd"), "perf_1y": perf.get("perf_1y")}
        # Fundamentals from cached Yahoo key statistics when previously loaded (cheap; no extra calls here).
        from backend.cache import store
        fc = store.peek(f"yfund:{a.yahoo}")
        if fc:
            f = fc.value
            pct = lambda v: v * 100 if v is not None else None  # noqa: E731
            row.update({"peg": f.get("peg"), "ps": f.get("price_to_sales"), "ev_ebitda": f.get("ev_to_ebitda"), "revenue_growth": pct(f.get("revenue_growth")),
                        "eps_growth": pct(f.get("earnings_growth")), "roe": pct(f.get("roe")), "gross_margin": pct(f.get("gross_margin")),
                        "operating_margin": pct(f.get("operating_margin")), "net_margin": pct(f.get("net_margin")), "debt_to_equity": f.get("debt_to_equity"),
                        "beta": f.get("beta")})
        rows.append(row)
    return rows


async def enrich_fundamentals(symbols: list[str]) -> int:
    """Load Yahoo key statistics for screener rows (rate limited, cached 12h)."""
    import asyncio
    from backend.services.assets import _ysummary
    from backend.cache import store
    from backend.config import ttl
    sem = asyncio.Semaphore(4)
    done = 0

    async def one(s: str) -> None:
        nonlocal done
        async with sem:
            try:
                await store.cached(f"yfund:{s}", ttl("fundamentals"), lambda: _ysummary(s))
                done += 1
            except Exception:
                pass

    await asyncio.gather(*(one(s) for s in symbols))
    return done


async def run_screen(req: ScreenRequest) -> dict[str, Any]:
    rows = await screener_universe(req.universe)
    out = screener.apply(rows, req.filters, req.sort, req.desc, req.limit)
    have_f = sum(1 for r in rows if r.get("roe") is not None)
    return {"rows": out, "total": len(rows), "matched": len(out), "fields": {**screener.NUMERIC_FIELDS, **screener.TEXT_FIELDS},
            "fundamentals_coverage": f"{have_f}/{len(rows)}",
            "note": "Growth/margin/ROE/EV fields populate after 'Load fundamentals' (Yahoo key statistics, cached 12h). ROIC is available per-company on the detail page (SEC-computed)."}


def save_screen(name: str, req: ScreenRequest) -> None:
    db.execute("INSERT INTO saved_screens (name, payload, created_at) VALUES (?,?,?) ON CONFLICT(name) DO UPDATE SET payload = excluded.payload",
               (name, req.model_dump_json(), time.time()))


def list_screens() -> list[dict[str, Any]]:
    return [{"id": r["id"], "name": r["name"], "request": json.loads(r["payload"])} for r in db.query("SELECT * FROM saved_screens ORDER BY name")]


def delete_screen(sid: int) -> None:
    db.execute("DELETE FROM saved_screens WHERE id = ?", (sid,))
