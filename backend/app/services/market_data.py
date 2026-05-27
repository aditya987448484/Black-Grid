"""
Market Data Service
Provides stock market data via Alpha Vantage and other sources
Handles OHLCV data, technical indicators, and real-time pricing
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TimeInterval(str, Enum):
    """Time intervals for OHLCV data"""
    INTRADAY_1MIN = "1min"
    INTRADAY_5MIN = "5min"
    INTRADAY_15MIN = "15min"
    INTRADAY_30MIN = "30min"
    INTRADAY_60MIN = "60min"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MarketDataProvider:
    """
    Abstract base for market data providers
    Implementations: AlphaVantageProvider, MockProvider, etc.
    """
    
    async def get_time_series(
        self,
        ticker: str,
        interval: TimeInterval = TimeInterval.DAILY,
        output_size: str = "compact"
    ) -> Dict[str, Any]:
        """Get OHLCV time series data"""
        raise NotImplementedError
    
    async def get_intraday(
        self,
        ticker: str,
        interval: TimeInterval = TimeInterval.INTRADAY_5MIN
    ) -> Dict[str, Any]:
        """Get intraday OHLCV data"""
        raise NotImplementedError
    
    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote data"""
        raise NotImplementedError


class AlphaVantageProvider(MarketDataProvider):
    """
    Alpha Vantage API integration for stock market data
    https://www.alphavantage.co/
    
    Free tier: 5 requests/minute, 500 requests/day
    Supports: OHLCV, technical indicators, intraday data
    """
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.alpha_vantage_key
        self.base_url = settings.alpha_vantage_base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured. Provider will not work.")
    
    async def get_time_series(
        self,
        ticker: str,
        interval: TimeInterval = TimeInterval.DAILY,
        output_size: str = "compact"
    ) -> Dict[str, Any]:
        """
        Get daily, weekly, or monthly OHLCV data
        
        Args:
            ticker: Stock ticker (e.g., "AAPL")
            interval: TimeInterval enum
            output_size: "compact" (100 latest data points) or "full" (all data)
        
        Returns:
            Dictionary with time series data
        """
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not configured")
        
        try:
            function_map = {
                TimeInterval.DAILY: "TIME_SERIES_DAILY_ADJUSTED",
                TimeInterval.WEEKLY: "TIME_SERIES_WEEKLY_ADJUSTED",
                TimeInterval.MONTHLY: "TIME_SERIES_MONTHLY_ADJUSTED",
            }
            
            function = function_map.get(interval)
            if not function:
                raise ValueError(f"Unsupported interval: {interval}")
            
            params = {
                "function": function,
                "symbol": ticker.upper(),
                "outputsize": output_size,
                "apikey": self.api_key,
            }
            
            response = await self.client.get(
                f"{self.base_url}/query",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                raise ValueError("Rate limit reached")
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching time series for {ticker}: {str(e)}")
            raise
    
    async def get_intraday(
        self,
        ticker: str,
        interval: TimeInterval = TimeInterval.INTRADAY_5MIN
    ) -> Dict[str, Any]:
        """
        Get intraday OHLCV data
        
        Args:
            ticker: Stock ticker
            interval: Intraday interval (1min, 5min, 15min, 30min, 60min)
        
        Returns:
            Dictionary with intraday time series
        """
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not configured")
        
        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": ticker.upper(),
                "interval": interval.value,
                "outputsize": "full",
                "apikey": self.api_key,
            }
            
            response = await self.client.get(
                f"{self.base_url}/query",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                raise ValueError("Rate limit reached")
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching intraday data for {ticker}: {str(e)}")
            raise
    
    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get real-time quote data
        
        Args:
            ticker: Stock ticker
        
        Returns:
            Quote with price, volume, bid/ask
        """
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not configured")
        
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": ticker.upper(),
                "apikey": self.api_key,
            }
            
            response = await self.client.get(
                f"{self.base_url}/query",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching quote for {ticker}: {str(e)}")
            raise
    
    async def get_technical_indicator(
        self,
        function: str,  # e.g., "SMA", "EMA", "RSI", "MACD", "BBANDS"
        ticker: str,
        interval: TimeInterval = TimeInterval.DAILY,
        time_period: int = 20
    ) -> Dict[str, Any]:
        """
        Get technical indicator data
        
        Args:
            function: Indicator function (SMA, EMA, RSI, MACD, BBANDS, etc.)
            ticker: Stock ticker
            interval: Time interval for calculation
            time_period: Period for indicator calculation
        
        Returns:
            Technical indicator values
        """
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not configured")
        
        try:
            params = {
                "function": function.upper(),
                "symbol": ticker.upper(),
                "interval": interval.value,
                "time_period": time_period,
                "apikey": self.api_key,
            }
            
            response = await self.client.get(
                f"{self.base_url}/query",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                raise ValueError("Rate limit reached")
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching {function} for {ticker}: {str(e)}")
            raise
    
    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()


class MarketDataService:
    """
    Service layer for market data
    Provides high-level methods for data retrieval and caching
    """
    
    def __init__(self, provider: Optional[MarketDataProvider] = None):
        """
        Initialize service
        
        Args:
            provider: Market data provider instance (defaults to Alpha Vantage)
        """
        settings = get_settings()
        
        if provider:
            self.provider = provider
        elif settings.market_data_provider == "alpha_vantage":
            self.provider = AlphaVantageProvider()
        else:
            # Fallback to mock provider
            logger.warning(f"Using mock provider (configured: {settings.market_data_provider})")
            self.provider = MockMarketDataProvider()
    
    async def get_daily_ohlcv(self, ticker: str) -> Dict[str, Any]:
        """Get daily OHLCV data for ticker"""
        return await self.provider.get_time_series(
            ticker,
            interval=TimeInterval.DAILY,
            output_size="full"
        )
    
    async def get_intraday_ohlcv(self, ticker: str) -> Dict[str, Any]:
        """Get intraday 5-minute OHLCV data"""
        return await self.provider.get_intraday(
            ticker,
            interval=TimeInterval.INTRADAY_5MIN
        )
    
    async def get_current_quote(self, ticker: str) -> Dict[str, Any]:
        """Get current price quote"""
        return await self.provider.get_quote(ticker)
    
    async def close(self):
        """Cleanup resources"""
        if hasattr(self.provider, 'close'):
            await self.provider.close()


class MockMarketDataProvider(MarketDataProvider):
    """Mock implementation for development and testing"""
    
    async def get_time_series(
        self,
        ticker: str,
        interval: TimeInterval = TimeInterval.DAILY,
        output_size: str = "compact"
    ) -> Dict[str, Any]:
        """Return mock OHLCV data"""
        return {
            "Meta Data": {
                "1. Information": "Daily Prices (adjusted)",
                "2. Symbol": ticker.upper(),
                "3. Last Refreshed": datetime.now().isoformat(),
                "4. Interval": interval.value,
            },
            "Time Series": {
                "2024-03-01": {
                    "1. open": "150.00",
                    "2. high": "152.50",
                    "3. low": "149.50",
                    "4. close": "151.25",
                    "5. adjusted close": "151.25",
                    "6. volume": "52000000",
                },
                "2024-02-29": {
                    "1. open": "148.75",
                    "2. high": "151.00",
                    "3. low": "148.50",
                    "4. close": "150.00",
                    "5. adjusted close": "150.00",
                    "6. volume": "47000000",
                },
            }
        }
    
    async def get_intraday(
        self,
        ticker: str,
        interval: TimeInterval = TimeInterval.INTRADAY_5MIN
    ) -> Dict[str, Any]:
        """Return mock intraday data"""
        return {
            "Meta Data": {
                "1. Information": "Intraday Prices",
                "2. Symbol": ticker.upper(),
                "3. Last Refreshed": datetime.now().isoformat(),
                "4. Interval": interval.value,
            },
            "Time Series (5min)": {
                "2024-03-01 15:55:00": {
                    "1. open": "150.50",
                    "2. high": "150.75",
                    "3. low": "150.25",
                    "4. close": "150.60",
                    "5. volume": "500000",
                },
            }
        }
    
    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Return mock quote"""
        return {
            "Global Quote": {
                "01. symbol": ticker.upper(),
                "05. price": "151.25",
                "08. previous close": "150.00",
                "09. change": "1.25",
                "10. change percent": "0.8333%",
                "06. volume": "52000000",
            }
        }
