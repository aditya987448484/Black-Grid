"""Portfolio/watchlist intelligence service."""

from __future__ import annotations

import random
from app.services.mock_data import get_asset_info, mock_watchlist


async def get_watchlist_intelligence() -> dict:
    """Generate watchlist intelligence across multiple tickers."""
    # For now, use mock data. When live providers are ready,
    # this will aggregate signals from forecast + technicals per ticker.
    return mock_watchlist()
