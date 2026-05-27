"""
Market data service layer
Abstracts data providers (mock, Alpha Vantage, IEX, etc.)
Allows easy switching between data sources
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.data.mock_data import (
    generate_mock_market_data,
    generate_mock_asset_details,
    generate_mock_forecast,
    generate_mock_analyst_report,
    generate_mock_backtest_summary,
    generate_mock_watchlist,
)
from app.schemas.schemas import (
    MarketMetric,
    AssetDetail,
    CandleData,
    ForecastPoint,
    AnalystReport,
    BacktestResult,
    BacktestMetrics,
    WatchlistItem,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ABSTRACT PROVIDER INTERFACES
# ============================================================================

class MarketDataProvider(ABC):
    """Abstract interface for market data providers"""

    @abstractmethod
    async def get_asset_detail(self, ticker: str) -> dict:
        """Get asset detail information"""
        pass

    @abstractmethod
    async def get_historical_data(self, ticker: str, days: int = 30) -> List[dict]:
        """Get historical OHLCV data"""
        pass

    @abstractmethod
    async def get_market_overview(self, tickers: List[str]) -> List[dict]:
        """Get market overview for multiple tickers"""
        pass


# ============================================================================
# MOCK PROVIDER (Development)
# ============================================================================

class MockMarketDataProvider(MarketDataProvider):
    """Mock market data provider for development"""

    async def get_asset_detail(self, ticker: str) -> dict:
        """Get mock asset details"""
        return generate_mock_asset_details(ticker)

    async def get_historical_data(self, ticker: str, days: int = 30) -> List[dict]:
        """Get mock historical data"""
        return generate_mock_market_data(ticker, days)

    async def get_market_overview(self, tickers: List[str]) -> List[dict]:
        """Get mock market overview"""
        return [
            {
                "symbol": ticker,
                "price": generate_mock_asset_details(ticker)["price"],
                "change": 5.12,
                "change_percent": 0.0325,
                "timestamp": datetime.utcnow().isoformat(),
            }
            for ticker in tickers
        ]


# ============================================================================
# ALPHA VANTAGE PROVIDER (Real Data - Template)
# ============================================================================

class AlphaVantageMarketDataProvider(MarketDataProvider):
    """Alpha Vantage API provider for real market data
    
    Implementation placeholder - to be filled in later
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co"

    async def get_asset_detail(self, ticker: str) -> dict:
        """Get asset details from Alpha Vantage"""
        # TODO: Implement Alpha Vantage API call
        logger.warning(f"AlphaVantage provider not fully implemented for {ticker}")
        raise NotImplementedError("AlphaVantage provider coming soon")

    async def get_historical_data(self, ticker: str, days: int = 30) -> List[dict]:
        """Get historical data from Alpha Vantage"""
        # TODO: Implement Alpha Vantage API call
        raise NotImplementedError("AlphaVantage provider coming soon")

    async def get_market_overview(self, tickers: List[str]) -> List[dict]:
        """Get market overview from Alpha Vantage"""
        # TODO: Implement Alpha Vantage API call
        raise NotImplementedError("AlphaVantage provider coming soon")


# ============================================================================
# SERVICE LAYER
# ============================================================================

class MarketDataService:
    """Service layer for market data operations
    
    Handles:
    - Provider selection and management
    - Data transformation
    - Caching
    - Error handling
    """

    def __init__(self, provider: MarketDataProvider):
        self.provider = provider
        self._cache = {}

    async def get_asset_detail(self, ticker: str) -> AssetDetail:
        """Get asset details with caching"""
        cache_key = f"asset:{ticker}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            data = await self.provider.get_asset_detail(ticker)
            asset = AssetDetail(**data)
            self._cache[cache_key] = asset
            return asset
        except Exception as e:
            logger.error(f"Error getting asset detail for {ticker}: {str(e)}")
            raise

    async def get_historical_data(
        self, ticker: str, days: int = 30
    ) -> List[CandleData]:
        """Get historical OHLCV data"""
        try:
            data = await self.provider.get_historical_data(ticker, days)
            return [
                CandleData(
                    date=datetime.fromisoformat(candle["date"]),
                    open=candle["open"],
                    high=candle["high"],
                    low=candle["low"],
                    close=candle["close"],
                    volume=candle["volume"],
                )
                for candle in data
            ]
        except Exception as e:
            logger.error(f"Error getting historical data for {ticker}: {str(e)}")
            raise

    async def get_market_overview(self, tickers: List[str]) -> List[MarketMetric]:
        """Get market overview for multiple assets"""
        try:
            data = await self.provider.get_market_overview(tickers)
            return [
                MarketMetric(
                    symbol=item["symbol"],
                    price=item["price"],
                    change=item["change"],
                    change_percent=item["change_percent"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                )
                for item in data
            ]
        except Exception as e:
            logger.error(f"Error getting market overview: {str(e)}")
            raise

    def clear_cache(self):
        """Clear cache"""
        self._cache.clear()


def get_market_data_service(provider_type: str = "mock") -> MarketDataService:
    """Factory function to create market data service with specified provider
    
    Args:
        provider_type: "mock", "alpha_vantage", etc.
    
    Returns:
        MarketDataService instance with selected provider
    """
    if provider_type == "mock":
        provider = MockMarketDataProvider()
    elif provider_type == "alpha_vantage":
        # API key should come from settings
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.alpha_vantage_key:
            logger.warning("Alpha Vantage key not configured, falling back to mock")
            provider = MockMarketDataProvider()
        else:
            provider = AlphaVantageMarketDataProvider(settings.alpha_vantage_key)
    else:
        logger.warning(f"Unknown provider {provider_type}, using mock")
        provider = MockMarketDataProvider()

    return MarketDataService(provider)
