"""Generic AND-filter screening engine over row dictionaries."""
from __future__ import annotations

from typing import Any, Iterable

from backend.models.schemas import ScreenFilter

NUMERIC_FIELDS = {
    "market_cap": "Market cap", "price": "Price", "volume": "Volume", "avg_volume": "Avg volume", "change_pct": "Change %",
    "pe": "P/E", "forward_pe": "Forward P/E", "peg": "PEG", "ps": "P/S", "pb": "P/B", "ev_ebitda": "EV/EBITDA",
    "dividend_yield": "Dividend yield %", "revenue_growth": "Revenue growth %", "eps_growth": "EPS growth %", "roe": "ROE %",
    "roic": "ROIC %", "debt_to_equity": "Debt/Equity", "gross_margin": "Gross margin %", "operating_margin": "Operating margin %",
    "net_margin": "Net margin %", "rsi14": "RSI(14)", "pct_vs_sma50": "% vs 50-DMA", "pct_vs_sma200": "% vs 200-DMA",
    "perf_1m": "1M perf %", "perf_ytd": "YTD perf %", "perf_1y": "1Y perf %", "beta": "Beta", "year_high_dist": "% from 52W high",
}
TEXT_FIELDS = {"sector": "Sector", "industry": "Industry", "country": "Country", "symbol": "Symbol", "name": "Name", "group": "Universe group"}


def _match(value: Any, f: ScreenFilter) -> bool:
    if f.op in ("contains",):
        return value is not None and str(f.value).lower() in str(value).lower()
    if f.op == "in":
        vals = f.value if isinstance(f.value, list) else [f.value]
        return value in vals
    if f.op == "eq":
        return str(value).lower() == str(f.value).lower() if isinstance(value, str) else value == f.value
    if value is None:
        return False
    try:
        v = float(value)
        a = float(f.value) if f.value not in (None, "") else None
        b = float(f.value2) if f.value2 not in (None, "") else None
    except (TypeError, ValueError):
        return False
    if f.op == "gt":
        return a is None or v > a
    if f.op == "gte":
        return a is None or v >= a
    if f.op == "lt":
        return a is None or v < a
    if f.op == "lte":
        return a is None or v <= a
    if f.op == "between":
        return (a is None or v >= a) and (b is None or v <= b)
    return True


def apply(rows: Iterable[dict[str, Any]], filters: list[ScreenFilter], sort: str | None = None, desc: bool = True, limit: int = 500) -> list[dict[str, Any]]:
    out = [r for r in rows if all(_match(r.get(f.field), f) for f in filters)]
    if sort:
        present = [r for r in out if r.get(sort) is not None]
        missing = [r for r in out if r.get(sort) is None]
        try:
            present.sort(key=lambda r: r[sort], reverse=desc)
        except TypeError:
            present.sort(key=lambda r: str(r[sort]), reverse=desc)
        out = present + missing
    return out[:limit]
