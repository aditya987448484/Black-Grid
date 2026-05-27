# Frontend Integration with Live Backend Data

**Status:** ✅ Complete - All pages now fetch from real backend API with proper error handling and loading states.

## Overview

The frontend has been fully integrated to use live backend API calls instead of mock data. All pages now support:

- **Real API calls** to the FastAPI backend
- **Loading states** with shimmer skeletons for better UX
- **Error handling** with user-friendly alerts
- **Type-safe responses** with TypeScript interfaces
- **Environment-based configuration** via `NEXT_PUBLIC_API_URL`

## Configuration

### Environment Variables

Add to `.env` or `.env.local` in the frontend directory:

```bash
# Backend API URL (defaults to localhost:8000 for development)
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# For production, use your deployed backend URL:
# NEXT_PUBLIC_API_URL=https://api.example.com/api
```

The API client (`lib/api/client.ts`) automatically uses this URL with a fallback to `http://localhost:8000/api` for local development.

## Architecture

### API Client (`lib/api/client.ts`)

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

**Response Interceptor:**
- Automatically extracts `data` field from backend responses
- Converts backend format `{ status, data, ... }` to just the data
- Handles errors with proper logging

### useApi Hook (`lib/hooks/useApi.ts`)

State management hook that wraps async API requests:

```typescript
const { data, status, error, execute } = useApi<T>(
  () => apiClient.get('/endpoint'),
  immediate // true to fetch on mount, false for manual trigger
);

// Status values: 'idle' | 'pending' | 'success' | 'error'
// data: T | null - the API response data
// error: E | null - the error object if request failed
// execute: () => Promise<T> - function to manually trigger request
```

### Type Definitions (`lib/types/index.ts`)

All API responses are mapped to TypeScript interfaces:

| Type | Purpose |
|------|---------|
| `MarketMetric` | Single market index data |
| `AssetDetail` | Company fundamentals |
| `TechnicalDataResponse` | OHLCV candles + technical indicators |
| `ForecastResponse` | ML model predictions for a ticker |
| `AnalystReport` | AI-generated analyst report |
| `BacktestResult` | Historical backtest performance |
| `WatchlistItem` | Portfolio watchlist entry |

## Pages Integration

### Dashboard (`app/(dashboard)/dashboard/page.tsx`)

**Status:** ✅ Live

```typescript
const { data: marketData, status, error } = useApi(
  () => market.getOverview(),
  true
);
```

**Features:**
- Fetches real index quotes (S&P 500, NASDAQ, Russell 2000, Dow Jones)
- Shows loading states with shimmer skeletons
- Displays error banner if API fails
- Updates in real-time when market opens

### Asset Detail (`app/asset/[ticker]/page.tsx`)

**Status:** ✅ Live

```typescript
const detailApi = useApi<AssetDetail>(() => asset.getDetail(ticker), !!ticker);
const techApi = useApi<TechnicalDataResponse>(() => asset.getTechnicals(ticker), !!ticker);
```

**Features:**
- Fetches company fundamentals and latest price
- Gets technical analysis with candlestick OHLCV data
- Parallel requests for both data types
- Graceful error handling with fallback UI

**Endpoints Used:**
- `GET /api/asset/{ticker}` - Fundamentals
- `GET /api/asset/{ticker}/technicals` - Technical data

### Report (`app/report/page.tsx`)

**Status:** ✅ Live

```typescript
const { data: reportData, status, error } = useApi<AnalystReport>(
  () => report.getAnalystReport(selectedTicker),
  !!selectedTicker
);
```

**Features:**
- Generates AI-powered analyst reports with ticker search
- Combines multiple data sources (market, SEC, macro, LLM)
- Shows loading state while generating report
- Displays professional investment recommendation

**Endpoint:**
- `GET /api/report/{ticker}` - AI analyst report

### Portfolio (`app/portfolio/page.tsx`)

**Status:** ✅ Live

```typescript
const { data: watchlistItems, status, error } = useApi<WatchlistItem[]>(
  () => portfolio.getWatchlist(),
  true
);
```

**Features:**
- Fetches real watchlist with live prices
- Updates prices from Alpha Vantage or falls back to mock
- Sortable and filterable watchlist table
- Real-time portfolio metrics

**Endpoint:**
- `GET /api/portfolio/watchlist` - Watchlist with current prices

### Backtest Lab (`app/backtest/page.tsx`)

**Status:** ✅ Live

```typescript
const { data: results, status, error } = useApi<BacktestResult[]>(
  () => backtest.getSummary(10),
  true
);
```

**Features:**
- Loads recent backtest results
- Shows historical strategy performance
- Ready for creating new backtests with real data

**Endpoint:**
- `GET /api/backtests/summary` - Recent backtest results

### Forecast (`app/forecast/page.tsx`)

**Status:** ✅ Live (Updated from mock to real API)

```typescript
const { data: forecastData, status, error, execute } = useApi<ForecastResponse>(
  () => forecast.getComparison(ticker),
  true
);
```

**Features:**
- Fetches real ML model predictions for any ticker
- Shows consensus signal from ensemble model
- Displays individual model performance metrics
- Allows refreshing predictions manually
- Ticker search with real-time updates

**Endpoint:**
- `GET /api/forecast/{ticker}` - ML model forecasts

**Architecture:**
- Converts backend response to component-friendly format
- Manages loading/error states for smooth UX
- Displays shimmer skeletons while fetching

## API Endpoints Reference

### Market Data

```
GET /api/market/overview
Returns: MarketMetric[]
Example: [
  { symbol: "^GSPC", price: 4783.45, change: 12.50, change_percent: 0.26, ... },
  { symbol: "^IXIC", price: 14923.12, change: -45.32, change_percent: -0.30, ... }
]
```

### Asset Data

```
GET /api/asset/{ticker}
Returns: AssetDetail
Example: {
  symbol: "AAPL",
  name: "Apple Inc",
  price: 189.45,
  change: 2.15,
  change_percent: 1.14,
  market_cap: 2980000000000,
  ...
}

GET /api/asset/{ticker}/technicals
Returns: TechnicalDataResponse
Example: {
  symbol: "AAPL",
  candles: [
    { date: "2026-03-05", open: 185.0, high: 190.0, low: 184.5, close: 189.45, volume: 54240000 }
  ],
  indicators: {
    sma_20: 187.5,
    sma_50: 185.2,
    rsi_14: 65.3,
    ...
  }
}

GET /api/asset/{ticker}/forecast
Returns: ForecastResponse for asset
```

### Reports

```
GET /api/report/{ticker}
Returns: AnalystReport
Example: {
  symbol: "AAPL",
  executive_summary: "Apple remains a strong buy...",
  technical_view: { trend: "uptrend", ... },
  final_rating: { recommendation: "BUY", target_price: 210.0, ... }
}
```

### Forecasts

```
GET /api/forecast/{ticker}
Returns: ForecastResponse
Example: {
  symbol: "AAPL",
  models: {
    baseline: { signal: "HOLD", expected_return: 2.5, confidence: 65.0, ... },
    lstm: { signal: "BUY", expected_return: 5.8, confidence: 78.5, ... },
    tft: { signal: "BUY", expected_return: 6.2, confidence: 82.1, ... },
    ensemble: { signal: "BUY", expected_return: 5.2, confidence: 85.3, ... }
  },
  consensus: { signal: "BUY", confidence: 78.0, ... }
}
```

### Backtests

```
GET /api/backtests/summary?limit=10
Returns: BacktestResult[]
Example: [
  {
    symbol: "AAPL",
    strategy: "Moving Average Crossover",
    total_return: 34.5,
    sharpe_ratio: 1.82,
    ...
  }
]
```

### Portfolio

```
GET /api/portfolio/watchlist
Returns: WatchlistItem[]
Example: [
  {
    ticker: "AAPL",
    name: "Apple Inc",
    current_price: 189.45,
    change: 2.15,
    change_percent: 1.14,
    ...
  }
]
```

## UI Patterns

### Loading States

All pages use **shimmer skeleton screens** while fetching:

```tsx
{isLoading ? (
  <>
    {[1, 2, 3, 4].map((i) => (
      <div key={i} className="h-32 rounded-lg bg-surface-secondary/50 shimmer" />
    ))}
  </>
) : (
  // Actual content
)}
```

### Error Handling

Consistent error alert pattern across all pages:

```tsx
{hasError && (
  <div className="flex items-start gap-4 px-4 py-4 rounded-lg bg-destructive/10 border border-destructive/20 mb-8 backdrop-blur-sm">
    <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
    <div>
      <p className="text-sm font-semibold text-destructive">Failed to load data</p>
      <p className="text-xs text-destructive/70 mt-1.5">Check your connection and try again</p>
    </div>
  </div>
)}
```

### Type-Safe Data Binding

All data is fully typed, enabling IDE autocomplete:

```typescript
// TypeScript knows exactly what properties are available
const price = data?.price;  // number | undefined
const change = data?.change_percent;  // number | undefined
```

## Error Handling Strategy

### Three-Level Fallback (Backend)

1. **Real Provider** - Alpha Vantage, FRED, SEC EDGAR, or Groq LLM
2. **Mock Data** - Fallback if provider fails or API key missing
3. **HTTP 500** - Only if both fail

### Frontend Handling

1. **Display Error Alert** - User-friendly message
2. **Show Retry Option** - Via refresh buttons on all pages
3. **Log to Console** - For debugging via browser DevTools

**Example Flow:**
```
User clicks "Refresh"
  ↓
Frontend calls API
  ↓
Backend tries real provider
  ↓
Real provider fails → Backend uses mock
  ↓
Frontend receives valid response
  ↓
UI updates with data (real or mock, user doesn't know)
```

## Development Workflow

### Local Development

1. **Start Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend will be available at `http://localhost:8000`

2. **Start Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:3000`

3. **Environment Variables:**

**Backend** - `backend/.env`:
```bash
ALPHA_VANTAGE_API_KEY=your_key
FRED_API_KEY=your_key
GROQ_API_KEY=your_key
```

**Frontend** - `.env` (or use defaults):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Testing with Mock Data

To test without real API keys:

1. **Backend** - Don't set API keys or set to empty
2. **Backend** will automatically use mock providers
3. **Frontend** will still work normally, just with mock data

### Testing with Real Providers

1. **Add API keys** to `backend/.env`
2. **Start backend** with `uvicorn app.main:app --reload`
3. **Frontend** will automatically fetch from real providers
4. **Check logs** for which provider was used

## Performance Optimization

### Caching Strategy

The API client currently doesn't cache responses. For production, consider:

```typescript
// Future enhancement: Add Redis caching
const cachedResponse = await cache.get(`forecast:${ticker}`);
if (!cachedResponse) {
  const response = await apiClient.get(`/forecast/${ticker}`);
  await cache.set(`forecast:${ticker}`, response, 3600); // 1 hour TTL
  return response;
}
```

### Request Batching

For endpoints showing multiple assets, consider batching requests:

```typescript
// Instead of: Promise.all([asset.getDetail(ticker1), asset.getDetail(ticker2)])
// Use: POST /api/asset/batch with { tickers: [ticker1, ticker2] }
```

### Rate Limiting

Each real provider has rate limits:
- **Alpha Vantage:** 5 requests/min (free tier)
- **FRED:** Unlimited
- **Groq:** 30 requests/min (free tier)
- **SEC EDGAR:** No limit

Frontend doesn't need to manage this; backend handles automatic fallback.

## Monitoring

### Frontend Logging

All API calls and errors are logged to browser console:

```typescript
console.log('API Call:', { endpoint: '/market/overview', status: 'success' });
console.error('API Error:', error);
```

### Backend Logging

Backend logs which provider was used:

```python
logger.info(f"Using real AlphaVantageProvider for {ticker}")
logger.warning(f"Real provider failed, using mock for {ticker}")
```

### Debugging

1. **Open Browser DevTools** (F12)
2. **Check Console** for API calls and errors
3. **Check Network Tab** to see actual HTTP requests
4. **Inspect Props** on React components to see data structure

## Troubleshooting

### API Returns 404

**Problem:** Endpoint not found

**Solutions:**
1. Check endpoint URL matches backend routing
2. Verify ticker symbol is valid (uppercase)
3. Check backend is running on correct port

### API Returns 500

**Problem:** Server error

**Solutions:**
1. Check backend logs for error message
2. Verify API keys are set (or accept mock fallback)
3. Check network connectivity

### Slow Loading

**Problem:** Pages take too long to load

**Solutions:**
1. Check network tab for slow requests
2. Verify backend server is running locally (not remote)
3. Check system resources (CPU/memory)

**Rate Limiting:**
If hitting provider rate limits, wait 60 seconds before retrying. Backend automatically falls back to mock.

### Blank/Broken Charts

**Problem:** Charts not displaying data

**Solutions:**
1. Check browser DevTools → Network tab
2. Verify API response has correct data structure
3. Check TypeScript types match actual response
4. Ensure chart component receives non-empty array

## Deployment

### Environment Variables in Production

```bash
# frontend/.env.production
NEXT_PUBLIC_API_URL=https://api.example.com/api
```

### CORS Configuration

If backend and frontend are on different domains, ensure CORS is enabled in FastAPI:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],  # Frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Docker Deployment

Frontend image needs access to `NEXT_PUBLIC_API_URL`:

```dockerfile
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
```

## Future Enhancements

### Planned Improvements

1. **WebSocket Real-Time Updates**
   ```tsx
   const ws = new WebSocket('ws://localhost:8000/ws/market/overview');
   ```

2. **Subscription-Based Updates**
   ```tsx
   const subscription = marketService.subscribe('quotes', (data) => {
     setMarketData(data);
   });
   ```

3. **Response Caching**
   - Redis for hot data
   - IndexedDB for offline access
   - SWR for automatic revalidation

4. **Advanced Error Recovery**
   - Exponential backoff on retry
   - Circuit breaker pattern
   - Offline-first strategy

5. **Analytics Integration**
   - Track which endpoints are slow
   - Monitor error rates
   - Alert on provider failures

## Summary

The frontend is now **fully integrated** with the live backend API:

| Feature | Status |
|---------|--------|
| API Client | ✅ Configured |
| Type Safety | ✅ Full TypeScript types |
| Loading States | ✅ Shimmer skeletons |
| Error Handling | ✅ User-friendly alerts |
| Dashboard | ✅ Live market data |
| Asset Pages | ✅ Live fundamentals + technicals |
| Reports | ✅ AI-generated reports |
| Forecasts | ✅ ML predictions |
| Portfolio | ✅ Live watchlist |
| Backtests | ✅ Historical results |
| Premium UI | ✅ No breaking changes |
| Environment Config | ✅ Via NEXT_PUBLIC_API_URL |

**All 6 pages are now fetching from real backend with proper loading, error, and success states.**
