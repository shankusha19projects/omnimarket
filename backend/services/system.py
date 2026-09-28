"""Settings, preferences, provider health and first-run status."""
from __future__ import annotations

import time
from typing import Any

from backend import db
from backend.agents.registry import agents_status
from backend.ai.providers import ai_status
from backend.config import NON_SECRET_ENV, SECRET_KEYS, app_config, env, has_secret, update_env_file
from backend.providers.registry import CATALOG
from backend.utils import provider_health

DEFAULT_PREFS: dict[str, Any] = {
    "theme": "dark", "default_watchlist": None, "auto_refresh_seconds": 60, "timezone": "local", "currency": "USD", "default_market": "US",
    "setup_complete": False, "density": "comfortable",
    "dashboard_layout": ["overview", "indices", "heatmap", "movers", "breadth", "volatility", "yield_curve", "crypto", "sectors", "news", "calendar", "clock"],
    "dashboard_hidden": [], "enabled_news_feeds": None,
}
ALLOWED_ENV = {"AI_PROVIDER", "AI_MODEL", "OLLAMA_BASE_URL", "SEC_USER_AGENT"}


def preferences() -> dict[str, Any]:
    out = dict(DEFAULT_PREFS)
    for r in db.query("SELECT key FROM user_preferences"):
        out[r["key"]] = db.get_pref(r["key"])
    return out


def update(prefs: dict[str, Any], secrets: dict[str, str | None], env_updates: dict[str, str | None]) -> dict[str, Any]:
    for k, v in prefs.items():
        if k in DEFAULT_PREFS:
            db.set_pref(k, v)
    clean: dict[str, str | None] = {}
    for k, v in secrets.items():
        if k not in SECRET_KEYS:
            raise ValueError(f"Unknown secret {k}")
        if v is not None and ("\n" in v or len(v) > 400):
            raise ValueError(f"Invalid value for {k}")
        clean[k] = (v or "").strip() or None
    for k, v in env_updates.items():
        if k not in ALLOWED_ENV:
            raise ValueError(f"Setting {k} cannot be changed from the UI")
        if v is not None and ("\n" in v or len(v) > 300):
            raise ValueError(f"Invalid value for {k}")
        clean[k] = (v or "").strip() or None
    if clean:
        update_env_file(clean)
    return settings()


def settings() -> dict[str, Any]:
    """Public settings — never includes secret values, only whether each is configured."""
    return {
        "app": {"name": app_config()["app_name"], "short_name": app_config().get("short_name"), "tagline": app_config().get("tagline")},
        "preferences": preferences(),
        "secrets": [{"key": k, **meta, "configured": has_secret(k)} for k, meta in SECRET_KEYS.items()],
        "env": {k: env(k) for k in ALLOWED_ENV} | {"SEC_USER_AGENT": env("SEC_USER_AGENT")},
        "ai": ai_status(),
        "agents": agents_status(),
        "cache_ttl_seconds": app_config()["cache_ttl_seconds"],
        "defaults": NON_SECRET_ENV,
    }


def provider_status() -> dict[str, Any]:
    snap = provider_health.snapshot()
    rows = []
    now = time.time()
    for key, label, needs, url, purpose in CATALOG:
        st = snap.get(key) or {}
        if key.startswith("rss"):
            rss = [v for k, v in snap.items() if k.startswith("rss:")]
            ok = [v for v in rss if v.get("status") == "online"]
            st = {"status": "online" if ok else ("error" if rss else "idle"), "last_request": max((v.get("last_request") or 0) for v in rss) if rss else None,
                  "last_success": max((v.get("last_success") or 0) for v in rss) if rss else None,
                  "last_failure": max((v.get("last_failure") or 0) for v in rss) if rss else None,
                  "last_error": f"{len(rss) - len(ok)} of {len(rss)} feeds failing" if rss and len(ok) < len(rss) else None,
                  "requests": sum(v.get("requests") or 0 for v in rss)}
        configured = needs is None or has_secret(needs)
        if key == "ollama":
            configured = (env("AI_PROVIDER") or "").lower() == "ollama"
        status = st.get("status") or "idle"
        if not configured:
            status = "not_configured"
        elif status == "online" and st.get("last_success") and now - st["last_success"] > 6 * 3600:
            status = "idle"
        rows.append({"id": key, "label": label, "purpose": purpose, "requires_key": needs, "configured": configured, "homepage": url,
                     "status": status, "last_request": st.get("last_request"), "last_success": st.get("last_success"),
                     "last_failure": st.get("last_failure"), "last_error": st.get("last_error"), "requests": st.get("requests") or 0,
                     "failures": st.get("failures") or 0, "quota": st.get("quota")})
    return {"providers": rows, "generated_at": now}


def first_run() -> dict[str, Any]:
    p = preferences()
    return {"setup_complete": bool(p.get("setup_complete")),
            "checks": [
                {"id": "sec", "label": "SEC EDGAR (filings & statements)", "ready": True, "note": "Keyless — enabled"},
                {"id": "treasury", "label": "U.S. Treasury & central banks", "ready": True, "note": "Keyless — enabled"},
                {"id": "fred", "label": "FRED economic data", "ready": has_secret("FRED_API_KEY"), "note": "Free key unlocks 800k+ series", "key": "FRED_API_KEY"},
                {"id": "crypto", "label": "Crypto provider (CoinGecko)", "ready": True, "note": "Keyless public tier"},
                {"id": "equity", "label": "Equity provider", "ready": True, "note": "Yahoo-compatible keyless; optional Finnhub / FMP / Polygon / Alpha Vantage",
                 "key": "FINNHUB_API_KEY"},
                {"id": "news", "label": "News provider", "ready": True, "note": "Publisher RSS feeds; optional NewsAPI / Finnhub", "key": "NEWS_API_KEY"},
                {"id": "ai", "label": "AI provider", "ready": ai_status()["active"] is not None, "note": "Anthropic Claude recommended; OpenAI or local Ollama also supported",
                 "key": "ANTHROPIC_API_KEY"},
                {"id": "agent", "label": "Web research agent (TinyFish)", "ready": has_secret("TINYFISH_API_KEY"), "note": "Free Search & Fetch API", "key": "TINYFISH_API_KEY"},
            ]}
