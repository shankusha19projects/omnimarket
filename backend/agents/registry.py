"""Chooses the active research agent. TinyFish when configured; otherwise public sources."""
from __future__ import annotations

from backend.agents.base import WebResearchAgent
from backend.agents.public_sources import PublicSourcesAgent
from backend.agents.tinyfish import TinyFishResearchProvider

tinyfish = TinyFishResearchProvider()
public = PublicSourcesAgent()


def research_agent(prefer_web: bool = True) -> WebResearchAgent:
    if prefer_web and tinyfish.available():
        return tinyfish
    return public


def agents_status() -> list[dict]:
    return [
        {"id": tinyfish.name, "label": tinyfish.label, "available": tinyfish.available(),
         "note": None if tinyfish.available() else "Set TINYFISH_API_KEY (free Search & Fetch) to enable."},
        {"id": public.name, "label": public.label, "available": True, "note": "Always-on fallback."},
    ]
