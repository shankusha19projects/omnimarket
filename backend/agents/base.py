"""Web research agent interface.

Agents are optional and isolated: services call `agents.registry.research_agent()`,
which returns TinyFish when configured and a public-sources fallback otherwise.
Every result carries source URLs and retrieval timestamps.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Evidence:
    title: str
    url: str
    snippet: str | None = None
    publisher: str | None = None
    published: str | None = None
    retrieved_at: float = field(default_factory=time.time)
    kind: str = "web"  # web | news | filing | page | dataset

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchResult:
    agent: str
    query: str
    evidence: list[Evidence] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    extracted: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"agent": self.agent, "query": self.query, "evidence": [e.to_dict() for e in self.evidence],
                "notes": self.notes, "errors": self.errors, "extracted": self.extracted}


class WebResearchAgent(ABC):
    name = "base"
    label = "Base agent"

    def available(self) -> bool:
        return True

    @abstractmethod
    async def search(self, query: str, *, news: bool = False, days: int | None = None, limit: int = 8) -> ResearchResult: ...

    async def fetch_pages(self, urls: list[str], purpose: str | None = None) -> ResearchResult:
        return ResearchResult(self.name, ", ".join(urls), notes=["page fetch not supported by this agent"])

    async def research_company(self, symbol: str, name: str | None = None) -> ResearchResult:
        return await self.search(f"{name or symbol} ({symbol}) stock news", news=True, days=30)

    async def research_sector(self, sector: str) -> ResearchResult:
        return await self.search(f"{sector} industry outlook demand supply pricing", news=True, days=30)

    async def collect_recent_news(self, topic: str, days: int = 7) -> ResearchResult:
        return await self.search(topic, news=True, days=days)

    async def research_macro_event(self, event: str) -> ResearchResult:
        return await self.search(f"{event} economy markets", news=True, days=14)

    async def investigate_market_move(self, asset: str, move_pct: float | None = None) -> ResearchResult:
        direction = "" if move_pct is None else ("rally " if move_pct > 0 else "decline ")
        return await self.search(f"why {asset} {direction}today", news=True, days=3)

    async def gather_public_filings(self, company: str) -> ResearchResult:
        return await self.search(f"{company} SEC filing 8-K 10-Q site:sec.gov", limit=6)
