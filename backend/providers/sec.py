"""SEC EDGAR provider: ticker→CIK map, filings, company facts (XBRL) → statements.

All SEC requests carry a descriptive User-Agent as required by the SEC's fair
access policy (configurable via SEC_USER_AGENT) and are rate limited.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from backend.config import env
from backend.models.schemas import Filing
from backend.providers.base import FilingsProvider
from backend.utils import http
from backend.utils.http import ProviderError

KEY_FORMS = {"10-K", "10-Q", "8-K", "DEF 14A", "S-1", "4", "SC 13D", "SC 13G", "SC 13D/A", "SC 13G/A", "13F-HR", "20-F", "6-K", "10-K/A", "10-Q/A", "S-1/A", "40-F", "424B4"}

# Concept preference lists: the first concept present wins for each period.
CONCEPTS: dict[str, list[str]] = {
    # income statement (duration)
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax", "RevenuesNetOfInterestExpense"],
    "cost_of_revenue": ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold"],
    "gross_profit": ["GrossProfit"],
    "rnd": ["ResearchAndDevelopmentExpense"],
    "sga": ["SellingGeneralAndAdministrativeExpense"],
    "operating_income": ["OperatingIncomeLoss"],
    "interest_expense": ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"],
    "pretax_income": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "income_tax": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "eps_basic": ["EarningsPerShareBasic"],
    "eps_diluted": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "dna": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet", "Depreciation"],
    # cash flow (duration)
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "dividends_paid": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "sbc": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    # balance sheet (instant)
    "total_assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "total_liabilities": ["Liabilities"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash"],
    "short_term_investments": ["MarketableSecuritiesCurrent", "ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
    "receivables": ["AccountsReceivableNetCurrent"],
    "inventory": ["InventoryNet"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"],
    "current_debt": ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings", "CommercialPaper"],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
    "shares_outstanding": ["CommonStockSharesOutstanding"],
}
INSTANT = {"total_assets", "current_assets", "total_liabilities", "current_liabilities", "equity", "cash", "short_term_investments",
           "receivables", "inventory", "long_term_debt", "current_debt", "retained_earnings", "shares_outstanding"}
PER_SHARE = {"eps_basic", "eps_diluted"}

STATEMENT_LAYOUT = {
    "income": ["revenue", "cost_of_revenue", "gross_profit", "rnd", "sga", "operating_income", "interest_expense", "pretax_income",
               "income_tax", "net_income", "eps_basic", "eps_diluted", "diluted_shares", "ebitda"],
    "balance": ["cash", "short_term_investments", "receivables", "inventory", "current_assets", "total_assets", "current_liabilities",
                "current_debt", "long_term_debt", "total_liabilities", "equity", "retained_earnings", "shares_outstanding"],
    "cashflow": ["operating_cash_flow", "capex", "free_cash_flow", "dna", "sbc", "dividends_paid", "buybacks"],
}
LABELS = {
    "revenue": "Revenue", "cost_of_revenue": "Cost of revenue", "gross_profit": "Gross profit", "rnd": "Research & development",
    "sga": "SG&A", "operating_income": "Operating income", "interest_expense": "Interest expense", "pretax_income": "Pre-tax income",
    "income_tax": "Income tax", "net_income": "Net income", "eps_basic": "EPS (basic)", "eps_diluted": "EPS (diluted)",
    "diluted_shares": "Diluted shares", "ebitda": "EBITDA (OI + D&A)", "cash": "Cash & equivalents", "short_term_investments": "Short-term investments",
    "receivables": "Receivables", "inventory": "Inventory", "current_assets": "Total current assets", "total_assets": "Total assets",
    "current_liabilities": "Total current liabilities", "current_debt": "Short-term debt", "long_term_debt": "Long-term debt",
    "total_liabilities": "Total liabilities", "equity": "Shareholders' equity", "retained_earnings": "Retained earnings",
    "shares_outstanding": "Shares outstanding", "operating_cash_flow": "Operating cash flow", "capex": "Capital expenditures",
    "free_cash_flow": "Free cash flow", "dna": "Depreciation & amortization", "sbc": "Stock-based compensation",
    "dividends_paid": "Dividends paid", "buybacks": "Share repurchases",
}


def _days(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


class SECProvider(FilingsProvider):
    name = "sec"
    label = "SEC EDGAR"
    homepage = "https://www.sec.gov/edgar"

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": env("SEC_USER_AGENT") or "OmniMarket Research admin@localhost", "Accept-Encoding": "gzip, deflate"}

    async def ticker_map(self) -> dict[str, dict[str, Any]]:
        data = await http.get_json(self.name, "https://www.sec.gov/files/company_tickers.json", headers=self.headers, timeout=30)
        return {v["ticker"].upper(): {"cik": int(v["cik_str"]), "title": v["title"]} for v in data.values()}

    async def submissions(self, cik: int) -> dict[str, Any]:
        return await http.get_json(self.name, f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=self.headers, timeout=30)

    async def company_facts(self, cik: int) -> dict[str, Any]:
        return await http.get_json(self.name, f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", headers=self.headers, timeout=45)

    async def full_text_search(self, q: str, forms: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        params = {"q": q}
        if forms:
            params["forms"] = forms
        data = await http.get_json(self.name, "https://efts.sec.gov/LATEST/search-index", params=params, headers=self.headers)
        out = []
        for h in (data.get("hits") or {}).get("hits", [])[:limit]:
            s = h.get("_source", {})
            adsh = (h.get("_id") or "").split(":")[0]
            ciks = s.get("ciks") or []
            doc = (h.get("_id") or ":").split(":")[1]
            url = None
            if ciks and adsh:
                url = f"https://www.sec.gov/Archives/edgar/data/{int(ciks[0])}/{adsh.replace('-', '')}/{doc}"
            out.append({"form": s.get("form") or s.get("file_type"), "filed": s.get("file_date"), "company": (s.get("display_names") or [""])[0],
                        "description": s.get("file_description"), "url": url})
        return out

    async def get_filings(self, symbol: str, forms: list[str] | None = None, limit: int = 60, cik: int | None = None) -> list[Filing]:
        if cik is None:
            raise ProviderError(self.name, "CIK required")
        sub = await self.submissions(cik)
        recent = (sub.get("filings") or {}).get("recent") or {}
        out: list[Filing] = []
        n = len(recent.get("accessionNumber", []))
        wanted = set(forms) if forms else KEY_FORMS
        for i in range(n):
            form = recent["form"][i]
            if form not in wanted:
                continue
            acc = recent["accessionNumber"][i]
            acc_nd = acc.replace("-", "")
            doc = recent["primaryDocument"][i]
            base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nd}"
            out.append(Filing(
                form=form, filed=recent["filingDate"][i], report_date=recent.get("reportDate", [None] * n)[i] or None,
                accession=acc, description=recent.get("primaryDocDescription", [None] * n)[i] or None,
                url=f"{base}/{doc}" if doc else f"{base}/", index_url=f"{base}/{acc}-index.htm",
            ))
            if len(out) >= limit:
                break
        return out

    # ---- XBRL → statements ------------------------------------------------------
    @staticmethod
    def build_statements(facts: dict[str, Any]) -> dict[str, Any]:
        """Normalize company facts into annual/quarterly/TTM statement tables.

        Annual values: 10-K facts whose duration is ~1 year. Quarterly: ~3-month
        durations from 10-Q/10-K; Q4 is derived as FY minus Q1..Q3 when needed.
        When the same period is reported in several filings the latest filing wins
        (captures restatements).
        """
        gaap = (facts.get("facts") or {}).get("us-gaap") or {}
        dei = (facts.get("facts") or {}).get("dei") or {}
        annual: dict[str, dict[str, float]] = defaultdict(dict)
        quarterly: dict[str, dict[str, float]] = defaultdict(dict)
        fy_of: dict[str, str] = {}

        for key, concepts in CONCEPTS.items():
            best_a: dict[str, tuple[str, float]] = {}
            best_q: dict[str, tuple[str, float]] = {}
            for concept in concepts:
                node = gaap.get(concept)
                if not node:
                    continue
                units = node.get("units") or {}
                unit_key = "USD/shares" if key in PER_SHARE else ("shares" if key in ("diluted_shares", "shares_outstanding") else "USD")
                rows = units.get(unit_key) or []
                for r in rows:
                    end, form, filed = r.get("end"), r.get("form", ""), r.get("filed", "")
                    if not end or r.get("val") is None:
                        continue
                    if key in INSTANT:
                        # Balance-sheet values: annual table uses fiscal-year-end snapshots (10-K),
                        # quarterly table uses every period-end snapshot (10-K and 10-Q).
                        val = float(r["val"])
                        if form.startswith(("10-K", "20-F")) and r.get("fp") == "FY":
                            if end not in best_a or filed > best_a[end][0]:
                                best_a[end] = (filed, val)
                        if form.startswith(("10-K", "10-Q", "20-F")):
                            if end not in best_q or filed > best_q[end][0]:
                                best_q[end] = (filed, val)
                        continue
                    start = r.get("start")
                    if not start:
                        continue
                    d = _days(start, end)
                    if 350 <= d <= 380 and (form.startswith("10-K") or form.startswith("20-F")):
                        if end not in best_a or filed > best_a[end][0]:
                            best_a[end] = (filed, float(r["val"]))
                            if r.get("fy"):
                                fy_of[end] = str(r["fy"])
                    elif 80 <= d <= 100:
                        if end not in best_q or filed > best_q[end][0]:
                            best_q[end] = (filed, float(r["val"]))
                # Use the first concept that has data for the most recent periods,
                # but allow later concepts to fill gaps (companies switch tags).
            for end, (_, v) in best_a.items():
                annual[end].setdefault(key, v)
            for end, (_, v) in best_q.items():
                quarterly[end].setdefault(key, v)

        # Derive Q4 flows: FY - (Q1+Q2+Q3) where the three prior quarters exist inside the fiscal year.
        q_ends = sorted(quarterly)
        for fy_end, fy_vals in list(annual.items()):
            # Q1..Q3 period ends fall roughly 90/180/270 days before the fiscal year end.
            prior = [e for e in q_ends if 60 <= _days(e, fy_end) <= 300][-3:]
            if len(prior) != 3:
                continue
            q4 = quarterly[fy_end]
            for k, v in fy_vals.items():
                if k in PER_SHARE or k == "diluted_shares" or k in q4:
                    continue
                if k in INSTANT:
                    q4[k] = v
                    continue
                parts = [quarterly[p].get(k) for p in prior]
                if all(p is not None for p in parts):
                    q4[k] = v - sum(parts)  # type: ignore[arg-type]

        def enrich(rows: dict[str, dict[str, float]]) -> None:
            for vals in rows.values():
                if "gross_profit" not in vals and "revenue" in vals and "cost_of_revenue" in vals:
                    vals["gross_profit"] = vals["revenue"] - vals["cost_of_revenue"]
                if "operating_cash_flow" in vals and "capex" in vals:
                    vals["free_cash_flow"] = vals["operating_cash_flow"] - vals["capex"]
                if "operating_income" in vals and "dna" in vals:
                    vals["ebitda"] = vals["operating_income"] + vals["dna"]

        enrich(annual)
        enrich(quarterly)

        def table(rows: dict[str, dict[str, float]], n: int, min_keys: int = 3) -> list[dict[str, Any]]:
            ends = [e for e in sorted(rows, reverse=True) if len(rows[e]) >= min_keys or "revenue" in rows[e] or "net_income" in rows[e]][:n]
            return [{"period_end": e, "fiscal_year": fy_of.get(e), **rows[e]} for e in ends]

        annual_t = table(annual, 10)
        quarterly_t = table(quarterly, 12)

        # TTM: sum of the four most recent quarters for flows; latest instant for balance items.
        ttm: dict[str, Any] = {}
        flows_q = [q for q in quarterly_t if "revenue" in q or "net_income" in q][:4]
        if len(flows_q) == 4:
            for k in set().union(*[set(q) for q in flows_q]):
                if k in ("period_end", "fiscal_year") or k in INSTANT or k == "diluted_shares":
                    continue
                vals = [q.get(k) for q in flows_q]
                if all(isinstance(v, (int, float)) for v in vals):
                    ttm[k] = sum(vals)  # type: ignore[arg-type]
            for k in INSTANT:
                if k in quarterly_t[0]:
                    ttm[k] = quarterly_t[0][k]
            if "diluted_shares" in flows_q[0]:
                ttm["diluted_shares"] = flows_q[0]["diluted_shares"]
            ttm["period_end"] = flows_q[0]["period_end"]

        shares_dei = None
        so = (dei.get("EntityCommonStockSharesOutstanding") or {}).get("units", {}).get("shares") or []
        if so:
            latest = max(so, key=lambda r: r.get("end", ""))
            shares_dei = {"value": latest["val"], "as_of": latest.get("end")}

        return {"annual": annual_t, "quarterly": quarterly_t, "ttm": ttm, "shares_outstanding": shares_dei,
                "entity": facts.get("entityName"), "layout": STATEMENT_LAYOUT, "labels": LABELS}
