"""News deduplication/clustering and the 'Potential Market-Moving Developments' score.

Clustering: two stories join the same event cluster when they were published
within 36h of each other and either (a) title-token Jaccard similarity ≥ 0.34,
or (b) they share a ticker and ≥ 2 salient keywords, or (c) they share ≥ 3
salient named-entity/event tokens. Union-find merges transitively.

Market-moving score (explicit, additive; shown in the UI):
  score = 2.0·log2(1 + distinct_publishers)
        + 1.5·macro_relevance     (1 if Fed/CPI/jobs/GDP/tariff/rates/OPEC…)
        + 1.0·earnings_event      (1 if earnings/guidance/results keywords)
        + 1.0·corporate_action    (1 if merger/acquisition/buyback/IPO…)
        + 1.0·large_cap_mention   (1 if a mentioned ticker is in the tracked large-cap set)
        + 0.5·|linked ticker move| in % (capped at 3 points, when a quote is available)
The score ranks attention-worthiness; it does not predict price direction.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

STOP = set("""a an the of to in on for and or but with from by at as is are was were be been it its this that these those
after before over under into about amid says said say new more most less than up down will would could should may might
can how why what who when where which while report reports update live today week year years stock stocks shares market
markets investors analyst analysts per vs via us u.s. first last just still big""".split())
MACRO = re.compile(r"\b(fed|fomc|powell|rate cut|rate hike|interest rates?|inflation|cpi|pce|payrolls?|jobs report|unemployment|gdp|"
                   r"recession|tariffs?|treasury yields?|bond yields?|ecb|boj|bank of england|opec|central bank|stimulus|debt ceiling|shutdown)\b", re.I)
EARN = re.compile(r"\b(earnings|quarterly results|guidance|revenue beat|revenue miss|eps|profit warning|outlook|beats estimates|misses estimates)\b", re.I)
CORP = re.compile(r"\b(merger|acquire[sd]?|acquisition|buyout|takeover|buyback|ipo|spin-?off|bankruptcy|chapter 11|layoffs|antitrust|lawsuit|sec charges)\b", re.I)
TICKER_RX = re.compile(r"\(([A-Z]{1,5})\)|\$([A-Z]{1,5})\b")

CATEGORY_RULES: list[tuple[str, re.Pattern]] = [
    ("Federal Reserve", re.compile(r"\b(fed|fomc|powell|federal reserve)\b", re.I)),
    ("Crypto", re.compile(r"\b(bitcoin|crypto|ethereum|stablecoin|btc|eth|solana|blockchain|token)\b", re.I)),
    ("Earnings", EARN),
    ("M&A", re.compile(r"\b(merger|acquire[sd]?|acquisition|takeover|buyout|deal to buy)\b", re.I)),
    ("IPOs", re.compile(r"\b(ipo|initial public offering|goes public|listing debut)\b", re.I)),
    ("Energy", re.compile(r"\b(oil|crude|opec|natural gas|lng|brent|wti|refiner|gasoline)\b", re.I)),
    ("Commodities", re.compile(r"\b(gold|silver|copper|lithium|uranium|rare earths?|wheat|corn|soybeans?|cocoa|coffee|metals?|mining)\b", re.I)),
    ("Bonds", re.compile(r"\b(treasur(y|ies)|bond|yields?|credit spreads?|debt sale)\b", re.I)),
    ("Forex", re.compile(r"\b(dollar|euro|yen|yuan|sterling|currency|forex|fx)\b", re.I)),
    ("Real Estate", re.compile(r"\b(housing|mortgage|home sales|real estate|reit|commercial property)\b", re.I)),
    ("Regulation", re.compile(r"\b(sec|regulator|regulation|antitrust|ftc|doj|lawsuit|probe|fine[sd]?)\b", re.I)),
    ("Geopolitics", re.compile(r"\b(war|sanctions?|china|russia|ukraine|israel|iran|taiwan|tariffs?|election|geopolitic)\b", re.I)),
    ("Economy", re.compile(r"\b(inflation|cpi|gdp|jobs|payrolls|unemployment|retail sales|consumer|recession|economy|pmi)\b", re.I)),
    ("Technology", re.compile(r"\b(ai|artificial intelligence|chip|semiconductor|nvidia|apple|microsoft|google|software|cloud|tech)\b", re.I)),
]


def classify(title: str, summary: str | None, default: str | None) -> str:
    text = f"{title} {summary or ''}"
    for cat, rx in CATEGORY_RULES:
        if rx.search(title):
            return cat
    for cat, rx in CATEGORY_RULES:
        if rx.search(text):
            return cat
    return default or "Markets"


def tokens(title: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9&'\.-]+", title.lower())
    return {w.strip(".'") for w in words if w not in STOP and len(w) > 2}


def extract_tickers(text: str, known: set[str], names: dict[str, str] | None = None) -> list[str]:
    found = set()
    for m in TICKER_RX.finditer(text):
        t = m.group(1) or m.group(2)
        if t in known:
            found.add(t)
    if names:
        low = text.lower()
        for name, sym in names.items():
            if len(name) >= 4 and re.search(rf"\b{re.escape(name)}\b", low):
                found.add(sym)
    return sorted(found)


class _UF:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        self.p[self.find(a)] = self.find(b)


def cluster(items: list[dict[str, Any]], window_h: float = 36) -> list[list[int]]:
    toks = [tokens(i["title"]) for i in items]
    uf = _UF(len(items))
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            ti, tj = items[i].get("published_at") or 0, items[j].get("published_at") or 0
            if abs(ti - tj) > window_h * 3600:
                continue
            a, b = toks[i], toks[j]
            if not a or not b:
                continue
            inter = len(a & b)
            jac = inter / len(a | b)
            shared_ticker = bool(set(items[i].get("tickers") or []) & set(items[j].get("tickers") or []))
            if jac >= 0.34 or (shared_ticker and inter >= 2) or inter >= 4:
                uf.union(i, j)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(items)):
        groups[uf.find(i)].append(i)
    return list(groups.values())


def score_cluster(members: list[dict[str, Any]], large_caps: set[str], moves: dict[str, float]) -> dict[str, Any]:
    publishers = {m["publisher"] for m in members}
    text = " ".join(m["title"] + " " + (m.get("summary") or "") for m in members)
    tickers = sorted({t for m in members for t in (m.get("tickers") or [])})
    comp = {
        "coverage": round(2.0 * math.log2(1 + len(publishers)), 2),
        "macro": 1.5 if MACRO.search(text) else 0.0,
        "earnings": 1.0 if EARN.search(text) else 0.0,
        "corporate_action": 1.0 if CORP.search(text) else 0.0,
        "large_cap": 1.0 if any(t in large_caps for t in tickers) else 0.0,
        "price_reaction": round(min(3.0, 0.5 * max((abs(moves[t]) for t in tickers if t in moves), default=0.0)), 2),
    }
    return {"score": round(sum(comp.values()), 2), "components": comp, "publishers": sorted(publishers), "tickers": tickers}
