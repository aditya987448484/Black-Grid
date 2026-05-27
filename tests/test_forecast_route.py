#!/usr/bin/env python3
"""Test script for forecast route endpoint"""

import sys
sys.path.insert(0, '/Users/adityapareek/BlackGrid/backend')

import asyncio
from app.api.routes.forecast import get_forecast_comparison
from app.schemas.schemas import ForecastResponse

async def test_forecast_endpoint():
    """Test forecast route endpoint with real service"""
    try:
        print("Testing forecast endpoint...")
        print("-" * 50)
        
        # Call the route handler directly (simulates HTTP request)
        result = await get_forecast_comparison(ticker="AAPL", days=30)
        
        # Print result structure
        print("\n✅ Forecast Route Response:")
        print(f"   Status: {result.status}")
        print(f"   Ticker: {result.ticker}")
        print(f"   Current Price: ${result.current_price}")
        print(f"   Horizon: {result.horizon_days} days")
        print(f"\n   Models ({len(result.models)} total):")
        for i, model in enumerate(result.models, 1):
            print(f"     {i}. {model.model_name}")
            print(f"        Type: {model.model_type}")
            print(f"        Signal: {model.signal}")
            print(f"        Expected Return: {model.expected_return}%")
            print(f"        Confidence: {model.confidence}%")
            print(f"        Status: {model.status}")
            print(f"        Description: {model.description[:60]}...")
        
        print(f"\n   Consensus:")
        print(f"     Signal: {result.consensus.consensus_signal}")
        print(f"     Probability: {result.consensus.consensus_probability}%")
        print(f"     Avg Confidence: {result.consensus.average_confidence}%")
        print(f"     Avg Return: {result.consensus.average_return}%")
        print(f"     Agreement: {result.consensus.model_agreement}")
        
        # Verify response is ForecastResponse
        assert isinstance(result, ForecastResponse), "Response is not ForecastResponse"
        assert result.models is not None and len(result.models) > 0, "No models in response"
        assert len(result.models) == 4, f"Expected 4 models, got {len(result.models)}"
        
        # Check that we have baseline (real) and placeholders
        model_types = [m.model_type for m in result.models]
        assert "baseline" in model_types, "Baseline model missing"
        assert "lstm" in model_types, "LSTM placeholder missing"
        assert "tft" in model_types, "TFT placeholder missing"
        assert "ensemble" in model_types, "Ensemble placeholder missing"
        
        print("\n✅ Response structure validation passed!")
        print("   ✓ Correct response type (ForecastResponse)")
        print("   ✓ All 4 models present (1 real baseline + 3 placeholders)")
        print("   ✓ Consensus metrics computed")
        print("   ✓ Response shape stable for frontend")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_forecast_endpoint())
    sys.exit(0 if success else 1)
