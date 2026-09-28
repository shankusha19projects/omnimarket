"""Caching, normalization, SEC statement building, refresh assessment and API endpoint tests."""
import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from backend.cache import store
from backend.cache.store import Fetched
from backend.providers.sec import SECProvider
from backend.services import refresh, universe
from backend.utils.http import ProviderError


# ---- caching ------------------------------------------------------------------------------
def test_cache_fresh_then_stale_on_failure():
    calls = {"n": 0}

    async def ok() -> Fetched:
        calls["n"] += 1
        return Fetched({"v": calls["n"]}, "test", "https://example.com")

    async def boom() -> Fetched:
        raise ProviderError("test", "down")

    async def run():
        a = await store.cached("k", 60, ok)
        b = await store.cached("k", 60, ok)
        assert a.status == "live" and b.status == "cache" and calls["n"] == 1
        c = await store.cached("k", 60, boom, force=True)  # forced refetch fails → last good value, labeled stale
        assert c.status == "stale" and c.value == {"v": 1} and c.error == "down"
        with pytest.raises(ProviderError):
            await store.cached("missing", 60, boom)

    asyncio.run(run())


def test_cache_stale_while_revalidate():
    async def run():
        async def v1() -> Fetched:
            return Fetched(1, "t")

        async def v2() -> Fetched:
            return Fetched(2, "t")

        await store.cached("swr", 1, v1)
        store._memory["swr"].fetched_at -= 5  # expired but inside SWR window
        c = await store.cached("swr", 1, v2)
        assert c.status == "revalidating" and c.value == 1
        await asyncio.sleep(0.05)  # background refresh completes
        assert store.peek("swr").value == 2

    asyncio.run(run())


def test_bulk_cache_partial_results():
    async def fetch_many(keys):
        return {k: {"p": 1} for k in keys if k != "BAD"}

    async def run():
        got, err = await store.bulk_cached("q", ["A", "B", "BAD"], 60, fetch_many, "t")
        assert set(got) == {"A", "B"} and err is None
        got2, _ = await store.bulk_cached("q", ["A"], 60, fetch_many, "t")
        assert got2["A"].status == "cache"

    asyncio.run(run())


def test_provenance_fields():
    c = store.Cached({"x": 1}, "yahoo", "https://x", time.time(), 30, None, "live")
    p = c.provenance()
    for k in ("provider", "source_url", "retrieved_at", "cache_status", "age_seconds", "ttl_seconds"):
        assert k in p


# ---- normalization ---------------------------------------------------------------------------
def test_canonical_ids_and_resolution():
    assert universe.resolve("AAPL").id == "equity:US:AAPL"
    assert universe.resolve("^GSPC").asset_class == "index"
    assert universe.resolve("GC=F").asset_class == "commodity"
    assert universe.resolve("EURUSD=X").id == "fx:EURUSD"
    assert universe.resolve("crypto:doge").yahoo == "DOGE-USD"
    unknown = universe.resolve("zzzz")
    assert unknown.symbol == "ZZZZ" and unknown.asset_class == "equity"
    assert not universe.valid_symbol("AAPL; DROP TABLE")


# ---- SEC XBRL normalization ------------------------------------------------------------------------
def _fact(start, end, val, form="10-K", fy=2025, fp="FY", filed="2026-02-01"):
    return {"start": start, "end": end, "val": val, "form": form, "fy": fy, "fp": fp, "filed": filed}


def test_sec_statements_annual_quarterly_q4_and_ttm():
    rev = [
        _fact("2025-01-01", "2025-12-31", 400.0),
        _fact("2024-01-01", "2024-12-31", 300.0, fy=2024, filed="2025-02-01"),
        _fact("2025-01-01", "2025-03-31", 90.0, form="10-Q", fp="Q1"),
        _fact("2025-04-01", "2025-06-30", 100.0, form="10-Q", fp="Q2"),
        _fact("2025-07-01", "2025-09-30", 105.0, form="10-Q", fp="Q3"),
    ]
    ni = [_fact("2025-01-01", "2025-12-31", 40.0), _fact("2025-01-01", "2025-03-31", 9.0, form="10-Q"),
          _fact("2025-04-01", "2025-06-30", 10.0, form="10-Q"), _fact("2025-07-01", "2025-09-30", 11.0, form="10-Q")]
    cash = [{"end": "2025-12-31", "val": 50.0, "form": "10-K", "fp": "FY", "filed": "2026-02-01"}]
    facts = {"entityName": "TestCo", "facts": {"us-gaap": {
        "Revenues": {"units": {"USD": rev}}, "NetIncomeLoss": {"units": {"USD": ni}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": cash}}}, "dei": {}}}
    st = SECProvider.build_statements(facts)
    assert st["annual"][0]["revenue"] == 400.0 and st["annual"][0]["cash"] == 50.0
    q = {r["period_end"]: r for r in st["quarterly"]}
    assert q["2025-12-31"]["revenue"] == pytest.approx(105.0)  # derived Q4 = 400 − (90+100+105)
    assert q["2025-12-31"]["net_income"] == pytest.approx(10.0)
    assert st["ttm"]["revenue"] == pytest.approx(400.0)


# ---- refresh assessment ------------------------------------------------------------------------------
def test_refresh_assess_statuses():
    assert refresh._assess({"rows": [{"provenance": {"provider": "yahoo", "cache_status": "live"}}]})[0] == "ok"
    st, msg, _ = refresh._assess({"rows": [{"provenance": {"provider": "yahoo", "cache_status": "stale", "error": "HTTP 500"}}]})
    assert st == "stale" and "HTTP 500" in msg
    assert refresh._assess({"feeds_ok": 3, "feeds_failed": 1})[0] == "partial"
    assert refresh._assess({"error": "boom"})[0] == "failed"


# ---- API endpoints (offline) ---------------------------------------------------------------------------
@pytest.fixture
def client(monkeypatch):
    from backend import main
    from backend.services import market_data as md

    async def fake_quotes(symbols, force=False):
        return {s: {"symbol": s, "name": s, "price": 100.0, "change": 1.0, "change_pct": 1.0, "provenance": {"provider": "fake", "cache_status": "live"}} for s in symbols}

    monkeypatch.setattr(md, "quotes", fake_quotes)
    with TestClient(main.app) as c:
        yield c


def test_api_health_settings_openapi(client):
    assert client.get("/api/health").json()["ok"] is True
    s = client.get("/api/settings").json()
    assert all("configured" in x and "value" not in x for x in s["secrets"])  # secrets never exposed
    assert client.get("/openapi.json").status_code == 200


def test_api_rejects_bad_input(client):
    assert client.get("/api/assets/AAPL;rm/quote").status_code in (400, 404)
    assert client.put("/api/settings", json={"secrets": {"NOT_A_KEY": "x"}}).status_code == 400
    assert client.post("/api/refresh", json={"scopes": ["nope"]}).status_code == 400


def test_api_watchlist_crud(client):
    lists = client.get("/api/watchlists").json()
    assert len(lists) >= 1  # defaults seeded
    wid = client.post("/api/watchlists", json={"name": "Test list"}).json()["id"]
    assert client.post(f"/api/watchlists/{wid}/items", json={"symbol": "MSFT"}).status_code == 200
    d = client.get(f"/api/watchlists/{wid}").json()
    assert d["rows"][0]["symbol"] == "MSFT" and d["rows"][0]["price"] == 100.0
    client.delete(f"/api/watchlists/{wid}/items/MSFT")
    assert client.get(f"/api/watchlists/{wid}").json()["rows"] == []
    client.delete(f"/api/watchlists/{wid}")


def test_api_portfolio_math(client):
    client.post("/api/portfolio/positions", json={"symbol": "AAPL", "quantity": 10, "purchase_price": 80})
    client.post("/api/portfolio/positions", json={"symbol": "MSFT", "quantity": 30, "purchase_price": 100})
    p = client.get("/api/portfolio").json()
    t = p["totals"]
    assert t["market_value"] == pytest.approx(4000) and t["cost_basis"] == pytest.approx(3800)
    assert t["unrealized_pl"] == pytest.approx(200)
    w = {r["symbol"]: r["weight"] for r in p["positions"]}
    assert w["MSFT"] == pytest.approx(75)
    assert p["concentration"]["hhi"] == pytest.approx(0.25 ** 2 + 0.75 ** 2)


@pytest.mark.network
def test_live_quote_provider():
    from backend.providers.yahoo import YahooProvider

    q = asyncio.run(YahooProvider().get_quotes(["AAPL", "^GSPC"]))
    assert q["AAPL"].price and q["^GSPC"].price
