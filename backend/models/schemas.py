"""Canonical data models. Every provider normalizes into these shapes."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

AssetClass = Literal["equity", "etf", "index", "commodity", "fx", "crypto", "rate", "fund", "future", "other"]


class Provenance(BaseModel):
    provider: str
    source_url: Optional[str] = None
    retrieved_at: Optional[float] = None
    market_time: Optional[float] = None
    cache_status: str = "live"
    delay: Optional[str] = None
    age_seconds: Optional[float] = None
    ttl_seconds: Optional[int] = None
    error: Optional[str] = None


class Asset(BaseModel):
    """Canonical asset, e.g. {"id": "equity:US:AAPL", "symbol": "AAPL", ...}."""
    id: str
    symbol: str
    name: str
    asset_class: AssetClass
    exchange: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    group: Optional[str] = None
    unit: Optional[str] = None
    provider_symbols: dict[str, str] = Field(default_factory=dict)

    @property
    def yahoo(self) -> str:
        return self.provider_symbols.get("yahoo", self.symbol)


class Quote(BaseModel):
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    prev_close: Optional[float] = None
    open: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    year_high: Optional[float] = None
    year_low: Optional[float] = None
    volume: Optional[float] = None
    avg_volume: Optional[float] = None
    market_cap: Optional[float] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    market_state: Optional[str] = None
    pre_price: Optional[float] = None
    pre_change_pct: Optional[float] = None
    post_price: Optional[float] = None
    post_change_pct: Optional[float] = None
    market_time: Optional[float] = None
    quote_type: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class Bar(BaseModel):
    t: int
    o: Optional[float] = None
    h: Optional[float] = None
    l: Optional[float] = None
    c: Optional[float] = None
    v: Optional[float] = None


class NewsItem(BaseModel):
    id: str
    title: str
    url: str
    publisher: str
    published_at: Optional[float] = None
    retrieved_at: Optional[float] = None
    category: Optional[str] = None
    tickers: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    thumbnail: Optional[str] = None
    source_feed: Optional[str] = None


class Filing(BaseModel):
    form: str
    filed: str
    report_date: Optional[str] = None
    accession: str
    description: Optional[str] = None
    url: str
    index_url: Optional[str] = None


# ---- API request bodies ----

class RefreshRequest(BaseModel):
    scopes: list[str] = Field(default_factory=lambda: ["everything"])
    asset: Optional[str] = None


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class WatchlistItemAdd(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)


class PositionIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)
    quantity: float
    purchase_price: float = Field(ge=0)
    purchase_date: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class ScreenFilter(BaseModel):
    field: str
    op: Literal["gt", "gte", "lt", "lte", "between", "eq", "in", "contains"]
    value: Any = None
    value2: Any = None


class ScreenRequest(BaseModel):
    filters: list[ScreenFilter] = Field(default_factory=list)
    sort: Optional[str] = "market_cap"
    desc: bool = True
    universe: str = "all"
    limit: int = 500


class SavedScreen(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    request: ScreenRequest


class DCFRequest(BaseModel):
    symbol: str
    # Any field left as None falls back to the SEC-derived default for the company.
    revenue: Optional[float] = None
    revenue_growth: Optional[float] = Field(default=None, ge=-0.5, le=2.0)
    growth_years: Optional[int] = Field(default=None, ge=1, le=15)
    terminal_growth: Optional[float] = Field(default=None, ge=-0.02, le=0.06)
    operating_margin: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    tax_rate: Optional[float] = Field(default=None, ge=0, le=0.6)
    reinvestment_rate: Optional[float] = Field(default=None, ge=-0.5, le=1.0)
    wacc: Optional[float] = Field(default=None, ge=0.02, le=0.3)
    shares: Optional[float] = None
    net_debt: Optional[float] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=20000)


class AdvisorRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)
    conversation: Optional[str] = None
    use_web_research: bool = False


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    use_web_agent: bool = True
    synthesize: bool = True


class SettingsUpdate(BaseModel):
    preferences: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Optional[str]] = Field(default_factory=dict)
    env: dict[str, Optional[str]] = Field(default_factory=dict)
