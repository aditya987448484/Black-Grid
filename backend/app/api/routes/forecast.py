"""
ML model forecast comparison endpoints
Connects to real forecast service with baseline ml models
"""
from fastapi import APIRouter, HTTPException, Path, Query
from datetime import datetime, timedelta
import logging

from app.schemas.schemas import (
    ForecastResponse,
    ModelForecastOutput,
    ForecastConsensus,
    ForecastModelStatus,
    RecommendationType,
)
from app.services.forecast_service import ForecastService
from app.api.service_factory import ServiceFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get(
    "/{ticker}",
    response_model=ForecastResponse,
    summary="Get ML model forecast"
)
async def get_forecast_comparison(
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
    - ticker: Asset ticker symbol (e.g., AAPL, MSFT)
    - days: Forecast horizon in days (default: 30, max: 252)
    
    Returns:
    - Individual model forecasts with signals and confidence
    - Consensus metrics across all models
    - Model accuracy and performance metrics
    
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

