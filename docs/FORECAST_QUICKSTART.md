# Forecast Pipeline - Quick Start Guide

## Quick Integration

### 1. Add to Forecast Route

```python
# backend/app/api/routes/forecast.py
from app.services.forecast_service import ForecastService
from app.services.market_data import AlphaVantageProvider

@router.get("/forecast/{ticker}")
async def generate_forecast(ticker: str, retrain: bool = False):
    """Generate AI forecast for ticker"""
    try:
        # Initialize service with market data provider
        provider = AlphaVantageProvider()
        service = ForecastService(provider)
        
        # Generate comprehensive forecast
        forecast = await service.generate_forecast(ticker, retrain=retrain)
        
        return {
            "status": "success",
            "data": forecast,
            "timestamp": datetime.utcnow()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 2. Test the Pipeline

```bash
cd /Users/adityapareek/BlackGrid
python3 test_forecast_pipeline.py

# Expected output:
# ✅ Feature Pipeline Works: Built 15 features
# ✅ Baseline Model Works: 73.68% accuracy
# ✅ All forecast pipeline components functional!
```

### 3. Use with Mock Provider

```python
from app.services.forecast_service import ForecastService
from app.services.market_data import MockMarketDataProvider

# For testing without API calls
provider = MockMarketDataProvider()
service = ForecastService(provider)
forecast = await service.generate_forecast("AAPL")
```

---

## Feature Pipeline Usage

```python
from app.pipelines.features import FeaturePipeline
import pandas as pd

# Initialize
pipeline = FeaturePipeline()

# Build features from OHLCV data
features_df, feature_cols = pipeline.build_features(df)
# df must have: Open, High, Low, Close, Volume columns
# Returns: DataFrame with original OHLCV + 15 computed features

# Extract recent window for model input
X = pipeline.get_recent_features(features_df, feature_cols, lookback_days=60)
# Returns: (60, 15) numpy array

# Normalize features
X_normalized, mean, std = pipeline.normalize_features(X)
# Returns: Normalized array + statistics for test data

# Flatten for traditional ML (not needed for LSTM/GRU)
X_flat = pipeline.flatten_features(X)
# Converts (batch, lookback, features) → (batch, lookback*features)
```

---

## Baseline Model Usage

```python
from app.models.baseline_model import BaselineModel
from app.pipelines.features import FeaturePipeline

# Initialize
model = BaselineModel(
    lookahead_period=5,      # 5-day forecasts
    direction_threshold=0.005 # 0.5% threshold for BUY/SELL
)

# Train on historical data
features_pipeline = FeaturePipeline()
features_df, feature_cols = features_pipeline.build_features(ohlcv_df)

training_metrics = model.train(features_df, feature_cols, test_size=0.2)
# Returns: {accuracy: float, rmse: float, n_samples: int, n_features: int}

# Make predictions
X_recent = features_pipeline.get_recent_features(features_df, feature_cols)
X_latest = features_pipeline.flatten_features(X_recent)[-1]

prediction = model.predict(X_latest)
# Returns: BaselinePrediction with:
#   - signal: SignalDirection (BUY/HOLD/SELL)
#   - expected_return: float (%)
#   - confidence: float (0-100)
#   - explanation: str

# Access prediction results
print(f"Signal: {prediction.signal}")
print(f"Expected 5-day return: {prediction.expected_return:.2f}%")
print(f"Confidence: {prediction.confidence:.1f}%")
print(f"Explanation: {prediction.explanation}")
```

---

## Forecast Service Usage

```python
from app.services.forecast_service import ForecastService
from app.services.market_data import AlphaVantageProvider

# Initialize with market data provider
provider = AlphaVantageProvider()
service = ForecastService(provider)

# Generate forecast (full pipeline)
forecast = await service.generate_forecast(
    ticker="AAPL",
    retrain=False  # Use cached model if available
)

# Response structure
print(f"Ticker: {forecast.ticker}")
print(f"Current Price: ${forecast.current_price:.2f}")
print(f"Forecast Horizon: {forecast.horizon_days} days")

# Individual model predictions
for model in forecast.models:
    print(f"\n{model.model_name}:")
    print(f"  Signal: {model.signal}")
    print(f"  Expected Return: {model.expected_return:.2f}%")
    print(f"  Confidence: {model.confidence:.1f}%")
    print(f"  Status: {model.status}")
    print(f"  Accuracy: {model.accuracy:.1f}%" if model.accuracy else "  Accuracy: N/A")

# Consensus metrics
consensus = forecast.consensus
print(f"\nConsensus:")
print(f"  Signal: {consensus.consensus_signal}")
print(f"  Probability: {consensus.consensus_probability:.1f}%")
print(f"  Average Confidence: {consensus.average_confidence:.1f}%")
print(f"  Average Expected Return: {consensus.average_return:.2f}%")
print(f"  Model Agreement: {consensus.model_agreement}")
print(f"  Best Model: {consensus.best_model}")
```

---

## Adding New Models

```python
from app.services.forecast_service import ForecastService
from app.models.lstm_model import LSTMModel  # Future implementation

# Create new model instance
lstm_model = LSTMModel(
    input_shape=(60, 15),
    lstm_units=64,
    dropout=0.3
)

# Add to service
service.add_model(
    model_key="lstm",
    model_instance=lstm_model,
    model_name="LSTM/GRU",
    model_type="lstm",
    description="2-layer LSTM with attention mechanism"
)

# Service now automatically includes LSTM in:
# - generate_forecast() → runs LSTM prediction
# - consensus computation → weights LSTM with Baseline
# - response → includes LSTM in models[] array
```

---

## Features Explained

### Daily Returns
- **Computation**: (Close_t - Close_t-1) / Close_t-1
- **Use**: Momentum, volatility calculations
- **Range**: -infinity to +infinity (typically -0.1 to +0.1)

### Rolling Returns (5, 10, 20 day)
- **Computation**: (Close_t - Close_t-N) / Close_t-N
- **Use**: Multi-period momentum, trend identification
- **Range**: Similar to daily returns

### SMA (20, 50 day)
- **Computation**: Average(Close, periods=20/50)
- **Use**: Trend identification, support/resistance levels
- **Signal**: Price > SMA → Uptrend, Price < SMA → Downtrend

### EMA (12, 26 day)
- **Computation**: Exponential moving average (recent data weighted more)
- **Use**: Similar to SMA but more responsive
- **Signal**: EMA12 > EMA26 → Uptrend (MACD foundation)

### RSI (14 day)
- **Computation**: 100 - (100 / (1 + RS))
  - RS = Avg(Gains) / Avg(Losses) over 14 periods
- **Use**: Overbought/Oversold detection
- **Range**: 0-100
- **Signal**: >70 Overbought, <30 Oversold, 50 Neutral

### MACD (12, 26, 9)
- **Computation**:
  - MACD = EMA12 - EMA26
  - Signal = EMA9(MACD)
  - Histogram = MACD - Signal
- **Use**: Trend and momentum
- **Signal**: MACD > Signal → Bullish, MACD < Signal → Bearish

### ATR (14 day)
- **Computation**: Average(True Range, periods=14)
  - True Range = max(High-Low, |High-Close_prev|, |Low-Close_prev|)
- **Use**: Volatility measure, position sizing
- **Higher ATR**: More volatility

### Rolling Volatility (20 day, annualized)
- **Computation**: StdDev(Daily Returns, 20) * sqrt(252)
- **Use**: Risk assessment, regime detection
- **Range**: 0 to ~100+ (as percentage)

### Volume Change
- **Computation**: (Volume_t - Volume_t-1) / Volume_t-1
- **Use**: Trade confirmation, accumulation/distribution
- **Signal**: High positive volume on price increases → Strength

---

## Performance Tuning

### For Better Accuracy
```python
# Retrain model with latest data
forecast = await service.generate_forecast("AAPL", retrain=True)
# Forces model retraining on all historical data

# Use more historical data
# Edit FeaturePipeline.min_required_rows = 250  # Default 100
# Or MarketDataProvider output_size="full"
```

### For Faster Predictions
```python
# Use cached models (default)
forecast = await service.generate_forecast("AAPL", retrain=False)

# Reduce feature window
X = pipeline.get_recent_features(features_df, feature_cols, lookback_days=30)
# Instead of default 60
```

### For Different Forecast Periods
```python
# 10-day forecast instead of 5-day
model = BaselineModel(lookahead_period=10)
service.models["baseline"]["instance"] = model
service.models["baseline"]["is_trained"] = False  # Force retrain

# Retraining will now optimize for 10-day returns
```

---

## Common Patterns

### Pattern 1: Generate Forecast with Error Handling
```python
try:
    forecast = await service.generate_forecast("AAPL")
    return {"status": "success", "data": forecast}
except ValueError as e:
    # Insufficient data
    return {"status": "error", "message": str(e)}
except Exception as e:
    # Unexpected error (API down, etc.)
    logger.error(f"Forecast error: {e}")
    return {"status": "error", "message": "Forecast generation failed"}
```

### Pattern 2: Batch Forecasts for Watchlist
```python
tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
forecasts = []

for ticker in tickers:
    try:
        forecast = await service.generate_forecast(ticker)
        forecasts.append(forecast)
    except Exception as e:
        logger.warning(f"Skipped {ticker}: {e}")

return {"forecasts": forecasts, "count": len(forecasts)}
```

### Pattern 3: Compare Models
```python
forecast = await service.generate_forecast("AAPL")

# Find most optimistic and conservative
optimistic = next(m for m in forecast.models if m.model_name == forecast.consensus.most_optimistic)
conservative = next(m for m in forecast.models if m.model_name == forecast.consensus.most_conservative)

spread = optimistic.expected_return - conservative.expected_return
print(f"Model disagreement: {spread:.2f}% (uncertainty range)")
```

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app/pipelines/features.py` | 474 | Feature engineering pipeline |
| `app/pipelines/__init__.py` | 7 | Pipeline package exports |
| `app/models/baseline_model.py` | 516 | ML baseline model |
| `app/models/__init__.py` | 7 | Models package exports |
| `app/services/forecast_service.py` | 434 | Forecasting service orchestrator |
| `test_forecast_pipeline.py` | 47 | Test script (in project root) |
| `FORECAST_PIPELINE.md` | Documentation | Full architecture reference |

---

## Troubleshooting

### "Insufficient data" Error
```
ValueError: Insufficient data: 50 rows. Need 100
```
**Solution**: Market provider returned <100 data points
- Check if ticker is valid
- Try with provider="full" to get maximum historical data
- Some tickers may not have 100+ days of data

### Model Not Trained
```
ValueError: Model not trained. Call train() first.
```
**Solution**: Model not yet trained on data
- ForecastService automatically trains on first `generate_forecast()` call
- If error persists, try with `retrain=True`

### Import Errors
```
ModuleNotFoundError: No module named 'numpy'
```
**Solution**: Missing ML dependencies
```bash
cd backend
pip3 install -r requirements.txt
```

### Pydantic Warnings
```
UserWarning: Field "model_name" has conflict with protected namespace "model_"
```
**Note**: These are warnings only, not errors. Core functionality works correctly.

---

## Next Steps

1. **Integrate with API Routes**
   - Add `/forecast/{ticker}` endpoint
   - Connect to existing API module structure

2. **Add More Models**
   - LSTM for sequence learning
   - GRU for computational efficiency
   - Temporal Fusion Transformer for multi-horizon

3. **Add Backtesting**
   - Use baseline predictions to test strategy returns
   - Optimize model hyperparameters

4. **Add Caching**
   - Cache trained models in database
   - Cache market data by hour
   - Reduce retraining frequency

5. **Add Monitoring**
   - Track prediction accuracy over time
   - Alert if model accuracy degrades
   - Detect data quality issues
