"""Asset-level services: search, detail, fundamentals, statements, filings, timeline, valuation."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from backend import db
from backend.analytics import fundamentals as fa
from backend.analytics import technicals, valuation
from backend.cache import store
from backend.cache.store import Fetched
from backend.config import load_config, ttl
from backend.models.schemas import DCFRequest
from backend.providers import registry
from backend.services import market_data as md
from backend.services import universe
from backend.utils.http import ProviderError


# ---- search ----------------------------------------------------------------------
async def search(q: str, limit: int = 12) -> dict[str, Any]:
    ql = q.strip().lower()
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for a in universe.all_assets():
        hay = f"{a.symbol} {a.name} {a.sector or ''} {a.industry or ''} {a.group or ''}".lower()
        score = 100 if a.symbol.lower() == ql else 80 if a.symbol.lower().startswith(ql) else 60 if a.name.lower().startswith(ql) else 40 if ql in hay else 0
        if score:
            results.append({"type": a.asset_class, "symbol": a.yahoo, "id": a.id, "name": a.name, "exchange": a.exchange,
                            "detail": " · ".join(x for x in (a.sector, a.industry or a.group) if x), "score": score, "source": "catalog"})
            seen.add(a.yahoo)
    if len(ql) >= 1:
        try:
            c = await store.cached(f"search:{ql}", ttl("search"), lambda: _yahoo_search(q))
            for r in c.value:
                if r["symbol"] not in seen:
                    results.append(r)
                    seen.add(r["symbol"])
        except ProviderError:
            pass
    extra: list[dict[str, Any]] = []
    econ = load_config("economics.json")
    for ind in econ["us"] + econ["real_estate"]:
        if ql in ind["name"].lower() or ql in ind["id"]:
            extra.append({"type": "indicator", "symbol": ind["id"], "name": ind["name"], "detail": ind.get("category", "Real estate"), "source": "economics"})
    for name, etf in load_config("universe.json")["sectors"]:
        if ql in name.lower():
            extra.append({"type": "sector", "symbol": etf, "name": f"{name} sector", "detail": f"Tracked via {etf}", "source": "sectors"})
    for t in load_config("themes.json")["themes"]:
        if ql in t["name"].lower():
            extra.append({"type": "theme", "symbol": t["id"], "name": t["name"], "detail": f"{len(t['symbols'])} constituents", "source": "themes"})
    arts = db.query("SELECT title, url, publisher, published_at FROM news WHERE LOWER(title) LIKE ? ORDER BY published_at DESC LIMIT 5", (f"%{ql}%",)) if len(ql) >= 3 else []
    for r in arts:
        extra.append({"type": "article", "symbol": r["url"], "name": r["title"], "detail": r["publisher"], "source": "news"})
    results.sort(key=lambda r: -r.get("score", 50))
    return {"query": q, "results": results[:limit] + extra[:10]}


async def _yahoo_search(q: str) -> Fetched:
    data = await registry.yahoo.search(q, quotes=10)
    out = []
    type_map = {"EQUITY": "equity", "ETF": "etf", "INDEX": "index", "FUTURE": "commodity", "CURRENCY": "fx", "CRYPTOCURRENCY": "crypto", "MUTUALFUND": "fund"}
    for r in data.get("quotes") or []:
        if not r.get("symbol") or not r.get("isYahooFinance", True):
            continue
        cls = type_map.get(r.get("quoteType", ""), "other")
        out.append({"type": cls, "symbol": r["symbol"], "id": universe.make_id(cls, r["symbol"]), "name": r.get("longname") or r.get("shortname") or r["symbol"],
                    "exchange": r.get("exchDisp"), "detail": " · ".join(x for x in (r.get("sectorDisp") or r.get("sector"), r.get("industryDisp") or r.get("industry"), r.get("typeDisp")) if x),
                    "score": 50, "source": "yahoo"})
    return Fetched(out, "yahoo", "https://finance.yahoo.com/lookup")


# ---- SEC helpers -----------------------------------------------------------------
async def cik_for(symbol: str) -> int | None:
    c = await store.cached("sec:tickers", 86400, lambda: _tickers())
    info = c.value.get(symbol.upper().replace(".", "-")) or c.value.get(symbol.upper())
    return info["cik"] if info else None


async def _tickers() -> Fetched:
    return Fetched(await registry.sec.ticker_map(), "sec", "https://www.sec.gov/files/company_tickers.json")


async def statements(symbol: str, force: bool = False) -> dict[str, Any]:
    cik = await cik_for(symbol)
    if not cik:
        return {"available": False, "reason": f"No SEC registrant found for {symbol}. Statements are sourced from SEC XBRL filings (US filers)."}

    async def fetch() -> Fetched:
        facts = await registry.sec.company_facts(cik)
        return Fetched(registry.sec.build_statements(facts), "sec", f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")

    c = await store.cached(f"statements:{symbol}", ttl("fundamentals"), fetch, force=force)
    return {"available": True, "cik": cik, **c.value, "provenance": c.provenance()}


async def filings(symbol: str, forms: list[str] | None = None, force: bool = False) -> dict[str, Any]:
    cik = await cik_for(symbol)
    if not cik:
        return {"available": False, "filings": [], "reason": f"{symbol} is not an SEC registrant (or ticker not mapped)."}

    async def fetch() -> Fetched:
        fl = await registry.sec.get_filings(symbol, forms, cik=cik, limit=120)
        return Fetched([f.model_dump() for f in fl], "sec", f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}")

    c = await store.cached(f"filings:{symbol}:{','.join(forms or [])}", ttl("filings"), fetch, force=force)
    return {"available": True, "cik": cik, "filings": c.value, "provenance": c.provenance()}


# ---- profile / fundamentals --------------------------------------------------------
async def profile(symbol: str, force: bool = False) -> dict[str, Any]:
    a = universe.resolve(symbol)
    out: dict[str, Any] = {"symbol": symbol, "asset": a.model_dump()}
    if a.asset_class in ("equity",):
        try:
            c = await store.cached(f"profile:{symbol}", ttl("profile"), lambda: _yprofile(symbol), force=force)
            out["profile"] = c.value
            out["profile_provenance"] = c.provenance()
        except ProviderError as exc:
            out["profile_error"] = exc.message
        cik = await cik_for(symbol)
        if cik:
            try:
                c = await store.cached(f"secsub:{cik}", ttl("filings"), lambda: _secsub(cik), force=force)
                out["sec"] = c.value
            except ProviderError as exc:
                out["sec_error"] = exc.message
    elif a.asset_class == "etf":
        try:
            c = await store.cached(f"fund:{symbol}", ttl("profile"), lambda: _yfund(symbol), force=force)
            out["fund"] = c.value
            out["fund_provenance"] = c.provenance()
        except ProviderError as exc:
            out["fund_error"] = exc.message
    # Competitors: same industry (or sector) within the tracked universe.
    if a.sector:
        peers = [x for x in universe.all_assets() if x.asset_class == "equity" and x.yahoo != a.yahoo and
                 ((a.industry and x.industry == a.industry) or x.sector == a.sector)]
        peers.sort(key=lambda x: (x.industry != a.industry, x.group != "US Large Cap"))
        out["peers"] = [{"symbol": p.yahoo, "name": p.name, "industry": p.industry} for p in peers[:8]]
    return out


async def _yprofile(symbol: str) -> Fetched:
    return Fetched(await registry.yahoo.get_company_profile(symbol), "yahoo", f"https://finance.yahoo.com/quote/{symbol}/profile")


async def _yfund(symbol: str) -> Fetched:
    return Fetched(await registry.yahoo.get_fund_profile(symbol), "yahoo", f"https://finance.yahoo.com/quote/{symbol}/holdings")


async def _secsub(cik: int) -> Fetched:
    s = await registry.sec.submissions(cik)
    addr = (s.get("addresses") or {}).get("business") or {}
    return Fetched({
        "cik": cik, "name": s.get("name"), "sic": s.get("sic"), "sic_description": s.get("sicDescription"),
        "exchanges": s.get("exchanges"), "tickers": s.get("tickers"), "state_of_incorporation": s.get("stateOfIncorporation"),
        "fiscal_year_end": s.get("fiscalYearEnd"), "category": s.get("category"), "entity_type": s.get("entityType"),
        "website": s.get("website") or None, "phone": s.get("phone"),
        "headquarters": ", ".join(x for x in (addr.get("street1"), addr.get("city"), addr.get("stateOrCountryDescription")) if x),
        "former_names": [f.get("name") for f in (s.get("formerNames") or [])][:5],
        "first_filing": min((s.get("filings") or {}).get("recent", {}).get("filingDate") or ["?"]),
    }, "sec", f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}")


async def fundamentals(symbol: str, force: bool = False) -> dict[str, Any]:
    q = await md.quote(symbol, force=force)
    st = await statements(symbol, force=force)
    ysum: dict[str, Any] = {}
    yprov = None
    try:
        c = await store.cached(f"yfund:{symbol}", ttl("fundamentals"), lambda: _ysummary(symbol), force=force)
        ysum, yprov = c.value, c.provenance()
    except ProviderError:
        pass
    metrics: dict[str, dict[str, Any]] = {}
    if st.get("available"):
        dps = (q.get("extra") or {}).get("trailingAnnualDividendYield")
        metrics = fa.compute(st, q.get("price"), q.get("market_cap"), (q.get("extra") or {}).get("sharesOutstanding"),
                             dividend_ps=(dps * q["price"]) if dps and q.get("price") else None)
        for m in metrics.values():
            m["source"] = "SEC XBRL (computed)" if m["value"] is not None else None
    ymap = {"forward_pe": ("forward_pe", "Price ÷ forward EPS (consensus)", "multiple"), "peg": ("peg", "Forward P/E ÷ expected EPS growth", "multiple"),
            "beta": ("beta", "5Y monthly beta vs S&P 500", "ratio"), "short_percent_float": ("short_percent_float", "Shares short ÷ float", "pct"),
            "held_institutions": ("held_institutions", "Institutional ownership", "pct"), "held_insiders": ("held_insiders", "Insider ownership", "pct")}
    for key, (ykey, formula, kind) in ymap.items():
        metrics[key] = {"value": ysum.get(ykey), "formula": formula, "kind": kind, "source": "Yahoo-compatible" if ysum.get(ykey) is not None else None}
    fallback = {"pe": "trailing_pe", "ps": "price_to_sales", "pb": "price_to_book", "ev_ebitda": "ev_to_ebitda", "ev_sales": "ev_to_revenue",
                "gross_margin": "gross_margin", "operating_margin": "operating_margin", "net_margin": "net_margin", "roe": "roe", "roa": "roa",
                "current_ratio": "current_ratio", "quick_ratio": "quick_ratio", "debt_to_equity": "debt_to_equity", "revenue_growth": "revenue_growth",
                "enterprise_value": "enterprise_value", "ebitda": "ebitda", "free_cash_flow": "free_cash_flow", "dividend_yield": "dividend_yield"}
    for key, ykey in fallback.items():
        cur = metrics.get(key)
        if (cur is None or cur.get("value") is None) and ysum.get(ykey) is not None:
            val = ysum[ykey] / 100 if key == "dividend_yield" and ysum[ykey] > 1 else ysum[ykey]
            metrics[key] = {"value": val, "formula": (cur or {}).get("formula", key), "kind": (cur or {}).get("kind", "ratio"), "source": "Yahoo-compatible"}
    groups = {
        "Size & cash flow": ["market_cap", "enterprise_value", "revenue", "ebitda", "operating_income", "net_income", "eps", "free_cash_flow", "cash", "debt", "net_debt"],
        "Valuation": ["pe", "forward_pe", "peg", "ps", "pb", "ev_sales", "ev_ebitda", "fcf_yield", "dividend_yield"],
        "Profitability": ["gross_margin", "operating_margin", "net_margin", "fcf_margin", "roa", "roe", "roic", "cash_conversion"],
        "Growth": ["revenue_growth", "eps_growth", "fcf_growth", "revenue_cagr_3y", "eps_cagr_3y", "fcf_cagr_3y"],
        "Balance sheet": ["current_ratio", "quick_ratio", "debt_to_equity", "net_debt_to_ebitda", "interest_coverage"],
        "Market & ownership": ["beta", "short_percent_float", "held_institutions", "held_insiders", "shares_outstanding"],
    }
    return {"symbol": symbol, "groups": groups, "metrics": metrics, "quote_provenance": q.get("provenance"),
            "statements_provenance": st.get("provenance"), "yahoo_provenance": yprov, "sec_available": st.get("available", False),
            "earnings_dates": ysum.get("earnings_dates"), "ex_dividend_date": ysum.get("ex_dividend_date")}


async def _ysummary(symbol: str) -> Fetched:
    return Fetched(await registry.yahoo.get_fundamentals(symbol), "yahoo", f"https://finance.yahoo.com/quote/{symbol}/key-statistics")


# ---- detail / technicals ----------------------------------------------------------
async def detail(symbol: str, force: bool = False) -> dict[str, Any]:
    a = universe.resolve(symbol)
    q = await md.quote(a.yahoo, force=force)
    name = q.get("name") if a.name == a.symbol else a.name
    return {"asset": {**a.model_dump(), "name": name or a.symbol, "symbol": a.yahoo}, "quote": q}


async def technical_snapshot(symbol: str) -> dict[str, Any]:
    h = await md.history(symbol, "1y")
    try:
        bench = await md.history("^GSPC", "1y")
        bc = [b["c"] for b in bench["bars"]]
    except ProviderError:
        bc = None
    return {**technicals.summary(h["bars"], bc), "provenance": h["provenance"]}


async def history_with_indicators(symbol: str, range_: str, interval: str | None, force: bool = False) -> dict[str, Any]:
    h = await md.history(symbol, range_, interval, force=force)
    h["indicators"] = technicals.series(h["bars"]) if len(h["bars"]) >= 20 else {}
    return h


# ---- timeline -----------------------------------------------------------------------
EIGHT_K_ITEMS = {"1.01": "Material agreement", "2.01": "Acquisition/disposition completed", "2.02": "Results of operations (earnings)",
                 "5.02": "Officer/director change", "5.07": "Shareholder vote", "7.01": "Reg FD disclosure", "8.01": "Other events", "1.02": "Agreement terminated"}


async def timeline(symbol: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    fl = await filings(symbol)
    for f in fl.get("filings", [])[:60]:
        if f["form"] in ("4",):
            continue
        kind = "earnings" if f["form"] in ("10-Q", "10-K") else "filing"
        events.append({"date": f["filed"], "type": kind, "title": f"{f['form']} filed" + (f" — {f['description']}" if f.get("description") else ""), "url": f["url"], "source": "SEC EDGAR"})
    try:
        h = await md.history(symbol, "5y")
        for d in (h.get("meta") or {}).get("dividends") or []:
            events.append({"date": datetime.fromtimestamp(d["t"], tz=timezone.utc).date().isoformat(), "type": "dividend", "title": f"Dividend ${d['amount']:.4g}/share", "source": "Yahoo-compatible"})
        for s in (h.get("meta") or {}).get("splits") or []:
            events.append({"date": datetime.fromtimestamp(s["t"], tz=timezone.utc).date().isoformat(), "type": "split", "title": f"Stock split {s['ratio']}", "source": "Yahoo-compatible"})
    except ProviderError:
        pass
    try:
        for n in (await asset_news(symbol))["items"][:15]:
            events.append({"date": datetime.fromtimestamp(n["published_at"] or 0, tz=timezone.utc).date().isoformat(), "type": "news", "title": n["title"], "url": n["url"], "source": n["publisher"]})
    except ProviderError:
        pass
    events.sort(key=lambda e: e["date"], reverse=True)
    return {"symbol": symbol, "events": events[:120]}


async def asset_news(symbol: str, force: bool = False) -> dict[str, Any]:
    a = universe.resolve(symbol)
    term = a.yahoo if a.asset_class in ("equity", "etf") else (a.name if a.name != a.symbol else a.yahoo)

    async def fetch() -> Fetched:
        items = await registry.yahoo.news_for(term, count=20)
        if registry.finnhub.configured() and a.asset_class == "equity":
            try:
                items += await registry.finnhub.get_news(a.yahoo, 20)
            except ProviderError:
                pass
        seen, uniq = set(), []
        for i in sorted(items, key=lambda x: -(x.published_at or 0)):
            if i.url not in seen:
                seen.add(i.url)
                uniq.append(i.model_dump())
        return Fetched(uniq, "yahoo", f"https://finance.yahoo.com/quote/{a.yahoo}/news")

    c = await store.cached(f"anews:{a.yahoo}", ttl("news"), fetch, force=force)
    return {"symbol": a.yahoo, "items": c.value, "provenance": c.provenance()}


# ---- valuation --------------------------------------------------------------------
async def dcf_defaults(symbol: str) -> dict[str, Any]:
    st = await statements(symbol)
    q = await md.quote(symbol)
    if not st.get("available") or not st.get("annual"):
        return {"available": False, "reason": st.get("reason") or "No statement history available for a DCF."}
    ann = st["annual"]
    ttm = st.get("ttm") or {}
    rev = ttm.get("revenue") or ann[0].get("revenue")
    oi = ttm.get("operating_income") or ann[0].get("operating_income")
    fundm = fa.compute(st, q.get("price"), q.get("market_cap"), (q.get("extra") or {}).get("sharesOutstanding"))
    growth = fundm["revenue_cagr_3y"]["value"] or fundm["revenue_growth"]["value"] or 0.05
    tax = fa.safe_div(ann[0].get("income_tax"), ann[0].get("pretax_income"))
    capex = ttm.get("capex") or ann[0].get("capex") or 0
    ocf = ttm.get("operating_cash_flow") or ann[0].get("operating_cash_flow")
    nopat = (oi or 0) * (1 - (tax if tax and 0 < tax < 0.4 else 0.21))
    reinvest = min(max((nopat - ((ocf or 0) - capex)) / nopat, 0.0), 0.8) if nopat > 0 and ocf else 0.25
    shares = fundm["shares_outstanding"]["value"]
    return {
        "available": True, "symbol": symbol, "price": q.get("price"),
        "inputs": {"revenue": rev, "revenue_growth": round(min(max(growth, -0.1), 0.4), 4), "growth_years": 5, "terminal_growth": 0.025,
                   "operating_margin": round(fa.safe_div(oi, rev) or 0.15, 4), "tax_rate": round(tax if tax and 0 < tax < 0.4 else 0.21, 4),
                   "reinvestment_rate": round(reinvest, 4), "wacc": 0.09, "shares": shares, "net_debt": fundm["net_debt"]["value"] or 0},
        "notes": ["Defaults derived from SEC filings: 3Y revenue CAGR (capped −10%…40%), TTM operating margin, last FY effective tax rate, "
                  "reinvestment = (NOPAT − FCF) ÷ NOPAT. WACC defaults to 9% — adjust for the company's risk profile."],
        "provenance": st.get("provenance"),
    }


async def run_dcf(req: DCFRequest) -> dict[str, Any]:
    defaults = await dcf_defaults(req.symbol)
    if not defaults.get("available"):
        return defaults
    base = {**defaults["inputs"], **{k: v for k, v in req.model_dump().items() if k != "symbol" and v is not None}}
    if not base.get("shares") or not base.get("revenue"):
        return {"available": False, "reason": "Shares outstanding or revenue unavailable."}
    try:
        res = valuation.dcf(**base)
    except ValueError as exc:
        return {"available": False, "reason": str(exc)}
    waccs = [round(base["wacc"] + d, 4) for d in (-0.02, -0.01, 0, 0.01, 0.02)]
    gs = [round(base["terminal_growth"] + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    price = defaults.get("price")
    implied = valuation.reverse_dcf(price, base) if price else None
    return {"available": True, "inputs": base, "result": res, "sensitivity": {"wacc": waccs, "terminal_growth": gs, "grid": valuation.sensitivity(base, waccs, gs)},
            "price": price, "upside_pct": ((res["per_share"] / price - 1) * 100) if price and res.get("per_share") else None,
            "reverse_dcf_growth": implied, "disclaimer": "Model output reflects the assumptions entered; it is not a forecast or a price target."}


async def comparables(symbol: str) -> dict[str, Any]:
    prof = await profile(symbol)
    peers = [p["symbol"] for p in prof.get("peers", [])]
    qs = await md.quotes([symbol] + peers)
    rows = []
    for s in peers:
        q, ex = qs[s], qs[s].get("extra") or {}
        rows.append({"symbol": s, "name": q.get("name"), "price": q.get("price"), "market_cap": q.get("market_cap"), "pe": ex.get("trailingPE"),
                     "forward_pe": ex.get("forwardPE"), "pb": ex.get("priceToBook")})
    tq, tex = qs[symbol], qs[symbol].get("extra") or {}
    target = {"eps": tex.get("epsTrailingTwelveMonths"), "book_per_share": tex.get("bookValue")}
    comp = valuation.comparables(target, rows)
    hist = await historical_multiples(symbol)
    return {"symbol": symbol, "target": {"price": tq.get("price"), "pe": tex.get("trailingPE"), "forward_pe": tex.get("forwardPE"), "pb": tex.get("priceToBook"), **target},
            **comp, "historical": hist, "method": "Peer-median multiple × target's own per-share metric. Peers = same industry/sector in the tracked universe."}


async def historical_multiples(symbol: str) -> list[dict[str, Any]]:
    """P/E at each fiscal year end: FY-end close ÷ FY diluted EPS (SEC)."""
    st = await statements(symbol)
    if not st.get("available"):
        return []
    try:
        h = await md.history(symbol, "10y")
    except ProviderError:
        return []
    bars = h["bars"]
    out = []
    for row in st["annual"][:10]:
        eps = row.get("eps_diluted")
        end = datetime.fromisoformat(row["period_end"]).replace(tzinfo=timezone.utc).timestamp()
        px = next((b["c"] for b in reversed(bars) if b["t"] <= end + 86400 * 3), None)
        if px and eps and eps > 0:
            out.append({"period_end": row["period_end"], "price": px, "eps": eps, "pe": px / eps})
    return out[::-1]


# ---- compare --------------------------------------------------------------------------
async def compare(symbols: list[str], range_: str = "1y") -> dict[str, Any]:
    symbols = symbols[:5]
    qs = await md.quotes(symbols)
    hist = await md.daily_closes(symbols, range_)
    series = {}
    rows = []

    async def fund_row(s: str) -> dict[str, Any]:
        a = universe.resolve(s)
        row: dict[str, Any] = {"symbol": s, "name": qs[s].get("name") or a.name, "asset_class": a.asset_class, "price": qs[s].get("price"),
                               "change_pct": qs[s].get("change_pct"), "market_cap": qs[s].get("market_cap")}
        bars = hist.get(s, [])
        row.update(md.perf_from_bars(bars))
        closes = [b["c"] for b in bars]
        row["volatility_1y"] = technicals.realized_vol(closes, 252, 365 if a.asset_class == "crypto" else 252)
        row["max_drawdown_1y"], _ = technicals.max_drawdown(closes)
        r = technicals.rsi(closes) if len(closes) > 20 else None
        row["rsi14"] = float(r[-1]) if r is not None and len(r) else None
        if a.asset_class == "equity":
            try:
                f = await fundamentals(s)
                for k in ("pe", "forward_pe", "ps", "ev_ebitda", "revenue_growth", "eps_growth", "gross_margin", "operating_margin", "net_margin", "roe", "roic", "debt_to_equity", "current_ratio", "fcf_yield"):
                    row[k] = (f["metrics"].get(k) or {}).get("value")
            except ProviderError:
                pass
        return row

    rows = await asyncio.gather(*(fund_row(s) for s in symbols))
    for s in symbols:
        bars = hist.get(s, [])
        if bars:
            base = bars[0]["c"]
            series[s] = [{"t": b["t"], "v": (b["c"] / base - 1) * 100} for b in bars]
    return {"symbols": symbols, "rows": list(rows), "series": series, "range": range_}


async def resolve_symbol_or_404(symbol: str) -> str:
    if not universe.valid_symbol(symbol):
        raise ValueError("invalid symbol")
    return universe.resolve(symbol).yahoo


def now_ts() -> float:
    return time.time()
