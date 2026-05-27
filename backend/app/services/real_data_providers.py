"""
Real financial data providers using external APIs
Replace mock data providers with these for production data integration

Supported providers:
- Alpha Vantage - Stock market data, technicals, indicators
- FRED - Federal Reserve economic data
- Fin Hub - Financial data aggregator
- News API - Financial news articles
"""

import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ============================================================================
# BASE PROVIDER INTERFACE
# ============================================================================

class RealDataProvider(ABC):
    """Abstract base class for real data providers"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    @abstractmethod
    async def get_asset_detail(self, ticker: str) -> Dict[str, Any]:
        """Get asset detail information"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, ticker: str, days: int) -> List[Dict]:
        """Get historical OHLCV data"""
        pass


# ============================================================================
# ALPHA VANTAGE PROVIDER
# ============================================================================

class AlphaVantageProvider(RealDataProvider):
    """Alpha Vantage API implementation for stock market data"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://www.alphavantage.co")
    
    async def get_asset_detail(self, ticker: str) -> Dict[str, Any]:
        """
        Get current asset price and basic info from Alpha Vantage
        
        Returns: {ticker, price, previous_close, change, change_percent}
        """
        try:
            # Use GLOBAL_QUOTE endpoint for current price
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": ticker,
                "apikey": self.api_key
            }
            
            response = await self.client.get(
                f"{self.base_url}/query",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            quote = data.get("Global Quote", {})
            
            # Parse Alpha Vantage response
            return {
                "ticker": ticker,
                "price": float(quote.get("05. price", 0)),
                "previous_close": float(quote.get("08. previous close", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": float(quote.get("10. change percent", "0").rstrip("%")),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Alpha Vantage error getting {ticker}: {str(e)}")
            raise
    
    async def get_historical_data(self, ticker: str, days: int = 30) -> List[Dict]:
        """
        Get historical daily data from Alpha Vantage
        
        Returns: List of {date, open, high, low, close, volume}
        """
        try:
            # Use TIME_SERIES_DAILY for historical data
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": "full" if days > 100 else "compact",
                "apikey": self.api_key
            }
            
            response = await self.client.get(
                f"{self.base_url}/query",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            time_series = data.get("Time Series (Daily)", {})
            candles = []
            
            for date_str, values in list(time_series.items())[:days]:
                candles.append({
                    "date": date_str,
                    "open": float(values.get("1. open", 0)),
                    "high": float(values.get("2. high", 0)),
                    "low": float(values.get("3. low", 0)),
                    "close": float(values.get("4. close", 0)),
                    "volume": int(values.get("5. volume", 0))
                })
            
            return list(reversed(candles))  # Return oldest first
        except Exception as e:
            logger.error(f"Alpha Vantage error getting history for {ticker}: {str(e)}")
            raise


# ============================================================================
# FRED PROVIDER (Federal Reserve Economic Data)
# ============================================================================

class FREDProvider:
    """FRED API for macroeconomic data"""
    
    # Common economic indicators
    SERIES_MAP = {
        "gdp": "A191RL1Q225SBEA",  # Real GDP
        "unemployment": "UNRATE",   # Unemployment rate
        "inflation": "CPIAUCSL",    # CPI
        "fed_funds": "FEDFUNDS",    # Federal funds rate
        "10y_yield": "DGS10",       # 10-year Treasury yield
        "recession": "USRECM"       # Recession indicator
    }
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_economic_data(self, indicator: str, days: int = 90) -> List[Dict]:
        """Get economic data series by indicator"""
        try:
            series_id = self.SERIES_MAP.get(indicator, indicator)
            
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json"
            }
            
            response = await self.client.get(
                f"{self.base_url}/series/observations",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            observations = data.get("observations", [])
            return observations[-days:] if days > 0 else observations
        except Exception as e:
            logger.error(f"FRED error getting {indicator}: {str(e)}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# ============================================================================
# FIN HUB PROVIDER
# ============================================================================

class FinHubProvider(RealDataProvider):
    """Fin Hub API for financial data aggregation"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://finnhub.io/api/v1")
    
    async def get_asset_detail(self, ticker: str) -> Dict[str, Any]:
        """
        Get company profile and quote from Fin Hub
        
        Returns: {ticker, name, price, market_cap, pe_ratio, dividend_yield}
        """
        try:
            # Get quote
            quote_params = {
                "symbol": ticker,
                "token": self.api_key
            }
            
            quote_response = await self.client.get(
                f"{self.base_url}/quote",
                params=quote_params
            )
            quote_response.raise_for_status()
            quote = quote_response.json()
            
            # Get company profile
            profile_params = {
                "symbol": ticker,
                "token": self.api_key
            }
            
            profile_response = await self.client.get(
                f"{self.base_url}/stock/profile2",
                params=profile_params
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
            
            return {
                "ticker": ticker,
                "name": profile.get("name", ""),
                "price": quote.get("c", 0),  # current price
                "change": quote.get("d", 0),  # change
                "change_percent": quote.get("dp", 0),  # change percent
                "market_cap": profile.get("marketCapitalization", 0),
                "pe_ratio": profile.get("pe", None),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Fin Hub error getting {ticker}: {str(e)}")
            raise
    
    async def get_historical_data(self, ticker: str, days: int = 30) -> List[Dict]:
        """Get historical candle data from Fin Hub"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days+10)
            
            params = {
                "symbol": ticker,
                "resolution": "D",  # Daily
                "from": int(start_date.timestamp()),
                "to": int(end_date.timestamp()),
                "token": self.api_key
            }
            
            response = await self.client.get(
                f"{self.base_url}/stock/candle",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("s") != "ok":
                raise Exception(f"Fin Hub error: {data.get('s')}")
            
            candles = []
            for i in range(len(data.get("o", []))):
                candles.append({
                    "date": datetime.fromtimestamp(data["t"][i]).isoformat(),
                    "open": data["o"][i],
                    "high": data["h"][i],
                    "low": data["l"][i],
                    "close": data["c"][i],
                    "volume": data.get("v", [0])[i]
                })
            
            return candles[-days:] if days > 0 else candles
        except Exception as e:
            logger.error(f"Fin Hub error getting history for {ticker}: {str(e)}")
            raise


# ============================================================================
# NEWS API PROVIDER
# ============================================================================

class NewsAPIProvider:
    """News API for financial news articles"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_news(self, ticker: str, limit: int = 10) -> List[Dict]:
        """Get news articles for a ticker"""
        try:
            params = {
                "q": f"{ticker} stock",
                "sortBy": "publishedAt",
                "pageSize": limit,
                "apiKey": self.api_key
            }
            
            response = await self.client.get(
                f"{self.base_url}/everything",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "published_at": article.get("publishedAt", ""),
                    "image": article.get("urlToImage", "")
                })
            
            return articles
        except Exception as e:
            logger.error(f"News API error for {ticker}: {str(e)}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def get_real_data_provider(provider_type: str, api_key: str):
    """
    Factory function to get real data provider instance
    
    Args:
        provider_type: 'alpha_vantage', 'fin_hub', etc.
        api_key: API key for the provider
    
    Returns:
        Configured provider instance
    """
    if provider_type.lower() == "alpha_vantage":
        return AlphaVantageProvider(api_key)
    elif provider_type.lower() == "fin_hub":
        return FinHubProvider(api_key)
    elif provider_type.lower() == "fred":
        return FREDProvider(api_key)
    elif provider_type.lower() == "news":
        return NewsAPIProvider(api_key)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
