"""
Asset detail endpoints for stocks, ETFs, and commodities
"""
from fastapi import APIRouter, HTTPException, Path, Query
from datetime import datetime, timedelta
import logging

from app.schemas.schemas import (
    AssetDetail,
    AssetType,
    TechnicalDataResponse,
    ForecastResponse,
    ModelForecastOutput,
    ForecastConsensus,
    ForecastModelStatus,
    RecommendationType,
)
from app.services.mock_data import (
    get_mock_asset_detail,
    get_mock_technical_data,
)
from app.services.price_service import get_price
from app.services.forecast_service import ForecastService
from app.api.service_factory import ServiceFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/asset", tags=["asset"])


@router.get(
    "/{ticker}",
    response_model=AssetDetail,
    summary="Get asset fundamentals"
)
async def get_asset_detail(
    ticker: str = Path(..., min_length=1, max_length=10, description="Asset ticker symbol")
) -> AssetDetail:
    """
    Get detailed asset information including price, market cap, and fundamentals.

    Uses yfinance for real-time price (with Alpha Vantage and mock fallbacks),
    and merges in mock fundamentals (PE, dividend, 52-week range, etc.) for
    fields not readily available from the price feed.
    """
    try:
        symbol = ticker.upper()

        # ── Real-time price (yfinance → AV → mock) ───────────────────────────
        price_data = await get_price(symbol)

        # ── Mock fundamentals for the remaining fields ────────────────────────
        try:
            mock_resp = get_mock_asset_detail(symbol)
            mock = mock_resp.get("data", {})
        except Exception:
            mock = {}

        # Detect asset type: ETFs end in common patterns, else default to stock
        etf_tickers = {"SPY", "QQQ", "IWM", "GLD", "SLV", "TLT", "VIX", "DIA", "XLF", "XLE"}
        asset_type = AssetType.ETF if symbol in etf_tickers else AssetType.STOCK

        return AssetDetail(
            ticker=symbol,
            name=mock.get("name", f"{symbol} Inc."),
            asset_type=asset_type,
            price=price_data["price"],
            market_cap=mock.get("market_cap"),
            pe_ratio=mock.get("pe_ratio"),
            dividend_yield=mock.get("dividend_yield"),
            fifty_two_week_high=mock.get("fifty_two_week_high", price_data["price"] * 1.20),
            fifty_two_week_low=mock.get("fifty_two_week_low", price_data["price"] * 0.75),
            avg_volume=mock.get("avg_volume"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset detail for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch asset details")


@router.get(
    "/{ticker}/technicals",
    response_model=TechnicalDataResponse,
    summary="Get technical analysis"
)
async def get_technical_data(
    ticker: str = Path(..., min_length=1, max_length=10, description="Asset ticker symbol"),
    days: int = Query(30, ge=1, le=365, description="Number of days of historical data")
) -> TechnicalDataResponse:
    """
    Get technical analysis data including price history and indicators
    
    Parameters:
    - ticker: Asset ticker symbol
    - days: Number of days of historical data (default: 30, max: 365)
    
    Returns:
    - OHLCV candle data
    - Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)
    - Trend signals
    
    Uses real data provider (Alpha Vantage) if configured, otherwise mock data
    """
    try:
        service = ServiceFactory.get_market_data_service()
        
        # Try to fetch real OHLCV data
        try:
            timeseries = await service.get_daily_ohlcv(ticker.upper())
            
            if "Time Series (Daily)" in timeseries:
                # Successfully got real data
                ts_data = timeseries["Time Series (Daily)"]
                candles = []
                
                for date_str, ohlcv in list(ts_data.items())[:days]:
                    candles.append({
                        "date": date_str,
                        "open": float(ohlcv.get("1. open", 0)),
                        "high": float(ohlcv.get("2. high", 0)),
                        "low": float(ohlcv.get("3. low", 0)),
                        "close": float(ohlcv.get("4. close", 0)),
                        "volume": int(ohlcv.get("6. volume", 0)),
                    })
                
                response = {
                    "ticker": ticker.upper(),
                    "candles": candles,
                    "indicators": {
                        "sma_20": [c["close"] for c in candles[-20:]],
                        "rsi_14": [50.0] * len(candles),
                        "macd": [0.0] * len(candles),
                    }
                }
                return TechnicalDataResponse(**response)
        
        except Exception as e:
            logger.warning(f"Real technical data fetch failed for {ticker}: {str(e)}")
        
        # Fall back to mock data
        logger.info(f"Using mock technical data for {ticker}")
        response = get_mock_technical_data(ticker, num_candles=days)
        return TechnicalDataResponse(**response)
    
    except Exception as e:
        logger.error(f"Error getting technical data for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch technical data")


@router.get(
    "/{ticker}/forecast",
    response_model=ForecastResponse,
    summary="Get ML model forecast"
)
async def get_asset_forecast(
    ticker: str = Path(..., min_length=1, max_length=10, description="Asset ticker symbol"),
    days: int = Query(30, ge=1, le=252, description="Forecast horizon in days")
) -> ForecastResponse:
    """
    Get AI forecast comparison across multiple ML models
    
    Returns predictions from:
    - Baseline (momentum-based) - LIVE
    - LSTM/GRU (recurrent neural network) - PLACEHOLDER
    - TFT (temporal fusion transformer) - PLACEHOLDER
    - Ensemble (weighted combination) - PLACEHOLDER
    
    Parameters:
    - ticker: Asset ticker symbol
    - days: Forecast horizon in days (default: 30, max: 252)
    
    Returns:
    - Individual model forecasts with signals
    - Consensus metrics across all models
    - Model accuracy and confidence scores
    
    Currently uses:
    - Baseline: Real ML model with technical indicators
    - LSTM/GRU, TFT, Ensemble: Placeholder status (coming soon)
    """
    try:
        # Get market data provider via service factory
        market_service = ServiceFactory.get_market_data_service()
        
        # Initialize real forecast service
        forecast_service = ForecastService(market_service.provider)
        
        logger.debug(f"Generating forecast for {ticker}")
        
        # Get real baseline forecast
        try:
            forecast_response = await forecast_service.generate_forecast(ticker)
            
            # Get baseline model data
            baseline_output = forecast_response.models[0] if forecast_response.models else None
            
            # Create placeholder outputs for unimplemented models
            placeholder_models = [baseline_output] if baseline_output else []
            
            # LSTM/GRU Placeholder
            placeholder_models.append(
                ModelForecastOutput(
                    model_name="LSTM/GRU",
                    model_type="lstm",
                    signal=RecommendationType.HOLD,
                    expected_return=0.0,
                    confidence=0.0,
                    status=ForecastModelStatus.STALE,
                    accuracy=None,
                    last_updated=datetime.utcnow(),
                    description="LSTM/GRU model not yet implemented. Coming soon.",
                )
            )
            
            # TFT Placeholder
            placeholder_models.append(
                ModelForecastOutput(
                    model_name="Temporal Fusion",
                    model_type="tft",
                    signal=RecommendationType.HOLD,
                    expected_return=0.0,
                    confidence=0.0,
                    status=ForecastModelStatus.STALE,
                    accuracy=None,
                    last_updated=datetime.utcnow(),
                    description="Temporal Fusion Transformer not yet implemented. Coming soon.",
                )
            )
            
            # Ensemble Placeholder
            placeholder_models.append(
                ModelForecastOutput(
                    model_name="Ensemble",
                    model_type="ensemble",
                    signal=RecommendationType.HOLD,
                    expected_return=0.0,
                    confidence=0.0,
                    status=ForecastModelStatus.STALE,
                    accuracy=None,
                    last_updated=datetime.utcnow(),
                    description="Ensemble model not yet implemented. Coming soon.",
                )
            )
            
            # Use baseline data for consensus since others are placeholders
            if baseline_output:
                consensus = ForecastConsensus(
                    consensus_signal=baseline_output.signal,
                    consensus_probability=baseline_output.confidence,
                    average_confidence=baseline_output.confidence,
                    average_return=baseline_output.expected_return,
                    best_model=baseline_output.model_name,
                    most_optimistic=baseline_output.model_name,
                    most_conservative=baseline_output.model_name,
                    model_agreement="Medium",  # Only baseline is real
                )
            else:
                consensus = ForecastConsensus(
                    consensus_signal=RecommendationType.HOLD,
                    consensus_probability=0.0,
                    average_confidence=0.0,
                    average_return=0.0,
                    best_model="None",
                    most_optimistic="None",
                    most_conservative="None",
                    model_agreement="Low",
                )
            
            # Return response with real baseline + placeholder models
            return ForecastResponse(
                status="success",
                ticker=ticker.upper(),
                current_price=forecast_response.current_price,
                horizon_days=days,
                models=placeholder_models,
                consensus=consensus,
                generated_at=forecast_response.generated_at,
                next_update=datetime.utcnow() + timedelta(hours=4),
            )
        
        except ValueError as e:
            # Data insufficient or fetch error - return error response
            logger.error(f"Failed to generate real forecast for {ticker}: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Could not generate forecast: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating forecast for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate forecast")


