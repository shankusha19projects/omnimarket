"""Fallback research agent built only from keyless public sources:
Yahoo-compatible news search, SEC EDGAR full-text search and cached publisher RSS headlines."""
from __future__ import annotations

import re
import time

from backend.agents.base import Evidence, ResearchResult, WebResearchAgent
from backend import db
from backend.utils.http import ProviderError


class PublicSourcesAgent(WebResearchAgent):
    name = "public"
    label = "Public sources (news search + SEC full-text + RSS)"

    async def search(self, query: str, *, news: bool = False, days: int | None = None, limit: int = 8) -> ResearchResult:
        from backend.providers.registry import sec, yahoo

        res = ResearchResult(self.name, query)
        cutoff = time.time() - (days or 30) * 86400
        clean = re.sub(r"\bsite:\S+", "", query).strip()
        try:
            for n in await yahoo.news_for(clean, count=limit):
                if n.published_at and n.published_at < cutoff:
                    continue
                res.evidence.append(Evidence(title=n.title, url=n.url, publisher=n.publisher,
                                             published=time.strftime("%Y-%m-%d %H:%M", time.gmtime(n.published_at or 0)) + " UTC", kind="news"))
        except ProviderError as exc:
            res.errors.append(f"news search: {exc.message}")
        # Local RSS archive (headline keyword match).
        words = [w for w in re.findall(r"[A-Za-z]{3,}", clean.lower()) if w not in {"the", "and", "why", "today", "stock", "news", "what", "how"}]
        if words:
            like = " OR ".join(["LOWER(title) LIKE ?"] * len(words[:4]))
            rows = db.query(f"SELECT title, url, publisher, published_at FROM news WHERE ({like}) AND published_at > ? ORDER BY published_at DESC LIMIT ?",
                            [f"%{w}%" for w in words[:4]] + [cutoff, limit])
            seen = {e.url for e in res.evidence}
            for r in rows:
                if r["url"] not in seen:
                    res.evidence.append(Evidence(title=r["title"], url=r["url"], publisher=r["publisher"],
                                                 published=time.strftime("%Y-%m-%d %H:%M", time.gmtime(r["published_at"] or 0)) + " UTC", kind="news"))
        if not news:
            try:
                for f in await sec.full_text_search(f'"{clean}"' if " " in clean and len(clean) < 60 else clean, limit=4):
                    if f.get("url"):
                        res.evidence.append(Evidence(title=f"{f['form']} — {f['company']}", url=f["url"], snippet=f.get("description"),
                                                     publisher="SEC EDGAR", published=f.get("filed"), kind="filing"))
            except ProviderError as exc:
                res.errors.append(f"SEC full-text: {exc.message}")
        res.evidence = res.evidence[: limit * 2]
        res.notes.append("TinyFish not configured — using keyless public sources. Add TINYFISH_API_KEY for broader web research.")
        return res
