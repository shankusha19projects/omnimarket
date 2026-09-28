"""Central configuration.

Secrets come only from environment variables (loaded from `.env`). Non-secret
application settings come from `config/app.json`. Nothing here is ever sent to
the browser except via `public_settings()`, which exposes *whether* a key is
configured, never its value.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / "cache"
LOG_DIR = ROOT / "logs"
ENV_FILE = ROOT / ".env"

for _d in (DATA_DIR, CACHE_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

load_dotenv(ENV_FILE, override=False)

# Every secret the application understands. Values are read lazily so the
# Settings page can update `.env` and have changes take effect without restart.
SECRET_KEYS: dict[str, dict[str, str]] = {
    "FRED_API_KEY": {"label": "FRED (St. Louis Fed)", "group": "Economic data", "url": "https://fred.stlouisfed.org/docs/api/api_key.html"},
    "FINNHUB_API_KEY": {"label": "Finnhub", "group": "Market data", "url": "https://finnhub.io/register"},
    "ALPHA_VANTAGE_API_KEY": {"label": "Alpha Vantage", "group": "Market data", "url": "https://www.alphavantage.co/support/#api-key"},
    "FMP_API_KEY": {"label": "Financial Modeling Prep", "group": "Market data", "url": "https://site.financialmodelingprep.com/developer/docs"},
    "POLYGON_API_KEY": {"label": "Polygon.io", "group": "Market data", "url": "https://polygon.io/dashboard/signup"},
    "COINMARKETCAP_API_KEY": {"label": "CoinMarketCap", "group": "Crypto", "url": "https://coinmarketcap.com/api/"},
    "NEWS_API_KEY": {"label": "NewsAPI.org", "group": "News", "url": "https://newsapi.org/register"},
    "TINYFISH_API_KEY": {"label": "TinyFish Web Agent", "group": "Research agents", "url": "https://agent.tinyfish.ai/api-keys"},
    "ANTHROPIC_API_KEY": {"label": "Anthropic (Claude)", "group": "AI", "url": "https://console.anthropic.com/"},
    "OPENAI_API_KEY": {"label": "OpenAI", "group": "AI", "url": "https://platform.openai.com/api-keys"},
}

NON_SECRET_ENV = {
    "AI_PROVIDER": "auto",          # auto | anthropic | openai | ollama | none
    "AI_MODEL": "",                 # empty = provider default
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "SEC_USER_AGENT": "OmniMarket Research Terminal (local research use) admin@localhost",
    "HOST": "127.0.0.1",
    "PORT": "8000",
    "CORS_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173",
}


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return NON_SECRET_ENV.get(name, default) if default is None else default
    return value.strip()


def has_secret(name: str) -> bool:
    return bool((os.environ.get(name) or "").strip())


def _read_json(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def app_config() -> dict[str, Any]:
    return _read_json("app.json")


@lru_cache(maxsize=None)
def load_config(name: str) -> dict[str, Any]:
    return _read_json(name)


def ttl(kind: str) -> int:
    return int(app_config()["cache_ttl_seconds"].get(kind, 300))


def app_name() -> str:
    return app_config().get("app_name", "OmniMarket Intelligence Terminal")


def update_env_file(updates: dict[str, str | None]) -> None:
    """Persist key updates to `.env` (server side only) and apply to os.environ.

    Values of None/"" remove the key. Existing comments and ordering are kept.
    """
    lines: list[str] = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    remaining = dict(updates)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                val = remaining.pop(key)
                if val:
                    out.append(f"{key}={val}")
                continue
        out.append(line)
    for key, val in remaining.items():
        if val:
            out.append(f"{key}={val}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
    for key, val in updates.items():
        if val:
            os.environ[key] = val
        else:
            os.environ.pop(key, None)
