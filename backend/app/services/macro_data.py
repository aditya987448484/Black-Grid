"""FRED macro data service with concurrent fetching and fallback to mock."""

from __future__ import annotations

from typing import Optional, List
import asyncio
import time as _time
import httpx
from app.core.config import FRED_API_KEY

FRED_SERIES = {
    "10Y Treasury": "DGS10",
    "Fed Funds Rate": "FEDFUNDS",
    "CPI YoY": "CPIAUCSL",
    "Unemployment": "UNRATE",
    "GDP Growth": "A191RL1Q225SBEA",
}

# Cache macro data for 30 minutes (doesn't change frequently)
_macro_cache: Optional[tuple[float, List[dict]]] = None
MACRO_CACHE_TTL = 1800

MOCK_MACRO = [
    {"name": "10Y Treasury", "value": 4.28, "unit": "%", "trend": "rising"},
    {"name": "Fed Funds Rate", "value": 5.33, "unit": "%", "trend": "stable"},
    {"name": "CPI YoY", "value": 3.2, "unit": "%", "trend": "falling"},
    {"name": "Unemployment", "value": 3.7, "unit": "%", "trend": "stable"},
    {"name": "GDP Growth", "value": 2.8, "unit": "%", "trend": "rising"},
]


async def _fetch_single_series(client: httpx.AsyncClient, name: str, series_id: str) -> Optional[dict]:
    """Fetch a single FRED series with retry."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 2,
    }
    for attempt in range(2):
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                await asyncio.sleep(1)
                continue
            data = resp.json()
            obs = data.get("observations", [])
            if obs:
                current = float(obs[0]["value"]) if obs[0]["value"] != "." else 0.0
                prev = float(obs[1]["value"]) if len(obs) > 1 and obs[1]["value"] != "." else current
                trend = "rising" if current > prev else ("falling" if current < prev else "stable")
                return {"name": name, "value": round(current, 2), "unit": "%", "trend": trend}
        except Exception as e:
            print(f"[macro_data] Error fetching {name}: {e}")
            if attempt == 0:
                await asyncio.sleep(0.5)
    return None


async def fetch_macro_indicators() -> Optional[List[dict]]:
    """Fetch key macro indicators from FRED concurrently. Returns mock on failure."""
    global _macro_cache

    # Check cache
    if _macro_cache and (_time.time() - _macro_cache[0]) < MACRO_CACHE_TTL:
        return _macro_cache[1]

    if not FRED_API_KEY:
        print("[macro_data] No FRED key. Using mock data.")
        return MOCK_MACRO

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            tasks = [
                _fetch_single_series(client, name, series_id)
                for name, series_id in FRED_SERIES.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        indicators = [r for r in results if isinstance(r, dict)]

        if indicators:
            _macro_cache = (_time.time(), indicators)
            return indicators
    except Exception as e:
        print(f"[macro_data] Error fetching FRED data: {e}")

    return MOCK_MACRO
