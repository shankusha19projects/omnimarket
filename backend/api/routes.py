"""HTTP API. FastAPI generates OpenAPI docs at /docs automatically."""
from __future__ import annotations

import csv
import io
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.config import app_config
from backend.models.schemas import (AdvisorRequest, DCFRequest, PositionIn, RefreshRequest, ResearchRequest, SavedScreen,
                                    ScreenRequest, SettingsUpdate, WatchlistCreate, WatchlistItemAdd)
from backend.research import advisor
from backend.research import context as research_ctx
from backend.services import analytics_svc, assets, asset_classes, calendar, macro, market_clock, markets, news, refresh, system, universe, user_state
from backend.services import market_data as md

router = APIRouter(prefix="/api")

RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y", "3y", "5y", "10y", "max"}


def _sym(s: str) -> str:
    if not universe.valid_symbol(s):
        raise HTTPException(400, "Invalid symbol")
    return universe.resolve(s).yahoo


# ---- system -------------------------------------------------------------------------------
@router.get("/health", tags=["system"])
async def health() -> dict[str, Any]:
    return {"ok": True, "app": app_config()["app_name"], "time": time.time(), "us_market": market_clock.us_status()}


@router.get("/settings", tags=["system"])
async def get_settings() -> dict[str, Any]:
    return system.settings()


@router.put("/settings", tags=["system"])
async def put_settings(body: SettingsUpdate) -> dict[str, Any]:
    try:
        return system.update(body.preferences, body.secrets, body.env)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/setup", tags=["system"])
async def setup_status() -> dict[str, Any]:
    return system.first_run()


@router.get("/providers/status", tags=["system"])
async def providers_status() -> dict[str, Any]:
    return {**system.provider_status(), "news_feeds": news.feed_status()}


@router.post("/refresh", tags=["refresh"])
async def start_refresh(body: RefreshRequest) -> dict[str, Any]:
    allowed = {"everything", "markets", "news", "crypto", "economics", "portfolio", "asset"}
    bad = set(body.scopes) - allowed
    if bad:
        raise HTTPException(400, f"Unknown scopes: {sorted(bad)}")
    asset = _sym(body.asset) if body.asset else None
    return refresh.start(body.scopes, asset)


@router.get("/refresh/last", tags=["refresh"])
async def refresh_last() -> dict[str, Any]:
    return {"last": refresh.last(), "history": refresh.history()}


@router.get("/refresh/{job_id}", tags=["refresh"])
async def refresh_status(job_id: str) -> dict[str, Any]:
    job = refresh.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown refresh job")
    return job


@router.get("/clock", tags=["markets"])
async def clock() -> dict[str, Any]:
    return {"sessions": market_clock.all_sessions(), "server_time": time.time()}


# ---- markets ---------------------------------------------------------------------------------
@router.get("/markets/overview", tags=["markets"])
async def overview() -> dict[str, Any]:
    return await markets.overview()


@router.get("/markets/ticker", tags=["markets"])
async def ticker() -> dict[str, Any]:
    return await markets.ticker_strip()


@router.get("/markets/indices", tags=["markets"])
async def indices() -> dict[str, Any]:
    return await markets.indices()


@router.get("/markets/heatmap", tags=["markets"])
async def heatmap(period: str = Query("1d", pattern="^(1d|5d|1m|ytd|1y)$"), group_by: str = Query("sector", pattern="^(sector|industry|cap)$")) -> dict[str, Any]:
    return await markets.heatmap(period, group_by)


@router.get("/markets/breadth", tags=["markets"])
async def breadth() -> dict[str, Any]:
    return await markets.breadth()


@router.get("/markets/volatility", tags=["markets"])
async def volatility() -> dict[str, Any]:
    return await markets.volatility()


@router.get("/markets/sectors", tags=["markets"])
async def sectors() -> dict[str, Any]:
    return await markets.sectors()


@router.get("/markets/themes", tags=["markets"])
async def themes() -> dict[str, Any]:
    return await markets.themes()


@router.get("/markets/movers", tags=["markets"])
async def movers() -> dict[str, Any]:
    stocks = universe.us_stocks()
    qs = await md.quotes([a.yahoo for a in stocks])
    rows = [{"symbol": a.yahoo, "name": a.name, "sector": a.sector, "price": qs[a.yahoo].get("price"), "change_pct": qs[a.yahoo].get("change_pct"),
             "volume": qs[a.yahoo].get("volume"), "avg_volume": qs[a.yahoo].get("avg_volume"), "market_cap": qs[a.yahoo].get("market_cap")}
            for a in stocks if qs[a.yahoo].get("change_pct") is not None]
    rows.sort(key=lambda r: r["change_pct"], reverse=True)
    active = sorted(rows, key=lambda r: -((r["volume"] or 0) / (r["avg_volume"] or 1)))
    return {"gainers": rows[:8], "losers": rows[-8:][::-1], "unusual_volume": active[:8]}


# ---- assets --------------------------------------------------------------------------------------
@router.get("/assets/search", tags=["assets"])
async def search(q: str = Query(..., min_length=1, max_length=60)) -> dict[str, Any]:
    return await assets.search(q)


@router.get("/assets/{symbol}", tags=["assets"])
async def asset_detail(symbol: str) -> dict[str, Any]:
    return await assets.detail(_sym(symbol))


@router.get("/assets/{symbol}/quote", tags=["assets"])
async def asset_quote(symbol: str) -> dict[str, Any]:
    return await md.quote(_sym(symbol))


@router.get("/assets/{symbol}/history", tags=["assets"])
async def asset_history(symbol: str, range: str = Query("1y"), interval: str | None = Query(None, pattern="^(1m|2m|5m|15m|30m|60m|1h|1d|1wk|1mo)$")) -> dict[str, Any]:
    if range not in RANGES:
        raise HTTPException(400, "Invalid range")
    return await assets.history_with_indicators(_sym(symbol), range, interval)


@router.get("/assets/{symbol}/technicals", tags=["assets"])
async def asset_technicals(symbol: str) -> dict[str, Any]:
    return await assets.technical_snapshot(_sym(symbol))


@router.get("/assets/{symbol}/fundamentals", tags=["assets"])
async def asset_fundamentals(symbol: str) -> dict[str, Any]:
    return await assets.fundamentals(_sym(symbol))


@router.get("/assets/{symbol}/statements", tags=["assets"])
async def asset_statements(symbol: str) -> dict[str, Any]:
    return await assets.statements(_sym(symbol))


@router.get("/assets/{symbol}/profile", tags=["assets"])
async def asset_profile(symbol: str) -> dict[str, Any]:
    return await assets.profile(_sym(symbol))


@router.get("/assets/{symbol}/filings", tags=["assets"])
async def asset_filings(symbol: str) -> dict[str, Any]:
    return await assets.filings(_sym(symbol))


@router.post("/assets/{symbol}/filings/summarize", tags=["assets"])
async def summarize_filing(symbol: str, body: dict[str, str]) -> dict[str, Any]:
    try:
        return await advisor.summarize_filing(body.get("url", ""), body.get("form", ""), body.get("company", symbol))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/assets/{symbol}/news", tags=["assets"])
async def asset_news(symbol: str) -> dict[str, Any]:
    return await assets.asset_news(_sym(symbol))


@router.get("/assets/{symbol}/timeline", tags=["assets"])
async def asset_timeline(symbol: str) -> dict[str, Any]:
    return await assets.timeline(_sym(symbol))


@router.get("/assets/{symbol}/analysis", tags=["assets"])
async def asset_analysis(symbol: str) -> dict[str, Any]:
    return await research_ctx.analysis_report(_sym(symbol))


@router.get("/assets/{symbol}/valuation", tags=["assets"])
async def asset_valuation(symbol: str) -> dict[str, Any]:
    s = _sym(symbol)
    d = await assets.dcf_defaults(s)
    if not d.get("available"):
        return d
    return await assets.run_dcf(DCFRequest(symbol=s))


@router.post("/valuation/dcf", tags=["assets"])
async def dcf(body: DCFRequest) -> dict[str, Any]:
    body.symbol = _sym(body.symbol)
    return await assets.run_dcf(body)


@router.get("/assets/{symbol}/comparables", tags=["assets"])
async def asset_comps(symbol: str) -> dict[str, Any]:
    return await assets.comparables(_sym(symbol))


@router.get("/assets/{symbol}/curve", tags=["assets"])
async def asset_curve(symbol: str) -> dict[str, Any]:
    return await asset_classes.futures_curve(_sym(symbol))


@router.get("/compare", tags=["analytics"])
async def compare(symbols: str = Query(..., description="Comma-separated, up to 5"), range: str = "1y") -> dict[str, Any]:
    syms = [_sym(s) for s in symbols.split(",") if s.strip()][:5]
    if range not in RANGES:
        raise HTTPException(400, "Invalid range")
    return await assets.compare(syms, range)


@router.get("/correlation", tags=["analytics"])
async def correlation(symbols: str, range: str = "1y", window: int | None = Query(None, ge=20, le=500)) -> dict[str, Any]:
    return await analytics_svc.correlations([_sym(s) for s in symbols.split(",") if s.strip()], range, window)


@router.get("/correlation/pair", tags=["analytics"])
async def correlation_pair(a: str, b: str, range: str = "2y", window: int = Query(60, ge=20, le=250)) -> dict[str, Any]:
    return await analytics_svc.pair(_sym(a), _sym(b), range, window)


@router.get("/correlation/presets", tags=["analytics"])
async def correlation_presets() -> dict[str, Any]:
    return await analytics_svc.presets()


@router.get("/risk", tags=["analytics"])
async def risk() -> dict[str, Any]:
    return await analytics_svc.risk_dashboard()


# ---- asset classes & macro ---------------------------------------------------------------------
@router.get("/crypto", tags=["markets"])
async def crypto() -> dict[str, Any]:
    return await asset_classes.crypto()


@router.get("/commodities", tags=["markets"])
async def commodities() -> dict[str, Any]:
    return await asset_classes.commodities()


@router.get("/forex", tags=["markets"])
async def forex() -> dict[str, Any]:
    return await asset_classes.forex()


@router.get("/etfs", tags=["markets"])
async def etfs() -> dict[str, Any]:
    return await asset_classes.etfs()


@router.get("/rare-earths", tags=["markets"])
async def rare_earths() -> dict[str, Any]:
    return await asset_classes.rare_earths()


@router.get("/bonds", tags=["macro"])
async def bonds() -> dict[str, Any]:
    return await macro.bonds()


@router.get("/central-banks", tags=["macro"])
async def central_banks() -> dict[str, Any]:
    return await macro.central_banks()


@router.get("/economics", tags=["macro"])
async def economics() -> dict[str, Any]:
    return await macro.economics()


@router.get("/real-estate", tags=["macro"])
async def real_estate() -> dict[str, Any]:
    return await macro.real_estate()


# ---- news & calendars ----------------------------------------------------------------------------
@router.get("/news", tags=["news"])
async def get_news(category: str | None = None, q: str | None = Query(None, max_length=60), limit: int = Query(120, le=400)) -> dict[str, Any]:
    return await news.news(category, q, limit)


@router.get("/news/clusters", tags=["news"])
async def news_clusters(hours: float = Query(48, le=168)) -> dict[str, Any]:
    return await news.clusters(hours)


@router.get("/news/market-moving", tags=["news"])
async def market_moving() -> dict[str, Any]:
    return await news.market_moving()


@router.get("/calendar/earnings", tags=["calendar"])
async def earnings(which: str = Query("this_week", pattern="^(today|tomorrow|this_week|next_week)$"), min_cap: float = 0) -> dict[str, Any]:
    return await calendar.earnings(which, min_cap)


@router.get("/calendar/economic", tags=["calendar"])
async def economic_calendar(which: str = Query("this_week", pattern="^(today|tomorrow|this_week|next_week)$"), min_importance: int = Query(1, ge=1, le=3)) -> dict[str, Any]:
    return await calendar.economic(which, min_importance)


# ---- watchlists ------------------------------------------------------------------------------------
@router.get("/watchlists", tags=["watchlists"])
async def watchlists() -> list[dict[str, Any]]:
    return user_state.list_watchlists()


@router.post("/watchlists", tags=["watchlists"])
async def create_watchlist(body: WatchlistCreate) -> dict[str, Any]:
    try:
        return user_state.create_watchlist(body.name)
    except Exception as exc:
        raise HTTPException(400, "A watchlist with that name already exists") from exc


@router.get("/watchlists/{wid}", tags=["watchlists"])
async def watchlist(wid: int) -> dict[str, Any]:
    try:
        return await user_state.watchlist_quotes(wid)
    except KeyError as exc:
        raise HTTPException(404, "Watchlist not found") from exc


@router.put("/watchlists/{wid}", tags=["watchlists"])
async def rename_watchlist(wid: int, body: WatchlistCreate) -> dict[str, Any]:
    user_state.rename_watchlist(wid, body.name)
    return {"ok": True}


@router.delete("/watchlists/{wid}", tags=["watchlists"])
async def delete_watchlist(wid: int) -> dict[str, Any]:
    user_state.delete_watchlist(wid)
    return {"ok": True}


@router.post("/watchlists/{wid}/items", tags=["watchlists"])
async def add_watch_item(wid: int, body: WatchlistItemAdd) -> dict[str, Any]:
    user_state.add_item(wid, _sym(body.symbol))
    return {"ok": True}


@router.delete("/watchlists/{wid}/items/{symbol}", tags=["watchlists"])
async def remove_watch_item(wid: int, symbol: str) -> dict[str, Any]:
    user_state.remove_item(wid, symbol)
    return {"ok": True}


@router.put("/watchlists/{wid}/order", tags=["watchlists"])
async def reorder_watchlist(wid: int, body: list[str]) -> dict[str, Any]:
    user_state.reorder(wid, body)
    return {"ok": True}


# ---- portfolio -----------------------------------------------------------------------------------------
@router.get("/portfolio", tags=["portfolio"])
async def portfolio() -> dict[str, Any]:
    return await user_state.portfolio()


@router.post("/portfolio/positions", tags=["portfolio"])
async def add_position(body: PositionIn) -> dict[str, Any]:
    body.symbol = _sym(body.symbol)
    return {"id": user_state.add_position(body)}


@router.put("/portfolio/positions/{pid}", tags=["portfolio"])
async def update_position(pid: int, body: PositionIn) -> dict[str, Any]:
    body.symbol = _sym(body.symbol)
    user_state.update_position(pid, body)
    return {"ok": True}


@router.delete("/portfolio/positions/{pid}", tags=["portfolio"])
async def delete_position(pid: int) -> dict[str, Any]:
    user_state.delete_position(pid)
    return {"ok": True}


# ---- screener -----------------------------------------------------------------------------------------
@router.post("/screener", tags=["screener"])
async def screen(body: ScreenRequest) -> dict[str, Any]:
    return await user_state.run_screen(body)


@router.post("/screener/export", tags=["screener"])
async def screen_export(body: ScreenRequest) -> StreamingResponse:
    res = await user_state.run_screen(body)
    buf = io.StringIO()
    rows = res["rows"]
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=screen_{time.strftime('%Y%m%d_%H%M')}.csv"})


@router.post("/screener/fundamentals", tags=["screener"])
async def screen_load_fundamentals(universe_name: str = Query("all", alias="universe")) -> dict[str, Any]:
    rows = await user_state.screener_universe(universe_name)
    n = await user_state.enrich_fundamentals([r["symbol"] for r in rows])
    return {"loaded": n, "total": len(rows)}


@router.get("/screener/saved", tags=["screener"])
async def saved_screens() -> list[dict[str, Any]]:
    return user_state.list_screens()


@router.post("/screener/saved", tags=["screener"])
async def save_screen(body: SavedScreen) -> dict[str, Any]:
    user_state.save_screen(body.name, body.request)
    return {"ok": True}


@router.delete("/screener/saved/{sid}", tags=["screener"])
async def delete_saved_screen(sid: int) -> dict[str, Any]:
    user_state.delete_screen(sid)
    return {"ok": True}


# ---- research & advisor ------------------------------------------------------------------------------
@router.post("/research", tags=["research"])
async def research(body: ResearchRequest) -> dict[str, Any]:
    return await advisor.research(body.query, body.use_web_agent, body.synthesize)


@router.get("/research/recent", tags=["research"])
async def research_recent() -> list[dict[str, Any]]:
    return advisor.recent_research()


@router.post("/advisor/chat", tags=["advisor"])
async def advisor_chat(body: AdvisorRequest) -> dict[str, Any]:
    return await advisor.chat(body.message, [m.model_dump() for m in body.history], body.conversation, body.use_web_research)


@router.get("/advisor/conversations", tags=["advisor"])
async def advisor_conversations() -> list[dict[str, Any]]:
    return advisor.conversations()


@router.get("/advisor/conversations/{conv}", tags=["advisor"])
async def advisor_conversation(conv: str) -> list[dict[str, Any]]:
    return advisor.conversation(conv)


@router.get("/universe", tags=["system"])
async def get_universe() -> dict[str, Any]:
    return {"assets": [a.model_dump() for a in universe.all_assets()]}
