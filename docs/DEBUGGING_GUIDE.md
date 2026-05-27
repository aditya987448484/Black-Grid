# Debugging Guide - Frontend Dashboard API Integration

## Problem Summary

The AXIOM Terminal frontend dashboard was not receiving live market values or chart data from the backend API. The dashboard appeared to load but showed blank values and displayed "Failed to fetch market data" error messages.

### Root Cause: CORS Blocking

**Primary Issue:** The FastAPI backend CORS configuration only allowed requests from:
- `http://localhost:3000`
- `http://127.0.0.1:3000`

However, the Next.js frontend was running on `http://localhost:3001` (due to port 3000 already being in use), causing the browser to **reject all API requests from the frontend due to CORS policy violations**.

## Solution Applied

### 1. **Fixed CORS Configuration** ✅

**File:** `/Users/adityapareek/BlackGrid/backend/app/core/config.py`

Updated the `backend_cors_origins` list to include ports 3000 and 3001:

```python
backend_cors_origins: List[str] = [
    "http://localhost:3000",
    "http://localhost:3001",      # ← Added for alt frontend port
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",      # ← Added for alt frontend port
]
```

**Why this works:**
- The browser's CORS policy requires preflight OPTIONS requests to be approved by the backend
- The backend now responds with `Access-Control-Allow-Origin: http://localhost:3001` headers
- Frontend can now make GET requests to `/api/market/overview` and other endpoints

### 2. **Enhanced Error Logging in Frontend** ✅

**File:** `/Users/adityapareek/BlackGrid/frontend/lib/api/client.ts`

Improved the Axios error interceptor to log detailed debugging information:

```typescript
// Logs show:
// - HTTP status codes
// - Full error messages
// - Response data
// - Network vs. server errors
// - Helpful hints about endpoint URLs
```

**File:** `/Users/adityapareek/BlackGrid/frontend/app/(dashboard)/dashboard/page.tsx`

Added error boundary logging to display the failing endpoint in error messages:

```tsx
<p className="text-sm font-semibold text-destructive">
  Failed to fetch market data from /api/market/overview
</p>
```

### 3. **Improved Backend Market Route** ✅

**File:** `/Users/adityapareek/BlackGrid/backend/app/api/routes/market.py`

- Simplified and clarified the real data provider logic
- Better error handling with graceful fallback to mock data
- Clearer logging at each stage
- Removed complex index symbol parsing that was causing issues

**Data Flow:**
```
Try Real Data (Alpha Vantage) 
  ↓
Success? → Return live quotes
Failed → Log warning
  ↓
Fallback to Mock Data
  ↓
Return mock quotes (always succeeds)
```

## Verification Steps

### Step 1: Verify CORS is Working

```bash
# Test CORS preflight from frontend origin
curl -i -H "Origin: http://localhost:3001" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/api/market/overview

# Expected response includes:
# HTTP/1.1 200 OK
# access-control-allow-origin: http://localhost:3001
```

### Step 2: Verify Backend Returns Data

```bash
# Test API endpoint directly
curl -s http://localhost:8000/api/market/overview | python3 -m json.tool

# Expected response:
# {
#   "status": "success",
#   "data": [
#     {
#       "symbol": "SPY",
#       "price": 450.00,
#       "change": 2.50,
#       "change_percent": 0.0056,
#       "timestamp": "2026-03-06T12:30:45..."
#     },
#     ...
#   ],
#   "market_time": "2026-03-06T12:30:45...",
#   "total_results": 4
# }
```

### Step 3: Test Frontend Connection

1. Open browser DevTools (F12)
2. Go to Console tab
3. Visit `http://localhost:3001/dashboard`
4. Watch for successful API calls (no CORS errors)
5. Dashboard should show live market data in cards

## Common Issues & Solutions

### Issue: "Disallowed CORS origin" error in browser

**Cause:** Frontend origin not in backend CORS whitelist

**Solution:**
1. Check frontend actual port:
   ```bash
   # Check what port frontend is running on
   lsof -i :3000
   lsof -i :3001
   ```
2. Add missing port to `backend_cors_origins` in `config.py`
3. Restart backend: `Ctrl+C` and `npm run dev` again

### Issue: Dashboard shows blank values

**Cause:** Could be:
- CORS blocking requests (check browser Network tab)
- API endpoint not returning data
- Response structure mismatch

**Debug:**
```bash
# 1. Check browser console for error messages
# 2. Check Network tab for failed requests
# 3. Test endpoint directly:
curl http://localhost:8000/api/market/overview

# 4. Verify environment variable:
cat frontend/.env.local | grep NEXT_PUBLIC_API_URL
```

### Issue: Backend crashes when fetching real data

**Cause:** Alpha Vantage provider failing, mock provider not available

**Solution:**
- Ensure mock provider is available and works
- Set `market_data_provider: "mock"` in config.py as fallback
- Check backend logs: `tail -f backend.log`

## Environment Variables

### Frontend (`.env.local`)

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

**Important:** Must match actual backend port!

### Backend (`.env`)

```dotenv
# Market data provider - use "mock" for development
MARKET_DATA_PROVIDER=mock

# Optional: Real data providers (have fallbacks)
ALPHA_VANTAGE_KEY=your_key_here
FRED_API_KEY=your_key_here
```

## Server Startup Instructions

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Runs on http://localhost:8000
# API docs at http://localhost:8000/docs
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install

# Creates .env.local if needed
cp .env.example .env.local

# If port 3000 is taken, automatically uses 3001
npm run dev

# Access at http://localhost:3000 or http://localhost:3001
```

## Data Shape Compatibility

### Frontend Expects (from TypeScript types)

```typescript
interface MarketOverviewResponse {
  status: string;
  data: MarketMetric[];
  market_time: string;
  total_results: number;
}

interface MarketMetric {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  timestamp: string;
}
```

### Backend Returns (from Pydantic models)

**endpoint:** `GET /api/market/overview`
**response:** Same structure as above ✅

**endpoint:** `GET /api/portfolio/watchlist/intelligence`  
**response:** Includes signal_score, confidence_score, risk_score, period_changes, etc. ✅

## Testing All Endpoints

```bash
# Market overview
curl http://localhost:8000/api/market/overview

# Portfolio watchlist
curl http://localhost:8000/api/portfolio/watchlist

# Portfolio intelligence metrics
curl "http://localhost:8000/api/portfolio/watchlist/intelligence?tickers=AAPL,MSFT"

# All should return { "status": "success", "data": [...], ... }
```

## Architecture Notes

### Request Flow (Corrected)

```
Browser (http://localhost:3001)
    ↓ (CORS preflight)
FastAPI Backend (http://localhost:8000/api)
    ↓ (check CORS origin header)
Allowed? → Process request
    ↓
ServiceFactory (selects provider)
    ↓
MarketDataProvider (mock or alpha_vantage)
    ↓
Response (JSON)
    ↓ (CORS headers include Access-Control-Allow-Origin)
Browser receives data
```

### Key Components

1. **CORS Middleware** - Validates origin, sets response headers
2. **ServiceFactory** - Selects mock vs. real data provider
3. **MarketDataProvider** - Abstract interface, implementations handle API calls
4. **MockProvider** - Always works, returns realistic test data (fallback)
5. **AlphaVantageProvider** - Real API, can fail gracefully

## Future Improvements

1. **Environment-based CORS:** Read allowed origins from env var
   ```python
   backend_cors_origins: List[str] = settings.cors_origins.split(",")
   ```

2. **Better error messages in frontend:** Display endpoint URL and status code
3. **WebSocket support:** Real-time data streaming
4. **Caching:** Cache market data to reduce API calls
5. **Healthcheck endpoint:** `/api/health` to verify connectivity

## References

- [CORS MDN Docs](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [Next.js Environment Variables](https://nextjs.org/docs/basic-features/environment-variables)
- [Axios Interceptors](https://axios-http.com/docs/interceptors)
