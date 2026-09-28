"""Loads config/universe.json into canonical Asset objects and resolves symbols."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

from backend.config import load_config
from backend.models.schemas import Asset

_SAFE_SYMBOL = re.compile(r"^[A-Za-z0-9\^\.\-=_:/ ]{1,40}$")


def valid_symbol(s: str) -> bool:
    return bool(_SAFE_SYMBOL.match(s or ""))


def classify_yahoo_symbol(sym: str) -> str:
    if sym.startswith("^"):
        return "index"
    if sym.endswith("=F"):
        return "commodity"
    if sym.endswith("=X") or sym == "DX-Y.NYB":
        return "fx"
    if sym.endswith("-USD"):
        return "crypto"
    return "equity"


def make_id(asset_class: str, symbol: str, country: str | None = None) -> str:
    if asset_class in ("equity", "etf", "index"):
        return f"{asset_class}:{country or 'US'}:{symbol}"
    return f"{asset_class}:{symbol}"


@lru_cache(maxsize=1)
def catalog() -> dict[str, Asset]:
    u = load_config("universe.json")
    out: dict[str, Asset] = {}

    def add(a: Asset) -> None:
        out.setdefault(a.provider_symbols.get("yahoo", a.symbol), a)

    for sym, name, country, region, ccy in u["indices"]:
        add(Asset(id=make_id("index", sym, country), symbol=sym, name=name, asset_class="index", country=country,
                  currency=ccy, group=region, provider_symbols={"yahoo": sym}))
    for group, rows in u["commodities"].items():
        for sym, name, unit in rows:
            add(Asset(id=make_id("commodity", sym), symbol=sym, name=name, asset_class="commodity", currency="USD",
                      group=group, unit=unit, provider_symbols={"yahoo": sym}))
    for sym, name, base, quote in u["forex"]:
        add(Asset(id=make_id("fx", sym.replace("=X", "")), symbol=sym, name=name, asset_class="fx",
                  currency=quote if quote != "Basket" else "USD", group="Forex", provider_symbols={"yahoo": sym}))
    for sym, name in u["rates_yahoo"]:
        add(Asset(id=make_id("rate", sym), symbol=sym, name=name, asset_class="rate", country="US", currency="%",
                  group="US Treasury", provider_symbols={"yahoo": sym}))
    for group, rows in u["etfs"].items():
        for sym, name in rows:
            add(Asset(id=make_id("etf", sym), symbol=sym, name=name, asset_class="etf", country="US", currency="USD",
                      group=group, provider_symbols={"yahoo": sym}))
    for sym, name, sector, industry in u["stocks"]:
        add(Asset(id=make_id("equity", sym), symbol=sym, name=name, asset_class="equity", country="US", currency="USD",
                  sector=sector, industry=industry, group="US Large Cap", provider_symbols={"yahoo": sym}))
    for sym, name, country, sector in u["international_equities"]:
        add(Asset(id=make_id("equity", sym, country), symbol=sym, name=name, asset_class="equity", country=country,
                  sector=sector, group="International", provider_symbols={"yahoo": sym}))
    for sym, name, segment in u["reits"]:
        add(Asset(id=make_id("equity", sym), symbol=sym, name=name, asset_class="equity", country="US", currency="USD",
                  sector="Real Estate", industry=f"{segment} REIT", group="REIT", provider_symbols={"yahoo": sym}))
    for sym, name, country, minerals, segment in u["rare_earths"]["companies"]:
        add(Asset(id=make_id("equity", sym, country), symbol=sym, name=name, asset_class="equity", country=country,
                  sector="Materials", industry=segment, group="Critical Minerals", provider_symbols={"yahoo": sym}))
    for sym, name in u["rare_earths"]["etfs"]:
        add(Asset(id=make_id("etf", sym), symbol=sym, name=name, asset_class="etf", country="US", currency="USD",
                  group="Thematic", provider_symbols={"yahoo": sym}))
    for sym, name in (("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum"), ("SOL-USD", "Solana")):
        add(Asset(id=make_id("crypto", sym.split("-")[0].lower()), symbol=sym, name=name, asset_class="crypto",
                  currency="USD", group="Crypto", provider_symbols={"yahoo": sym}))
    themes = load_config("themes.json")["themes"]
    for t in themes:
        for sym in t["symbols"]:
            if sym not in out:
                add(Asset(id=make_id("equity", sym), symbol=sym, name=sym, asset_class="equity", group=f"Theme: {t['name']}",
                          provider_symbols={"yahoo": sym}))
    return out


def all_assets() -> list[Asset]:
    return list(catalog().values())


def by_class(asset_class: str) -> list[Asset]:
    return [a for a in catalog().values() if a.asset_class == asset_class]


def us_stocks() -> list[Asset]:
    u = load_config("universe.json")
    cat = catalog()
    return [cat[s[0]] for s in u["stocks"] if s[0] in cat]


def resolve(ident: str) -> Asset:
    """Resolve a canonical id or provider symbol into an Asset (synthesizing unknown ones)."""
    ident = ident.strip()
    cat = catalog()
    if ident in cat:
        return cat[ident]
    up = ident.upper()
    if up in cat:
        return cat[up]
    for a in cat.values():
        if a.id == ident:
            return a
    if ":" in ident:
        parts = ident.split(":")
        cls, sym = parts[0], parts[-1]
        if cls == "crypto" and not sym.upper().endswith("-USD"):
            sym = f"{sym.upper()}-USD"
        if cls == "fx" and not sym.endswith("=X"):
            sym = f"{sym}=X"
        return Asset(id=ident, symbol=sym, name=sym, asset_class=cls if cls in ("equity", "etf", "index", "commodity", "fx", "crypto", "rate") else "other",
                     provider_symbols={"yahoo": sym})
    cls = classify_yahoo_symbol(up)
    return Asset(id=make_id(cls, up), symbol=up, name=up, asset_class=cls, provider_symbols={"yahoo": up})


def symbols(assets: Iterable[Asset]) -> list[str]:
    return [a.yahoo for a in assets]
