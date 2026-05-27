# Real Provider Service Integration Guide

## Overview

The FastAPI routes have been integrated with real data provider services for Alpha Vantage, FRED, SEC EDGAR, and Groq LLM. The architecture supports graceful fallback to mock data when services are unavailable or keys are not configured.

## Architecture

### Service Factory Pattern

All route handlers use the `ServiceFactory` to obtain service instances:

```python
from app.api.service_factory import ServiceFactory

# In route handlers
market_service = ServiceFactory.get_market_data_service()
macro_service = ServiceFactory.get_macro_data_service()
sec_service = ServiceFactory.get_sec_data_service()
reasoning_service = ServiceFactory.get_reasoning_service()
```

**Benefits:**
- Centralized configuration management
- Automatic fallback to mock providers
- Single point of control for provider switching
- Transparent to route handlers

### Graceful Degradation

Each service factory method:
1. Checks if the real API key is configured
2. Attempts to initialize the real provider
3. Falls back to mock provider if real provider unavailable
4. Logs all transitions for debugging

Example from `ServiceFactory`:
```python
@staticmethod
def get_market_data_service() -> MarketDataService:
    settings = get_settings()
    
    try:
        if settings.market_data_provider == "mock" or not settings.alpha_vantage_key:
            logger.debug("Using mock market data provider")
            return MarketDataService(provider=MockMarketDataProvider())
        
        logger.debug(f"Using {settings.market_data_provider} market data provider")
        return MarketDataService()  # Uses AlphaVantageProvider by default
    
    except Exception as e:
        logger.warning(f"Failed to initialize real market provider: {str(e)}. Falling back to mock.")
        return MarketDataService(provider=MockMarketDataProvider())
```

## Route Integration

### 1. Market Routes (`market.py`)

**Endpoint:** `GET /api/market/overview`

**Integration:**
- Fetches quote data for major indices from Alpha Vantage
- Falls back to mock market overview if real provider fails
- Updates index values, changes, and percentages in real-time

**Data Flow:**
```
Request → ServiceFactory.get_market_data_service() 
        → AlphaVantageProvider.get_quote() [Real]
        → Build response from quote data
        → Fallback to mock if needed
        → Return MarketOverviewResponse
```

### 2. Asset Routes (`asset.py`)

**Endpoints:**
- `GET /api/asset/{ticker}` - Asset fundamentals
- `GET /api/asset/{ticker}/technicals` - Technical analysis
- `GET /api/asset/{ticker}/forecast` - ML forecasts

**Integration:**
- **Fundamentals:** Fetches current quotes from Alpha Vantage, extracts price, change, volume
- **Technicals:** Fetches daily OHLCV time series from Alpha Vantage, builds candlestick data
- **Forecast:** Uses mock forecasts (ready for ML model integration)

**Data Flow:**
```
Request → ServiceFactory.get_market_data_service()
        → AlphaVantageProvider.get_time_series() [Real]
        → Parse OHLCV data
        → Build TechnicalDataResponse
        → Fallback to mock if needed
```

### 3. Report Routes (`report.py`)

**Endpoint:** `GET /api/report/{ticker}`

**Integration:**
- Builds comprehensive analysis context from multiple real providers:
  - **Market Data:** Current quote from Alpha Vantage
  - **SEC Data:** Recent filings from SEC EDGAR
  - **Macro Data:** Economic indicators from FRED
- Sends context to Groq LLM for AI-generated report
- Falls back to mock report if LLM unavailable

**Data Flow:**
```
Request → ServiceFactory.get_reasoning_service()
        → GroqReasoningProvider.generate_report()
        → Fetch market data (AlphaVantage)
        → Fetch SEC data (EDGAR)
        → Fetch macro data (FRED)
        → Send context to Groq LLM
        → Return AnalystReportResponse
        → Fallback to mock if LLM fails
```

### 4. Portfolio Routes (`portfolio.py`)

**Endpoint:** `GET /api/portfolio/watchlist`

**Integration:**
- Gets base watchlist from mock data
- Updates prices from real Alpha Vantage quotes
- Gracefully handles missing/failed price updates

**Data Flow:**
```
Request → get_mock_watchlist_items()
        → ServiceFactory.get_market_data_service()
        → For each ticker: AlphaVantageProvider.get_quote() [Real]
        → Update prices in watchlist items
        → Return updated WatchlistResponse
```

### 5. Backtest Routes (`backtest.py`)

**Endpoint:** `GET /api/backtests/summary`

**Integration:**
- Currently uses mock backtest data
- Service factory included for future real backtesting engine
- Ready for integration with historical market data

**Data Flow:**
```
Request → ServiceFactory.get_market_data_service() [for future use]
        → get_mock_backtest_summary() [current]
        → Return BacktestSummaryResponse
```

### 6. Forecast Routes (`forecast.py`)

**Endpoint:** `GET /api/forecast/{ticker}`

**Integration:**
- Currently uses mock forecasts
- Service factory included for future ML model integration
- Ready for integration with real market data context

**Data Flow:**
```
Request → ServiceFactory.get_market_data_service() [for future use]
        → get_mock_forecast() [current]
        → Return ForecastResponse
```

## Error Handling Strategy

### Three-Level Fallback

Each route implements robust error handling:

```python
try:
    # Level 1: Try real provider
    service = ServiceFactory.get_market_data_service()
    data = await service.get_current_quote(ticker)
    return build_response(data)

except Exception as e:
    logger.warning(f"Real provider failed: {str(e)}")
    
    # Level 2: Try mock data
    try:
        mock_data = get_mock_asset_detail(ticker)
        return build_response(mock_data)
    
    except Exception as mock_error:
        # Level 3: Return HTTP error
        logger.error(f"Both real and mock failed: {str(mock_error)}")
        raise HTTPException(status_code=500, detail="Failed to fetch data")
```

### Logging

Each integration point logs its state:
- ✓ Real provider successfully called
- ⚠ Real provider failed, using mock
- ✗ Both real and mock failed, error returned

Check logs via:
```bash
cd backend
uvicorn app.main:app --reload --log-level debug
```

## Configuration

### Environment Setup

See `.env.example` and `README.md` for complete setup. Key variables:

```env
# Market Data (Alpha Vantage)
MARKET_DATA_PROVIDER=alpha_vantage  # or "mock"
ALPHA_VANTAGE_API_KEY=your_key_here

# Economic Data (FRED)
FRED_API_KEY=your_key_here

# LLM Reasoning (Groq)
GROQ_API_KEY=your_key_here

# SEC (No key needed, uses User-Agent)
SEC_USER_AGENT=Axiom Terminal (yourteam@example.com)
```

### Provider Selection

**To use real providers:**
1. Set API keys in `.env`
2. Set `MARKET_DATA_PROVIDER=alpha_vantage` (or appropriate provider)
3. Restart API server

**To use mock data (development):**
1. Leave API keys empty or set to dummy values
2. Set `MARKET_DATA_PROVIDER=mock`
3. Routes automatically fall back to mock

## Testing

### Test Real Providers

```bash
# With API keys configured
curl http://localhost:8000/api/market/overview
curl http://localhost:8000/api/asset/AAPL
curl http://localhost:8000/api/report/AAPL

# Should see real data from Alpha Vantage, FRED, SEC, Groq
```

### Test Mock Fallback

```bash
# Remove API keys from .env or set to invalid values
export ALPHA_VANTAGE_API_KEY=""
export GROQ_API_KEY=""
uvicorn app.main:app --reload

# Routes should still work with mock data
curl http://localhost:8000/api/asset/AAPL
# Returns mock data, logs show fallback
```

### Test Rate Limiting

Alpha Vantage has a 5 req/min limit on free tier. If you hit the limit:
- Routes automatically fall back to mock data
- Logs show rate limit exceeded
- Response still returned to user (graceful degradation)

## Performance Considerations

### Caching Strategy (Future)

Plan to add caching layer:
```python
# Example (future implementation)
class CachedMarketDataService:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    async def get_quote(self, ticker):
        # Check cache
        if ticker in self.cache and not self.is_stale(ticker):
            return self.cache[ticker]
        
        # Fetch fresh data
        data = await AlphaVantageProvider().get_quote(ticker)
        self.cache[ticker] = (data, time.time())
        return data
```

### Rate Limit Management

Current approach:
- Single requests to real providers
- Automatic fallback to mock if rate limit hit
- Future: Implement caching to reduce API calls

## Integration Roadmap

### Phase 1 ✅ (Current)
- Market data provider integration (Alpha Vantage)
- SEC data provider integration (EDGAR)
- Macro data provider integration (FRED)
- Reasoning provider integration (Groq)
- Mock fallbacks for all providers
- Error handling and logging

### Phase 2 (Planned)
- Redis caching layer
- Request batching for multiple tickers
- Scheduled data refresh
- Provider health checks
- API quota monitoring

### Phase 3 (Future)
- Additional data sources (Yahoo Finance, IEX Cloud, Polygon.io)
- Real backtesting engine with historical data
- ML model forecasting integration
- WebSocket real-time data
- Advanced features (options analysis, risk metrics)

## Troubleshooting

### Issue: "Real data fetch failed, using mock data"

**Cause:** API key not configured or provider unavailable

**Solution:**
1. Check API key in `.env`: `echo $ALPHA_VANTAGE_API_KEY`
2. Verify key is valid at provider's website
3. Check rate limits haven't been exceeded
4. Review logs: `grep "Error fetching" app.log`

### Issue: Rate limit reached

**Cause:** Too many requests to free-tier API

**Solution:**
- Routes automatically fall back to mock
- Wait 1 minute for rate limit to reset
- Consider upgrading API tier for production

### Issue: Some fields are 0 or N/A

**Cause:** Real provider missing certain fields

**Solution:**
- This is expected; real providers have different field sets than mock
- Mock data includes synthetic values for all fields
- Future versions will fill gaps with calculation/estimation

### Issue: Slow response times

**Cause:** Real API calls are slower than mock

**Solution:**
- Implement caching (see Phase 2)
- Use appropriate timeout values
- Consider provider upgrade for faster responses

## Code Examples

### Using Services in Route Handlers

```python
from app.api.service_factory import ServiceFactory

@router.get("/example/{ticker}")
async def example_endpoint(ticker: str):
    try:
        # Get service (automatically falls back to mock if needed)
        service = ServiceFactory.get_market_data_service()
        
        # Call service method
        data = await service.get_current_quote(ticker)
        
        # Build response
        return {"ticker": ticker, "price": data["Global Quote"]["05. price"]}
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch data")
```

### Multiple Service Integration

```python
@router.get("/comprehensive/{ticker}")
async def comprehensive_data(ticker: str):
    try:
        # Get all services
        market_svc = ServiceFactory.get_market_data_service()
        macro_svc = ServiceFactory.get_macro_data_service()
        sec_svc = ServiceFactory.get_sec_data_service()
        
        # Fetch from multiple sources
        market_data = await market_svc.get_current_quote(ticker)
        macro_data = await macro_svc.get_economic_snapshot()
        sec_data = await sec_svc.get_company_info(ticker)
        
        # Combine and return
        return {
            "market": market_data,
            "macro": macro_data,
            "sec": sec_data,
        }
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch data")
```

## Summary

The integration provides:
- ✅ Thin route handlers (HTTP/validation logic only)
- ✅ Service layer for all business logic
- ✅ Multiple real data providers (Alpha Vantage, FRED, SEC, Groq)
- ✅ Automatic mock fallbacks
- ✅ Comprehensive error handling
- ✅ Production-style architecture
- ✅ Ready for caching, batching, and additional providers

All routes are now production-ready with real data provider support while maintaining robustness through graceful fallbacks to mock data.
