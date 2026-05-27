"""
Portfolio and watchlist endpoints
"""
from fastapi import APIRouter, HTTPException, Query
import logging
from typing import List, Optional
from datetime import datetime

from app.schemas.schemas import (
    WatchlistResponse,
    WatchlistIntelligenceResponse,
    WatchlistIntelligenceItem,
)
from app.services.mock_data import get_mock_watchlist_items
from app.services.portfolio_service import PortfolioService
from app.api.service_factory import ServiceFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get(
    "/watchlist",
    response_model=WatchlistResponse,
    summary="Get watchlist"
)
async def get_watchlist(
    historical_days: int = Query(252, description="Days of historical data for analysis")
) -> WatchlistResponse:
    """
    Get user's watchlist with current prices and changes
    
    Returns:
    - List of watchlist items (tickers, prices, changes)
    - Total items count
    - Last update timestamp
    
    Uses real market data from portfolio intelligence service when available,
    gracefully falls back to mock data if service unavailable
    """
    try:
        # Default watchlist tickers
        ticker_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        
        # Try to get real intelligence data
        try:
            market_service = ServiceFactory.get_market_data_service()
            portfolio_service = PortfolioService(market_service)
            
            intelligence_items = await portfolio_service.analyze_watchlist(
                tickers=ticker_list,
                historical_days=historical_days,
            )
            
            # Convert intelligence items to basic WatchlistItem format for response
            items = [
                {
                    "ticker": item.ticker,
                    "name": item.name,
                    "current_price": round(item.current_price, 2),
                    "change_24h": round(item.change_24h, 2) if item.change_24h is not None else 0.0,
                    "added_date": item.added_date,
                }
                for item in intelligence_items if item is not None
            ]
            
            logger.info(f"Fetched {len(items)} watchlist items with real market data")
            
            return WatchlistResponse(
                status="success",
                data=items,
                total_items=len(items),
                updated_at=datetime.utcnow(),
            )
        
        except Exception as e:
            logger.warning(f"Real market data failed: {str(e)}. Falling back to mock data")
            # Fall back to mock data
            watchlist = get_mock_watchlist_items()
            mock_items = [
                {
                    "ticker": item.get("ticker", ""),
                    "name": item.get("name", ""),
                    "current_price": float(item.get("current_price", 0)),
                    "change_24h": float(item.get("change_24h", 0)),
                    "added_date": datetime.fromisoformat(item.get("added_date", datetime.utcnow().isoformat())),
                }
                for item in watchlist.get("data", [])
            ]
            
            return WatchlistResponse(
                status="success",
                data=mock_items,
                total_items=len(mock_items),
                updated_at=datetime.utcnow(),
            )
    
    except Exception as e:
        logger.error(f"Error fetching watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch watchlist")


@router.get(
    "/watchlist/intelligence",
    summary="Get watchlist with intelligence metrics"
)
async def get_watchlist_intelligence(
    tickers: Optional[str] = Query(None, description="Comma-separated list of tickers (e.g., AAPL,MSFT,GOOGL)"),
    historical_days: int = Query(252, description="Days of historical data for risk calculation"),
) -> dict:
    """
    Get watchlist items with intelligence metrics
    
    Includes:
    - Signal scores (BUY/HOLD/SELL from forecasts)
    - Confidence scores (model agreement)
    - Risk scores (volatility, drawdown)
    - Period changes (1D, 5D, 1M)
    - Alert status and messages
    - Allocation suggestions
    
    Args:
        tickers: Space or comma-separated list of tickers
        historical_days: Days of data for analysis (default 252 = 1 year)
    
    Returns:
        Enhanced watchlist with intelligence metrics for portfolio analysis
    
    Example:
        GET /api/portfolio/watchlist/intelligence?tickers=AAPL,MSFT,GOOGL&historical_days=252
    """
    try:
        # Parse tickers
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.replace(" ", ",").split(",") if t.strip()]
        else:
            # Default to common watchlist
            ticker_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        
        if not ticker_list:
            raise ValueError("No tickers provided")
        
        logger.info(f"Analyzing {len(ticker_list)} tickers with intelligence metrics")
        
        # Get portfolio service
        market_service = ServiceFactory.get_market_data_service()
        portfolio_service = PortfolioService(market_service)
        
        # Analyze watchlist - returns intelligence items directly
        intelligence_items = await portfolio_service.analyze_watchlist(
            tickers=ticker_list,
            historical_days=historical_days,
        )
        
        # Convert to response format
        items_data = [
            {
                "ticker": item.ticker,
                "name": item.name,
                "current_price": round(item.current_price, 2),
                "change_24h": round(item.change_24h, 2),
                "added_date": item.added_date.isoformat(),
                "signal_score": round(item.signal_score, 2) if item.signal_score is not None else None,
                "confidence_score": round(item.confidence_score, 2) if item.confidence_score is not None else None,
                "risk_score": round(item.risk_score, 2) if item.risk_score is not None else None,
                "period_changes": item.period_changes.to_dict() if item.period_changes else None,
                "alert_level": item.alert_level,
                "alert_message": item.alert_message,
                "allocation_weight": round(item.allocation_weight, 2) if item.allocation_weight is not None else None,
            }
            for item in intelligence_items
        ]
        
        return {
            "status": "success",
            "data": items_data,
            "total_items": len(items_data),
            "updated_at": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error analyzing watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze watchlist: {str(e)}")



