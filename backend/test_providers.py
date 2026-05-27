#!/usr/bin/env python3
"""
Test script to verify all real data providers are working with configured API keys

Usage:
    python3 backend/test_providers.py [provider_name] [ticker]
    
Examples:
    python3 backend/test_providers.py alpha_vantage AAPL
    python3 backend/test_providers.py fin_hub MSFT
    python3 backend/test_providers.py all AAPL
"""

import asyncio
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_alpha_vantage(ticker: str = "AAPL"):
    """Test Alpha Vantage provider"""
    print("\n" + "="*60)
    print("Testing Alpha Vantage Provider")
    print("="*60)
    
    from app.core.config import get_settings
    from app.services.real_data_providers import AlphaVantageProvider
    
    settings = get_settings()
    
    if not settings.alpha_vantage_key:
        print("✗ Alpha Vantage API key not configured")
        return
    
    try:
        provider = AlphaVantageProvider(settings.alpha_vantage_key)
        
        print(f"\n1. Testing get_asset_detail('{ticker}')...")
        asset = await provider.get_asset_detail(ticker)
        print(f"   ✓ Got price: ${asset['price']}")
        print(f"   ✓ Change: {asset['change_percent']:.2f}%")
        
        print(f"\n2. Testing get_historical_data('{ticker}', days=5)...")
        candles = await provider.get_historical_data(ticker, days=5)
        print(f"   ✓ Got {len(candles)} candles")
        if candles:
            print(f"   Latest close: ${candles[-1]['close']}")
        
        await provider.close()
        print("\n✓ Alpha Vantage provider working!")
    
    except Exception as e:
        print(f"\n✗ Alpha Vantage error: {str(e)}")


async def test_fin_hub(ticker: str = "AAPL"):
    """Test Fin Hub provider"""
    print("\n" + "="*60)
    print("Testing Fin Hub Provider")
    print("="*60)
    
    from app.core.config import get_settings
    from app.services.real_data_providers import FinHubProvider
    
    settings = get_settings()
    
    if not settings.fin_hub_api_key:
        print("✗ Fin Hub API key not configured")
        return
    
    try:
        provider = FinHubProvider(settings.fin_hub_api_key)
        
        print(f"\n1. Testing get_asset_detail('{ticker}')...")
        asset = await provider.get_asset_detail(ticker)
        print(f"   ✓ Company: {asset.get('name', 'N/A')}")
        print(f"   ✓ Price: ${asset['price']}")
        print(f"   ✓ Change: {asset['change_percent']:.2f}%")
        
        print(f"\n2. Testing get_historical_data('{ticker}', days=5)...")
        candles = await provider.get_historical_data(ticker, days=5)
        print(f"   ✓ Got {len(candles)} candles")
        if candles:
            print(f"   Latest close: ${candles[-1]['close']}")
        
        await provider.close()
        print("\n✓ Fin Hub provider working!")
    
    except Exception as e:
        print(f"\n✗ Fin Hub error: {str(e)}")


async def test_fred():
    """Test FRED provider"""
    print("\n" + "="*60)
    print("Testing FRED Provider")
    print("="*60)
    
    from app.core.config import get_settings
    from app.services.real_data_providers import FREDProvider
    
    settings = get_settings()
    
    if not settings.fred_api_key:
        print("✗ FRED API key not configured")
        return
    
    try:
        provider = FREDProvider(settings.fred_api_key)
        
        print("\nTesting get_economic_data('gdp', days=4)...")
        data = await provider.get_economic_data("gdp", days=4)
        print(f"   ✓ Got {len(data)} data points")
        if data:
            print(f"   Latest value: {data[-1]}")
        
        await provider.close()
        print("\n✓ FRED provider working!")
    
    except Exception as e:
        print(f"\n✗ FRED error: {str(e)}")


async def test_news_api(ticker: str = "AAPL"):
    """Test News API provider"""
    print("\n" + "="*60)
    print("Testing News API Provider")
    print("="*60)
    
    from app.core.config import get_settings
    from app.services.real_data_providers import NewsAPIProvider
    
    settings = get_settings()
    
    if not settings.news_api_key:
        print("✗ News API key not configured")
        return
    
    try:
        provider = NewsAPIProvider(settings.news_api_key)
        
        print(f"\nTesting get_news('{ticker}', limit=3)...")
        articles = await provider.get_news(ticker, limit=3)
        print(f"   ✓ Got {len(articles)} articles")
        if articles:
            print(f"   Latest: {articles[0]['title'][:60]}...")
        
        await provider.close()
        print("\n✓ News API provider working!")
    
    except Exception as e:
        print(f"\n✗ News API error: {str(e)}")


async def test_provider_manager(ticker: str = "AAPL"):
    """Test unified ProviderManager"""
    print("\n" + "="*60)
    print("Testing Provider Manager (Unified Interface)")
    print("="*60)
    
    from app.services.provider_manager import get_provider_manager
    
    try:
        manager = await get_provider_manager()
        
        print(f"\n1. Testing get_asset_detail('{ticker}')...")
        asset = await manager.get_asset_detail(ticker)
        print(f"   ✓ Price: ${asset.get('price', 'N/A')}")
        
        print(f"\n2. Testing get_technical_data('{ticker}')...")
        technical = await manager.get_technical_data(ticker, days=5)
        print(f"   ✓ Status: {technical.get('status')}")
        print(f"   ✓ Indicators: {list(technical.get('indicators', {}).keys())[:3]}")
        
        await manager.close()
        print("\n✓ Provider Manager working!")
    
    except Exception as e:
        print(f"\n✗ Provider Manager error: {str(e)}")


async def main():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# Real Data Provider Test Suite")
    print(f"# {datetime.utcnow().isoformat()}")
    print("#"*60)
    
    ticker = sys.argv[2] if len(sys.argv) > 2 else "AAPL"
    provider = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    
    print(f"\nTesting ticker: {ticker}")
    print(f"Configuration loaded from: .env")
    
    try:
        if provider in ["all", "alpha_vantage", "alpha"]:
            await test_alpha_vantage(ticker)
        
        if provider in ["all", "fin_hub", "finnhub"]:
            await test_fin_hub(ticker)
        
        if provider in ["all", "fred"]:
            await test_fred()
        
        if provider in ["all", "news", "news_api"]:
            await test_news_api(ticker)
        
        if provider in ["all", "manager"]:
            await test_provider_manager(ticker)
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "#"*60)
    print("# Test Complete")
    print("#"*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
