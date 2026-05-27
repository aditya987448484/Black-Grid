"""
Quick Start Guide - Using Real API Providers

This guide shows you how to immediately start using real financial data APIs
"""

# ============================================================================
# STEP 1: Setup
# ============================================================================

"""
1. Copy the .env template:
   $ cp .env.example .env

2. Edit .env with your actual API keys:
   ALPHA_VANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_API_KEY
   FRED_API_KEY=YOUR_FRED_API_KEY
   FIN_HUB_API_KEY=YOUR_FINHUB_API_KEY
   NEWS_API_KEY=139f0bcd5fa848998c2b327b5129d8fb
   GROQ_API_KEY=YOUR_GROQ_API_KEY

3. Verify .env is in .gitignore (already done)
   $ grep ".env" .gitignore
"""


# ============================================================================
# STEP 2: Use in Routes
# ============================================================================

"""
Option A: Use ProviderManager (recommended - with fallback to mock)
"""

# In your route file:
from app.services.provider_manager import get_provider_manager
from fastapi import APIRouter, HTTPException, Path

router = APIRouter()

@router.get("/{ticker}", tags=["asset"])
async def get_asset_detail(ticker: str = Path(..., min_length=1, max_length=10)):
    try:
        manager = await get_provider_manager()
        asset = await manager.get_asset_detail(ticker)
        return {
            "status": "success",
            "data": asset,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Option B: Use Provider Directly
from app.services.real_data_providers import FinHubProvider
from app.core.config import get_settings

@router.get("/{ticker}/tech", tags=["asset"])
async def get_technicals(ticker: str):
    try:
        settings = get_settings()
        
        if settings.fin_hub_api_key:
            provider = FinHubProvider(settings.fin_hub_api_key)
            data = await provider.get_historical_data(ticker, days=30)
            await provider.close()
            
            return {
                "status": "success",
                "ticker": ticker,
                "data": data
            }
        else:
            # Fallback to mock
            from app.services import mock_data
            return mock_data.get_mock_technical_data(ticker)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STEP 3: Configure Which Provider to Use
# ============================================================================

"""
In .env file:
MARKET_DATA_PROVIDER=fin_hub  # Switch between: mock, alpha_vantage, fin_hub

Or in code:
from app.core.config import get_settings
settings = get_settings()
print(f"Using provider: {settings.market_data_provider}")
"""


# ============================================================================
# STEP 4: Test Your Integration
# ============================================================================

"""
Test with curl:

# Get asset detail (uses real API if configured)
curl http://localhost:8000/api/asset/AAPL

# Get technicals
curl http://localhost:8000/api/asset/AAPL/technicals

# Get forecast
curl http://localhost:8000/api/asset/AAPL/forecast

# Get analyst report (uses Groq AI if configured)
curl http://localhost:8000/api/report/AAPL
"""


# ============================================================================
# STEP 5: Monitor API Usage
# ============================================================================

"""
Keep track of your API rate limits:

Alpha Vantage:
  - Free: 5 requests/minute, 500/day
  - Check at: https://www.alphavantage.co/

FRED:
  - Free: 120 requests/minute, unlimited
  - Check at: https://fred.stlouisfed.org/docs/api/

Fin Hub:
  - Free: 60 requests/minute
  - Check at: https://finnhub.io/docs/api

News API:
  - Free: 100 requests/day
  - Check at: https://newsapi.org/

Groq:
  - Free tier: 30 requests/minute
  - Check at: https://console.groq.com/
"""


# ============================================================================
# STEP 6: Add Caching (Recommended)
# ============================================================================

"""
To reduce API calls and stay within rate limits, add caching:

from functools import lru_cache
from datetime import datetime, timedelta

class CachedProvider:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
    
    async def get_asset_detail(self, ticker: str, ttl_seconds: int = 300):
        now = datetime.utcnow()
        
        # Check cache
        if ticker in self.cache:
            cache_age = (now - self.cache_time[ticker]).total_seconds()
            if cache_age < ttl_seconds:
                return self.cache[ticker]
        
        # Fetch fresh
        manager = await get_provider_manager()
        data = await manager.get_asset_detail(ticker)
        
        # Store in cache
        self.cache[ticker] = data
        self.cache_time[ticker] = now
        
        return data
"""


# ============================================================================
# STEP 7: Error Handling
# ============================================================================

"""
Always handle API failures gracefully:

async def get_market_data(ticker: str):
    try:
        # Try real provider
        manager = await get_provider_manager()
        data = await manager.get_asset_detail(ticker)
        return data
    
    except TimeoutError:
        logger.warning(f"API timeout for {ticker}, using mock data")
        return mock_data.get_mock_asset_detail(ticker)
    
    except ValueError as e:
        logger.error(f"Invalid ticker {ticker}: {str(e)}")
        return {
            "status": "error",
            "detail": f"Invalid ticker: {ticker}"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "status": "error",
            "detail": "Failed to fetch data, using mock"
        }
"""


# ============================================================================
# SUMMARY
# ============================================================================

"""
Real Data Provider Setup Checklist:

✓ Created .env.example template
✓ Created .gitignore to exclude .env
✓ Created real_data_providers.py with Alpha Vantage, FRED, Fin Hub, News API
✓ Created groq_provider.py for AI analyst reports
✓ Created provider_manager.py for unified interface
✓ Updated config.py to support all API keys

Next steps:

1. Create .env file with your API keys
2. Update MARKET_DATA_PROVIDER in .env to use real providers
3. Test one endpoint to verify it works
4. Enable Groq for AI-powered analyst reports (optional)
5. Implement caching to optimize API usage
6. Monitor costs and rate limits

Your system is now ready to seamlessly switch between mock and real data!
"""
