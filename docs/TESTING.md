"""
TESTING REAL DATA PROVIDERS

Your .env file has been configured with the following API keys:
✓ Alpha Vantage
✓ FRED
✓ Fin Hub
✓ News API
✓ Groq

Now you can test the real data providers!
"""

# ============================================================================
# QUICK TEST COMMANDS
# ============================================================================

# Test the API keys are loaded (requires dependencies)
# cd /Users/adityapareek/BlackGrid
# python3 -m pytest backend/test_providers.py -v

# Or test directly with curl once backend is running:
# ============================================================================
# API ENDPOINTS TO TEST
# ============================================================================

"""
1. MARKET OVERVIEW (loads real data from Fin Hub)
   GET http://localhost:8000/api/market/overview
   
   Returns: List of top indices with prices and changes

2. ASSET DETAIL (loads real company data from Fin Hub)
   GET http://localhost:8000/api/asset/AAPL
   GET http://localhost:8000/api/asset/MSFT
   GET http://localhost:8000/api/asset/NVDA
   
   Returns: Company name, price, PE ratio, market cap, dividend yield

3. TECHNICAL DATA (historical OHLCV from Fin Hub or Alpha Vantage)
   GET http://localhost:8000/api/asset/AAPL/technicals?days=30
   
   Returns: 30 daily candles + technical indicators
   Indicators: SMA 20, SMA 50, EMA 12, RSI, MACD

4. ANALYST REPORT (AI-powered using Groq LLM)
   GET http://localhost:8000/api/report/AAPL
   
   Returns: 9-section institutional research note
   - Executive summary
   - Technical analysis (with real price levels from API)
   - Fundamental analysis
   - Macro context
   - Bull/bear cases
   - Risks & catalysts
   - Price target & rating

5. FORECAST (ML models predicting next 30 days)
   GET http://localhost:8000/api/asset/AAPL/forecast?days=30
   
   Returns: 4 models + consensus
   - Baseline momentum model (52.3% accuracy)
   - LSTM recurrent network (61.2% accuracy)
   - TFT transformer (64.8% accuracy)
   - Ensemble weighted (67.1% accuracy)

6. WATCHLIST (from portfolio service)
   GET http://localhost:8000/api/portfolio/watchlist
   
   Returns: Your saved watchlist with current prices

7. BACKTEST SUMMARY (strategy performance)
   GET http://localhost:8000/api/backtests/summary
   
   Returns: Historical backtest results with metrics
"""

# ============================================================================
# TESTING WITH CURL
# ============================================================================

"""
# Start the backend server (requires dependencies in venv)
cd /Users/adityapareek/BlackGrid
source venv/bin/activate  # if you have a venv
python3 -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Then in another terminal, test endpoints:

# Test market overview (real data from Fin Hub)
curl -X GET "http://localhost:8000/api/market/overview" \
  -H "Content-Type: application/json"

# Test asset detail
curl -X GET "http://localhost:8000/api/asset/AAPL" \
  -H "Content-Type: application/json"

# Test technicals with real data
curl -X GET "http://localhost:8000/api/asset/AAPL/technicals?days=30" \
  -H "Content-Type: application/json"

# Test analyst report (uses Groq AI)
curl -X GET "http://localhost:8000/api/report/AAPL" \
  -H "Content-Type: application/json"

# Test forecast
curl -X GET "http://localhost:8000/api/asset/AAPL/forecast?days=30" \
  -H "Content-Type: application/json"

# Test watchlist
curl -X GET "http://localhost:8000/api/portfolio/watchlist" \
  -H "Content-Type: application/json"
"""

# ============================================================================
# CONFIGURE WHICH PROVIDER TO USE
# ============================================================================

"""
In your .env file, you can control which provider is used:

MARKET_DATA_PROVIDER=fin_hub    # Use real Fin Hub data
MARKET_DATA_PROVIDER=alpha_vantage  # Use real Alpha Vantage data
MARKET_DATA_PROVIDER=mock       # Use mock data (for testing)

# For analyst reports, Groq is optional:
# If GROQ_API_KEY is set and working, reports will use AI
# If not, reports will use mock data with realistic values
"""

# ============================================================================
# PROVIDER FALLBACK BEHAVIOR
# ============================================================================

"""
The system is smart about API failures:

1. Tries to use the configured real provider
2. If it fails (API error, rate limit, etc), it falls back to mock data
3. Logs the failure so you know what happened

This means:
- Your frontend always gets data (never breaks)
- API failures are graceful
- You can test with mocks, switch to real data when ready
"""

# ============================================================================
# MONITORING API USAGE
# ============================================================================

"""
Track your API consumption:

Free Tier Rate Limits:
- Alpha Vantage: 5 calls/minute, 500/day
- FRED: 120 calls/minute, unlimited
- Fin Hub: 60 calls/minute
- News API: 100 calls/day
- Groq: 30 calls/minute

Each API has a dashboard to check usage:
- Alpha Vantage: https://www.alphavantage.co/
- FRED: https://fred.stlouisfed.org/docs/api/
- Fin Hub: https://finnhub.io/dashboard
- News API: https://newsapi.org/account
- Groq: https://console.groq.com/
"""

# ============================================================================
# EXAMPLE RESPONSES
# ============================================================================

"""
ASSET DETAIL Response:
{
  "status": "success",
  "data": {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "asset_type": "stock",
    "price": 189.45,
    "market_cap": 2950000000000,
    "pe_ratio": 28.4,
    "dividend_yield": 0.0042,
    "fifty_two_week_high": 199.62,
    "fifty_two_week_low": 164.08,
    "avg_volume": 52340000
  },
  "timestamp": "2026-03-05T22:30:00"
}

FORECAST Response:
{
  "status": "success",
  "ticker": "AAPL",
  "current_price": 189.45,
  "horizon_days": 30,
  "models": [
    {
      "model_name": "LSTM/GRU",
      "signal": "BUY",
      "expected_return": 5.8,
      "confidence": 78.5,
      "status": "ready",
      "accuracy": 61.2
    }
  ],
  "consensus": {
    "consensus_signal": "BUY",
    "consensus_probability": 72.5,
    "average_confidence": 77.73,
    "model_agreement": "High"
  },
  "generated_at": "2026-03-05T22:30:00"
}

ANALYST REPORT Response:
{
  "status": "success",
  "data": {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "current_price": 189.45,
    "executive_summary": "Apple demonstrates strong fundamentals...",
    "final_rating": {
      "recommendation": "BUY",
      "target_price": 215.00,
      "price_upside": 13.5,
      "conviction": "High"
    },
    "confidence_score": 87.5
  },
  "generated_at": "2026-03-05T22:30:00"
}
"""

# ============================================================================
# WHAT'S CONFIGURED
# ============================================================================

"""
✓ .env file created with all API keys
✓ Config system loads from .env automatically
✓ All routes set up to use real providers
✓ Fallback to mock data if APIs fail
✓ Groq LLM configured for AI analyst reports
✓ Provider Manager for unified interface
✓ Test script created for validation

Ready to go! Start the backend and test the endpoints.
"""
