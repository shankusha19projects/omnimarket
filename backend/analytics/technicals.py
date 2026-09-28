"""Technical indicators computed locally from price history (numpy only).

All functions return arrays aligned with the input (NaN where undefined).
Interpretations are descriptive, never predictive.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

TRADING_DAYS = 252


def _arr(x: Sequence[float | None]) -> np.ndarray:
    return np.array([np.nan if v is None else float(v) for v in x], dtype=float)


def sma(close: Sequence[float], n: int) -> np.ndarray:
    c = _arr(close)
    out = np.full_like(c, np.nan)
    if len(c) >= n:
        cs = np.cumsum(np.insert(c, 0, 0.0))
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def ema(close: Sequence[float], n: int) -> np.ndarray:
    c = _arr(close)
    out = np.full_like(c, np.nan)
    if len(c) < n:
        return out
    k = 2 / (n + 1)
    out[n - 1] = np.nanmean(c[:n])  # seed with SMA
    for i in range(n, len(c)):
        out[i] = c[i] * k + out[i - 1] * (1 - k)
    return out


def rsi(close: Sequence[float], n: int = 14) -> np.ndarray:
    """Wilder's RSI: 100 - 100/(1+RS), RS = smoothed avg gain / smoothed avg loss."""
    c = _arr(close)
    out = np.full_like(c, np.nan)
    if len(c) <= n:
        return out
    d = np.diff(c)
    gains, losses = np.clip(d, 0, None), np.clip(-d, 0, None)
    ag, al = gains[:n].mean(), losses[:n].mean()
    out[n] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(c)):
        ag = (ag * (n - 1) + gains[i - 1]) / n
        al = (al * (n - 1) + losses[i - 1]) / n
        out[i] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def macd(close: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    line = ema(close, fast) - ema(close, slow)
    sig = np.full_like(line, np.nan)
    valid = ~np.isnan(line)
    if valid.sum() >= signal:
        first = int(np.argmax(valid))
        sig[first:] = ema(line[first:], signal)
    return line, sig, line - sig


def bollinger(close: Sequence[float], n: int = 20, k: float = 2.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    c = _arr(close)
    mid = sma(c, n)
    sd = np.full_like(c, np.nan)
    for i in range(n - 1, len(c)):
        sd[i] = np.std(c[i - n + 1:i + 1])
    return mid + k * sd, mid, mid - k * sd


def atr(high: Sequence[float], low: Sequence[float], close: Sequence[float], n: int = 14) -> np.ndarray:
    h, l, c = _arr(high), _arr(low), _arr(close)
    tr = np.full_like(c, np.nan)
    tr[0] = h[0] - l[0]
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])
    out = np.full_like(c, np.nan)
    if len(c) > n:
        out[n - 1] = np.nanmean(tr[:n])
        for i in range(n, len(c)):
            out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def stochastic(high: Sequence[float], low: Sequence[float], close: Sequence[float], n: int = 14, d: int = 3) -> tuple[np.ndarray, np.ndarray]:
    h, l, c = _arr(high), _arr(low), _arr(close)
    k = np.full_like(c, np.nan)
    for i in range(n - 1, len(c)):
        hh, ll = np.nanmax(h[i - n + 1:i + 1]), np.nanmin(l[i - n + 1:i + 1])
        k[i] = 50.0 if hh == ll else (c[i] - ll) / (hh - ll) * 100
    dline = np.full_like(k, np.nan)
    for i in range(n - 1 + d - 1, len(k)):
        dline[i] = np.mean(k[i - d + 1:i + 1])
    return k, dline


def roc(close: Sequence[float], n: int = 12) -> np.ndarray:
    c = _arr(close)
    out = np.full_like(c, np.nan)
    out[n:] = (c[n:] / c[:-n] - 1) * 100
    return out


def log_returns(close: Sequence[float]) -> np.ndarray:
    c = _arr(close)
    return np.diff(np.log(c))


def realized_vol(close: Sequence[float], window: int = 20, periods_per_year: int = TRADING_DAYS) -> float | None:
    """Annualized standard deviation of daily log returns over the trailing window."""
    r = log_returns(close)
    r = r[~np.isnan(r)][-window:]
    if len(r) < max(5, window // 2):
        return None
    return float(np.std(r, ddof=1) * math.sqrt(periods_per_year) * 100)


def max_drawdown(close: Sequence[float]) -> tuple[float | None, float | None]:
    """Returns (max drawdown %, current drawdown from peak %)."""
    c = _arr(close)
    c = c[~np.isnan(c)]
    if len(c) < 2:
        return None, None
    peak = np.maximum.accumulate(c)
    dd = c / peak - 1
    return float(dd.min() * 100), float(dd[-1] * 100)


def pct_change_over(closes: list[float], times: list[int], seconds: int) -> float | None:
    if not closes:
        return None
    target = times[-1] - seconds
    idx = next((i for i in range(len(times) - 1, -1, -1) if times[i] <= target), None)
    if idx is None:
        return None
    base = closes[idx]
    return (closes[-1] / base - 1) * 100 if base else None


def _last(a: np.ndarray) -> float | None:
    v = a[~np.isnan(a)]
    return float(v[-1]) if len(v) else None


def summary(bars: list[dict[str, Any]], benchmark_closes: list[float] | None = None) -> dict[str, Any]:
    """Compute the indicator snapshot plus neutral, descriptive interpretations."""
    closes = [b["c"] for b in bars]
    highs = [b.get("h") or b["c"] for b in bars]
    lows = [b.get("l") or b["c"] for b in bars]
    vols = [b.get("v") or 0 for b in bars]
    if len(closes) < 20:
        return {"available": False, "reason": "Fewer than 20 observations — indicators not computed."}
    price = closes[-1]
    s20, s50, s200 = _last(sma(closes, 20)), _last(sma(closes, 50)), _last(sma(closes, 200))
    e12, e26 = _last(ema(closes, 12)), _last(ema(closes, 26))
    r = _last(rsi(closes))
    m_line, m_sig, m_hist = (_last(x) for x in macd(closes))
    bb_u, bb_m, bb_l = (_last(x) for x in bollinger(closes))
    a = _last(atr(highs, lows, closes))
    st_k, st_d = (_last(x) for x in stochastic(highs, lows, closes))
    rc = _last(roc(closes))
    vol20, vol60 = realized_vol(closes, 20), realized_vol(closes, 60)
    mdd, cur_dd = max_drawdown(closes[-TRADING_DAYS:])
    vavg20 = float(np.mean(vols[-20:])) if any(vols[-20:]) else None
    rel = None
    if benchmark_closes and len(benchmark_closes) >= 60 and len(closes) >= 60:
        a_ret = closes[-1] / closes[-60] - 1
        b_ret = benchmark_closes[-1] / benchmark_closes[-60] - 1
        rel = (a_ret - b_ret) * 100

    notes: list[str] = []
    if r is not None:
        zone = ("a historically elevated momentum range (≥70)" if r >= 70 else
                "a historically depressed momentum range (≤30)" if r <= 30 else "a neutral momentum range (30–70)")
        notes.append(f"RSI(14) is {r:.1f}, placing the asset in {zone}. RSI extremes can persist; they are not reversal signals on their own.")
    if s50 and s200:
        rel_txt = "above" if s50 > s200 else "below"
        notes.append(f"The 50-day average ({s50:,.2f}) is {rel_txt} the 200-day average ({s200:,.2f}); price is "
                     f"{(price / s200 - 1) * 100:+.1f}% versus the 200-day.")
    if m_line is not None and m_sig is not None:
        notes.append(f"MACD line ({m_line:.2f}) is {'above' if m_line > m_sig else 'below'} its signal line ({m_sig:.2f}), "
                     f"describing {'positive' if m_line > m_sig else 'negative'} short-term momentum relative to the recent trend.")
    if bb_u and bb_l:
        pos = (price - bb_l) / (bb_u - bb_l) * 100 if bb_u != bb_l else 50
        notes.append(f"Price sits at {pos:.0f}% of the 20-day Bollinger band width.")
    if vol20:
        notes.append(f"20-day realized volatility is {vol20:.1f}% annualized" + (f" (60-day: {vol60:.1f}%)." if vol60 else "."))
    if cur_dd is not None:
        notes.append(f"Current drawdown from the trailing 1-year peak is {cur_dd:.1f}% (max over the window {mdd:.1f}%).")
    return {
        "available": True, "price": price, "sma20": s20, "sma50": s50, "sma200": s200, "ema12": e12, "ema26": e26,
        "rsi14": r, "macd": m_line, "macd_signal": m_sig, "macd_hist": m_hist, "bb_upper": bb_u, "bb_mid": bb_m, "bb_lower": bb_l,
        "atr14": a, "stoch_k": st_k, "stoch_d": st_d, "roc12": rc, "realized_vol_20d": vol20, "realized_vol_60d": vol60,
        "max_drawdown_1y": mdd, "current_drawdown": cur_dd, "avg_volume_20d": vavg20, "relative_strength_60d_vs_spx": rel,
        "above_sma20": price > s20 if s20 else None, "above_sma50": price > s50 if s50 else None, "above_sma200": price > s200 if s200 else None,
        "interpretation": notes,
        "method": "Computed locally from provider OHLCV. RSI/ATR use Wilder smoothing; volatility = stdev of daily log returns × √252.",
    }


def series(bars: list[dict[str, Any]]) -> dict[str, list[float | None]]:
    """Full indicator series for chart overlays."""
    closes = [b["c"] for b in bars]
    highs = [b.get("h") or b["c"] for b in bars]
    lows = [b.get("l") or b["c"] for b in bars]
    clean = lambda a: [None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(float(v), 6) for v in a]  # noqa: E731
    up, mid, lo = bollinger(closes)
    m, s, h = macd(closes)
    k, d = stochastic(highs, lows, closes)
    return {"sma20": clean(sma(closes, 20)), "sma50": clean(sma(closes, 50)), "sma200": clean(sma(closes, 200)),
            "ema12": clean(ema(closes, 12)), "ema26": clean(ema(closes, 26)), "rsi14": clean(rsi(closes)),
            "macd": clean(m), "macd_signal": clean(s), "macd_hist": clean(h), "bb_upper": clean(up), "bb_mid": clean(mid),
            "bb_lower": clean(lo), "atr14": clean(atr(highs, lows, closes)), "stoch_k": clean(k), "stoch_d": clean(d)}
