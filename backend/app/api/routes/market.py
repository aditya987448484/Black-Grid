"""
Market overview endpoints
"""
from fastapi import APIRouter, HTTPException
import logging
from datetime import datetime

from app.schemas.schemas import MarketOverviewResponse
from app.services.price_service import get_prices_bulk

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["market"])

MARKET_TICKERS = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "META"]


@router.get(
    "/overview",
    response_model=MarketOverviewResponse,
    summary="Get market overview"
)
async def get_market_overview() -> MarketOverviewResponse:
    """
    Get market overview with major indices and key equities.

    Returns real-time prices via yfinance (Alpha Vantage and mock fallbacks).
    Tickers returned: SPY, QQQ, IWM, AAPL, MSFT, NVDA, TSLA, META.
    """
    try:
        logger.info("Fetching market overview via price_service…")
        now = datetime.utcnow().isoformat()

        price_list = await get_prices_bulk(MARKET_TICKERS)

        data = [
            {
                "symbol":         p["symbol"],
                "price":          p["price"],
                "change":         p["change"],
                "change_percent": p["change_percent"],
                "timestamp":      now,
            }
            for p in price_list
        ]

        logger.info(f"Returning {len(data)} market quotes")
        return MarketOverviewResponse(
            status="success",
            data=data,
            market_time=now,
            total_results=len(data),
        )

    except Exception as e:
        logger.error(f"Error getting market overview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market overview: {str(e)}",
        )


