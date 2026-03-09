"""FRED macro data service with fallback to mock."""

from __future__ import annotations

from typing import Optional, List
import httpx
from app.core.config import FRED_API_KEY


FRED_SERIES = {
    "10Y Treasury": "DGS10",
    "Fed Funds Rate": "FEDFUNDS",
    "CPI YoY": "CPIAUCSL",
    "Unemployment": "UNRATE",
    "GDP Growth": "A191RL1Q225SBEA",
}


async def fetch_macro_indicators() -> Optional[List[dict]]:
    """Fetch key macro indicators from FRED. Returns None on failure."""
    if not FRED_API_KEY:
        print("[macro_data] No FRED key. Using mock data.")
        return None

    results = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for name, series_id in FRED_SERIES.items():
                url = "https://api.stlouisfed.org/fred/series/observations"
                params = {
                    "series_id": series_id,
                    "api_key": FRED_API_KEY,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 2,
                }
                resp = await client.get(url, params=params)
                data = resp.json()
                obs = data.get("observations", [])
                if obs:
                    current = float(obs[0]["value"]) if obs[0]["value"] != "." else 0.0
                    prev = float(obs[1]["value"]) if len(obs) > 1 and obs[1]["value"] != "." else current
                    trend = "rising" if current > prev else ("falling" if current < prev else "stable")
                    results.append({
                        "name": name,
                        "value": round(current, 2),
                        "unit": "%",
                        "trend": trend,
                    })
    except Exception as e:
        print(f"[macro_data] Error fetching FRED data: {e}")
        return None

    return results if results else None
