# Axiom Terminal - Backend API

FastAPI-powered backend for the Axiom Terminal financial research platform.

## Tech Stack

- **Framework**: FastAPI
- **Server**: Uvicorn
- **Database**: SQLAlchemy ORM (SQLite dev, PostgreSQL production)
- **Data Processing**: pandas, numpy
- **Validation**: Pydantic
- **Testing**: pytest, pytest-asyncio
- **ML Ready**: Structure ready for PyTorch integration

## Project Structure

```
backend/
├── app/
│   ├── main.py                # FastAPI application entry point
│   ├── api/
│   │   ├── api.py            # API v1 router
│   │   └── routes/           # API endpoint routes
│   │       ├── market.py      # Market overview endpoints
│   │       ├── asset.py       # Asset detail endpoints
│   │       ├── report.py      # Analyst report endpoints
│   │       ├── backtest.py    # Backtesting endpoints
│   │       └── portfolio.py   # Portfolio/watchlist endpoints
│   ├── core/
│   │   └── config.py          # Application configuration
│   ├── db/
│   │   └── session.py         # Database session management
│   ├── models/
│   │   └── models.py          # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── schemas.py         # Pydantic request/response schemas
│   ├── services/              # Business logic services
│   ├── utils/
│   │   └── calculations.py    # Data processing utilities
│   ├── data/
│   │   └── mock_data.py       # Mock data generators
│   └── ml/                    # ML models (future)
├── tests/
├── requirements.txt
├── .env.example
└── .gitignore
```

## Getting Started

### Prerequisites

- Python 3.10+
- pip or conda

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` from `.env.example`:
```bash
cp .env.example .env
```

4. Update `.env` with your configuration

### Development

Run the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at [http://localhost:8000](http://localhost:8000)

API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Market
- `GET /api/market/overview` - Get market overview with top movers

### Asset
- `GET /api/asset/{ticker}` - Get asset details
- `GET /api/asset/{ticker}/technicals` - Get technical analysis data
- `GET /api/asset/{ticker}/forecast` - Get AI price forecast

### Report
- `GET /api/asset/{ticker}/report` - Get analyst report (currently at `/asset/{ticker}`)
- `POST /api/asset/{ticker}/report/regenerate` - Regenerate report

### Backtest
- `GET /api/backtests/summary` - Get backtest results
- `POST /api/backtests/run` - Run new backtest

### Portfolio
- `GET /api/portfolio/watchlist` - Get watchlist
- `POST /api/portfolio/watchlist/{ticker}` - Add to watchlist
- `DELETE /api/portfolio/watchlist/{ticker}` - Remove from watchlist

## Database Models

- **Asset** - Stock, ETF, bond, commodity metadata
- **MarketData** - OHLCV historical data
- **Watchlist** - User's watched assets
- **BacktestResult** - Backtest performance metrics

## Configuration

Edit `.env` to customize:

```
DATABASE_URL=sqlite:///./test.db
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
SECRET_KEY=your-secret-key
DEBUG=True
```

## Mock Data

During development, all endpoints return mock data from `app/data/mock_data.py`. Replace these with real data providers (Alpha Vantage, Yahoo Finance, etc.) as needed.

### Mock Data Generators

- `generate_mock_market_data()` - OHLCV candle data
- `generate_mock_asset_details()` - Asset information
- `generate_mock_forecast()` - Price predictions
- `generate_mock_analyst_report()` - Report text and recommendation
- `generate_mock_backtest_summary()` - Backtest results
- `generate_mock_watchlist()` - Watchlist items

## Data Processing Utilities

Located in `app/utils/calculations.py`:

- `calculate_technical_indicators()` - SMA, EMA, RSI, MACD
- `calculate_returns()` - Daily returns calculation
- `calculate_sharpe_ratio()` - Performance metric
- `calculate_max_drawdown()` - Risk metric

## ML Integration (Future)

The `app/ml/` directory is ready for ML models. Structure it as:

```
app/ml/
├── models/          # Trained model files
├── pipelines/       # ML pipelines
├── forecast.py      # Price forecasting models
├── classifier.py    # Sentiment/signal classification
└── utils.py         # ML utilities
```

## Testing

```bash
pytest tests/
pytest --cov=app tests/  # With coverage
```

## Future Enhancements

- Integration with real data providers (Alpha Vantage, IEX Cloud)
- WebSocket real-time data streaming
- Advanced ML models for forecasting
- Portfolio optimization algorithms
- Risk analysis and VaR calculations
- News sentiment analysis
- Options pricing models
- Macroeconomic indicators integration

## Notes

- All development uses SQLite for simplicity
- Switch to PostgreSQL in `.env` for production
- Mock data ensures rapid iteration during development
- Routes use async/await for performance
- Pydantic ensures strict type validation
