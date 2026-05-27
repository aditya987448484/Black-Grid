#!/usr/bin/env python3
"""Quick test script to verify service integration"""

import sys
sys.path.insert(0, '/Users/adityapareek/BlackGrid/backend')

from app.core.config import get_settings
from app.api.service_factory import ServiceFactory

print("Testing Service Integration...")
print("=" * 70)

# Test settings
settings = get_settings()
print("✓ Settings loaded successfully")
print(f"  Database: {settings.database_url}")
print(f"  Market Provider: {settings.market_data_provider}")
print(f"  Alpha Vantage Key: {'✓ Configured' if settings.alpha_vantage_key else '✗ Not configured'}")
print(f"  FRED Key: {'✓ Configured' if settings.fred_api_key else '✗ Not configured'}")
print(f"  Groq Key: {'✓ Configured' if settings.groq_api_key else '✗ Not configured'}")

print("\nTesting Service Factory...")
print("-" * 70)

# Test market service
try:
    market_svc = ServiceFactory.get_market_data_service()
    print("✓ MarketDataService initialized")
    print(f"  Provider: {type(market_svc.provider).__name__}")
except Exception as e:
    print(f"✗ MarketDataService failed: {str(e)}")

# Test macro service
try:
    macro_svc = ServiceFactory.get_macro_data_service()
    print("✓ MacroDataService initialized")
    print(f"  Provider: {type(macro_svc.provider).__name__}")
except Exception as e:
    print(f"✗ MacroDataService failed: {str(e)}")

# Test SEC service
try:
    sec_svc = ServiceFactory.get_sec_data_service()
    print("✓ SECDataService initialized")
    print(f"  Provider: {type(sec_svc.provider).__name__}")
except Exception as e:
    print(f"✗ SECDataService failed: {str(e)}")

# Test reasoning service
try:
    reasoning_svc = ServiceFactory.get_reasoning_service()
    print("✓ ReasoningService initialized")
    print(f"  Provider: {type(reasoning_svc.provider).__name__}")
except Exception as e:
    print(f"✗ ReasoningService failed: {str(e)}")

print("\n" + "=" * 70)
print("Integration test complete!")
