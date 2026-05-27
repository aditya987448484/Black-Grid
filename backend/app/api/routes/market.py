"""
Market overview endpoints
"""
from fastapi import APIRouter, HTTPException
import logging
from datetime import datetime

from app.schemas.schemas import MarketOverviewResponse
from app.services.mock_data import get_mock_market_overview
from app.api.service_factory import ServiceFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["market"])


@router.get(
    "/overview",
    response_model=MarketOverviewResponse,
    summary="Get market overview"
)
async def get_market_overview() -> MarketOverviewResponse:
    """
    Get market overview with top indices and movers
    
    Returns:
    - List of major market indices (S&P 500, NASDAQ, Russell 2000, Dow Jones)
    - Current prices, changes, and percentage changes
    - Market timestamp
    
    Uses real data provider (Alpha Vantage) if configured, otherwise falls back to mock data
    """
    try:
        logger.info("Fetching market overview...")
        
        # Try to get real market data first
        try:
            service = ServiceFactory.get_market_data_service()
            
            # Fetch quotes for major tickers (not indices, as Alpha Vantage doesn't support index symbols)
            major_tickers = ["SPY", "QQQ", "IWM", "VIX"]
            data = []
            
            for ticker in major_tickers:
                try:
                    quote = await service.provider.get_quote(ticker)
                    # Parse response from Alpha Vantage format
                    if "Global Quote" in quote:
                        global_quote = quote["Global Quote"]
                        price = float(global_quote.get("05. price", 0) or 0)
                        if price > 0:  # Only include valid quotes
                            change_str = str(global_quote.get("09. change", 0) or 0)
                            change = float(change_str)
                            change_percent_str = str(global_quote.get("10. change percent", "0%")).strip("%")
                            change_percent = float(change_percent_str or 0) / 100
                            
                            data.append({
                                "symbol": ticker,
                                "price": round(price, 2),
                                "change": round(change, 2),
                                "change_percent": round(change_percent, 6),
                                "timestamp": datetime.utcnow().isoformat()
                            })
                except Exception as e:
                    logger.warning(f"Failed to fetch quote for {ticker}: {str(e)}")
                    continue
            
            # If we got some real data, return it
            if len(data) >= 2:  # We need at least some real data
                logger.info(f"Returning {len(data)} real market quotes")
                return MarketOverviewResponse(
                    status="success",
                    data=data,
                    market_time=datetime.utcnow().isoformat(),
                    total_results=len(data)
                )
        except Exception as e:
            logger.warning(f"Real market data provider failed: {str(e)}")
        
        # Fall back to mock data
        logger.info("Falling back to mock market data")
        overview = get_mock_market_overview()
        return MarketOverviewResponse(**overview)
    
    except Exception as e:
        logger.error(f"Error getting market overview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market overview: {str(e)}"
        )


