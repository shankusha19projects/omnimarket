"""Context assembly for analysis reports, the Research Command Center and the AI advisor.

The LLM never guesses market data: every number it sees comes from this
structured context, tagged with source and retrieval time.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

from backend.analytics import report, valuation
from backend.config import load_config
from backend.services import assets, macro, markets, universe
from backend.services import market_data as md
from backend.utils.http import ProviderError

COMMODITY_WORDS = {"gold": "GC=F", "silver": "SI=F", "copper": "HG=F", "oil": "CL=F", "crude": "CL=F", "wti": "CL=F", "brent": "BZ=F",
                   "natural gas": "NG=F", "nat gas": "NG=F", "platinum": "PL=F", "palladium": "PA=F", "wheat": "ZW=F", "corn": "ZC=F",
                   "soybean": "ZS=F", "coffee": "KC=F", "cocoa": "CC=F", "sugar": "SB=F", "cotton": "CT=F", "uranium": "URA", "lithium": "LIT",
                   "rare earth": "REMX", "bitcoin": "BTC-USD", "btc": "BTC-USD", "ethereum": "ETH-USD", "eth": "ETH-USD", "solana": "SOL-USD",
                   "dollar": "DX-Y.NYB", "dxy": "DX-Y.NYB", "yen": "JPY=X", "euro": "EURUSD=X", "treasur": "^TNX", "bond": "^TNX", "yield": "^TNX",
                   "vix": "^VIX", "s&p": "^GSPC", "sp500": "^GSPC", "nasdaq": "^NDX", "dow": "^DJI", "russell": "^RUT", "nikkei": "^N225", "nifty": "^NSEI"}
STOPWORDS = {"A", "I", "AN", "THE", "AND", "OR", "WHY", "HOW", "WHAT", "IS", "ARE", "DID", "DO", "US", "IN", "ON", "OF", "TO", "FOR", "IT", "ME",
             "TODAY", "MOVE", "ETF", "CEO", "AI", "GDP", "CPI", "FED", "PE", "EPS", "YOY", "Q1", "Q2", "Q3", "Q4", "USD", "VS"}


def _ts(t: float | None) -> str | None:
    return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(t)) if t else None


async def detect_entities(text: str) -> dict[str, Any]:
    """Find tickers / assets / themes mentioned in free text."""
    low = text.lower()
    found: list[str] = []
    for word, sym in COMMODITY_WORDS.items():
        if word in low and sym not in found:
            found.append(sym)
    cat = universe.catalog()
    for tok in re.findall(r"\$?\b[A-Z][A-Z0-9\.\-]{0,6}\b", text):
        t = tok.lstrip("$")
        if t in STOPWORDS:
            continue
        if t in cat and t not in found:
            found.append(t)
    if not found:
        # Try name search for company names ("analyze nvidia").
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z\.&-]{2,}", text) if w.upper() not in STOPWORDS and w.lower() not in {"analyze", "analysis", "happening", "what", "think", "about", "stock", "company", "industry", "sector", "outlook"}]
        for w in words[:3]:
            try:
                r = await assets.search(w, limit=3)
                hit = next((x for x in r["results"] if x.get("type") in ("equity", "etf", "crypto", "index", "commodity") and x.get("source") in ("catalog", "yahoo")), None)
                if hit and hit["symbol"] not in found:
                    found.append(hit["symbol"])
                    break
            except ProviderError:
                continue
    themes = [t for t in load_config("themes.json")["themes"] if t["name"].lower() in low or t["id"].replace("_", " ") in low]
    sectors = [s for s in load_config("universe.json")["sectors"] if s[0].lower() in low]
    return {"symbols": found[:5], "themes": themes[:2], "sectors": sectors[:2]}


async def asset_context(symbol: str, deep: bool = True) -> dict[str, Any]:
    a = universe.resolve(symbol)
    sym = a.yahoo
    tasks: dict[str, Any] = {
        "detail": assets.detail(sym),
        "technicals": assets.technical_snapshot(sym),
        "news": assets.asset_news(sym),
        "macro": macro.macro_snapshot(),
        "history": md.history(sym, "1y"),
    }
    if a.asset_class == "equity" and deep:
        tasks.update(fundamentals=assets.fundamentals(sym), statements=assets.statements(sym), filings=assets.filings(sym),
                     profile=assets.profile(sym), dcf_defaults=assets.dcf_defaults(sym), historical=assets.historical_multiples(sym))
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    ctx: dict[str, Any] = {}
    errors: list[str] = []
    for k, v in zip(tasks.keys(), results):
        if isinstance(v, Exception):
            errors.append(f"{k}: {getattr(v, 'message', str(v))}")
            ctx[k] = None
        else:
            ctx[k] = v
    ctx["errors"] = errors
    return ctx


async def analysis_report(symbol: str) -> dict[str, Any]:
    ctx = await asset_context(symbol)
    detail = ctx.get("detail") or {"asset": universe.resolve(symbol).model_dump(), "quote": {}}
    sector_row = None
    a = universe.resolve(symbol)
    if a.sector:
        try:
            sec = await markets.sectors()
            sector_row = next((r for r in sec["rows"] if r["sector"] == a.sector), None)
        except ProviderError:
            pass
    rdcf = None
    d = ctx.get("dcf_defaults") or {}
    if d.get("available") and d.get("price"):
        try:
            rdcf = valuation.reverse_dcf(d["price"], d["inputs"])
        except (ValueError, ZeroDivisionError, TypeError):
            rdcf = None
    rep = report.build({
        "asset": detail["asset"], "quote": detail["quote"], "fundamentals": ctx.get("fundamentals"), "statements": ctx.get("statements"),
        "technicals": ctx.get("technicals"), "news": (ctx.get("news") or {}).get("items", []), "filings": (ctx.get("filings") or {}).get("filings", []),
        "profile": ctx.get("profile"), "macro": ctx.get("macro"), "sector": sector_row, "dcf_defaults": d, "historical_multiples": ctx.get("historical"),
        "performance": md.perf_from_bars((ctx.get("history") or {}).get("bars", [])), "reverse_dcf_growth": rdcf,
    })
    rep["data_errors"] = ctx["errors"]
    return rep


def compact_for_llm(ctx: dict[str, Any]) -> dict[str, Any]:
    """Reduce an asset context to the facts an LLM needs, with provenance."""
    det = ctx.get("detail") or {}
    q = det.get("quote") or {}
    out: dict[str, Any] = {"asset": {k: (det.get("asset") or {}).get(k) for k in ("symbol", "name", "asset_class", "sector", "industry", "country")}}
    prov = q.get("provenance") or {}
    out["quote"] = {k: q.get(k) for k in ("price", "change", "change_pct", "prev_close", "day_high", "day_low", "year_high", "year_low", "volume", "avg_volume", "market_cap", "currency", "market_state")}
    out["quote"]["source"] = f"{prov.get('provider')} · {prov.get('delay')} · retrieved {_ts(prov.get('retrieved_at'))} · cache {prov.get('cache_status')}"
    out["quote"]["market_time"] = _ts(q.get("market_time"))
    out["performance"] = md.perf_from_bars((ctx.get("history") or {}).get("bars", []))
    t = ctx.get("technicals") or {}
    out["technicals"] = {k: t.get(k) for k in ("rsi14", "sma50", "sma200", "macd", "macd_signal", "realized_vol_20d", "current_drawdown", "relative_strength_60d_vs_spx")} if t.get("available") else None
    f = ctx.get("fundamentals")
    if f:
        out["fundamentals"] = {k: {"value": v.get("value"), "source": v.get("source")} for k, v in f["metrics"].items() if v.get("value") is not None}
    st = ctx.get("statements")
    if st and st.get("available"):
        keep = ("period_end", "fiscal_year", "revenue", "gross_profit", "operating_income", "net_income", "eps_diluted", "operating_cash_flow", "capex", "free_cash_flow", "sbc", "diluted_shares", "cash", "long_term_debt", "equity")
        out["annual_statements"] = [{k: r.get(k) for k in keep if r.get(k) is not None} for r in st["annual"][:5]]
        out["quarterly_statements"] = [{k: r.get(k) for k in keep if r.get(k) is not None} for r in st["quarterly"][:5]]
        out["statements_source"] = f"SEC EDGAR XBRL (CIK {st.get('cik')}), retrieved {_ts((st.get('provenance') or {}).get('retrieved_at'))}"
    fl = ctx.get("filings")
    if fl and fl.get("filings"):
        out["recent_filings"] = [{"form": x["form"], "filed": x["filed"], "description": x.get("description"), "url": x["url"]} for x in fl["filings"][:10] if x["form"] != "4"]
    n = ctx.get("news")
    if n:
        out["news"] = [{"title": x["title"], "publisher": x["publisher"], "published": _ts(x.get("published_at")), "url": x["url"]} for x in n["items"][:10]]
    prof = ctx.get("profile") or {}
    if prof.get("profile"):
        out["profile"] = {k: prof["profile"].get(k) for k in ("sector", "industry", "employees", "country", "website")}
        out["profile"]["description"] = (prof["profile"].get("description") or "")[:1200]
    out["macro"] = ctx.get("macro")
    out["data_gaps"] = ctx.get("errors")
    return out


async def market_context() -> dict[str, Any]:
    """Broad market context for general questions."""
    from backend.services import news as news_svc
    qs = await md.quotes(["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX", "^TNX", "DX-Y.NYB", "GC=F", "CL=F", "HG=F", "BTC-USD", "EURUSD=X", "JPY=X"])
    try:
        mm = await news_svc.market_moving(8)
        headlines = [{"headline": c["headline"], "publishers": c["publishers"][:5], "score": c["score"], "first_seen": _ts(c["first_seen"])} for c in mm["items"]]
    except Exception:
        headlines = []
    return {"snapshot": {s: {"name": q.get("name"), "price": q.get("price"), "change_pct": q.get("change_pct"),
                             "retrieved": _ts((q.get("provenance") or {}).get("retrieved_at"))} for s, q in qs.items()},
            "macro": await macro.macro_snapshot(), "top_developments": headlines}


def to_prompt_json(obj: Any, limit: int = 60000) -> str:
    s = json.dumps(obj, default=str, separators=(",", ":"))
    return s[:limit]
