"""Return correlations across assets aligned on common dates."""
from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np


def _day(t: int) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")


def align(series: dict[str, list[dict]]) -> tuple[list[str], dict[str, np.ndarray]]:
    """Align close series on dates common to all inputs (daily bars)."""
    maps = {k: {_day(b["t"]): b["c"] for b in v if b.get("c") is not None} for k, v in series.items()}
    common = sorted(set.intersection(*[set(m) for m in maps.values()])) if maps else []
    return common, {k: np.array([m[d] for d in common], dtype=float) for k, m in maps.items()}


def correlation_matrix(series: dict[str, list[dict]], window: int | None = None) -> dict:
    dates, closes = align(series)
    keys = list(closes)
    if len(dates) < 10:
        return {"keys": keys, "matrix": [], "observations": len(dates), "error": "insufficient overlapping history"}
    rets = {k: np.diff(np.log(v)) for k, v in closes.items()}
    if window:
        rets = {k: r[-window:] for k, r in rets.items()}
    mat = []
    for a in keys:
        row = []
        for b in keys:
            ra, rb = rets[a], rets[b]
            c = float(np.corrcoef(ra, rb)[0, 1]) if np.std(ra) > 0 and np.std(rb) > 0 else float("nan")
            row.append(None if math.isnan(c) else round(c, 3))
        mat.append(row)
    return {"keys": keys, "matrix": mat, "observations": len(next(iter(rets.values()))), "start": dates[0], "end": dates[-1],
            "method": "Pearson correlation of daily log returns on dates common to all series."}


def rolling_correlation(a: list[dict], b: list[dict], window: int = 60) -> list[dict]:
    dates, closes = align({"a": a, "b": b})
    if len(dates) <= window + 1:
        return []
    ra, rb = np.diff(np.log(closes["a"])), np.diff(np.log(closes["b"]))
    out = []
    for i in range(window, len(ra) + 1):
        x, y = ra[i - window:i], rb[i - window:i]
        if np.std(x) > 0 and np.std(y) > 0:
            out.append({"date": dates[i], "corr": round(float(np.corrcoef(x, y)[0, 1]), 4)})
    return out
