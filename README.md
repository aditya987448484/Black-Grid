# BlackGrid

AI-powered financial research platform for stocks, ETFs, bond proxies, and commodities. A dark-themed, futuristic research terminal with live market data, technical analysis, ML forecasting, backtesting, AI-generated analyst reports, and a global intelligence map.

## Features

- **Market Dashboard** - Live index quotes (SPY, QQQ, IWM, DIA, GLD), FRED macro data, signals, watchlist
- **Asset Detail** - Real price charts, live technical indicators (RSI, EMA, MACD, ATR), forecast models
- **AI Analyst Reports** - 10-section institutional-style reports powered by Anthropic Claude or Groq
- **Backtest Lab** - Walk-forward backtesting with equity curves, Sharpe ratios, accuracy metrics
- **Portfolio Monitor** - Watchlist intelligence with signal scores, allocation suggestions
- **World Hub** - Global intelligence map with live flights, vessel tracking, geopolitical hotspots, news sentiment

## Architecture

```
Frontend (Next.js / TypeScript / Tailwind / Recharts / Mapbox GL / Framer Motion)
    |
    | REST API
    |
Backend (FastAPI / Python / pandas / scikit-learn)
    |
    |-- Alpha Vantage + Finnhub (market data, quotes, OHLCV)
    |-- FRED (macro indicators)
    |-- SEC EDGAR (fundamental data)
    |-- Anthropic Claude / Groq (AI report generation)
    |-- Aviationstack + OpenSky (live flight tracking)
    |-- AISStream (vessel AIS data)
    |-- NewsAPI (market-relevant news sentiment)
    |-- GDELT (geopolitical event data)
    |-- Mock fallback (always available for every provider)
```

## Project Structure

```
blackgrid/
  app/                      # Next.js pages
    assets/[ticker]/         # Asset detail
    reports/[ticker]/        # AI report
    backtests/               # Backtest lab
    portfolio/               # Portfolio monitor
    world-hub/               # Global intelligence map
  components/                # React components
    layout/                  # Sidebar, Topbar
    dashboard/               # MetricCard, SignalList, WatchlistTable
    asset/                   # ChartPanel, IndicatorCard, ModelCard
    report/                  # ReportSection, RatingBadge
    backtest/                # PerformanceChart, ComparisonTable
    portfolio/               # PortfolioTable, AllocationPanel
    world-hub/               # WorldMap, ControlBar, IntelPanel, StatsBar
  lib/                       # API client, utilities
  types/                     # TypeScript type definitions
  backend/
    main.py                  # FastAPI entry point
    app/
      api/                   # Route handlers
      schemas/               # Pydantic response models
      services/              # Data providers with fallback
        market_data.py       # Alpha Vantage + Finnhub
        macro_data.py        # FRED
        sec_data.py          # SEC EDGAR
        flight_data.py       # Aviationstack + OpenSky
        ship_data.py         # AISStream + MarineTraffic
        geopolitical_data.py # GDELT + curated hotspots
        news_sentiment.py    # NewsAPI with scoring
        reasoning_provider.py # Anthropic + Groq + mock
        forecast_service.py  # ML forecast pipeline
        mock_data.py         # Comprehensive fallback data
      indicators/            # Technical indicator functions
      models/                # ML models (baseline logistic regression)
      pipelines/             # Feature engineering + backtesting
      reports/               # AI report generator
```

## Setup

### Prerequisites

- Node.js 18+
- Python 3.9+
- pnpm

### Frontend

```bash
cp .env.local.example .env.local  # then add your Mapbox token
pnpm install
pnpm dev
```

Runs on http://localhost:3000

### Backend

```bash
cd backend
cp .env.example .env  # then add your API keys
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Runs on http://localhost:8000

## Environment Variables

### Frontend `.env.local`

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | Backend URL (default: http://localhost:8000) |
| `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` | For World Hub | Mapbox GL JS token for map rendering |

### Backend `backend/.env`

| Variable | Required | Provider | Description |
|----------|----------|----------|-------------|
| `ALPHA_VANTAGE_API_KEY` | Recommended | Alpha Vantage | Stock quotes + OHLCV history |
| `FINNHUB_API_KEY` | Optional | Finnhub | Fallback quotes + candle data |
| `FRED_API_KEY` | Recommended | FRED | Macro indicators (rates, CPI, unemployment) |
| `ANTHROPIC_API_KEY` | Recommended | Anthropic | Claude-powered analyst reports |
| `GROQ_API_KEY` | Optional | Groq | Alternative AI report generation |
| `NEWS_API_KEY` | Optional | NewsAPI | Market-relevant news sentiment |
| `AVIATIONSTACK_API_KEY` | Optional | Aviationstack | Live flight tracking |
| `OPENSKY_USERNAME` | Optional | OpenSky | Flight tracking fallback |
| `OPENSKY_PASSWORD` | Optional | OpenSky | Flight tracking fallback |
| `AISSTREAM_API_KEY` | Optional | AISStream | Vessel AIS tracking |
| `MARINETRAFFIC_API_KEY` | Optional | MarineTraffic | Vessel tracking fallback |
| `SEC_USER_AGENT` | Recommended | SEC EDGAR | Required User-Agent for SEC API |
| `REASONING_PROVIDER` | Optional | — | `anthropic`, `groq`, or `mock` |
| `MARKET_DATA_PROVIDER` | Optional | — | `alpha_vantage` (default) |
| `FLIGHT_DATA_PROVIDER` | Optional | — | `aviationstack` (default) |
| `SHIP_DATA_PROVIDER` | Optional | — | `aisstream` (default) |
| `NEWS_PROVIDER` | Optional | — | `newsapi` (default) |

All keys are optional. Every provider gracefully falls back to mock data if unavailable.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/market/overview` | Live index quotes, FRED macro, signals, watchlist |
| GET | `/api/asset/{ticker}` | Asset detail with real price history |
| GET | `/api/asset/{ticker}/technicals` | Live technical indicators from real OHLCV |
| GET | `/api/asset/{ticker}/forecast` | ML forecast models |
| GET | `/api/asset/{ticker}/report` | AI-generated analyst report (Anthropic/Groq) |
| GET | `/api/backtests/summary` | Backtest results and equity curves |
| GET | `/api/portfolio/watchlist` | Portfolio watchlist intelligence |
| GET | `/api/world-hub/flights` | Live flight positions |
| GET | `/api/world-hub/ships` | Vessel tracking data |
| GET | `/api/world-hub/geopolitical` | Geopolitical events + curated hotspots |
| GET | `/api/world-hub/overview` | Aggregated global intelligence |

## Data Provider Chain

Each service uses a provider chain with automatic fallback:

| Service | Primary | Fallback | Last Resort |
|---------|---------|----------|-------------|
| Market quotes | Alpha Vantage | Finnhub | Mock |
| Price history | Alpha Vantage | Finnhub candles | Mock |
| Macro data | FRED | — | Mock |
| Fundamentals | SEC EDGAR | — | Mock |
| AI Reports | Anthropic Claude | Groq | Mock template |
| Flights | Aviationstack | OpenSky | Mock |
| Ships | AISStream | MarineTraffic | Mock |
| Geopolitical | GDELT + NewsAPI | — | Curated hotspots |

## Future Roadmap

- PyTorch LSTM/GRU sequence models
- Temporal Fusion Transformer (TFT)
- Weighted model ensemble
- Real-time WebSocket price feeds and AIS streaming
- Interactive portfolio construction
- Options flow analysis
- User authentication and saved watchlists

## Disclaimer

This platform is a research and educational tool. Forecasts are probabilistic estimates based on historical patterns and should not be interpreted as financial advice. Past performance does not guarantee future results. Always consult a qualified financial advisor before making investment decisions.
