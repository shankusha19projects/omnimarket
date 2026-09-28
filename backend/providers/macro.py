"""Official macro / rates sources: US Treasury, FRED, BLS, World Bank, central banks."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any

from backend.config import env, has_secret
from backend.providers.base import EconomicDataProvider
from backend.utils import http
from backend.utils.http import ProviderError

TREASURY_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all"
                "?type={kind}&field_tdr_date_value={year}&page&_format=csv")
TENOR_MAP = {"1 Mo": "1M", "1.5 Month": "6W", "2 Mo": "2M", "3 Mo": "3M", "4 Mo": "4M", "6 Mo": "6M", "1 Yr": "1Y", "2 Yr": "2Y",
             "3 Yr": "3Y", "5 Yr": "5Y", "7 Yr": "7Y", "10 Yr": "10Y", "20 Yr": "20Y", "30 Yr": "30Y"}
TENOR_YEARS = {"1M": 1 / 12, "6W": 1.5 / 12, "2M": 2 / 12, "3M": 0.25, "4M": 4 / 12, "6M": 0.5, "1Y": 1, "2Y": 2, "3Y": 3, "5Y": 5,
               "7Y": 7, "10Y": 10, "20Y": 20, "30Y": 30}


class TreasuryProvider:
    name = "treasury"
    label = "U.S. Treasury (daily par yield curve)"
    homepage = "https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics"

    async def curve_year(self, year: int, real: bool = False) -> list[dict[str, Any]]:
        kind = "daily_treasury_real_yield_curve" if real else "daily_treasury_yield_curve"
        text = await http.get_text(self.name, TREASURY_URL.format(year=year, kind=kind), timeout=30)
        rows = list(csv.DictReader(io.StringIO(text)))
        out = []
        for r in rows:
            try:
                d = datetime.strptime(r["Date"], "%m/%d/%Y").date().isoformat()
            except (KeyError, ValueError):
                continue
            pts = {}
            for k, v in r.items():
                if k == "Date" or v in ("", None):
                    continue
                label = TENOR_MAP.get(k.strip(), k.strip().replace(" YR", "Y").replace(" Yr", "Y"))
                try:
                    pts[label] = float(v)
                except ValueError:
                    pass
            out.append({"date": d, "yields": pts})
        out.sort(key=lambda x: x["date"])
        return out

    def source_url(self, year: int) -> str:
        return TREASURY_URL.format(year=year, kind="daily_treasury_yield_curve")


class FREDProvider(EconomicDataProvider):
    name = "fred"
    label = "FRED (St. Louis Fed)"
    requires_key = "FRED_API_KEY"
    homepage = "https://fred.stlouisfed.org"

    async def get_series(self, series_id: str, start: str | None = None) -> list[tuple[str, float]]:
        if not has_secret("FRED_API_KEY"):
            raise ProviderError(self.name, "FRED_API_KEY not configured")
        data = await http.get_json(self.name, "https://api.stlouisfed.org/fred/series/observations", params={
            "series_id": series_id, "api_key": env("FRED_API_KEY"), "file_type": "json",
            "observation_start": start or "2010-01-01",
        })
        out = []
        for o in data.get("observations", []):
            try:
                out.append((o["date"], float(o["value"])))
            except (ValueError, KeyError):
                continue
        return out

    async def release_dates(self, days_ahead: int = 21) -> list[dict[str, Any]]:
        if not has_secret("FRED_API_KEY"):
            raise ProviderError(self.name, "FRED_API_KEY not configured")
        today = date.today().isoformat()
        data = await http.get_json(self.name, "https://api.stlouisfed.org/fred/releases/dates", params={
            "api_key": env("FRED_API_KEY"), "file_type": "json", "realtime_start": today,
            "include_release_dates_with_no_data": "true", "sort_order": "asc", "limit": 200,
        })
        return data.get("release_dates", [])

    @staticmethod
    def url(series_id: str) -> str:
        return f"https://fred.stlouisfed.org/series/{series_id}"


class BLSProvider(EconomicDataProvider):
    """Keyless BLS Public Data API v1 (≤25 series/request, ≤10 years, small daily quota)."""
    name = "bls"
    label = "U.S. Bureau of Labor Statistics"
    homepage = "https://www.bls.gov/developers/"

    async def get_many(self, series_ids: list[str], years: int = 9) -> dict[str, list[tuple[str, float]]]:
        end = date.today().year
        body = {"seriesid": series_ids[:25], "startyear": str(end - years), "endyear": str(end)}
        data = await http.request(self.name, "POST", "https://api.bls.gov/publicAPI/v1/timeseries/data/", json_body=body, timeout=40)
        if data.get("status") != "REQUEST_SUCCEEDED":
            raise ProviderError(self.name, "; ".join(data.get("message") or ["request failed"]))
        out: dict[str, list[tuple[str, float]]] = {}
        for s in (data.get("Results") or {}).get("series", []):
            pts = []
            for d in s.get("data", []):
                p = d.get("period", "")
                if not p.startswith("M") or p == "M13":
                    continue
                try:
                    pts.append((f"{d['year']}-{p[1:]}-01", float(d["value"])))
                except (ValueError, KeyError):
                    continue
            out[s["seriesID"]] = sorted(pts)
        return out

    async def get_series(self, series_id: str, start: str | None = None) -> list[tuple[str, float]]:
        return (await self.get_many([series_id])).get(series_id, [])

    @staticmethod
    def url(series_id: str) -> str:
        return f"https://data.bls.gov/timeseries/{series_id}"


class WorldBankProvider:
    name = "worldbank"
    label = "World Bank Open Data"
    homepage = "https://data.worldbank.org"

    async def indicator(self, countries: list[str], indicator: str, mrv: int = 8) -> dict[str, list[tuple[str, float]]]:
        url = f"https://api.worldbank.org/v2/country/{';'.join(countries)}/indicator/{indicator}"
        data = await http.get_json(self.name, url, params={"format": "json", "mrv": mrv, "per_page": 500})
        out: dict[str, list[tuple[str, float]]] = {}
        if not isinstance(data, list) or len(data) < 2:
            return out
        for r in data[1] or []:
            if r.get("value") is None:
                continue
            out.setdefault(r["country"]["id"], []).append((r["date"], float(r["value"])))
        for k in out:
            out[k].sort()
        return out


class CentralBankRates:
    """Keyless official policy-rate endpoints."""
    name = "centralbanks"
    label = "Central bank data portals (NY Fed, ECB, BoE, BoC)"

    async def nyfed_effr(self) -> dict[str, Any]:
        d = await http.get_json("nyfed", "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/30.json")
        rows = d.get("refRates") or []
        if not rows:
            raise ProviderError("nyfed", "no EFFR data")
        latest = rows[0]
        return {"value": latest.get("percentRate"), "date": latest.get("effectiveDate"),
                "target_low": latest.get("targetRateFrom"), "target_high": latest.get("targetRateTo"),
                "history": sorted([(r["effectiveDate"], r["percentRate"]) for r in rows]),
                "source_url": "https://www.newyorkfed.org/markets/reference-rates/effr", "provider": "Federal Reserve Bank of New York"}

    async def ecb_dfr(self) -> dict[str, Any]:
        d = await http.get_json("ecb", "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV",
                                params={"format": "jsondata", "lastNObservations": 400})
        series = list((d.get("dataSets") or [{}])[0].get("series", {}).values())
        dims = (d.get("structure") or {}).get("dimensions", {}).get("observation", [])
        times = [v.get("id") for v in (dims[0].get("values") if dims else [])]
        obs = series[0].get("observations", {}) if series else {}
        pts = sorted((times[int(k)], v[0]) for k, v in obs.items() if v and v[0] is not None)
        if not pts:
            raise ProviderError("ecb", "no DFR observations")
        return {"value": pts[-1][1], "date": pts[-1][0], "history": _thin(pts),
                "source_url": "https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV", "provider": "ECB Data Portal"}

    async def boe_bank_rate(self) -> dict[str, Any]:
        start = f"01/Jan/{date.today().year - 2}"
        text = await http.get_text("boe", "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp", params={
            "csv.x": "yes", "Datefrom": start, "Dateto": "now", "SeriesCodes": "IUDBEDR", "CSVF": "TN", "UsingCodes": "Y"})
        pts = []
        for line in text.strip().splitlines()[1:]:
            parts = line.split(",")
            try:
                pts.append((datetime.strptime(parts[0].strip(), "%d %b %Y").date().isoformat(), float(parts[1])))
            except (ValueError, IndexError):
                continue
        if not pts:
            raise ProviderError("boe", "no Bank Rate data")
        pts.sort()
        return {"value": pts[-1][1], "date": pts[-1][0], "history": _thin(pts),
                "source_url": "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp", "provider": "Bank of England IADB"}

    async def boc_valet(self) -> dict[str, Any]:
        d = await http.get_json("boc", "https://www.bankofcanada.ca/valet/observations/V39079/json", params={"recent": 500})
        pts = sorted((o["d"], float(o["V39079"]["v"])) for o in d.get("observations", []) if o.get("V39079"))
        if not pts:
            raise ProviderError("boc", "no data")
        return {"value": pts[-1][1], "date": pts[-1][0], "history": _thin(pts),
                "source_url": "https://www.bankofcanada.ca/rates/interest-rates/canadian-interest-rates/", "provider": "Bank of Canada Valet"}


def _thin(pts: list[tuple[str, float]], max_points: int = 200) -> list[tuple[str, float]]:
    """Keep all rate changes plus an evenly thinned backbone for charting."""
    if len(pts) <= max_points:
        return pts
    step = max(1, len(pts) // max_points)
    keep = {0, len(pts) - 1}
    for i in range(1, len(pts)):
        if pts[i][1] != pts[i - 1][1]:
            keep.update({i - 1, i})
    keep.update(range(0, len(pts), step))
    return [pts[i] for i in sorted(keep)]
