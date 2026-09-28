"""REFRESH LIVE DATA orchestrator.

POST /api/refresh starts a job and returns its id; the UI polls
GET /api/refresh/{id} for per-dataset progress. Every dataset reports
ok / stale / failed with the provider, error and timestamps. Jobs are
also persisted to the refresh_logs table.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Awaitable, Callable

from backend import db
from backend.utils.http import ProviderError
from backend.utils.logging_setup import get_logger

log = get_logger("refresh")
JOBS: dict[str, dict[str, Any]] = {}


def _datasets(scopes: set[str], asset: str | None) -> list[tuple[str, str, str, Callable[[], Awaitable[Any]]]]:
    from backend.services import asset_classes as ac
    from backend.services import calendar, macro, markets, news
    from backend.services import user_state
    from backend.services import assets
    everything = "everything" in scopes
    ds: list[tuple[str, str, str, Callable[[], Awaitable[Any]]]] = []

    def add(scope: str, key: str, label: str, fn: Callable[[], Awaitable[Any]]) -> None:
        if everything or scope in scopes:
            ds.append((key, label, scope, fn))

    add("markets", "strip", "Global market ticker", lambda: markets.ticker_strip(force=True))
    add("markets", "indices", "Global indices", lambda: markets.indices(force=True))
    add("markets", "us_equities", "US equities (tracked large caps)", lambda: markets.heatmap("1d", force=True))
    add("markets", "sectors", "Sector ETFs", lambda: markets.sectors(force=True))
    add("markets", "commodities", "Commodities futures", lambda: ac.commodities(force=True))
    add("markets", "forex", "Forex", lambda: ac.forex(force=True))
    add("markets", "etfs", "ETFs", lambda: ac.etfs(force=True))
    add("crypto", "crypto", "Crypto (CoinGecko)", lambda: ac.crypto(force=True))
    add("economics", "treasury", "Treasury yield curve", lambda: macro.bonds(force=True))
    add("economics", "central_banks", "Central bank policy rates", lambda: macro.central_banks(force=True))
    add("economics", "economic", "Economic indicators", lambda: macro.economics(force=True))
    add("news", "news", "News feeds", lambda: news.refresh_feeds(force=True))
    add("news", "calendar", "Earnings & economic calendar", lambda: calendar.economic("this_week", force=True))
    add("portfolio", "portfolio", "Portfolio valuation", lambda: user_state.portfolio(force=True))
    if asset and (everything or "asset" in scopes):
        ds.append(("asset_quote", f"{asset} quote & chart", "asset", lambda: assets.detail(asset, force=True)))
        ds.append(("asset_fund", f"{asset} fundamentals (SEC + key stats)", "asset", lambda: assets.fundamentals(asset, force=True)))
        ds.append(("asset_news", f"{asset} news", "asset", lambda: assets.asset_news(asset, force=True)))
    return ds


def _assess(result: Any) -> tuple[str, str | None, str | None]:
    """Inspect a dataset result for stale/unavailable markers."""
    stale, errors, provider = 0, [], None

    def walk(o: Any, depth: int = 0) -> None:
        nonlocal stale, provider
        if depth > 4:
            return
        if isinstance(o, dict):
            prov = o.get("provenance")
            if isinstance(prov, dict):
                provider = provider or prov.get("provider")
                if prov.get("cache_status") in ("stale", "unavailable"):
                    stale += 1
                    if prov.get("error"):
                        errors.append(str(prov["error"]))
            if o.get("available") is False and o.get("reason"):
                errors.append(str(o["reason"]))
            for v in list(o.values())[:400]:
                walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o[:400]:
                walk(v, depth + 1)

    walk(result)
    if isinstance(result, dict) and result.get("feeds_failed"):
        errors.append(f"{result['feeds_failed']} feed(s) failed")
        return ("partial" if result.get("feeds_ok") else "failed"), "; ".join(errors[:3]), "rss"
    if isinstance(result, dict) and result.get("error"):
        return "failed", str(result["error"]), provider
    if stale:
        return "stale", f"{stale} item(s) served from cache: " + "; ".join(dict.fromkeys(errors[:3])), provider
    if errors:
        return "partial", "; ".join(dict.fromkeys(errors[:3])), provider
    return "ok", None, provider


async def _run(job_id: str) -> None:
    job = JOBS[job_id]
    sem = asyncio.Semaphore(4)

    async def one(item: dict[str, Any], fn: Callable[[], Awaitable[Any]]) -> None:
        async with sem:
            item["status"], item["started_at"] = "running", time.time()
            try:
                res = await asyncio.wait_for(fn(), timeout=150)
                item["status"], item["message"], item["provider"] = _assess(res)
            except asyncio.TimeoutError:
                item["status"], item["message"] = "failed", "timed out after 150s"
            except ProviderError as exc:
                item["status"], item["message"], item["provider"] = ("rate_limited" if exc.rate_limited else "failed"), exc.message, exc.provider
            except Exception as exc:
                log.exception(f"refresh dataset {item['key']} crashed")
                item["status"], item["message"] = "failed", f"{type(exc).__name__}: {exc}"
            item["finished_at"] = time.time()
            job["completed"] += 1

    fns = job.pop("_fns")
    await asyncio.gather(*(one(item, fn) for item, fn in zip(job["datasets"], fns)))
    job["finished_at"] = time.time()
    counts: dict[str, int] = {}
    for d in job["datasets"]:
        counts[d["status"]] = counts.get(d["status"], 0) + 1
    job["summary"] = counts
    job["status"] = "completed" if counts.get("failed", 0) == 0 else ("completed_with_errors" if counts.get("ok") or counts.get("stale") or counts.get("partial") else "failed")
    db.execute("UPDATE refresh_logs SET status = ?, finished_at = ?, payload = ? WHERE id = ?",
               (job["status"], job["finished_at"], json.dumps(job, default=str), job_id))
    log.info(f"refresh {job_id} {job['status']} {counts} in {job['finished_at'] - job['started_at']:.1f}s")


def start(scopes: list[str], asset: str | None = None) -> dict[str, Any]:
    running = [j for j in JOBS.values() if j["status"] == "running"]
    if running:
        return {**public(running[0]), "note": "A refresh is already in progress; attached to it."}
    job_id = uuid.uuid4().hex[:12]
    ds = _datasets(set(scopes or ["everything"]), asset)
    job = {"id": job_id, "scopes": scopes, "asset": asset, "status": "running", "started_at": time.time(), "finished_at": None,
           "completed": 0, "total": len(ds), "summary": {},
           "datasets": [{"key": k, "label": lbl, "scope": sc, "status": "queued", "message": None, "provider": None, "started_at": None, "finished_at": None} for k, lbl, sc, _ in ds],
           "_fns": [fn for *_, fn in ds]}
    JOBS[job_id] = job
    db.execute("INSERT INTO refresh_logs (id, scope, status, started_at, payload) VALUES (?,?,?,?,?)", (job_id, ",".join(scopes), "running", job["started_at"], "{}"))
    log.info(f"refresh {job_id} started scopes={scopes} asset={asset} datasets={len(ds)}")
    asyncio.get_running_loop().create_task(_run(job_id))
    return public(job)


def public(job: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in job.items() if not k.startswith("_")}


def get(job_id: str) -> dict[str, Any] | None:
    job = JOBS.get(job_id)
    if job:
        return public(job)
    rows = db.query("SELECT payload FROM refresh_logs WHERE id = ?", (job_id,))
    return json.loads(rows[0]["payload"]) if rows and rows[0]["payload"] not in (None, "{}") else None


def last() -> dict[str, Any] | None:
    rows = db.query("SELECT payload FROM refresh_logs WHERE status != 'running' ORDER BY started_at DESC LIMIT 1")
    if rows and rows[0]["payload"]:
        try:
            return json.loads(rows[0]["payload"])
        except ValueError:
            return None
    return None


def history(limit: int = 15) -> list[dict[str, Any]]:
    return db.query("SELECT id, scope, status, started_at, finished_at FROM refresh_logs ORDER BY started_at DESC LIMIT ?", (limit,))
