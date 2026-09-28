"""Valuation models: DCF (FCFF), reverse DCF, dividend discount, comparables, sensitivity.

These are tools for testing assumptions, not price targets. Outputs are only as
good as the inputs, which the user can edit.
"""
from __future__ import annotations

from statistics import median
from typing import Any


def dcf(revenue: float, revenue_growth: float, growth_years: int, terminal_growth: float, operating_margin: float,
        tax_rate: float, reinvestment_rate: float, wacc: float, shares: float, net_debt: float) -> dict[str, Any]:
    """Two-stage unlevered DCF.

    Stage 1 (explicit years): revenue grows at `revenue_growth`, fading linearly
    toward `terminal_growth` in the final third of the horizon.
      NOPAT_t = Revenue_t × operating_margin × (1 − tax_rate)
      FCFF_t  = NOPAT_t × (1 − reinvestment_rate)
    Terminal value (Gordon growth) at year N: TV = FCFF_N × (1 + g) ÷ (WACC − g)
    Equity value = PV(FCFF) + PV(TV) − net debt;  per share = equity ÷ shares.
    """
    if wacc <= terminal_growth:
        raise ValueError("WACC must exceed terminal growth for the Gordon growth terminal value to be finite.")
    rows = []
    rev = revenue
    pv_sum = 0.0
    fade_start = max(1, int(growth_years * 2 / 3))
    for t in range(1, growth_years + 1):
        if t > fade_start:
            frac = (t - fade_start) / max(1, growth_years - fade_start)
            g = revenue_growth + (terminal_growth - revenue_growth) * frac
        else:
            g = revenue_growth
        rev *= 1 + g
        nopat = rev * operating_margin * (1 - tax_rate)
        fcff = nopat * (1 - reinvestment_rate)
        df = 1 / (1 + wacc) ** t
        pv_sum += fcff * df
        rows.append({"year": t, "growth": g, "revenue": rev, "nopat": nopat, "fcff": fcff, "discount_factor": df, "pv": fcff * df})
    tv = rows[-1]["fcff"] * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_tv = tv / (1 + wacc) ** growth_years
    ev = pv_sum + pv_tv
    equity = ev - net_debt
    return {"rows": rows, "pv_explicit": pv_sum, "terminal_value": tv, "pv_terminal": pv_tv, "enterprise_value": ev,
            "equity_value": equity, "per_share": equity / shares if shares else None,
            "terminal_share_of_ev": pv_tv / ev if ev else None}


def sensitivity(base: dict[str, Any], waccs: list[float], growths: list[float]) -> list[list[float | None]]:
    grid: list[list[float | None]] = []
    for w in waccs:
        row: list[float | None] = []
        for g in growths:
            try:
                row.append(dcf(**{**base, "wacc": w, "terminal_growth": g})["per_share"])
            except ValueError:
                row.append(None)
        grid.append(row)
    return grid


def reverse_dcf(price: float, base: dict[str, Any], lo: float = -0.3, hi: float = 0.8) -> float | None:
    """Solve for the stage-1 revenue growth that makes DCF value per share equal the market price (bisection)."""
    def f(g: float) -> float:
        v = dcf(**{**base, "revenue_growth": g})["per_share"]
        return (v or 0) - price

    try:
        flo, fhi = f(lo), f(hi)
    except ValueError:
        return None
    if flo * fhi > 0:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(fm) < 1e-6:
            break
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def ddm(dividend: float, growth: float, cost_of_equity: float) -> float | None:
    """Gordon growth dividend discount model: P = D1 ÷ (r − g), D1 = D0 × (1 + g)."""
    if cost_of_equity <= growth or dividend <= 0:
        return None
    return dividend * (1 + growth) / (cost_of_equity - growth)


def comparables(target: dict[str, float | None], peers: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply peer-median multiples to the target's own fundamentals."""
    out: dict[str, Any] = {"peers": peers, "implied": {}}
    for multiple, metric in (("pe", "eps"), ("ps", "revenue_per_share"), ("pb", "book_per_share")):
        vals = [p[multiple] for p in peers if isinstance(p.get(multiple), (int, float)) and 0 < p[multiple] < 500]
        if len(vals) >= 2 and target.get(metric):
            med = median(vals)
            out["implied"][multiple] = {"peer_median": med, "target_metric": target[metric], "implied_price": med * target[metric], "n": len(vals)}
    return out
