"""Financial calculation tests: technicals, fundamentals, valuation, correlation, screener, clustering."""
import math

import numpy as np
import pytest

from backend.analytics import correlation, fundamentals as fa, news_cluster as nc, screener, technicals as ta, valuation
from backend.models.schemas import ScreenFilter


def test_sma_and_ema_basic():
    x = [1, 2, 3, 4, 5, 6]
    s = ta.sma(x, 3)
    assert math.isnan(s[1]) and s[2] == pytest.approx(2) and s[-1] == pytest.approx(5)
    e = ta.ema(x, 3)
    assert e[2] == pytest.approx(2)  # seeded with SMA
    assert e[3] == pytest.approx(4 * 0.5 + 2 * 0.5)


def test_rsi_extremes_and_range():
    up = list(range(1, 40))
    assert ta.rsi(up)[-1] == pytest.approx(100)
    rng = np.random.default_rng(0)
    walk = list(np.cumsum(rng.normal(0, 1, 300)) + 100)
    r = ta.rsi(walk)
    vals = r[~np.isnan(r)]
    assert vals.min() >= 0 and vals.max() <= 100


def test_macd_bollinger_atr_stochastic_shapes():
    rng = np.random.default_rng(1)
    c = list(np.cumsum(rng.normal(0, 1, 120)) + 100)
    h = [v + 1 for v in c]
    l = [v - 1 for v in c]
    line, sig, hist = ta.macd(c)
    assert len(line) == len(c) and not math.isnan(sig[-1])
    assert hist[-1] == pytest.approx(line[-1] - sig[-1])
    up, mid, lo = ta.bollinger(c)
    assert up[-1] > mid[-1] > lo[-1]
    assert ta.atr(h, l, c)[-1] > 0
    k, d = ta.stochastic(h, l, c)
    assert 0 <= k[-1] <= 100 and not math.isnan(d[-1])


def test_realized_vol_and_drawdown():
    # Constant 1% daily log-return drift has zero volatility.
    c = [100 * math.exp(0.01 * i) for i in range(60)]
    assert ta.realized_vol(c, 20) == pytest.approx(0, abs=1e-9)
    mdd, cur = ta.max_drawdown([100, 120, 90, 110])
    assert mdd == pytest.approx(-25) and cur == pytest.approx((110 / 120 - 1) * 100)


def test_technical_summary_is_descriptive_not_predictive():
    rng = np.random.default_rng(2)
    bars = [{"t": i * 86400, "c": float(v), "h": float(v) + 1, "l": float(v) - 1, "v": 1000} for i, v in enumerate(np.cumsum(rng.normal(0.1, 1, 260)) + 100)]
    s = ta.summary(bars)
    assert s["available"]
    text = " ".join(s["interpretation"]).lower()
    assert "rsi(14)" in text and "buy" not in text and "sell" not in text


def test_cagr_and_growth():
    assert fa.cagr(100, 121, 2) == pytest.approx(0.1)
    assert fa.cagr(-5, 10, 2) is None
    assert fa.growth(110, 100) == pytest.approx(0.1)
    assert fa.safe_div(1, 0) is None


def _statements():
    ann = [
        {"period_end": "2025-12-31", "revenue": 1000.0, "gross_profit": 600.0, "operating_income": 250.0, "net_income": 200.0, "eps_diluted": 2.0,
         "operating_cash_flow": 300.0, "capex": 50.0, "free_cash_flow": 250.0, "dna": 50.0, "ebitda": 300.0, "income_tax": 50.0, "pretax_income": 250.0,
         "interest_expense": 10.0, "cash": 100.0, "long_term_debt": 300.0, "equity": 800.0, "total_assets": 1500.0, "current_assets": 500.0,
         "current_liabilities": 250.0, "inventory": 50.0},
        {"period_end": "2024-12-31", "revenue": 900.0, "eps_diluted": 1.8, "free_cash_flow": 200.0},
        {"period_end": "2023-12-31", "revenue": 800.0},
        {"period_end": "2022-12-31", "revenue": 729.0, "eps_diluted": 1.0, "free_cash_flow": 100.0},
    ]
    return {"annual": ann, "quarterly": [], "ttm": {}, "shares_outstanding": {"value": 100.0}}


def test_fundamental_metrics_math():
    m = fa.compute(_statements(), price=40.0)
    v = {k: x["value"] for k, x in m.items()}
    assert v["market_cap"] == pytest.approx(4000)
    assert v["net_debt"] == pytest.approx(200)
    assert v["enterprise_value"] == pytest.approx(4200)
    assert v["pe"] == pytest.approx(20)
    assert v["ev_ebitda"] == pytest.approx(14)
    assert v["gross_margin"] == pytest.approx(0.6)
    assert v["fcf_yield"] == pytest.approx(250 / 4000)
    assert v["revenue_growth"] == pytest.approx(1000 / 900 - 1)
    assert v["revenue_cagr_3y"] == pytest.approx((1000 / 729) ** (1 / 3) - 1)
    assert v["current_ratio"] == pytest.approx(2)
    assert v["interest_coverage"] == pytest.approx(25)
    # ROIC = OI × (1 − 20% tax) ÷ (equity + debt − cash)
    assert v["roic"] == pytest.approx(250 * 0.8 / (800 + 300 - 100))
    assert all("formula" in x for x in m.values())


def test_dcf_gordon_and_sensitivity():
    base = dict(revenue=1000, revenue_growth=0.1, growth_years=5, terminal_growth=0.02, operating_margin=0.2, tax_rate=0.2,
                reinvestment_rate=0.25, wacc=0.09, shares=100, net_debt=0)
    r = valuation.dcf(**base)
    fcff5 = r["rows"][-1]["fcff"]
    assert r["terminal_value"] == pytest.approx(fcff5 * 1.02 / (0.09 - 0.02))
    assert r["enterprise_value"] == pytest.approx(r["pv_explicit"] + r["pv_terminal"])
    grid = valuation.sensitivity(base, [0.08, 0.09, 0.10], [0.02])
    assert grid[0][0] > grid[1][0] > grid[2][0]  # higher WACC → lower value
    with pytest.raises(ValueError):
        valuation.dcf(**{**base, "wacc": 0.02})


def test_reverse_dcf_recovers_growth():
    base = dict(revenue=1000, revenue_growth=0.12, growth_years=5, terminal_growth=0.02, operating_margin=0.2, tax_rate=0.2,
                reinvestment_rate=0.25, wacc=0.09, shares=100, net_debt=0)
    price = valuation.dcf(**base)["per_share"]
    assert valuation.reverse_dcf(price, base) == pytest.approx(0.12, abs=1e-4)


def test_ddm_and_comparables():
    assert valuation.ddm(2.0, 0.03, 0.08) == pytest.approx(2.06 / 0.05)
    assert valuation.ddm(2.0, 0.09, 0.08) is None
    comp = valuation.comparables({"eps": 5, "book_per_share": 10}, [{"pe": 10, "pb": 2}, {"pe": 20, "pb": 4}, {"pe": 30, "pb": None}])
    assert comp["implied"]["pe"]["implied_price"] == pytest.approx(100)
    assert comp["implied"]["pb"]["implied_price"] == pytest.approx(30)


def test_correlation_matrix_perfect_and_inverse():
    days = [{"t": 1_700_000_000 + i * 86400, "c": 100 * math.exp(0.01 * math.sin(i))} for i in range(40)]
    inv = [{"t": b["t"], "c": 100 * math.exp(-0.01 * math.sin(i))} for i, b in enumerate(days)]
    m = correlation.correlation_matrix({"a": days, "b": days, "c": inv})
    assert m["matrix"][0][1] == pytest.approx(1)
    assert m["matrix"][0][2] == pytest.approx(-1)


def test_screener_filters_and_sort():
    rows = [{"symbol": "A", "pe": 10, "sector": "Tech", "market_cap": 5}, {"symbol": "B", "pe": 30, "sector": "Tech", "market_cap": 9},
            {"symbol": "C", "pe": None, "sector": "Energy", "market_cap": 7}]
    out = screener.apply(rows, [ScreenFilter(field="pe", op="lt", value=25)])
    assert [r["symbol"] for r in out] == ["A"]
    out = screener.apply(rows, [ScreenFilter(field="sector", op="contains", value="tech")], sort="market_cap")
    assert [r["symbol"] for r in out] == ["B", "A"]
    out = screener.apply(rows, [ScreenFilter(field="market_cap", op="between", value=6, value2=10)], sort="pe", desc=False)
    assert [r["symbol"] for r in out] == ["B", "C"]  # None sorts last


def test_news_clustering_and_scoring():
    t = 1_700_000_000
    items = [
        {"title": "Fed holds interest rates steady as inflation cools", "publisher": "Reuters", "published_at": t, "tickers": []},
        {"title": "Federal Reserve holds rates steady, signals inflation cooling", "publisher": "CNBC", "published_at": t + 600, "tickers": []},
        {"title": "Nvidia unveils new AI chip at developer conference", "publisher": "Yahoo", "published_at": t + 900, "tickers": ["NVDA"]},
    ]
    groups = sorted(nc.cluster(items), key=len, reverse=True)
    assert len(groups) == 2 and len(groups[0]) == 2
    sc = nc.score_cluster([items[i] for i in groups[0]], set(), {})
    assert sc["components"]["macro"] == 1.5 and sc["components"]["coverage"] == pytest.approx(2 * math.log2(3), abs=0.01)
    assert nc.classify("Bitcoin rallies past record", None, None) == "Crypto"
