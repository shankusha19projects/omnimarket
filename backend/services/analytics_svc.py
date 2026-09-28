"""Correlation tool and objective risk dashboard (no opaque composite score)."""
from __future__ import annotations

from typing import Any

from backend.analytics import correlation, technicals
from backend.services import macro
from backend.services import market_data as md

PRESET_PAIRS = [
    ("BTC-USD", "^NDX", "BTC vs Nasdaq 100"), ("GC=F", "DX-Y.NYB", "Gold vs Dollar Index"), ("CL=F", "XLE", "Oil vs Energy stocks"),
    ("^TNX", "XLK", "10Y yield vs Tech"), ("HG=F", "FXI", "Copper vs China equities"), ("^GSPC", "TLT", "Stocks vs long Treasuries"),
]


async def correlations(symbols: list[str], range_: str = "1y", window: int | None = None) -> dict[str, Any]:
    symbols = list(dict.fromkeys(symbols))[:12]
    hist = await md.daily_closes(symbols, range_)
    mat = correlation.correlation_matrix({s: b for s, b in hist.items() if b}, window)
    return {**mat, "range": range_, "missing": [s for s, b in hist.items() if not b]}


async def pair(a: str, b: str, range_: str = "2y", window: int = 60) -> dict[str, Any]:
    hist = await md.daily_closes([a, b], range_)
    roll = correlation.rolling_correlation(hist[a], hist[b], window)
    full = correlation.correlation_matrix({a: hist[a], b: hist[b]})
    return {"a": a, "b": b, "window": window, "rolling": roll, "full_period": full["matrix"][0][1] if full.get("matrix") else None,
            "observations": full.get("observations")}


async def presets() -> dict[str, Any]:
    out = []
    for a, b, label in PRESET_PAIRS:
        p = await pair(a, b, "1y", 60)
        out.append({"a": a, "b": b, "label": label, "corr_1y": p["full_period"], "latest_60d": p["rolling"][-1]["corr"] if p["rolling"] else None})
    return {"pairs": out}


async def risk_dashboard(force: bool = False) -> dict[str, Any]:
    """Objective risk indicators, each with its raw value, a reference threshold, and source."""
    from backend.services import markets
    vol = await markets.volatility(force)
    br = await markets.breadth(force)
    b = await macro.bonds(force)
    qs = await md.quotes(["DX-Y.NYB", "HYG", "LQD", "^GSPC", "^NDX", "^RUT", "BTC-USD"], force=force)
    hist = await md.daily_closes(["^GSPC", "^NDX", "^RUT", "DX-Y.NYB", "HYG", "IEF", "BTC-USD", "CL=F", "GC=F"], "1y")
    dd = {s: technicals.max_drawdown([x["c"] for x in hist.get(s, [])])[1] for s in ("^GSPC", "^NDX", "^RUT", "BTC-USD")}
    hyg, ief = hist.get("HYG", []), hist.get("IEF", [])
    credit_proxy = None
    if len(hyg) > 63 and len(ief) > 63:
        credit_proxy = ((hyg[-1]["c"] / hyg[-63]["c"]) - (ief[-1]["c"] / ief[-63]["c"])) * 100
    hy_oas = next((x for x in (b.get("extras") or []) if x["id"] == "hy_oas" and x.get("available")), None)
    ind = [
        {"name": "VIX", "value": (vol.get("vix") or {}).get("price"), "unit": "", "reference": "Long-run median ≈ 18; > 30 historically associated with stress",
         "percentile_1y": vol.get("vix_1y_percentile"), "source": "CBOE via Yahoo-compatible"},
        {"name": "MOVE (Treasury implied vol)", "value": (vol.get("move") or {}).get("price"), "unit": "", "reference": "> 120 historically elevated", "source": "ICE via Yahoo-compatible"},
        {"name": "2s10s Treasury spread", "value": (b.get("spreads") or {}).get("10Y-2Y"), "unit": "pp", "reference": "< 0 = inverted curve", "source": "U.S. Treasury"},
        {"name": "3m10y Treasury spread", "value": (b.get("spreads") or {}).get("10Y-3M"), "unit": "pp", "reference": "< 0 = inverted curve", "source": "U.S. Treasury"},
        {"name": "High-yield OAS", "value": hy_oas.get("latest") if hy_oas else None, "unit": "%", "reference": "> 5% historically associated with credit stress",
         "source": "ICE BofA via FRED" if hy_oas else "Requires FRED_API_KEY"},
        {"name": "HY vs Treasuries (3M relative return, proxy)", "value": credit_proxy, "unit": "pp", "reference": "Negative = credit underperforming duration", "source": "HYG vs IEF ETF prices"},
        {"name": "Dollar index (DXY)", "value": qs["DX-Y.NYB"].get("price"), "unit": "", "reference": "Rapid USD strength tightens global financial conditions", "source": "ICE via Yahoo-compatible"},
        {"name": "S&P 500 20d realized vol", "value": vol["realized"]["^GSPC"]["rv20"], "unit": "%", "reference": "Long-run average ≈ 15%", "source": "Computed locally"},
        {"name": "Crude oil 20d realized vol", "value": vol["realized"]["CL=F"]["rv20"], "unit": "%", "reference": "Long-run average ≈ 30–35%", "source": "Computed locally"},
        {"name": "Bitcoin 20d realized vol", "value": vol["realized"]["BTC-USD"]["rv20"], "unit": "%", "reference": "Long-run average ≈ 55–65%", "source": "Computed locally (365-day)"},
        {"name": "% of tracked large caps above 200-DMA", "value": br.get("above_200dma_pct"), "unit": "%", "reference": "< 40% = weak breadth; > 70% = broad participation", "source": "Computed locally"},
        {"name": "Advancers / decliners", "value": f"{br.get('advancers')} / {br.get('decliners')}", "unit": "", "reference": "Session breadth", "source": "Computed locally"},
        {"name": "S&P 500 drawdown from 1Y high", "value": dd.get("^GSPC"), "unit": "%", "reference": "> 10% = correction; > 20% = bear market (convention)", "source": "Computed locally"},
        {"name": "Nasdaq 100 drawdown from 1Y high", "value": dd.get("^NDX"), "unit": "%", "reference": "", "source": "Computed locally"},
        {"name": "Russell 2000 drawdown from 1Y high", "value": dd.get("^RUT"), "unit": "%", "reference": "", "source": "Computed locally"},
        {"name": "Bitcoin drawdown from 1Y high", "value": dd.get("BTC-USD"), "unit": "%", "reference": "", "source": "Computed locally"},
    ]
    return {"indicators": ind, "vix_history": vol.get("vix_history"),
            "note": "Objective indicators with reference thresholds. No composite 'risk score' is computed — conventions shown are historical rules of thumb, not predictions."}
