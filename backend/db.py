"""SQLite persistence with a tiny forward-only migration system."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from backend.config import DATA_DIR

DB_PATH = DATA_DIR / "omnimarket.db"
_lock = threading.RLock()
_db_path_override: Path | None = None

MIGRATIONS: list[str] = [
    # 1 — core schema
    """
    CREATE TABLE IF NOT EXISTS assets (
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, name TEXT, asset_class TEXT, exchange TEXT,
        currency TEXT, country TEXT, sector TEXT, industry TEXT, provider_symbols TEXT, meta TEXT
    );
    CREATE TABLE IF NOT EXISTS cache_entries (
        key TEXT PRIMARY KEY, value TEXT NOT NULL, provider TEXT, source_url TEXT,
        fetched_at REAL NOT NULL, ttl INTEGER NOT NULL, market_time REAL
    );
    CREATE TABLE IF NOT EXISTS quotes (
        asset_id TEXT PRIMARY KEY, price REAL, change REAL, change_pct REAL, payload TEXT,
        provider TEXT, market_time REAL, retrieved_at REAL
    );
    CREATE TABLE IF NOT EXISTS price_history (
        asset_id TEXT, interval TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL,
        PRIMARY KEY (asset_id, interval, ts)
    );
    CREATE TABLE IF NOT EXISTS company_profiles (symbol TEXT PRIMARY KEY, payload TEXT, provider TEXT, retrieved_at REAL);
    CREATE TABLE IF NOT EXISTS financial_statements (symbol TEXT, period TEXT, payload TEXT, provider TEXT, retrieved_at REAL, PRIMARY KEY(symbol, period));
    CREATE TABLE IF NOT EXISTS fundamentals (symbol TEXT PRIMARY KEY, payload TEXT, provider TEXT, retrieved_at REAL);
    CREATE TABLE IF NOT EXISTS news (
        id TEXT PRIMARY KEY, title TEXT, url TEXT, publisher TEXT, published_at REAL, retrieved_at REAL,
        category TEXT, tickers TEXT, summary TEXT, thumbnail TEXT, cluster_id TEXT, source_feed TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at DESC);
    CREATE TABLE IF NOT EXISTS news_clusters (id TEXT PRIMARY KEY, headline TEXT, payload TEXT, score REAL, updated_at REAL);
    CREATE TABLE IF NOT EXISTS economic_indicators (id TEXT PRIMARY KEY, payload TEXT, provider TEXT, retrieved_at REAL);
    CREATE TABLE IF NOT EXISTS watchlists (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, position INTEGER DEFAULT 0, created_at REAL);
    CREATE TABLE IF NOT EXISTS watchlist_items (
        watchlist_id INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE, symbol TEXT NOT NULL,
        added_at REAL, position INTEGER DEFAULT 0, PRIMARY KEY (watchlist_id, symbol)
    );
    CREATE TABLE IF NOT EXISTS portfolio_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, quantity REAL NOT NULL, purchase_price REAL NOT NULL,
        purchase_date TEXT, notes TEXT, created_at REAL
    );
    CREATE TABLE IF NOT EXISTS research_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT, kind TEXT, payload TEXT, created_at REAL);
    CREATE TABLE IF NOT EXISTS filings (symbol TEXT, accession TEXT, form TEXT, filed TEXT, payload TEXT, PRIMARY KEY(symbol, accession));
    CREATE TABLE IF NOT EXISTS refresh_logs (
        id TEXT PRIMARY KEY, scope TEXT, status TEXT, started_at REAL, finished_at REAL, payload TEXT
    );
    CREATE TABLE IF NOT EXISTS provider_status (
        provider TEXT PRIMARY KEY, status TEXT, last_request REAL, last_success REAL, last_failure REAL,
        last_error TEXT, requests INTEGER DEFAULT 0, failures INTEGER DEFAULT 0, quota TEXT
    );
    CREATE TABLE IF NOT EXISTS user_preferences (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS saved_screens (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, payload TEXT, created_at REAL);
    """,
    # 2 — advisor conversation history
    """
    CREATE TABLE IF NOT EXISTS advisor_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, conversation TEXT, role TEXT, content TEXT, meta TEXT, created_at REAL
    );
    """,
]


def set_db_path(path: Path | None) -> None:
    """Used by tests to point at a temporary database."""
    global _db_path_override
    _db_path_override = path


def _path() -> Path:
    return _db_path_override or DB_PATH


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_path(), check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def migrate() -> int:
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        current = row["version"] if row else 0
        if not row:
            conn.execute("INSERT INTO schema_version (version) VALUES (0)")
        for idx, sql in enumerate(MIGRATIONS, start=1):
            if idx > current:
                conn.executescript(sql)
                conn.execute("UPDATE schema_version SET version = ?", (idx,))
                current = idx
        return current


def query(sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
    with db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def execute(sql: str, params: tuple | list = ()) -> int:
    with db() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid or cur.rowcount


def get_pref(key: str, default: Any = None) -> Any:
    rows = query("SELECT value FROM user_preferences WHERE key = ?", (key,))
    if not rows:
        return default
    try:
        return json.loads(rows[0]["value"])
    except (TypeError, ValueError):
        return rows[0]["value"]


def set_pref(key: str, value: Any) -> None:
    execute(
        "INSERT INTO user_preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value)),
    )
