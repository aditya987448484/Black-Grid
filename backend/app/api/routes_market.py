"""Market overview routes — live data with mock fallback."""

from __future__ import annotations

from fastapi import APIRouter
from app.schemas.market import MarketOverviewResponse
from app.services.mock_data import mock_market_overview
from app.services.macro_data import fetch_macro_indicators
from app.services.market_data import fetch_quote

router = APIRouter(prefix="/api/market", tags=["market"])

INDEX_SYMBOLS = [
    {"symbol": "SPY", "name": "S&P 500"},
    {"symbol": "QQQ", "name": "Nasdaq 100"},
    {"symbol": "IWM", "name": "Russell 2000"},
    {"symbol": "DIA", "name": "Dow Jones"},
    {"symbol": "GLD", "name": "Gold"},
]


@router.get("/overview", response_model=MarketOverviewResponse)
async def market_overview():
    data = mock_market_overview()

    # Enrich indices with live quotes
    for idx_meta in INDEX_SYMBOLS:
        quote = await fetch_quote(idx_meta["symbol"])
        if quote:
            for i, idx in enumerate(data["indices"]):
                if idx["symbol"] == idx_meta["symbol"]:
                    data["indices"][i]["price"] = quote["price"]
                    data["indices"][i]["change"] = quote["change"]
                    data["indices"][i]["changePercent"] = quote["changePercent"]
                    if quote.get("volume"):
                        data["indices"][i]["volume"] = quote["volume"]
                    break

    # Enrich watchlist with live quotes
    for i, item in enumerate(data["watchlist"]):
        quote = await fetch_quote(item["ticker"])
        if quote:
            data["watchlist"][i]["price"] = quote["price"]
            data["watchlist"][i]["change1d"] = quote["changePercent"]

    # Try to enrich with live macro data
    live_macro = await fetch_macro_indicators()
    if live_macro:
        data["macro"] = live_macro

    return data
