# AXIOM Terminal

A full-stack AI-powered financial research platform for equities, ETFs, bond proxies, and commodities. Combines real-time market data, SEC EDGAR fundamentals, FRED macroeconomic indicators, ML-based forecasting, and Groq LLM synthesis into an institutional-grade dark interface with portfolio intelligence.

---

## Overview

AXIOM Terminal is built for buy-side teams, retail investors, and portfolio managers who want deep research capabilities combined with real-time monitoring. The platform features:

- **Portfolio Intelligence Dashboard** — Real-time watchlist monitoring with signal score, confidence levels, risk assessment, period-over-period changes, and AI-generated allocation weights
- **AI Analyst Reports** — Groq LLM generates structured research grounded in SEC EDGAR fundamentals and FRED macro data with deterministic fallback
- **ML Forecasting** — Multi-model ensemble with confidence bands and consensus signals
- **Strategy Backtesting** — Sharpe ratio, max drawdown, annualized return across MA Crossover, RSI, MACD, Bollinger Band strategies
- **Market Context** — Live indices (S&P 500, NASDAQ, Russell 2000, Dow Jones), FRED macro series, yield curves

---

## Key Features

### Portfolio Intelligence

- **Signal Score** — Momentum-based technical indicator (-1.0 to +1.0) showing trend strength and direction
- **Confidence Score** — Volume and volatility adjusted confidence (0-100%) in the signal
- **Risk Score** — Composite metric combining volatility (0-40 pts), max drawdown (0-30 pts), and trend weakness (0-30 pts)
- **Period Changes** — 1-day, 5-day, and 1-month percentage changes with color-coded badges
- **Institutional Allocation** — Risk-adjusted position sizing recommendation (normalized to 100% across portfolio)
- **Alert System** — Priority-based alerts for extreme moves (>5%), strong momentum (>0.75/-0.75), low confidence (<40%), and high volatility (>30%)
- **Dark Theme Dashboard** — ScoreBar visualizations, subtle color theming (/12 background opacity, /90 text), smooth transitions, professional institutional aesthetic

### Core Analysis

- **AI Analyst Reports** — Groq LLM generates structured research reports grounded in real SEC EDGAR fundamentals and FRED macro data with deterministic fallback when API unavailable.
- **Fundamental Analysis** — Fetches 10-K filings from SEC EDGAR via XBRL company facts API. Extracts revenue, net income, EPS, operating cash flow, total assets, liabilities, and equity with multi-tag fallbacks across different XBRL naming conventions.
- **Macro Context** — Pulls live FRED series: 10Y Treasury (`GS10`), Fed funds rate (`FEDFUNDS`), CPI YoY (`CPIAUCSL`), unemployment (`UNRATE`), and yield curve spread (`T10Y2Y`).
- **Real-Time Market Data** — Alpha Vantage integration for live quotes and OHLCV time series. Full mock provider available for development without API keys.
- **Strategy Backtesting** — Configurable backtesting engine with Sharpe ratio, max drawdown, and annualized return across MA Crossover, RSI, MACD, and Bollinger Band strategies.
- **Multi-Model Forecasts** — Ensemble of ML-based forecast models with confidence bands and consensus signals.

---

## Screenshots

> _Add screenshots to `docs/screenshots/` and update paths below_

| View | Description |
|---|---|
| `docs/screenshots/dashboard.png` | Main dashboard with market indices and status |
| `docs/screenshots/portfolio.png` | Portfolio Monitor — watchlist intelligence with all metrics |
| `docs/screenshots/report.png` | AI analyst report with fundamentals and macro sections |
| `docs/screenshots/backtest.png` | Backtest lab with performance metrics and strategy selector |
| `docs/screenshots/asset-detail.png` | Asset detail with forecast consensus and technical indicators |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Next.js 14 Frontend                        │
│ App Router · TypeScript · Tailwind CSS · Recharts · Axios    │
└────────────────────────┬─────────────────────────────────────┘
                         │  REST / JSON
┌────────────────────────▼─────────────────────────────────────┐
│                   FastAPI Backend                            │
│           Pydantic v2 · Uvicorn · SQLAlchemy                 │
├──────────────────────────────────────────────────────────────┤
│  ServiceFactory + Dependency Injection                        │
│    ├── MarketDataService      → Alpha Vantage (or mock)      │
│    ├── FundamentalService     → SEC EDGAR XBRL (or mock)     │
│    ├── MacroDataService       → FRED API (or mock)           │
│    ├── PortfolioService       → Intelligence metrics         │
│    ├── BacktestService        → Deterministic engine         │
│    ├── ForecastService        → ML ensemble                  │
│    ├── ReasoningService       → Groq LLM (or mock)           │
│    └── AnalystService         → Structured report fallback   │
└──────────────────────────────────────────────────────────────┘
```

Every external integration has a deterministic mock fallback. The `ServiceFactory` selects the active provider based on which API keys are present in `.env`. The API schema is always fully populated — no partial responses reach the frontend.

---

## Folder Structure

```
BlackGrid/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── market.py              # GET /api/market/overview
│   │   │   │   ├── asset.py               # GET /api/assets/{ticker}
│   │   │   │   ├── forecast.py            # GET /api/forecasts/{ticker}
│   │   │   │   ├── backtest.py            # GET /api/backtests/{ticker}
│   │   │   │   ├── portfolio.py           # GET /api/portfolio/watchlist[/intelligence]
│   │   │   │   └── report.py              # GET /api/report/{ticker}
│   │   │   ├── api.py                     # Router aggregation
│   │   │   └── service_factory.py         # Provider selection and DI
│   │   ├── core/
│   │   │   └── config.py                  # Pydantic Settings (env vars)
│   │   ├── schemas/
│   │   │   └── schemas.py                 # All Pydantic response models
│   │   ├── services/
│   │   │   ├── market_data.py             # Alpha Vantage + mock
│   │   │   ├── market_service.py          # Indices aggregation
│   │   │   ├── sec_data.py                # SEC EDGAR XBRL + mock
│   │   │   ├── macro_data.py              # FRED API + mock
│   │   │   ├── fundamental_service.py     # Combines SEC + FRED
│   │   │   ├── portfolio_service.py       # Watchlist intelligence metrics
│   │   │   ├── indicator_service.py       # Technical indicators
│   │   │   ├── backtest_service.py        # Strategy backtesting
│   │   │   ├── forecast_service.py        # ML ensemble forecasting
│   │   │   ├── reasoning_provider.py      # Groq LLM + mock
│   │   │   ├── analyst_service.py         # Structured fallback report
│   │   │   ├── provider_manager.py        # Provider registry
│   │   │   └── mock_data.py               # Mock data generators
│   │   ├── data/
│   │   │   └── mock_data.py               # Mock data library
│   │   ├── models/
│   │   │   ├── baseline_model.py          # Baseline ML model
│   │   │   └── models.py                  # Additional models
│   │   ├── pipelines/
│   │   │   ├── backtest.py                # Backtesting pipeline
│   │   │   └── features.py                # Feature engineering
│   │   ├── db/
│   │   │   └── session.py                 # SQLAlchemy session
│   │   ├── utils/
│   │   │   └── calculations.py            # Shared calculations
│   │   └── main.py                        # App entrypoint, CORS, health
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── (dashboard)/
│   │   │   ├── dashboard/page.tsx         # Market overview
│   │   │   ├── asset/page.tsx             # Asset browser + detail
│   │   │   ├── report/page.tsx            # AI analyst report
│   │   │   ├── backtest/page.tsx          # Backtest lab
│   │   │   ├── forecast/page.tsx          # Forecast playground
│   │   │   ├── portfolio/page.tsx         # Portfolio intelligence monitor
│   │   │   └── layout.tsx                 # Dashboard shell + sidebar
│   │   └── page.tsx                       # Landing page
│   ├── components/
│   │   ├── common/
│   │   │   ├── Card.tsx                   # GlassCard, DataCard
│   │   │   ├── DashboardLayout.tsx        # Sidebar navigation
│   │   │   └── ScoreBar.tsx               # Score visualization component
│   │   ├── portfolio/
│   │   │   └── WatchlistTable.tsx         # Reusable watchlist component
│   │   ├── charts/
│   │   │   └── ChartContainer.tsx         # Chart wrapper with toolbar
│   │   └── ui/
│   │       └── [shadcn components]        # Button, Card, Alert, Badge, etc.
│   ├── lib/
│   │   ├── api/client.ts                  # Axios client + typed endpoints
│   │   ├── hooks/useApi.ts                # Generic async fetch hook
│   │   └── types/index.ts                 # Shared TypeScript types
│   ├── styles/
│   │   └── globals.css                    # Global Tailwind + variables
│   ├── .env.example
│   ├── package.json
│   └── next.config.js
│
├── docs/
│   ├── INDEX.md                           # Master documentation index
│   ├── QUICKSTART.md                      # 5-minute quick start
│   ├── API_SETUP_GUIDE.md                 # API key configuration
│   ├── ROUTES_IMPLEMENTATION.md           # Route technical details
│   ├── FORECAST_PIPELINE.md               # Forecasting architecture
│   ├── GROQ_QUICK_REFERENCE.md            # LLM integration reference
│   ├── SETUP_CHECKLIST.md                 # Development setup verification
│   └── screenshots/                       # Screenshot placeholders
│
├── tests/                                 # Integration tests
├── setup.sh                               # One-shot setup script
└── README.md                              # This file
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) API keys for live data — all have mock fallbacks, none are required to run

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (all keys optional)
cp .env.example .env

# Start the server
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Start dev server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `ALPHA_VANTAGE_KEY` | No | Live market quotes and OHLCV data. Get a free key at [alphavantage.co](https://www.alphavantage.co/support/#api-key). Without it, realistic mock data is used. |
| `FRED_API_KEY` | No | FRED macro series (10Y Treasury, CPI, unemployment, Fed funds). Get a free key at [fredaccount.stlouisfed.org](https://fredaccount.stlouisfed.org). Without it, stable mock values are used. |
| `GROQ_API_KEY` | No | LLM inference for AI analyst report generation. Get a free key at [console.groq.com](https://console.groq.com). Without it, a structured deterministic fallback report is generated. |
| `GROQ_MODEL` | No | Defaults to `mixtral-8x7b-32768` |
| `SEC_USER_AGENT` | No | Required by EDGAR fair-use policy. Format: `AppName (email@example.com)`. Without it, mock SEC data is used. |
| `MARKET_DATA_PROVIDER` | No | `mock` (default) or `alpha_vantage` |
| `DEBUG` | No | `True` / `False`. Includes full error detail in responses when `True`. |
| `DATABASE_URL` | No | Defaults to `sqlite:///./axiom.db` |
| `SECRET_KEY` | No | JWT signing key (auth layer not yet implemented) |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Backend base URL. Default: `http://localhost:8000/api` |

---

## Available Endpoints

All routes are prefixed with `/api`.

| Method | Path | Query Params | Description |
|---|---|---|---|
| `GET` | `/market/overview` | — | Major index quotes — S&P 500, NASDAQ, Russell 2000, Dow Jones |
| `GET` | `/assets/{ticker}` | — | Asset detail: price, change, technicals, forecast consensus |
| `GET` | `/assets/{ticker}/technical` | — | OHLCV candles and computed technical indicators |
| `GET` | `/forecasts/{ticker}` | `days_ahead` (optional) | Multi-model ML forecast with confidence bands |
| `GET` | `/backtests/{ticker}` | `strategy`, `lookback` (optional) | Strategy backtest with metrics |
| `GET` | `/report/{ticker}` | — | Full AI analyst report (SEC EDGAR + FRED + LLM) |
| `GET` | `/portfolio/watchlist` | — | Watchlist items (ticker, name, price, 24h change) |
| `GET` | `/portfolio/watchlist/intelligence` | `tickers`, `historical_days` (optional) | Full intelligence metrics: signal, confidence, risk, periods, allocation, alerts |
| `GET` | `/health` | — | Health check with UTC timestamp |
| `GET` | `/status` | — | Provider configuration and availability status |

### Portfolio Intelligence Response Format

```json
{
  "status": "success",
  "data": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "current_price": 150.25,
      "change_24h": 1.2,
      "added_date": "2024-01-15",
      "signal_score": 0.45,
      "confidence_score": 78.5,
      "risk_score": 35.2,
      "period_changes": {
        "change_1d": 1.2,
        "change_5d": 2.8,
        "change_1m": 5.1
      },
      "alert_level": "none",
      "alert_message": "No alerts",
      "allocation_weight": 25.5
    }
  ],
  "total_items": 1,
  "updated_at": "2024-03-06T14:30:00Z"
}
```

Full schema documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Data Sources

| Source | Data Provided | Auth | Status |
|---|---|---|---|
| [Alpha Vantage](https://www.alphavantage.co) | Real-time quotes, OHLCV time series | Free API key | Optional (mock fallback) |
| [SEC EDGAR](https://www.sec.gov/developer) | 10-K filings via XBRL company facts API | None (public) | Optional (mock fallback) |
| [FRED](https://fred.stlouisfed.org) | Treasury yields, CPI, Fed funds rate, unemployment | Free API key | Optional (mock fallback) |
| [Groq](https://groq.com) | LLM inference (Mixtral-8x7b) for analyst reports | Free API key | Optional (deterministic fallback) |

The platform runs fully offline without any API keys configured. Mock providers return realistic, deterministic data suitable for development and demonstration.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 14 · TypeScript · Tailwind CSS · Recharts · Lucide Icons · Axios |
| **Backend** | Python 3.11+ · FastAPI · Pydantic v2 · Uvicorn · SQLAlchemy · pandas · NumPy |
| **AI / LLM** | Groq API (Mixtral-8x7b) with fallback to structured generation |
| **Data** | SEC EDGAR XBRL · FRED API · Alpha Vantage · Market data caching |
| **Testing** | pytest (backend) · Integration test suites |

---

## Roadmap

- [x] Portfolio intelligence metrics (signal, confidence, risk, allocation)
- [x] Dark theme institutional dashboard with score visualizations
- [x] AI analyst report generation via Groq
- [x] Backtesting engine with multiple strategies
- [ ] Interactive live OHLCV charts with Recharts
- [ ] WebSocket streaming for real-time price updates
- [ ] News sentiment aggregation and display
- [ ] Multi-ticker side-by-side comparison view
- [ ] PDF export for analyst reports
- [ ] Authentication and persisted user sessions
- [ ] PostgreSQL migration for production deployment
- [ ] Mobile application
- [ ] Portfolio construction optimizer
- [ ] Risk parity allocation engine

---

## Disclaimer

> **This platform is a research and portfolio analysis tool, not a financial advisor.**
>
> All analyst reports, forecasts, price targets, and recommendations generated by this application are produced by AI models and algorithmic processes. They are provided for **informational and educational purposes only** and do **NOT** constitute financial advice, investment recommendations, or solicitations to buy or sell any security.
>
> **Portfolio intelligence metrics including signal scores, confidence scores, and allocation weights are research outputs only.** They are not investment recommendations and should not be used as the sole basis for investment decisions. Historical backtests do not guarantee future results. Market data may be delayed or sourced from mock providers. Volatility and risk metrics are approximate and based on available data windows.
>
> Always consult a qualified financial professional, licensed advisor, or investment manager before making investment decisions. The authors of this project accept no liability for any financial decisions made based on output from this application.

---

## Contributing

We welcome contributions! Please see individual module READMEs in `docs/` for development guidelines.

## Support

For issues, questions, or feature requests, please open a GitHub issue with detailed context and reproducible steps.

## License

This project is provided as-is for educational and research purposes.
