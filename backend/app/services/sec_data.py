"""
SEC Data Service
Provides SEC filings data via EDGAR (Electronic Data Gathering, Online Retrieval)
No API key required - uses SEC_USER_AGENT header for identification
"""

import httpx
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FormType(str, Enum):
    """Common SEC filing types"""
    FORM_10_K = "10-K"
    FORM_10_Q = "10-Q"
    FORM_8_K = "8-K"
    FORM_DEF_14A = "DEF 14A"
    FORM_S_1 = "S-1"
    FORM_4 = "4"
    FORM_5 = "5"
    FORM_S_8 = "S-8"
    FORM_424B5 = "424B5"


@dataclass
class FinancialsSummary:
    """Normalized company financials extracted from SEC EDGAR"""
    ticker: str
    company_name: str
    cik: str

    # Income Statement (most recent annual, USD)
    revenue: Optional[float]
    net_income: Optional[float]
    eps_diluted: Optional[float]

    # Cash Flow
    operating_cash_flow: Optional[float]

    # Balance Sheet
    total_assets: Optional[float]
    total_liabilities: Optional[float]
    shares_outstanding: Optional[float]

    # YoY Growth (%)
    revenue_growth_yoy: Optional[float]
    net_income_growth_yoy: Optional[float]

    # Derived
    equity: Optional[float]
    debt_to_assets: Optional[float]

    # Metadata
    fiscal_year_end: Optional[str]
    data_source: str  # "edgar" | "mock"
    fetched_at: str


class SECDataProvider:
    """Abstract base for SEC data providers"""

    async def get_company_ciks(self, ticker: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_filings(
        self,
        cik: str,
        form_type: Optional[str] = None,
        count: int = 10
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_filing_detail(self, accession_number: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_financials_summary(self, ticker: str) -> FinancialsSummary:
        raise NotImplementedError


class EDGARProvider(SECDataProvider):
    """
    SEC EDGAR API integration
    https://www.sec.gov/edgar/

    Free data - no API key required
    Public company filings: 10-K, 10-Q, 8-K, etc.
    Uses SEC_USER_AGENT header for identification
    """

    COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    # Ordered candidate XBRL tags for each concept (first match wins)
    _REVENUE_TAGS = [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ]
    _NET_INCOME_TAGS = ["NetIncomeLoss", "ProfitLoss"]
    _EPS_TAGS = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
    _OCF_TAGS = ["NetCashProvidedByUsedInOperatingActivities"]
    _ASSETS_TAGS = ["Assets"]
    _LIABILITIES_TAGS = ["Liabilities"]
    _SHARES_TAGS = [
        "CommonStockSharesOutstanding",
        "WeightedAverageNumberOfDilutedSharesOutstanding",
    ]

    def __init__(self):
        settings = get_settings()
        self.user_agent = settings.sec_user_agent or "Axiom Terminal (contact support@example.com)"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
        )
        logger.info(f"SEC EDGAR Provider initialized with User-Agent: {self.user_agent}")

    # ------------------------------------------------------------------
    # Existing API methods
    # ------------------------------------------------------------------

    async def get_company_ciks(self, ticker: str) -> Dict[str, Any]:
        """Get CIK for a ticker from SEC company_tickers.json"""
        try:
            response = await self.client.get(self.TICKERS_URL)
            response.raise_for_status()
            ticker_upper = ticker.upper()
            for entry in response.json().values():
                if entry.get("ticker", "").upper() == ticker_upper:
                    return {
                        "cik": str(entry["cik_str"]).zfill(10),
                        "ticker": entry["ticker"],
                        "title": entry["title"],
                    }
            raise ValueError(f"Ticker {ticker} not found in SEC EDGAR")
        except Exception as e:
            logger.error(f"Error looking up CIK for {ticker}: {e}")
            raise

    async def get_filings(
        self, cik: str, form_type: Optional[str] = None, count: int = 10
    ) -> Dict[str, Any]:
        """Get company filings from submissions endpoint"""
        try:
            cik_normalized = str(cik).zfill(10)
            url = self.SUBMISSIONS_URL.format(cik=cik_normalized)
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            filings_raw = data.get("filings", {}).get("recent", {})

            accessions = filings_raw.get("accessionNumber", [])
            forms = filings_raw.get("form", [])
            filing_dates = filings_raw.get("filingDate", [])
            report_dates = filings_raw.get("reportDate", [])

            results = []
            for i, accession in enumerate(accessions):
                if len(results) >= count:
                    break
                form = forms[i] if i < len(forms) else "N/A"
                if form_type and form != form_type:
                    continue
                results.append({
                    "accessionNumber": accession,
                    "form": form,
                    "filingDate": filing_dates[i] if i < len(filing_dates) else "N/A",
                    "reportDate": report_dates[i] if i < len(report_dates) else "N/A",
                })
            return {"cik": cik_normalized, "filings": results}
        except Exception as e:
            logger.error(f"Error fetching filings for CIK {cik}: {e}")
            raise

    async def get_filing_detail(self, cik: str, accession_number: str) -> Dict[str, Any]:
        cik_normalized = str(cik).zfill(10)
        return {
            "cik": cik_normalized,
            "accessionNumber": accession_number,
            "viewUrl": (
                f"https://www.sec.gov/cgi-bin/viewer?"
                f"action=view&cik={cik_normalized}&accession_number={accession_number}"
            ),
        }

    # ------------------------------------------------------------------
    # Company Facts / Financial Extraction
    # ------------------------------------------------------------------

    async def _fetch_company_facts(self, cik: str) -> Dict[str, Any]:
        """Fetch XBRL company facts from EDGAR"""
        cik_normalized = str(cik).zfill(10)
        url = self.COMPANY_FACTS_URL.format(cik=cik_normalized)
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _latest_annual(
        facts: Dict[str, Any],
        tags: List[str],
        namespace: str = "us-gaap",
        unit: str = "USD",
    ) -> tuple[Optional[float], Optional[str]]:
        """
        Extract the most recent annual (10-K) value for the first matching tag.
        Returns (value, end_date) or (None, None).
        """
        ns = facts.get("facts", {}).get(namespace, {})
        for tag in tags:
            concept = ns.get(tag)
            if not concept:
                continue
            observations = concept.get("units", {}).get(unit, [])
            # Keep only annual 10-K filings with a valid numeric value
            annual = [
                o for o in observations
                if o.get("form") == "10-K" and o.get("val") is not None
            ]
            if not annual:
                continue
            # Sort descending by end date, take the most recent
            annual.sort(key=lambda o: o["end"], reverse=True)
            best = annual[0]
            return float(best["val"]), best["end"]
        return None, None

    @staticmethod
    def _two_latest_annual(
        facts: Dict[str, Any],
        tags: List[str],
        namespace: str = "us-gaap",
        unit: str = "USD",
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Return (most_recent, prior_year) annual values for YoY growth calculation.
        Returns (None, None) if insufficient data.
        """
        ns = facts.get("facts", {}).get(namespace, {})
        for tag in tags:
            concept = ns.get(tag)
            if not concept:
                continue
            observations = concept.get("units", {}).get(unit, [])
            annual = [
                o for o in observations
                if o.get("form") == "10-K" and o.get("val") is not None
            ]
            if len(annual) < 2:
                continue
            annual.sort(key=lambda o: o["end"], reverse=True)
            return float(annual[0]["val"]), float(annual[1]["val"])
        return None, None

    @staticmethod
    def _yoy_growth(current: Optional[float], prior: Optional[float]) -> Optional[float]:
        """Compute YoY % growth. Returns None if inputs are invalid."""
        if current is None or prior is None or prior == 0:
            return None
        return round((current - prior) / abs(prior) * 100, 2)

    async def get_financials_summary(self, ticker: str) -> FinancialsSummary:
        """
        Fetch and normalize key financial metrics from SEC EDGAR for a ticker.
        Tries multiple XBRL tag aliases to handle company-specific variation.
        Gracefully returns None for any missing fields.
        """
        company_info = await self.get_company_ciks(ticker)
        cik = company_info["cik"]
        company_name = company_info["title"]

        facts = await self._fetch_company_facts(cik)

        revenue, fiscal_year_end = self._latest_annual(facts, self._REVENUE_TAGS)
        revenue_curr, revenue_prev = self._two_latest_annual(facts, self._REVENUE_TAGS)
        revenue_growth_yoy = self._yoy_growth(revenue_curr, revenue_prev)

        net_income, _ = self._latest_annual(facts, self._NET_INCOME_TAGS)
        ni_curr, ni_prev = self._two_latest_annual(facts, self._NET_INCOME_TAGS)
        net_income_growth_yoy = self._yoy_growth(ni_curr, ni_prev)

        eps_diluted, _ = self._latest_annual(facts, self._EPS_TAGS, unit="USD/shares")
        if eps_diluted is None:
            # Some filers store EPS in USD unit
            eps_diluted, _ = self._latest_annual(facts, self._EPS_TAGS)

        ocf, _ = self._latest_annual(facts, self._OCF_TAGS)
        total_assets, _ = self._latest_annual(facts, self._ASSETS_TAGS)
        total_liabilities, _ = self._latest_annual(facts, self._LIABILITIES_TAGS)
        shares, _ = self._latest_annual(facts, self._SHARES_TAGS, unit="shares")

        equity = (
            round(total_assets - total_liabilities, 0)
            if total_assets is not None and total_liabilities is not None
            else None
        )
        debt_to_assets = (
            round(total_liabilities / total_assets, 4)
            if total_assets and total_liabilities
            else None
        )

        return FinancialsSummary(
            ticker=ticker.upper(),
            company_name=company_name,
            cik=cik,
            revenue=revenue,
            net_income=net_income,
            eps_diluted=eps_diluted,
            operating_cash_flow=ocf,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            shares_outstanding=shares,
            revenue_growth_yoy=revenue_growth_yoy,
            net_income_growth_yoy=net_income_growth_yoy,
            equity=equity,
            debt_to_assets=debt_to_assets,
            fiscal_year_end=fiscal_year_end,
            data_source="edgar",
            fetched_at=datetime.utcnow().isoformat(),
        )

    async def close(self):
        await self.client.aclose()


class SECDataService:
    """
    Service layer for SEC data.
    Provides high-level methods for company research and financial extraction.
    """

    def __init__(self, provider: Optional[SECDataProvider] = None):
        self.provider = provider or EDGARProvider()

    async def get_company_info(self, ticker: str) -> Dict[str, Any]:
        return await self.provider.get_company_ciks(ticker)

    async def get_annual_filings(self, cik: str, count: int = 5) -> List[Dict[str, Any]]:
        filings = await self.provider.get_filings(cik, form_type="10-K", count=count)
        return filings.get("filings", [])

    async def get_quarterly_filings(self, cik: str, count: int = 8) -> List[Dict[str, Any]]:
        filings = await self.provider.get_filings(cik, form_type="10-Q", count=count)
        return filings.get("filings", [])

    async def get_current_reports(self, cik: str, count: int = 10) -> List[Dict[str, Any]]:
        filings = await self.provider.get_filings(cik, form_type="8-K", count=count)
        return filings.get("filings", [])

    async def get_all_filings(self, cik: str, count: int = 20) -> List[Dict[str, Any]]:
        filings = await self.provider.get_filings(cik, count=count)
        return filings.get("filings", [])

    async def get_financials_summary(self, ticker: str) -> FinancialsSummary:
        """
        Return normalized financial summary for a ticker.
        Fetches live data from EDGAR; mock provider returns deterministic values.
        """
        return await self.provider.get_financials_summary(ticker)

    async def close(self):
        if hasattr(self.provider, "close"):
            await self.provider.close()


# ---------------------------------------------------------------------------
# Mock implementation — deterministic, no network calls
# ---------------------------------------------------------------------------

_MOCK_FINANCIALS: Dict[str, Dict[str, Any]] = {
    "AAPL": dict(
        company_name="Apple Inc.",
        cik="0000320193",
        revenue=394_328_000_000,
        net_income=96_995_000_000,
        eps_diluted=6.13,
        operating_cash_flow=110_543_000_000,
        total_assets=352_755_000_000,
        total_liabilities=290_437_000_000,
        shares_outstanding=15_552_752_000,
        revenue_growth_yoy=-2.8,
        net_income_growth_yoy=2.9,
        fiscal_year_end="2023-09-30",
    ),
    "MSFT": dict(
        company_name="Microsoft Corporation",
        cik="0000789019",
        revenue=211_915_000_000,
        net_income=72_361_000_000,
        eps_diluted=9.71,
        operating_cash_flow=87_582_000_000,
        total_assets=411_976_000_000,
        total_liabilities=205_753_000_000,
        shares_outstanding=7_432_000_000,
        revenue_growth_yoy=16.0,
        net_income_growth_yoy=20.1,
        fiscal_year_end="2023-06-30",
    ),
    "NVDA": dict(
        company_name="NVIDIA Corporation",
        cik="0001045810",
        revenue=60_922_000_000,
        net_income=29_760_000_000,
        eps_diluted=11.93,
        operating_cash_flow=28_608_000_000,
        total_assets=65_728_000_000,
        total_liabilities=22_516_000_000,
        shares_outstanding=2_462_000_000,
        revenue_growth_yoy=122.4,
        net_income_growth_yoy=581.3,
        fiscal_year_end="2024-01-28",
    ),
    "GOOGL": dict(
        company_name="Alphabet Inc.",
        cik="0001652044",
        revenue=307_394_000_000,
        net_income=73_795_000_000,
        eps_diluted=5.80,
        operating_cash_flow=101_746_000_000,
        total_assets=402_392_000_000,
        total_liabilities=109_120_000_000,
        shares_outstanding=12_634_000_000,
        revenue_growth_yoy=8.7,
        net_income_growth_yoy=23.5,
        fiscal_year_end="2023-12-31",
    ),
    "AMZN": dict(
        company_name="Amazon.com Inc.",
        cik="0001018724",
        revenue=574_785_000_000,
        net_income=30_425_000_000,
        eps_diluted=2.90,
        operating_cash_flow=84_946_000_000,
        total_assets=527_854_000_000,
        total_liabilities=325_981_000_000,
        shares_outstanding=10_333_000_000,
        revenue_growth_yoy=12.5,
        net_income_growth_yoy=4812.0,
        fiscal_year_end="2023-12-31",
    ),
}

_MOCK_FINANCIALS_DEFAULT = dict(
    company_name="{ticker} Inc.",
    cik="0000000001",
    revenue=10_000_000_000,
    net_income=1_200_000_000,
    eps_diluted=2.40,
    operating_cash_flow=1_800_000_000,
    total_assets=20_000_000_000,
    total_liabilities=12_000_000_000,
    shares_outstanding=500_000_000,
    revenue_growth_yoy=8.0,
    net_income_growth_yoy=10.5,
    fiscal_year_end="2023-12-31",
)


class MockSECDataProvider(SECDataProvider):
    """Deterministic mock — no network calls"""

    async def get_company_ciks(self, ticker: str) -> Dict[str, Any]:
        mock_data = {
            "AAPL": {"cik": "0000320193", "ticker": "AAPL", "title": "Apple Inc."},
            "MSFT": {"cik": "0000789019", "ticker": "MSFT", "title": "Microsoft Corp."},
            "GOOGL": {"cik": "0001652044", "ticker": "GOOGL", "title": "Alphabet Inc."},
        }
        ticker_upper = ticker.upper()
        return mock_data.get(ticker_upper, {
            "cik": "0000012345",
            "ticker": ticker_upper,
            "title": f"{ticker_upper} Inc.",
        })

    async def get_filings(
        self, cik: str, form_type: Optional[str] = None, count: int = 10
    ) -> Dict[str, Any]:
        return {
            "cik": cik,
            "filings": [
                {"accessionNumber": "0000320193-24-000006", "form": "10-K",
                 "filingDate": "2024-01-30", "reportDate": "2023-09-30"},
                {"accessionNumber": "0000320193-24-000003", "form": "10-Q",
                 "filingDate": "2024-02-01", "reportDate": "2023-12-30"},
            ],
        }

    async def get_filing_detail(self, accession_number: str) -> Dict[str, Any]:
        return {
            "accessionNumber": accession_number,
            "viewUrl": f"https://www.sec.gov/cgi-bin/viewer?action=view&accession_number={accession_number}",
        }

    async def get_financials_summary(self, ticker: str) -> FinancialsSummary:
        ticker_upper = ticker.upper()
        base = _MOCK_FINANCIALS.get(ticker_upper, _MOCK_FINANCIALS_DEFAULT)
        company_name = base["company_name"].replace("{ticker}", ticker_upper)
        total_assets = base["total_assets"]
        total_liabilities = base["total_liabilities"]
        equity = round(total_assets - total_liabilities, 0) if total_assets and total_liabilities else None
        debt_to_assets = round(total_liabilities / total_assets, 4) if total_assets and total_liabilities else None

        return FinancialsSummary(
            ticker=ticker_upper,
            company_name=company_name,
            cik=base["cik"],
            revenue=base["revenue"],
            net_income=base["net_income"],
            eps_diluted=base["eps_diluted"],
            operating_cash_flow=base["operating_cash_flow"],
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            shares_outstanding=base["shares_outstanding"],
            revenue_growth_yoy=base["revenue_growth_yoy"],
            net_income_growth_yoy=base["net_income_growth_yoy"],
            equity=equity,
            debt_to_assets=debt_to_assets,
            fiscal_year_end=base["fiscal_year_end"],
            data_source="mock",
            fetched_at=datetime.utcnow().isoformat(),
        )
