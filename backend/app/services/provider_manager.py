"""
Provider integration examples and utilities
Demonstrates how to use real data providers with fallback to mock data
"""

import logging
from typing import Optional, Dict, Any, List
from app.core.config import get_settings
from app.services import mock_data
from app.services.real_data_providers import (
    AlphaVantageProvider,
    FinHubProvider,
    FREDProvider,
    NewsAPIProvider
)

logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Manager for switching between mock and real data providers
    Provides fallback to mock data if real API fails
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._providers = {}
    
    async def get_asset_detail(self, ticker: str) -> Dict[str, Any]:
        """Get asset detail with fallback to mock data"""
        
        if self.settings.market_data_provider == "mock":
            logger.info(f"Using mock data for {ticker}")
            response = mock_data.get_mock_asset_detail(ticker)
            return response["data"]
        
        try:
            # Try real provider
            if self.settings.market_data_provider == "alpha_vantage":
                if "alpha_vantage" not in self._providers:
                    self._providers["alpha_vantage"] = AlphaVantageProvider(
                        self.settings.alpha_vantage_key
                    )
                provider = self._providers["alpha_vantage"]
                data = await provider.get_asset_detail(ticker)
                return data
            
            elif self.settings.market_data_provider == "fin_hub":
                if "fin_hub" not in self._providers:
                    self._providers["fin_hub"] = FinHubProvider(
                        self.settings.fin_hub_api_key
                    )
                provider = self._providers["fin_hub"]
                return await provider.get_asset_detail(ticker)
        
        except Exception as e:
            logger.warning(f"Real provider failed for {ticker}: {str(e)}, falling back to mock")
            response = mock_data.get_mock_asset_detail(ticker)
            return response["data"]
    
    async def get_technical_data(self, ticker: str, days: int = 30) -> Dict[str, Any]:
        """Get technical data with fallback"""
        
        if self.settings.market_data_provider == "mock":
            return mock_data.get_mock_technical_data(ticker, num_candles=days)
        
        try:
            if self.settings.market_data_provider == "alpha_vantage":
                if "alpha_vantage" not in self._providers:
                    self._providers["alpha_vantage"] = AlphaVantageProvider(
                        self.settings.alpha_vantage_key
                    )
                provider = self._providers["alpha_vantage"]
                candles = await provider.get_historical_data(ticker, days)
                
                # Convert to schema format
                from app.services.indicator_service import IndicatorService
                prices = [c["close"] for c in candles]
                highs = [c["high"] for c in candles]
                lows = [c["low"] for c in candles]
                
                indicators = IndicatorService.calculate_agg_indicators(prices, highs, lows)
                
                return {
                    "status": "success",
                    "ticker": ticker,
                    "data": candles,
                    "indicators": indicators
                }
        
        except Exception as e:
            logger.warning(f"Real provider failed for {ticker}: {str(e)}, falling back to mock")
            return mock_data.get_mock_technical_data(ticker, num_candles=days)
    
    async def get_forecast(self, ticker: str, days: int = 30) -> Dict[str, Any]:
        """Get forecast - currently mock only, ready for real ML integration"""
        # Real forecast would come from actual ML models
        return mock_data.get_mock_forecast(ticker, horizon_days=days)
    
    async def get_analyst_report(self, ticker: str) -> Dict[str, Any]:
        """Get analyst report with optional Groq AI generation"""
        
        # Check if Groq is configured
        if self.settings.groq_api_key:
            try:
                from app.services.groq_provider import GroqAnalystProvider
                groq = GroqAnalystProvider(self.settings.groq_api_key)
                
                # Get market context
                asset = await self.get_asset_detail(ticker)
                technical = await self.get_technical_data(ticker)
                
                context = {
                    "price": asset.get("price", 0),
                    "pe_ratio": asset.get("pe_ratio"),
                    "market_cap": asset.get("market_cap"),
                    "dividend_yield": asset.get("dividend_yield")
                }
                
                # Generate report using Groq
                report_text = await groq.generate_analyst_report(ticker, context)
                logger.info(f"Generated AI report for {ticker} using Groq")
                
                await groq.close()
                
                # Return in schema format
                return {
                    "status": "success",
                    "data": {
                        "ticker": ticker,
                        "company_name": asset.get("name", ticker),
                        "report_date": mock_data.datetime.utcnow().isoformat(),
                        "current_price": asset.get("price", 0),
                        "executive_summary": report_text[:500],
                        "ai_generated": True,
                        "full_report": report_text
                    }
                }
            
            except Exception as e:
                logger.warning(f"Groq report generation failed: {str(e)}, using mock")
        
        # Fallback to mock
        return mock_data.get_mock_analyst_report(ticker)
    
    async def get_news(self, ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get news articles for ticker"""
        
        if not self.settings.news_api_key:
            logger.info(f"News API not configured, returning empty news for {ticker}")
            return []
        
        try:
            provider = NewsAPIProvider(self.settings.news_api_key)
            news = await provider.get_news(ticker, limit)
            await provider.close()
            return news
        
        except Exception as e:
            logger.warning(f"News API failed for {ticker}: {str(e)}")
            return []
    
    async def get_economic_data(self, indicator: str, days: int = 90) -> List[Dict]:
        """Get economic data from FRED"""
        
        if not self.settings.fred_api_key:
            logger.info(f"FRED not configured, returning empty data for {indicator}")
            return []
        
        try:
            provider = FREDProvider(self.settings.fred_api_key)
            data = await provider.get_economic_data(indicator, days)
            await provider.close()
            return data
        
        except Exception as e:
            logger.warning(f"FRED failed for {indicator}: {str(e)}")
            return []
    
    async def close(self):
        """Close all provider connections"""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()


# Global manager instance
_manager: Optional[ProviderManager] = None


async def get_provider_manager() -> ProviderManager:
    """Get or create global provider manager"""
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager
