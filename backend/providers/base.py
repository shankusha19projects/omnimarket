"""Provider interfaces. The UI and services depend only on these abstractions,
so any vendor can be swapped in by implementing the relevant class and
registering it in `backend/providers/registry.py`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.models.schemas import Bar, Filing, NewsItem, Quote


class BaseProvider(ABC):
    name: str = "base"
    label: str = "Base"
    requires_key: str | None = None
    homepage: str | None = None

    def configured(self) -> bool:
        from backend.config import has_secret
        return self.requires_key is None or has_secret(self.requires_key)


class MarketDataProvider(BaseProvider):
    """Quotes, history, fundamentals and profiles for listed instruments."""

    @abstractmethod
    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]: ...

    async def get_quote(self, symbol: str) -> Quote | None:
        return (await self.get_quotes([symbol])).get(symbol)

    @abstractmethod
    async def get_history(self, symbol: str, range_: str, interval: str) -> tuple[list[Bar], dict[str, Any]]: ...

    async def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    async def get_company_profile(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    async def get_market_status(self) -> dict[str, Any]:
        raise NotImplementedError


class NewsProvider(BaseProvider):
    @abstractmethod
    async def get_news(self, query: str | None = None, limit: int = 50) -> list[NewsItem]: ...


class EconomicDataProvider(BaseProvider):
    @abstractmethod
    async def get_series(self, series_id: str, start: str | None = None) -> list[tuple[str, float]]: ...


class CryptoProvider(BaseProvider):
    @abstractmethod
    async def get_markets(self, limit: int = 100) -> list[dict[str, Any]]: ...

    async def get_global(self) -> dict[str, Any]:
        return {}


class FilingsProvider(BaseProvider):
    @abstractmethod
    async def get_filings(self, symbol: str, forms: list[str] | None = None, limit: int = 60) -> list[Filing]: ...
