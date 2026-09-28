"""CoinGecko public API (keyless tier; optional COINGECKO demo key not required)."""
from __future__ import annotations

from typing import Any

from backend.config import load_config
from backend.providers.base import CryptoProvider
from backend.utils import http

BASE = "https://api.coingecko.com/api/v3"


class CoinGeckoProvider(CryptoProvider):
    name = "coingecko"
    label = "CoinGecko"
    homepage = "https://www.coingecko.com/en/api"

    async def get_markets(self, limit: int = 100) -> list[dict[str, Any]]:
        cats = load_config("universe.json")["crypto_categories"]
        data = await http.get_json(self.name, f"{BASE}/coins/markets", params={
            "vs_currency": "usd", "order": "market_cap_desc", "per_page": min(limit, 250), "page": 1,
            "sparkline": "true", "price_change_percentage": "1h,24h,7d,30d,1y",
        })
        out = []
        for c in data:
            spark = ((c.get("sparkline_in_7d") or {}).get("price") or [])
            out.append({
                "id": c["id"], "symbol": (c.get("symbol") or "").upper(), "name": c.get("name"), "image": c.get("image"),
                "price": c.get("current_price"), "market_cap": c.get("market_cap"), "rank": c.get("market_cap_rank"),
                "fdv": c.get("fully_diluted_valuation"), "volume": c.get("total_volume"),
                "high_24h": c.get("high_24h"), "low_24h": c.get("low_24h"),
                "change_1h": c.get("price_change_percentage_1h_in_currency"),
                "change_24h": c.get("price_change_percentage_24h_in_currency") or c.get("price_change_percentage_24h"),
                "change_7d": c.get("price_change_percentage_7d_in_currency"),
                "change_30d": c.get("price_change_percentage_30d_in_currency"),
                "change_1y": c.get("price_change_percentage_1y_in_currency"),
                "circulating_supply": c.get("circulating_supply"), "total_supply": c.get("total_supply"), "max_supply": c.get("max_supply"),
                "ath": c.get("ath"), "ath_change_pct": c.get("ath_change_percentage"), "last_updated": c.get("last_updated"),
                "category": cats.get(c["id"], "Other"), "yahoo": f"{(c.get('symbol') or '').upper()}-USD",
                "spark": [round(p, 8) for p in spark[::4]],
            })
        return out

    async def get_global(self) -> dict[str, Any]:
        data = await http.get_json(self.name, f"{BASE}/global")
        d = data.get("data") or {}
        return {
            "total_market_cap": (d.get("total_market_cap") or {}).get("usd"),
            "total_volume": (d.get("total_volume") or {}).get("usd"),
            "market_cap_change_24h": d.get("market_cap_change_percentage_24h_usd"),
            "dominance": d.get("market_cap_percentage") or {},
            "active_cryptocurrencies": d.get("active_cryptocurrencies"),
            "updated_at": d.get("updated_at"),
        }
