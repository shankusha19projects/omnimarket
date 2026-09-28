"""Fundamental metrics derived from normalized statements (SEC XBRL) and market data.

Each metric returns value + formula + source so the UI can show provenance.
"""
from __future__ import annotations

from typing import Any


def safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def cagr(first: float | None, last: float | None, years: float) -> float | None:
    """Compound annual growth rate. Undefined when either endpoint is ≤ 0."""
    if first is None or last is None or years <= 0 or first <= 0 or last <= 0:
        return None
    return (last / first) ** (1 / years) - 1


def growth(cur: float | None, prev: float | None) -> float | None:
    if cur is None or prev is None or prev == 0:
        return None
    return (cur - prev) / abs(prev)


def compute(statements: dict[str, Any], price: float | None, market_cap: float | None = None,
            shares: float | None = None, dividend_ps: float | None = None) -> dict[str, dict[str, Any]]:
    """Compute valuation/quality/growth/strength metrics.

    Uses TTM where available (falls back to latest fiscal year). Market cap is
    price × shares outstanding when the provider does not supply it.
    """
    annual = statements.get("annual") or []
    ttm = statements.get("ttm") or {}
    base = ttm if ttm.get("revenue") else (annual[0] if annual else {})
    bal = (statements.get("quarterly") or [{}])[0] if statements.get("quarterly") else (annual[0] if annual else {})
    so = shares or (statements.get("shares_outstanding") or {}).get("value") or bal.get("shares_outstanding")
    mcap = market_cap or (price * so if price and so else None)

    rev, ni, oi = base.get("revenue"), base.get("net_income"), base.get("operating_income")
    ebitda = base.get("ebitda")
    fcf = base.get("free_cash_flow")
    ocf = base.get("operating_cash_flow")
    eps = base.get("eps_diluted")
    cash = (bal.get("cash") or 0) + (bal.get("short_term_investments") or 0) if bal.get("cash") is not None else None
    debt = None
    if bal.get("long_term_debt") is not None or bal.get("current_debt") is not None:
        debt = (bal.get("long_term_debt") or 0) + (bal.get("current_debt") or 0)
    equity = bal.get("equity")
    net_debt = debt - cash if debt is not None and cash is not None else None
    ev = mcap + net_debt if mcap is not None and net_debt is not None else None
    tax_rate = safe_div(base.get("income_tax"), base.get("pretax_income"))
    tr = min(max(tax_rate, 0.0), 0.35) if tax_rate is not None else 0.21
    invested = (equity or 0) + (debt or 0) - (cash or 0) if equity is not None else None
    roic = safe_div(oi * (1 - tr) if oi is not None else None, invested) if invested and invested > 0 else None
    div_yield = safe_div(dividend_ps, price) if dividend_ps else (safe_div(abs(base.get("dividends_paid") or 0), mcap) if base.get("dividends_paid") and mcap else None)

    rev_cagr = eps_cagr = fcf_cagr = None
    if len(annual) >= 4:
        rev_cagr = cagr(annual[3].get("revenue"), annual[0].get("revenue"), 3)
        eps_cagr = cagr(annual[3].get("eps_diluted"), annual[0].get("eps_diluted"), 3)
        fcf_cagr = cagr(annual[3].get("free_cash_flow"), annual[0].get("free_cash_flow"), 3)
    rev_g = growth(annual[0].get("revenue"), annual[1].get("revenue")) if len(annual) >= 2 else None
    eps_g = growth(annual[0].get("eps_diluted"), annual[1].get("eps_diluted")) if len(annual) >= 2 else None
    fcf_g = growth(annual[0].get("free_cash_flow"), annual[1].get("free_cash_flow")) if len(annual) >= 2 else None
    pe = safe_div(price, eps) if eps and eps > 0 else None

    def m(value: float | None, formula: str, kind: str = "ratio") -> dict[str, Any]:
        return {"value": value, "formula": formula, "kind": kind}

    period = "TTM" if base is ttm else f"FY ending {base.get('period_end', '?')}"
    return {
        "market_cap": m(mcap, "price × shares outstanding", "money"),
        "enterprise_value": m(ev, "market cap + total debt − cash & ST investments", "money"),
        "revenue": m(rev, f"Revenue ({period})", "money"),
        "ebitda": m(ebitda, f"Operating income + D&A ({period})", "money"),
        "operating_income": m(oi, f"Operating income ({period})", "money"),
        "net_income": m(ni, f"Net income ({period})", "money"),
        "eps": m(eps, f"Diluted EPS ({period})", "per_share"),
        "free_cash_flow": m(fcf, f"Operating cash flow − capex ({period})", "money"),
        "cash": m(cash, "Cash & equivalents + short-term investments (latest balance sheet)", "money"),
        "debt": m(debt, "Long-term debt + current debt (latest balance sheet)", "money"),
        "net_debt": m(net_debt, "Total debt − cash & ST investments", "money"),
        "pe": m(pe, "Price ÷ diluted EPS", "multiple"),
        "ps": m(safe_div(mcap, rev), "Market cap ÷ revenue", "multiple"),
        "pb": m(safe_div(mcap, equity) if equity and equity > 0 else None, "Market cap ÷ shareholders' equity", "multiple"),
        "ev_sales": m(safe_div(ev, rev), "EV ÷ revenue", "multiple"),
        "ev_ebitda": m(safe_div(ev, ebitda) if ebitda and ebitda > 0 else None, "EV ÷ EBITDA", "multiple"),
        "fcf_yield": m(safe_div(fcf, mcap), "Free cash flow ÷ market cap", "pct"),
        "dividend_yield": m(div_yield, "Dividends per share ÷ price (or dividends paid ÷ market cap)", "pct"),
        "gross_margin": m(safe_div(base.get("gross_profit"), rev), "Gross profit ÷ revenue", "pct"),
        "operating_margin": m(safe_div(oi, rev), "Operating income ÷ revenue", "pct"),
        "net_margin": m(safe_div(ni, rev), "Net income ÷ revenue", "pct"),
        "fcf_margin": m(safe_div(fcf, rev), "Free cash flow ÷ revenue", "pct"),
        "cash_conversion": m(safe_div(ocf, ni) if ni and ni > 0 else None, "Operating cash flow ÷ net income", "multiple"),
        "roe": m(safe_div(ni, equity) if equity and equity > 0 else None, "Net income ÷ shareholders' equity", "pct"),
        "roa": m(safe_div(ni, bal.get("total_assets")), "Net income ÷ total assets", "pct"),
        "roic": m(roic, f"Operating income × (1 − tax {tr:.0%}) ÷ (equity + debt − cash)", "pct"),
        "revenue_growth": m(rev_g, "Latest FY revenue ÷ prior FY − 1", "pct"),
        "eps_growth": m(eps_g, "Latest FY diluted EPS ÷ prior FY − 1", "pct"),
        "fcf_growth": m(fcf_g, "Latest FY FCF ÷ prior FY − 1", "pct"),
        "revenue_cagr_3y": m(rev_cagr, "(Rev_t ÷ Rev_t−3)^(1/3) − 1", "pct"),
        "eps_cagr_3y": m(eps_cagr, "(EPS_t ÷ EPS_t−3)^(1/3) − 1", "pct"),
        "fcf_cagr_3y": m(fcf_cagr, "(FCF_t ÷ FCF_t−3)^(1/3) − 1", "pct"),
        "current_ratio": m(safe_div(bal.get("current_assets"), bal.get("current_liabilities")), "Current assets ÷ current liabilities", "multiple"),
        "quick_ratio": m(safe_div((bal.get("current_assets") or 0) - (bal.get("inventory") or 0), bal.get("current_liabilities")) if bal.get("current_assets") else None,
                         "(Current assets − inventory) ÷ current liabilities", "multiple"),
        "debt_to_equity": m(safe_div(debt, equity) if equity and equity > 0 else None, "Total debt ÷ shareholders' equity", "multiple"),
        "net_debt_to_ebitda": m(safe_div(net_debt, ebitda) if ebitda and ebitda > 0 else None, "Net debt ÷ EBITDA", "multiple"),
        "interest_coverage": m(safe_div(oi, base.get("interest_expense")) if base.get("interest_expense") else None, "Operating income ÷ interest expense", "multiple"),
        "shares_outstanding": m(so, "Shares outstanding (SEC cover page / balance sheet)", "count"),
    }
