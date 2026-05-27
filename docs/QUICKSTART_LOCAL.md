# Local Development Quickstart

**Complete guide to running the full Axiom Terminal stack locally with real backend data.**

## Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.10+ (for backend)
- **npm** or **yarn** (for frontend dependencies)
- **Git** (for version control)

## Quick Start (5 minutes)

### 1. Start the Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start API server
uvicorn app.main:app --reload --log-level debug

# Backend now running at http://localhost:8000
# Docs available at http://localhost:8000/docs
```

**Output should show:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### 2. Start the Frontend

In a **new terminal window**:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Frontend now running at http://localhost:3000
```

**Output should show:**
```
> next dev
  ▲ Next.js 14.0.0
  - Local:        http://localhost:3000
```

### 3. Open the App

Visit **http://localhost:3000** in your browser.

All API calls will automatically route to `http://localhost:8000/api` with proper loading and error states.

## Configuration

### Environment Variables

**Backend** - Create `backend/.env`:

```bash
# Application
DEBUG=True
DATABASE_URL=sqlite:///./axiom.db

# Data providers - use "mock" for development without API keys
MARKET_DATA_PROVIDER=mock
FORECAST_PROVIDER=mock

# Optional: Add real API keys for live data
ALPHA_VANTAGE_API_KEY=your_key_here
FRED_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
SEC_API_KEY=your_key_here
```

**Frontend** - Uses `.env` with:

```bash
# Automatically set to http://localhost:8000/api
# Override in .env.local if needed
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## Testing Different Modes

### Mode 1: Pure Mock (No API Keys Required)

**Best for:** Initial testing, development without internet, learning the platform

```bash
# Backend - Don't set any API keys
# Leave backend/.env with empty or unset keys
# Backend will automatically use mock providers

# Frontend - Will receive real-looking mock data
# All endpoints work without configuration
```

### Mode 2: Real Data with Free API Keys

**Best for:** Real market data, development testing

1. **Get Free API Keys:**
   - [Alpha Vantage](https://www.alphavantage.co/api) - Free tier: 5 req/min
   - [FRED](https://fredaccount.stlouisfed.org/api/keys) - Free: Unlimited
   - [Groq](https://console.groq.com) - Free: 30 req/min, 500 req/day

2. **Configure backend/.env:**
   ```bash
   ALPHA_VANTAGE_API_KEY=your_actual_key
   FRED_API_KEY=your_actual_key
   GROQ_API_KEY=your_actual_key
   ```

3. **Restart backend:**
   ```bash
   # Stop current server (Ctrl+C)
   # Run again
   uvicorn app.main:app --reload --log-level debug
   ```

4. **Backend will now:**
   - Use real Alpha Vantage for stock data
   - Use real FRED for economic data
   - Use real Groq for AI analysis
   - Fall back to mock if any provider fails

## Testing Endpoints

### Via Frontend UI (Recommended)

1. Visit **http://localhost:3000**
2. Navigate to each section:
   - **Dashboard** - Market indices (S&P 500, NASDAQ, etc)
   - **Asset** - Search any ticker (AAPL, MSFT, TSLA)
   - **Report** - AI analyst report for any ticker
   - **Portfolio** - Watchlist with real prices
   - **Forecast** - ML model predictions
   - **Backtest** - Historical strategy results

### Via API Directly (Testing)

Use **curl** or **Postman**:

```bash
# Get market indices
curl http://localhost:8000/api/market/overview

# Get Apple stock fundamentals
curl http://localhost:8000/api/asset/AAPL

# Get technical data
curl http://localhost:8000/api/asset/AAPL/technicals

# Get AI report
curl http://localhost:8000/api/report/AAPL

# Get ML forecasts
curl http://localhost:8000/api/forecast/AAPL

# Get watchlist
curl http://localhost:8000/api/portfolio/watchlist

# Get backtest results
curl http://localhost:8000/api/backtests/summary
```

### Via Swagger UI

Backend includes interactive API documentation:

1. Visit **http://localhost:8000/docs**
2. Click any endpoint to expand
3. Click **Try it out**
4. Enter parameters (e.g., ticker: "AAPL")
5. Click **Execute**
6. See request and response

Perfect for testing individual endpoints!

## Monitoring & Debugging

### Backend Logs

The backend logs which provider is being used:

```
INFO: Using real AlphaVantageProvider for quote: AAPL
INFO: Successfully fetched quote for AAPL: ${price}
```

Or if provider fails:

```
WARNING: Real AlphaVantageProvider failed: Invalid API key
INFO: Using MockMarketDataProvider instead
```

**Log Levels:**
```bash
# For more detailed logs
uvicorn app.main:app --reload --log-level debug

# For production
uvicorn app.main:app --log-level info
```

### Frontend Logs

Open browser **DevTools** (F12):

1. **Console Tab** - See API calls and errors
2. **Network Tab** - See HTTP requests/responses
3. **Application Tab** - See LocalStorage/Cache

**Example console output:**
```
GET http://localhost:8000/api/market/overview 200 OK
GET http://localhost:8000/api/asset/AAPL 200 OK
```

### Health Checks

```bash
# Check backend is running
curl http://localhost:8000/health

# Check API is accessible
curl http://localhost:8000/api/market/overview | jq .

# Verify environment
curl http://localhost:8000/config/providers
```

## Performance Tips

### Speed Up Local Development

1. **Use mock data** initially - don't waste API limits
2. **Limit API calls** per minute - respect rate limits
3. **Use VSCode** extensions:
   - REST Client (for testing endpoints)
   - Thunder Client (API testing)
   - Python extension (backend debugging)

### Monitor Rate Limits

Alpha Vantage (most restrictive):
- Free tier: **5 requests per minute**
- Premium: **500+ per minute**

If you hit rate limits:
```
API Error: Status 429 - Thank you for using Alpha Vantage!
Our standard API call frequency is 5 calls per minute.
```

**Solutions:**
- Wait 60 seconds before retrying
- Backend will automatically use mock data
- Upgrade to paid tier for testing

## Common Issues & Solutions

### "Connection Refused" - Backend not running

```bash
# Fix: Start the backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### "NEXT_PUBLIC_API_URL is not set" warning

This is just a warning. Frontend defaults to `http://localhost:8000/api`.

To suppress, add to `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### API Returns Empty Data or 500 Error

**Check:**
1. Backend is running (`http://localhost:8000/docs` accessible?)
2. Database file exists (`backend/axiom.db`)
3. Python virtual environment is activated
4. All imports are correct

**Solution:**
```bash
# Restart backend
Ctrl+C  # Stop current process
source venv/bin/activate  # Ensure venv is active
uvicorn app.main:app --reload --log-level debug
```

### Ticker Returns "Not Found"

**Check:**
1. Ticker is valid (e.g., "AAPL", not "apple")
2. Ticker must be uppercase (auto-converted in API)
3. If using mock, all tickers work
4. If using real API, check provider has data

**Example valid tickers:**
- AAPL, MSFT, GOOGL, TSLA (US stocks)
- ^GSPC (S&P 500)
- ^IXIC (NASDAQ)

### Port Already in Use

**Backend port 8000 taken:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill it (macOS/Linux)
kill -9 <PID>

# Or run backend on different port
uvicorn app.main:app --port 8001 --reload
# Then set NEXT_PUBLIC_API_URL=http://localhost:8001/api
```

**Frontend port 3000 taken:**
```bash
# Run on different port
npm run dev -- -p 3001
# Visit http://localhost:3001
```

## File Structure for Reference

```
BlackGrid/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/          # API endpoints
│   │   │   └── service_factory.py  # Service initialization
│   │   ├── services/            # Real data providers
│   │   ├── main.py              # FastAPI app
│   │   └── core/config.py       # Configuration
│   ├── requirements.txt          # Python dependencies
│   ├── .env                      # Configuration (create this)
│   └── axiom.db                 # SQLite database (auto-created)
│
├── frontend/
│   ├── app/                      # Next.js pages
│   │   ├── (dashboard)/dashboard/page.tsx   # Dashboard
│   │   ├── asset/[ticker]/      # Asset detail pages
│   │   ├── report/              # Analyst report
│   │   ├── forecast/            # ML forecasts
│   │   ├── portfolio/           # Watchlist
│   │   └── backtest/            # Backtest lab
│   ├── lib/
│   │   ├── api/client.ts        # API client configuration
│   │   ├── hooks/useApi.ts      # State management hook
│   │   └── types/               # TypeScript interfaces
│   ├── components/              # React components
│   ├── package.json             # NPM dependencies
│   └── .env.local              # Frontend config (optional)
│
├── .env                         # Project-wide env (includes both)
├── FRONTEND_INTEGRATION.md      # Frontend docs
├── PROVIDER_INTEGRATION.md      # Backend provider docs
└── README.md                    # Main documentation
```

## Next Steps

### After Getting it Running

1. **Explore the UI** - Navigate through all pages
2. **Read the documentation:**
   - [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md) - Frontend details
   - [PROVIDER_INTEGRATION.md](./PROVIDER_INTEGRATION.md) - Backend details
3. **Test with Real APIs** - Add your own API keys
4. **Customize** - Modify colors, add features, etc.

### Learning Resources

**Frontend:**
- Next.js: https://nextjs.org/learn
- React Hooks: https://react.dev/reference/react/hooks
- Tailwind CSS: https://tailwindcss.com/docs
- TypeScript: https://www.typescriptlang.org/docs

**Backend:**
- FastAPI: https://fastapi.tiangolo.com
- SQLAlchemy: https://docs.sqlalchemy.org
- Pydantic: https://docs.pydantic.dev
- Python async: https://docs.python.org/3/library/asyncio.html

## Getting Help

### Check Logs First

**Backend logs:**
```bash
# Look for error messages
uvicorn app.main:app --reload --log-level debug
```

**Frontend logs:**
- Browser DevTools → Console (F12)
- Check Network tab for failed requests

### Common Commands

```bash
# Backend
cd backend && source venv/bin/activate  # Activate
pip install -r requirements.txt         # Install deps
uvicorn app.main:app --reload          # Run dev server
python3 test_integration.py             # Test services

# Frontend
cd frontend && npm install              # Install deps
npm run dev                             # Run dev server
npm run build                           # Production build
npm run lint                            # Check code quality
```

### Testing Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Can visit http://localhost:3000
- [ ] Dashboard loads with market data
- [ ] Can search assets (e.g., AAPL)
- [ ] Error states display gracefully
- [ ] Loading states show (shimmer skeletons)
- [ ] Network tab shows successful API calls
- [ ] Forecast page loads predictions

---

**Status:** ✅ Ready to develop!

Start with `npm run dev` in frontend and `uvicorn app.main:app --reload` in backend, then visit http://localhost:3000.
