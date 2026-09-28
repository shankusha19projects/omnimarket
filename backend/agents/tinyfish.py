"""TinyFishResearchProvider — adapter for the TinyFish Web Agent REST API.

Endpoints (docs.tinyfish.ai/for-coding-agents):
  Search: GET  https://api.search.tinyfish.ai?query=...     (free, ~30 req/min)
  Fetch:  POST https://api.fetch.tinyfish.ai {"urls": [...]} (free, ≤10 URLs)
  Agent:  POST https://agent.tinyfish.ai/v1/automation/run-sse (metered; goal-based browsing)

Only used when TINYFISH_API_KEY is configured. It never attempts to bypass
paywalls, logins, CAPTCHAs or robots rules; blocked pages are reported as errors.
All calls are rate limited via the shared HTTP layer and results are cached by callers.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from backend.agents.base import Evidence, ResearchResult, WebResearchAgent
from backend.config import env, has_secret
from backend.utils import http
from backend.utils.http import ProviderError

BLOCK_SIGNALS = ("captcha", "access denied", "blocked", "subscribe to continue", "sign in to read")


class TinyFishResearchProvider(WebResearchAgent):
    name = "tinyfish"
    label = "TinyFish Web Agent"

    def available(self) -> bool:
        return has_secret("TINYFISH_API_KEY")

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": env("TINYFISH_API_KEY") or ""}

    async def search(self, query: str, *, news: bool = False, days: int | None = None, limit: int = 8,
                     purpose: str | None = None, include_domains: str | None = None) -> ResearchResult:
        res = ResearchResult(self.name, query)
        params: dict[str, Any] = {"query": query, "location": "US", "language": "en"}
        if news:
            params["domain_type"] = "news"
        if days:
            params["after_date"] = (date.today() - timedelta(days=days)).isoformat()
        if purpose:
            params["purpose"] = purpose[:2000]
        if include_domains:
            params["include_domains"] = include_domains
        try:
            data = await http.get_json("tinyfish", "https://api.search.tinyfish.ai", params=params, headers=self._headers, timeout=15)
        except ProviderError as exc:
            res.errors.append(f"TinyFish search failed: {exc.message}")
            return res
        for r in (data.get("results") or [])[:limit]:
            res.evidence.append(Evidence(
                title=r.get("title") or r.get("url", ""), url=r.get("url", ""), snippet=r.get("snippet"),
                publisher=r.get("publisher") or r.get("site_name"), published=r.get("date"), kind="news" if news else "web",
            ))
        return res

    async def fetch_pages(self, urls: list[str], purpose: str | None = None) -> ResearchResult:
        res = ResearchResult(self.name, ", ".join(urls[:10]))
        body: dict[str, Any] = {"urls": urls[:10], "format": "markdown"}
        if purpose:
            body["purpose"] = purpose[:2000]
        try:
            data = await http.request("tinyfish", "POST", "https://api.fetch.tinyfish.ai", json_body=body, headers=self._headers, timeout=150)
        except ProviderError as exc:
            res.errors.append(f"TinyFish fetch failed: {exc.message}")
            return res
        for page in data.get("results") or []:
            text = page.get("text") or ""
            if isinstance(text, dict):
                text = json.dumps(text)[:4000]
            low = text[:3000].lower()
            if any(s in low for s in BLOCK_SIGNALS):
                res.errors.append(f"{page.get('url')}: page appears access-restricted; skipped (no bypass attempted)")
                continue
            res.evidence.append(Evidence(title=page.get("title") or page.get("url", ""), url=page.get("final_url") or page.get("url", ""),
                                         snippet=text[:1500], published=page.get("published_date"), publisher=page.get("author"), kind="page"))
        for err in data.get("errors") or []:
            res.errors.append(f"{err.get('url')}: {err.get('error')}")
        return res

    async def run_agent(self, url: str, goal: str) -> ResearchResult:
        """Goal-based browsing (metered). Parses the SSE stream for the COMPLETE event."""
        res = ResearchResult(self.name, goal)
        try:
            text = await http.request("tinyfish", "POST", "https://agent.tinyfish.ai/v1/automation/run-sse",
                                      json_body={"url": url, "goal": goal}, headers=self._headers, timeout=180, expect_json=False, retries=0)
        except ProviderError as exc:
            res.errors.append(f"TinyFish agent failed: {exc.message}")
            return res
        result: Any = None
        for line in text.splitlines():
            if not line.startswith("data:"):
                continue
            try:
                evt = json.loads(line[5:].strip())
            except ValueError:
                continue
            if (evt.get("type") or "").upper() == "COMPLETE":
                result = evt.get("result") or evt.get("resultJson") or evt.get("result_json")
        if result is None:
            res.errors.append("TinyFish agent returned no COMPLETE event")
        else:
            flat = json.dumps(result).lower()
            if any(s in flat for s in BLOCK_SIGNALS):
                res.errors.append("Target site blocked automated access; result discarded (no bypass attempted)")
            else:
                res.extracted = result if isinstance(result, dict) else {"result": result}
                res.evidence.append(Evidence(title=f"TinyFish agent run on {url}", url=url, snippet=goal, kind="page"))
        return res

    async def research_company(self, symbol: str, name: str | None = None) -> ResearchResult:
        res = await self.search(f"{name or symbol} {symbol} latest news earnings guidance", news=True, days=30,
                                purpose=f"Collect recent material developments for equity research on {symbol}")
        return res

    async def investigate_market_move(self, asset: str, move_pct: float | None = None) -> ResearchResult:
        direction = "" if move_pct is None else (" up" if move_pct > 0 else " down")
        return await self.search(f"why is {asset}{direction} today", news=True, days=3,
                                 purpose=f"Identify observable drivers of today's price move in {asset}; multiple sources preferred")
