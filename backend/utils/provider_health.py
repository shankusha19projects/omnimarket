"""Tracks per-provider request/success/failure state for the Provider Health dashboard."""
from __future__ import annotations

import time
from threading import RLock

from backend import db

_lock = RLock()
_state: dict[str, dict] = {}
_last_flush = 0.0


def _get(provider: str) -> dict:
    st = _state.get(provider)
    if st is None:
        rows = db.query("SELECT * FROM provider_status WHERE provider = ?", (provider,))
        st = rows[0] if rows else {
            "provider": provider, "status": "idle", "last_request": None, "last_success": None,
            "last_failure": None, "last_error": None, "requests": 0, "failures": 0, "quota": None,
        }
        _state[provider] = st
    return st


def _flush(force: bool = False) -> None:
    global _last_flush
    now = time.time()
    if not force and now - _last_flush < 3:
        return
    _last_flush = now
    with db.db() as conn:
        for st in _state.values():
            conn.execute(
                """INSERT INTO provider_status (provider, status, last_request, last_success, last_failure, last_error, requests, failures, quota)
                   VALUES (:provider, :status, :last_request, :last_success, :last_failure, :last_error, :requests, :failures, :quota)
                   ON CONFLICT(provider) DO UPDATE SET status=excluded.status, last_request=excluded.last_request,
                   last_success=excluded.last_success, last_failure=excluded.last_failure, last_error=excluded.last_error,
                   requests=excluded.requests, failures=excluded.failures, quota=excluded.quota""",
                st,
            )


def record_request(provider: str) -> None:
    with _lock:
        st = _get(provider)
        st["last_request"] = time.time()
        st["requests"] = (st.get("requests") or 0) + 1


def record_success(provider: str, quota: str | None = None) -> None:
    with _lock:
        st = _get(provider)
        st["last_success"] = time.time()
        st["status"] = "online"
        if quota:
            st["quota"] = quota
        _flush()


def record_failure(provider: str, error: str, rate_limited: bool = False) -> None:
    with _lock:
        st = _get(provider)
        st["last_failure"] = time.time()
        st["last_error"] = error[:300]
        st["failures"] = (st.get("failures") or 0) + 1
        st["status"] = "rate_limited" if rate_limited else (
            "degraded" if st.get("last_success") and time.time() - st["last_success"] < 3600 else "error"
        )
        _flush(force=True)


def snapshot() -> dict[str, dict]:
    with _lock:
        rows = db.query("SELECT * FROM provider_status")
        merged = {r["provider"]: r for r in rows}
        merged.update({k: dict(v) for k, v in _state.items()})
        return merged
