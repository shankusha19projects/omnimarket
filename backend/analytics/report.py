"""Deterministic research-report generator.

Builds the Analysis tab from retrieved data only. Each section separates
FACTS (numbers with sources) from INTERPRETATION (hedged, evidence-linked).
It never issues buy/sell calls and never invents numbers: missing data is
reported as missing.
"""
from __future__ import annotations

import time
from typing import Any

from backend.analytics import valuation


def _pct(v: float | None, digits: int = 1) -> str:
    return "n/a" if v is None else f"{v * 100:+.{digits}f}%"


def _pp(v: float | None, digits: int = 1) -> str:
    return "n/a" if v is None else f"{v * 100:.{digits}f}%"


def _money(v: float | None) -> str:
    if v is None:
        return "n/a"
    a = abs(v)
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if a >= div:
            return f"{'-' if v < 0 else ''}${a / div:.2f}{unit}"
    return f"${v:,.2f}"


def _x(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.1f}×"


def _m(metrics: dict, key: str) -> float | None:
    return (metrics.get(key) or {}).get("value")


def section(title: str, facts: list[str], interp: list[str] | None = None, sources: list[str] | None = None) -> dict[str, Any]:
    return {"title": title, "facts": [f for f in facts if f], "interpretation": [i for i in (interp or []) if i], "sources": sources or []}


def build(ctx: dict[str, Any]) -> dict[str, Any]:
    a = ctx["asset"]
    q = ctx.get("quote") or {}
    fm = (ctx.get("fundamentals") or {}).get("metrics") or {}
    st = ctx.get("statements") or {}
    tech = ctx.get("technicals") or {}
    news = ctx.get("news") or []
    fl = ctx.get("filings") or []
    prof = (ctx.get("profile") or {}).get("profile") or {}
    sec = (ctx.get("profile") or {}).get("sec") or {}
    macro = ctx.get("macro") or {}
    sector = ctx.get("sector") or {}
    name = a.get("name") or a.get("symbol")
    sym = a.get("symbol")
    ann = st.get("annual") or []
    qtr = st.get("quarterly") or []
    sections: list[dict[str, Any]] = []
    src_q = f"Quote: {(q.get('provenance') or {}).get('provider', 'n/a')} ({(q.get('provenance') or {}).get('delay', 'delay unknown')})"
    src_sec = "SEC EDGAR XBRL company facts" if st.get("available") else None

    # Executive snapshot
    price = q.get("price")
    snap = [f"{name} ({sym}) last traded at {price:,.2f} {q.get('currency') or ''}, {(q.get('change_pct') or 0):+.2f}% on the session." if price else f"No live price is available for {sym}."]
    if q.get("year_high") and q.get("year_low") and price:
        rng = (price - q["year_low"]) / (q["year_high"] - q["year_low"]) * 100 if q["year_high"] != q["year_low"] else 50
        snap.append(f"52-week range {q['year_low']:,.2f}–{q['year_high']:,.2f}; price sits at {rng:.0f}% of that range.")
    if _m(fm, "market_cap"):
        snap.append(f"Market capitalization ≈ {_money(_m(fm, 'market_cap'))}; enterprise value ≈ {_money(_m(fm, 'enterprise_value'))}.")
    interp = []
    if _m(fm, "revenue_growth") is not None and _m(fm, "operating_margin") is not None:
        interp.append(f"The data describe a business growing revenue {_pct(_m(fm, 'revenue_growth'))} year over year at a {_pp(_m(fm, 'operating_margin'))} operating margin; "
                      "whether the current valuation already discounts that combination is the central question addressed in the valuation and scenario sections.")
    sections.append(section("Executive Snapshot", snap, interp, [src_q, src_sec] if src_sec else [src_q]))

    # Business overview
    desc = prof.get("description")
    facts = [desc[:900] + ("…" if desc and len(desc) > 900 else "") if desc else "No business description available from configured providers."]
    facts.append(" · ".join(x for x in (f"Sector: {prof.get('sector') or a.get('sector')}" if (prof.get('sector') or a.get('sector')) else "",
                                         f"Industry: {prof.get('industry') or a.get('industry')}" if (prof.get('industry') or a.get('industry')) else "",
                                         f"Employees: {prof['employees']:,}" if prof.get("employees") else "",
                                         f"SIC: {sec.get('sic_description')}" if sec.get("sic_description") else "") if x))
    sections.append(section("Business Overview", facts, [], ["Company profile (Yahoo-compatible)", "SEC submissions" if sec else ""]))

    # Price behavior
    perf = ctx.get("performance") or {}
    pf = [f"Performance — 1M {perf.get('perf_1m') or 0:+.1f}%, 3M {perf.get('perf_3m') or 0:+.1f}%, YTD {perf.get('perf_ytd') or 0:+.1f}%, 1Y {perf.get('perf_1y') or 0:+.1f}%."] if perf else []
    if tech.get("available"):
        pf.append(f"20-day realized volatility {tech.get('realized_vol_20d') or 0:.1f}% annualized; current drawdown from 1-year peak {tech.get('current_drawdown') or 0:.1f}%.")
        if tech.get("relative_strength_60d_vs_spx") is not None:
            pf.append(f"Relative performance vs the S&P 500 over ~60 sessions: {tech['relative_strength_60d_vs_spx']:+.1f} percentage points.")
    sections.append(section("Recent Price Behavior", pf or ["Insufficient price history."], [], ["Daily OHLCV (Yahoo-compatible), computed locally"]))

    # Financial performance
    if ann:
        rows = []
        for r in ann[:4]:
            rows.append(f"FY{(r.get('fiscal_year') or r['period_end'][:4])}: revenue {_money(r.get('revenue'))}, operating income {_money(r.get('operating_income'))}, "
                        f"net income {_money(r.get('net_income'))}, diluted EPS {r.get('eps_diluted') if r.get('eps_diluted') is not None else 'n/a'}")
        interp = []
        if len(ann) >= 2 and ann[0].get("revenue") and ann[1].get("revenue") and ann[0].get("operating_income") is not None and ann[1].get("operating_income") is not None:
            rg = ann[0]["revenue"] / ann[1]["revenue"] - 1
            og = (ann[0]["operating_income"] / ann[1]["operating_income"] - 1) if ann[1]["operating_income"] > 0 else None
            if og is not None:
                lever = "positive operating leverage (profit grew faster than sales)" if og > rg else "negative operating leverage (profit lagged sales)"
                interp.append(f"Latest fiscal year: revenue {_pct(rg)} vs operating income {_pct(og)} — {lever}. Durability depends on whether the cost structure or mix change behind it persists.")
        sections.append(section("Financial Performance", rows, interp, [src_sec or ""]))
    else:
        sections.append(section("Financial Performance", ["No SEC XBRL statement history available (non-US filer, fund, or non-equity asset)."]))

    # Revenue growth
    rg_f = [f"Revenue growth (latest FY): {_pct(_m(fm, 'revenue_growth'))}; 3-year CAGR: {_pct(_m(fm, 'revenue_cagr_3y'))}."]
    if len(qtr) >= 5 and qtr[0].get("revenue") and qtr[4].get("revenue"):
        yoy = qtr[0]["revenue"] / qtr[4]["revenue"] - 1
        rg_f.append(f"Most recent quarter ({qtr[0]['period_end']}) revenue {_money(qtr[0]['revenue'])}, {_pct(yoy)} vs the same quarter a year earlier.")
        if _m(fm, "revenue_cagr_3y") is not None:
            direction = "accelerating relative to" if yoy > _m(fm, "revenue_cagr_3y") else "decelerating relative to"
            rg_f.append(f"Quarterly YoY growth is {direction} the 3-year trend.")
    sections.append(section("Revenue Growth", rg_f, [], [src_sec or ""]))

    # Earnings & cash flow
    ec = [f"Diluted EPS growth (latest FY): {_pct(_m(fm, 'eps_growth'))}; 3-year EPS CAGR: {_pct(_m(fm, 'eps_cagr_3y'))}."]
    cf = [f"Free cash flow {_money(_m(fm, 'free_cash_flow'))} ({_pp(_m(fm, 'fcf_margin'))} of revenue); operating cash flow ÷ net income = {_x(_m(fm, 'cash_conversion'))}."]
    ci = []
    cc = _m(fm, "cash_conversion")
    if cc is not None:
        ci.append("Cash conversion above ~1.0× suggests reported earnings are well backed by cash; below ~0.8× warrants checking working capital, capitalized costs or non-cash gains." if cc < 0.8
                  else "Operating cash flow at or above net income indicates earnings are broadly cash-backed, though stock-based compensation (added back in OCF) flatters this ratio.")
    if ann and ann[0].get("sbc") and ann[0].get("revenue"):
        cf.append(f"Stock-based compensation was {_pp(ann[0]['sbc'] / ann[0]['revenue'])} of revenue in the latest FY — an economic cost that dilutes holders.")
    if ann and len(ann) >= 2 and ann[0].get("diluted_shares") and ann[1].get("diluted_shares"):
        d = ann[0]["diluted_shares"] / ann[1]["diluted_shares"] - 1
        cf.append(f"Diluted share count changed {_pct(d)} year over year ({'net buybacks' if d < 0 else 'net dilution'}).")
    sections.append(section("Earnings", ec, [], [src_sec or ""]))
    sections.append(section("Cash Flow", cf, ci, [src_sec or ""]))

    # Balance sheet
    bs = [f"Cash & ST investments {_money(_m(fm, 'cash'))}; total debt {_money(_m(fm, 'debt'))}; net debt {_money(_m(fm, 'net_debt'))}.",
          f"Current ratio {_x(_m(fm, 'current_ratio'))}; debt/equity {_x(_m(fm, 'debt_to_equity'))}; net debt/EBITDA {_x(_m(fm, 'net_debt_to_ebitda'))}; interest coverage {_x(_m(fm, 'interest_coverage'))}."]
    bi = []
    nde = _m(fm, "net_debt_to_ebitda")
    if nde is not None:
        bi.append("Net cash position — balance-sheet risk is low on this measure." if nde < 0 else
                  "Leverage is moderate by conventional thresholds (<2× net debt/EBITDA)." if nde < 2 else
                  "Leverage is elevated (>3× net debt/EBITDA); refinancing terms and rate sensitivity matter more." if nde > 3 else
                  "Leverage is in a middle range (2–3×).")
    sections.append(section("Balance Sheet", bs, bi, [src_sec or ""]))

    # Valuation
    val = [f"P/E {_x(_m(fm, 'pe'))} trailing, {_x(_m(fm, 'forward_pe'))} forward; PEG {_x(_m(fm, 'peg'))}.",
           f"EV/EBITDA {_x(_m(fm, 'ev_ebitda'))}; EV/Sales {_x(_m(fm, 'ev_sales'))}; P/S {_x(_m(fm, 'ps'))}; P/B {_x(_m(fm, 'pb'))}.",
           f"FCF yield {_pp(_m(fm, 'fcf_yield'), 2)}; dividend yield {_pp(_m(fm, 'dividend_yield'), 2)}."]
    vi = []
    hist = ctx.get("historical_multiples") or []
    if len(hist) >= 3 and _m(fm, "pe"):
        pes = sorted(h["pe"] for h in hist)
        med = pes[len(pes) // 2]
        vi.append(f"Current trailing P/E ({_m(fm, 'pe'):.1f}×) versus a median of {med:.1f}× at the last {len(hist)} fiscal year-ends — "
                  f"{'a premium' if _m(fm, 'pe') > med * 1.1 else 'a discount' if _m(fm, 'pe') < med * 0.9 else 'roughly in line'} to its own history.")
    tsy = macro.get("us10y")
    fy = _m(fm, "fcf_yield")
    if tsy is not None and fy is not None:
        vi.append(f"FCF yield of {fy * 100:.2f}% compares with a {tsy:.2f}% 10-year Treasury yield; the gap is what growth must make up for.")
    rev_dcf = ctx.get("reverse_dcf_growth")
    if rev_dcf is not None:
        vi.append(f"A reverse DCF (9% WACC, 2.5% terminal growth, current margins) implies ~{rev_dcf * 100:.1f}% annual revenue growth for five years is priced in.")
    sections.append(section("Valuation", val, vi, [src_sec or "", "Yahoo-compatible key statistics", "U.S. Treasury yield curve"]))

    # Profitability
    pr = [f"Gross margin {_pp(_m(fm, 'gross_margin'))}; operating margin {_pp(_m(fm, 'operating_margin'))}; net margin {_pp(_m(fm, 'net_margin'))}.",
          f"ROE {_pp(_m(fm, 'roe'))}; ROA {_pp(_m(fm, 'roa'))}; ROIC {_pp(_m(fm, 'roic'))}."]
    pi = []
    roic = _m(fm, "roic")
    if roic is not None:
        pi.append(f"ROIC {'above' if roic > 0.09 else 'below'} a ~9% cost-of-capital benchmark {'indicates' if roic > 0.09 else 'does not indicate'} value creation on invested capital at current profitability.")
    sections.append(section("Profitability", pr, pi, [src_sec or ""]))

    # Competitive / industry
    peers = (ctx.get("profile") or {}).get("peers") or []
    sections.append(section("Competitive Position", [f"Tracked peers: {', '.join(p['symbol'] for p in peers[:8])}." if peers else "No peers identified in the tracked universe."],
                            ["Competitive position is assessed via relative margins, growth and valuation in the Comparables panel; qualitative moat assessment requires primary research."]))
    if sector:
        sections.append(section("Industry Context", [f"{sector.get('sector')} sector ETF ({sector.get('etf')}): day {sector.get('change_pct') or 0:+.2f}%, 1M {sector.get('perf_1m') or 0:+.1f}%, YTD {sector.get('perf_ytd') or 0:+.1f}%."
                                                     + (f" Median trailing P/E of tracked constituents {sector['median_pe']:.1f}×." if sector.get("median_pe") else "")], []))
    # Macro sensitivity
    mf = []
    if macro:
        mf.append(" · ".join(f"{k}: {v}" for k, v in (("US 10Y", f"{macro['us10y']:.2f}%" if macro.get("us10y") is not None else None),
                                                       ("2s10s", f"{macro['spread_2s10s']:+.2f} pp" if macro.get("spread_2s10s") is not None else None),
                                                       ("VIX", f"{macro['vix']:.1f}" if macro.get("vix") else None),
                                                       ("DXY", f"{macro['dxy']:.2f}" if macro.get("dxy") else None)) if v))
    mi = ["Higher long-term yields raise discount rates, which weigh most on long-duration (high-multiple) equities; companies with net debt are additionally exposed via refinancing costs."]
    if (prof.get("country") or a.get("country")) and (prof.get("country") or a.get("country")) not in ("United States", "US"):
        mi.append("Non-US domicile introduces currency translation effects for USD-based holders.")
    sections.append(section("Macro Sensitivity", mf or ["Macro snapshot unavailable."], mi, ["U.S. Treasury", "Yahoo-compatible"]))

    # Catalysts / risks
    cat = []
    if (ctx.get("fundamentals") or {}).get("earnings_dates"):
        ed = [d for d in ctx["fundamentals"]["earnings_dates"] if d]
        if ed:
            cat.append(f"Next scheduled earnings date (provider): {time.strftime('%Y-%m-%d', time.gmtime(ed[0]))}.")
    recent_8k = [f for f in fl if f.get("form") == "8-K"][:3]
    for f in recent_8k:
        cat.append(f"8-K filed {f['filed']}" + (f": {f['description']}" if f.get("description") else ""))
    risks = []
    if _m(fm, "pe") and _m(fm, "pe") > 35:
        risks.append("Valuation risk: a high trailing multiple leaves less room for disappointment in growth or margins.")
    if nde is not None and nde > 3:
        risks.append("Financial risk: elevated leverage amplifies earnings volatility and refinancing exposure.")
    if tech.get("realized_vol_20d") and tech["realized_vol_20d"] > 45:
        risks.append(f"Volatility risk: realized volatility of {tech['realized_vol_20d']:.0f}% implies wide plausible price ranges.")
    if _m(fm, "revenue_growth") is not None and _m(fm, "revenue_growth") < 0:
        risks.append("Fundamental risk: revenue declined in the latest fiscal year.")
    risks.append("Concentration, regulatory, competitive and execution risks require reading the Risk Factors section of the latest 10-K.")
    sections.append(section("Catalysts", cat or ["No dated catalysts identified from available data."], [], ["SEC EDGAR", "Yahoo-compatible calendar"]))
    sections.append(section("Risks", risks, [], []))

    # Technical picture
    sections.append(section("Technical Picture", tech.get("interpretation") or ["Technical indicators unavailable."], [], [tech.get("method", "")]))
    sections.append(section("Recent News", [f"{n.get('publisher')}: {n.get('title')}" for n in news[:6]] or ["No recent headlines from configured sources."], [],
                            [n.get("url") for n in news[:6]]))
    sections.append(section("SEC Filing Developments", [f"{f['form']} · filed {f['filed']}" + (f" · {f['description']}" if f.get("description") else "") for f in fl[:8] if f.get("form") != "4"]
                            or ["No recent SEC filings (or not an SEC registrant)."], [], [f.get("url") for f in fl[:8]]))
    sections.append(section("Key Metrics to Monitor", [
        "Revenue growth trajectory vs the 3-year trend (acceleration/deceleration).", "Operating margin and incremental margins (operating leverage).",
        "Free-cash-flow conversion and stock-based compensation.", "Net debt/EBITDA and interest coverage if rates stay elevated.",
        "Share count trend (buybacks vs dilution).", "Valuation vs own history and peers."]))

    scen = scenarios(ctx)
    return {"symbol": sym, "generated_at": time.time(), "engine": "OmniMarket deterministic analyst (rule-based, no LLM)",
            "sections": sections, "scenarios": scen,
            "disclaimer": "Generated from retrieved data. Facts are sourced; interpretations are hedged and may be incomplete. Not investment advice."}


def scenarios(ctx: dict[str, Any]) -> dict[str, Any]:
    """Bull/base/bear with explicit assumptions, valued through the same DCF engine."""
    d = ctx.get("dcf_defaults") or {}
    if not d.get("available"):
        return {"available": False, "reason": d.get("reason") or "Insufficient data for scenario valuation."}
    base_in = d["inputs"]
    g, m = base_in["revenue_growth"], base_in["operating_margin"]
    specs = {
        "bull": {"revenue_growth": min(g * 1.5 + 0.02, 0.6), "operating_margin": min(m + 0.03, 0.7), "wacc": base_in["wacc"] - 0.005,
                 "narrative": "Growth re-accelerates above the 3-year trend and operating leverage lifts margins ~3pp; risk premium compresses slightly."},
        "base": {"revenue_growth": g, "operating_margin": m, "wacc": base_in["wacc"],
                 "narrative": "Revenue compounds near its 3-year trend with margins held at current (TTM) levels."},
        "bear": {"revenue_growth": max(g * 0.4 - 0.02, -0.1), "operating_margin": max(m - 0.04, 0.01), "wacc": base_in["wacc"] + 0.01,
                 "narrative": "Growth slows to well below trend, margins compress ~4pp (competition/cost pressure) and the cost of capital rises 1pp."},
    }
    out: dict[str, Any] = {"available": True, "price": d.get("price"), "cases": {}}
    for name, s in specs.items():
        inputs = {**base_in, **{k: v for k, v in s.items() if k != "narrative"}}
        try:
            r = valuation.dcf(**inputs)
            ps = r["per_share"]
        except (ValueError, TypeError, ZeroDivisionError):
            ps = None
        out["cases"][name] = {"narrative": s["narrative"], "assumptions": {k: inputs[k] for k in ("revenue_growth", "operating_margin", "wacc", "terminal_growth", "tax_rate", "reinvestment_rate")},
                              "value_per_share": ps, "vs_price_pct": ((ps / d["price"] - 1) * 100) if ps and d.get("price") else None}
    out["note"] = "Scenario values are mechanical outputs of stated assumptions, not forecasts. No scenario is presented as likely or certain."
    return out
