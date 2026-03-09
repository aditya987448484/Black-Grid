"""SEC EDGAR public data service — dynamic CIK resolution for all tickers."""

from __future__ import annotations

from typing import Optional
import time as _time
import httpx
from app.core.config import SEC_USER_AGENT

# Dynamic CIK cache: populated from SEC's company_tickers.json
_cik_map: dict[str, str] = {}
_cik_loaded_at: float = 0
CIK_CACHE_TTL = 3600 * 12  # 12 hours


async def _load_cik_map() -> dict[str, str]:
    """Load ticker → CIK mapping from SEC EDGAR (covers all US-listed companies)."""
    global _cik_map, _cik_loaded_at

    if _cik_map and (_time.time() - _cik_loaded_at) < CIK_CACHE_TTL:
        return _cik_map

    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": SEC_USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"[sec_data] Failed to load CIK map: HTTP {resp.status_code}")
                return _cik_map
            data = resp.json()

        new_map: dict[str, str] = {}
        for entry in data.values():
            ticker = entry.get("ticker", "").upper()
            cik = str(entry.get("cik_str", ""))
            if ticker and cik:
                new_map[ticker] = cik.zfill(10)

        _cik_map = new_map
        _cik_loaded_at = _time.time()
        print(f"[sec_data] Loaded CIK map: {len(_cik_map)} tickers")
        return _cik_map
    except Exception as e:
        print(f"[sec_data] Error loading CIK map: {e}")
        return _cik_map


async def _resolve_cik(ticker: str) -> Optional[str]:
    """Resolve ticker to CIK number via SEC's company_tickers.json."""
    cik_map = await _load_cik_map()
    cik = cik_map.get(ticker.upper())
    if not cik:
        # Try without dots (BRK.B → BRKB)
        alt = ticker.upper().replace(".", "")
        cik = cik_map.get(alt)
    return cik


async def fetch_company_facts(ticker: str) -> Optional[dict]:
    """Fetch company facts from SEC EDGAR. Dynamically resolves CIK for any ticker."""
    cik = await _resolve_cik(ticker)
    if not cik:
        print(f"[sec_data] No CIK found for {ticker} (not in SEC database)")
        return None

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {"User-Agent": SEC_USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 429:
                print(f"[sec_data] SEC rate limited for {ticker}, waiting 2s...")
                import asyncio
                await asyncio.sleep(2)
                resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"[sec_data] SEC returned {resp.status_code} for {ticker} (CIK: {cik})")
                return None
            data = resp.json()

        us_gaap = data.get("facts", {}).get("us-gaap", {})
        # Some companies use IFRS
        if not us_gaap:
            us_gaap = data.get("facts", {}).get("ifrs-full", {})
        if not us_gaap:
            print(f"[sec_data] No GAAP/IFRS data for {ticker}")
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
                    # Fallback to most recent filing of any type
                    return float(vals[-1]["val"])
            return None

        revenue = (
            get_latest("Revenues")
            or get_latest("RevenueFromContractWithCustomerExcludingAssessedTax")
            or get_latest("RevenueFromContractWithCustomerIncludingAssessedTax")
            or get_latest("SalesRevenueNet")
            or get_latest("TotalRevenuesAndOtherIncome")
        )

        result = {
            "revenue": revenue,
            "netIncome": get_latest("NetIncomeLoss"),
            "eps": get_latest("EarningsPerShareDiluted") or get_latest("EarningsPerShareBasic"),
            "operatingCashFlow": get_latest("NetCashProvidedByOperatingActivities"),
            "totalAssets": get_latest("Assets"),
            "totalLiabilities": get_latest("Liabilities"),
            "sharesOutstanding": (
                get_latest("CommonStockSharesOutstanding")
                or get_latest("EntityCommonStockSharesOutstanding")
                or get_latest("WeightedAverageNumberOfShareOutstandingBasicAndDiluted")
            ),
            "grossProfit": get_latest("GrossProfit"),
            "operatingIncome": get_latest("OperatingIncomeLoss"),
            "totalEquity": get_latest("StockholdersEquity"),
            "longTermDebt": get_latest("LongTermDebt") or get_latest("LongTermDebtNoncurrent"),
            "currentAssets": get_latest("AssetsCurrent"),
            "currentLiabilities": get_latest("LiabilitiesCurrent"),
        }

        has_data = any(v is not None for v in result.values())
        if has_data:
            print(f"[sec_data] Got SEC data for {ticker}: revenue={'${:.1f}B'.format(result['revenue']/1e9) if result.get('revenue') else 'N/A'}")
        return result if has_data else None

    except Exception as e:
        print(f"[sec_data] Error fetching SEC data for {ticker}: {e}")
        return None
