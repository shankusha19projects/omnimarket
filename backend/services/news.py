"""News Intelligence Engine: aggregation, classification, deduplication, market-moving ranking."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from backend import db
from backend.analytics import news_cluster as nc
from backend.cache import store
from backend.config import load_config, ttl
from backend.providers import registry
from backend.services import market_data as md
from backend.services import universe
from backend.utils.http import ProviderError
from backend.utils.logging_setup import get_logger

log = get_logger("provider")
_last_refresh = {"at": 0.0, "results": []}


def _known() -> tuple[set[str], dict[str, str]]:
    assets = [a for a in universe.all_assets() if a.asset_class in ("equity", "etf")]
    names = {}
    for a in assets:
        if a.asset_class == "equity" and a.name and a.name != a.symbol and len(a.name) >= 4:
            names[a.name.lower().replace(" inc", "").replace(" corp", "")] = a.yahoo
    return {a.yahoo for a in assets}, names


async def refresh_feeds(force: bool = False) -> dict[str, Any]:
    """Fetch all enabled RSS feeds (and keyed news APIs) into SQLite."""
    if not force and time.time() - _last_refresh["at"] < ttl("news"):
        return {"skipped": True, "results": _last_refresh["results"], "last_refresh": _last_refresh["at"]}
    feeds = [f for f in load_config("news_feeds.json")["feeds"] if f.get("enabled", True)]
    known, names = _known()
    results: list[dict[str, Any]] = []

    async def one(feed: dict) -> list:
        try:
            items = await registry.rss.fetch_feed(feed)
            results.append({"feed": feed["id"], "publisher": feed["publisher"], "ok": True, "count": len(items)})
            return items
        except (ProviderError, Exception) as exc:  # malformed XML etc. must not break the batch
            msg = exc.message if isinstance(exc, ProviderError) else f"{type(exc).__name__}"
            results.append({"feed": feed["id"], "publisher": feed["publisher"], "ok": False, "error": msg})
            return []

    batches = await asyncio.gather(*(one(f) for f in feeds))
    items = [i for b in batches for i in b]
    for prov in (registry.finnhub, registry.newsapi):
        if prov.configured():
            try:
                extra = await prov.get_news(None, 50)
                items += extra
                results.append({"feed": prov.name, "publisher": prov.label, "ok": True, "count": len(extra)})
            except ProviderError as exc:
                results.append({"feed": prov.name, "publisher": prov.label, "ok": False, "error": exc.message})
    with db.db() as conn:
        for i in items:
            cat = nc.classify(i.title, i.summary, i.category)
            tick = sorted(set(i.tickers) | set(nc.extract_tickers(f"{i.title} {i.summary or ''}", known, names)))
            conn.execute(
                """INSERT INTO news (id, title, url, publisher, published_at, retrieved_at, category, tickers, summary, thumbnail, source_feed)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET retrieved_at=excluded.retrieved_at, category=excluded.category,
                   tickers=excluded.tickers""",
                (i.id, i.title, i.url, i.publisher, i.published_at, i.retrieved_at, cat, json.dumps(tick), i.summary, i.thumbnail, i.source_feed))
        conn.execute("DELETE FROM news WHERE published_at < ?", (time.time() - 21 * 86400,))
    _last_refresh.update(at=time.time(), results=results)
    ok = sum(1 for r in results if r["ok"])
    return {"skipped": False, "results": results, "feeds_ok": ok, "feeds_failed": len(results) - ok, "items": len(items), "last_refresh": _last_refresh["at"]}


def _rows(category: str | None, q: str | None, limit: int, hours: float) -> list[dict[str, Any]]:
    sql = "SELECT * FROM news WHERE published_at > ?"
    params: list[Any] = [time.time() - hours * 3600]
    if category and category != "All":
        sql += " AND category = ?"
        params.append(category)
    if q:
        sql += " AND (LOWER(title) LIKE ? OR tickers LIKE ?)"
        params += [f"%{q.lower()}%", f"%{q.upper()}%"]
    sql += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)
    rows = db.query(sql, params)
    for r in rows:
        r["tickers"] = json.loads(r["tickers"] or "[]")
    return rows


async def news(category: str | None = None, q: str | None = None, limit: int = 120, hours: float = 72, force: bool = False) -> dict[str, Any]:
    status = await refresh_feeds(force=force)
    rows = _rows(category, q, limit, hours)
    return {"items": rows, "categories": ["All"] + load_config("news_feeds.json")["categories"], "feed_status": status.get("results", []),
            "last_refresh": status.get("last_refresh"), "provenance": {"provider": "rss", "note": "Headlines, metadata and short excerpts only; follow links for full articles."}}


async def clusters(hours: float = 48, limit: int = 40, force: bool = False) -> dict[str, Any]:
    await refresh_feeds(force=force)
    rows = _rows(None, None, 600, hours)
    groups = nc.cluster(rows)
    large_caps = {a.yahoo for a in universe.us_stocks()}
    tick = sorted({t for r in rows for t in r["tickers"]})[:120]
    moves: dict[str, float] = {}
    if tick:
        qs = await md.quotes(tick)
        moves = {s: q["change_pct"] for s, q in qs.items() if q.get("change_pct") is not None}
    out = []
    for g in groups:
        members = sorted((rows[i] for i in g), key=lambda r: r["published_at"] or 0)
        sc = nc.score_cluster(members, large_caps, moves)
        lead = members[0]
        out.append({"id": lead["id"], "headline": max(members, key=lambda r: len(nc.tokens(r["title"]) & set().union(*[nc.tokens(m["title"]) for m in members if m is not r])) if len(members) > 1 else 0)["title"],
                    "category": lead["category"], "first_seen": lead["published_at"], "last_update": members[-1]["published_at"],
                    "size": len(members), **sc, "ticker_moves": {t: moves.get(t) for t in sc["tickers"] if t in moves},
                    "articles": [{"title": m["title"], "url": m["url"], "publisher": m["publisher"], "published_at": m["published_at"]} for m in members[:12]]})
    out.sort(key=lambda c: (-c["score"], -(c["last_update"] or 0)))
    return {"clusters": out[:limit], "total_articles": len(rows), "method": nc.__doc__}


async def market_moving(limit: int = 10) -> dict[str, Any]:
    c = await clusters(hours=36, limit=200)
    top = [x for x in c["clusters"] if x["size"] >= 2 or x["components"]["macro"] or x["components"]["price_reaction"] >= 1][:limit]
    return {"items": top, "label": "Potential Market-Moving Developments",
            "caveat": "Ranked by an explicit attention score (coverage, macro relevance, earnings/corporate-action keywords, large-cap linkage, observed price reaction). It does not establish causality or predict direction."}


def feed_status() -> dict[str, Any]:
    return {"results": _last_refresh["results"], "last_refresh": _last_refresh["at"]}
