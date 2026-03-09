"""SEC EDGAR public data service."""

from __future__ import annotations

from typing import Optional
import httpx
from app.core.config import SEC_USER_AGENT

# Mapping of common tickers to CIK numbers
TICKER_CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "META": "0001326801",
}


async def fetch_company_facts(ticker: str) -> Optional[dict]:
    """Fetch company facts from SEC EDGAR. Returns None on failure."""
    cik = TICKER_CIK.get(ticker.upper())
    if not cik:
        print(f"[sec_data] No CIK mapping for {ticker}")
        return None

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {"User-Agent": SEC_USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"[sec_data] SEC returned {resp.status_code} for {ticker}")
                return None
            data = resp.json()

        us_gaap = data.get("facts", {}).get("us-gaap", {})
        if not us_gaap:
            return None

        def get_latest(concept: str) -> Optional[float]:
            entry = us_gaap.get(concept, {})
            units = entry.get("units", {})
            for unit_type in ["USD", "USD/shares", "shares", "pure"]:
                vals = units.get(unit_type, [])
                if vals:
                    # Get the most recent annual filing
                    annual = [v for v in vals if v.get("form") == "10-K"]
                    if annual:
                        return float(annual[-1]["val"])
                    return float(vals[-1]["val"])
            return None

        return {
            "revenue": get_latest("Revenues") or get_latest("RevenueFromContractWithCustomerExcludingAssessedTax"),
            "netIncome": get_latest("NetIncomeLoss"),
            "eps": get_latest("EarningsPerShareDiluted"),
            "operatingCashFlow": get_latest("NetCashProvidedByOperatingActivities"),
            "totalAssets": get_latest("Assets"),
            "totalLiabilities": get_latest("Liabilities"),
            "sharesOutstanding": get_latest("CommonStockSharesOutstanding") or get_latest("EntityCommonStockSharesOutstanding"),
        }
    except Exception as e:
        print(f"[sec_data] Error fetching SEC data for {ticker}: {e}")
        return None
