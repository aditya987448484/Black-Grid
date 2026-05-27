"""
Forecast Service
Orchestrates feature engineering, model predictions, and structured responses
Integrates with market data fetching and multiple forecast models
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import numpy as np
import pandas as pd

from app.pipelines.features import FeaturePipeline
from app.models.baseline_model import BaselineModel, SignalDirection
from app.schemas.schemas import (
    ForecastResponse,
    ModelForecastOutput,
    ForecastConsensus,
    ForecastModelStatus,
    RecommendationType,
)
from app.services.market_data import MarketDataProvider, TimeInterval

logger = logging.getLogger(__name__)


class ForecastService:
    """
    Comprehensive forecast service using multiple models
    
    Architecture:
    - Fetches market data (OHLCV)
    - Builds features via FeaturePipeline
    - Runs multiple forecast models (Baseline initially, LSTM/GRU/TFT coming)
    - Computes consensus across models
    - Returns structured ForecastResponse
    
    Design:
    - Modular model integration (easy to add LSTM, GRU, TFT)
    - Graceful fallback on data insufficiency
    - Ensemble consensus across models
    - Configurable forecast horizon
    """
    
    def __init__(self, market_data_provider: MarketDataProvider):
        """
        Initialize forecast service
        
        Args:
            market_data_provider: Instance of MarketDataProvider (Alpha Vantage, Mock, etc.)
        """
        self.market_data_provider = market_data_provider
        self.feature_pipeline = FeaturePipeline()
        
        # Models dictionary - easily extensible
        self.models: Dict[str, Dict[str, Any]] = {
            "baseline": {
                "instance": BaselineModel(lookahead_period=5),
                "name": "Baseline",
                "type": "baseline",
                "description": "Simple momentum indicator based on recent price action and technical indicators",
                "is_trained": False,
            }
        }
        
        # Configuration
        self.forecast_horizon_days = 30
        self.min_data_points = 100
    
    async def generate_forecast(
        self,
        ticker: str,
        retrain: bool = False,
    ) -> ForecastResponse:
        """
        Generate comprehensive forecast for ticker
        
        Pipeline:
        1. Fetch OHLCV data from market data provider
        2. Build features via pipeline
        3. Train/load models
        4. Run predictions
        5. Compute consensus
        6. Return structured response
        
        Args:
            ticker: Stock ticker (e.g., "AAPL")
            retrain: Force retraining of models
        
        Returns:
            ForecastResponse with all model predictions and consensus
        
        Raises:
            ValueError: If insufficient data or market provider error
        """
        logger.info(f"Generating forecast for {ticker}")
        
        try:
            # Step 1: Fetch market data
            logger.debug(f"Fetching market data for {ticker}")
            market_data = await self._fetch_market_data(ticker)
            
            # Step 2: Build features
            logger.debug(f"Building features from {len(market_data)} rows")
            features_df, feature_cols = self.feature_pipeline.build_features(market_data)
            
            # Step 3: Get current price and prepare data
            current_price = features_df["Close"].iloc[-1]
            
            # Step 4: Train/predict with all models
            logger.debug(f"Running predictions with {len(self.models)} models")
            model_forecasts = []
            
            for model_key, model_info in self.models.items():
                try:
                    forecast = await self._run_model_forecast(
                        model_key,
                        features_df,
                        feature_cols,
                        current_price,
                        retrain=retrain,
                    )
                    model_forecasts.append(forecast)
                except Exception as e:
                    logger.error(f"Model {model_key} failed: {e}")
                    # Add fallback/error forecast
                    model_forecasts.append(
                        self._create_error_forecast(model_info)
                    )
            
            # Step 5: Compute consensus
            consensus = self._compute_consensus(model_forecasts)
            
            # Step 6: Construct response
            response = ForecastResponse(
                status="success",
                ticker=ticker,
                current_price=float(current_price),
                horizon_days=self.forecast_horizon_days,
                models=model_forecasts,
                consensus=consensus,
                generated_at=datetime.utcnow(),
                next_update=datetime.utcnow() + timedelta(hours=1),
            )
            
            logger.info(
                f"Forecast generated for {ticker}: consensus={consensus.consensus_signal}"
            )
            
            return response
        
        except ValueError as e:
            logger.error(f"Forecast generation failed for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in forecast: {e}")
            raise ValueError(f"Forecast generation failed: {str(e)}")
    
    async def _fetch_market_data(self, ticker: str) -> pd.DataFrame:
        """
        Fetch OHLCV data from market data provider
        
        Args:
            ticker: Stock ticker
        
        Returns:
            DataFrame with OHLCV columns, index is datetime
        
        Raises:
            ValueError: If insufficient data or provider error
        """
        try:
            # Fetch data with full history
            data_dict = await self.market_data_provider.get_time_series(
                ticker,
                interval=TimeInterval.DAILY,
                output_size="full",  # Get all available data
            )
            
            if not data_dict or "Time Series (Daily)" not in data_dict:
                raise ValueError(f"No time series data received for {ticker}")
            
            # Convert to DataFrame
            time_series = data_dict.get("Time Series (Daily)", {})
            if not time_series:
                raise ValueError(f"Empty time series for {ticker}")
            
            rows = []
            for date_str, day_data in time_series.items():
                try:
                    rows.append({
                        "Date": pd.to_datetime(date_str),
                        "Open": float(day_data.get("1. open", 0)),
                        "High": float(day_data.get("2. high", 0)),
                        "Low": float(day_data.get("3. low", 0)),
                        "Close": float(day_data.get("4. close", 0)),
                        "Volume": int(day_data.get("6. volume", 0)),
                    })
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid row {date_str}: {e}")
                    continue
            
            if not rows:
                raise ValueError(f"No valid OHLCV data for {ticker}")
            
            df = pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
            df.set_index("Date", inplace=True)
            
            # Validate data
            if len(df) < self.min_data_points:
                raise ValueError(
                    f"Insufficient data: {len(df)} rows. Need {self.min_data_points}"
                )
            
            logger.debug(f"Fetched {len(df)} rows for {ticker}")
            
            return df
        
        except Exception as e:
            logger.error(f"Market data fetch failed for {ticker}: {e}")
            raise ValueError(f"Market data fetch failed: {str(e)}")
    
    async def _run_model_forecast(
        self,
        model_key: str,
        features_df: pd.DataFrame,
        feature_cols: List[str],
        current_price: float,
        retrain: bool = False,
    ) -> ModelForecastOutput:
        """
        Run single model forecast
        
        Args:
            model_key: Key in self.models dict
            features_df: DataFrame with computed features
            feature_cols: List of feature column names
            current_price: Current stock price
            retrain: Force retraining
        
        Returns:
            ModelForecastOutput with prediction and metadata
        """
        model_info = self.models[model_key]
        model_instance = model_info["instance"]
        
        try:
            # Train model if needed
            if retrain or not model_instance.is_trained:
                logger.debug(f"Training model {model_key}")
                metrics = model_instance.train(features_df, feature_cols)
                model_info["is_trained"] = True
                logger.debug(f"Model {model_key} trained: accuracy={metrics['accuracy']:.2%}")
            
            # Get recent features
            X_recent = self.feature_pipeline.get_recent_features(
                features_df,
                feature_cols,
                lookback_days=60,
            )
            
            # Flatten for traditional ML models
            X_latest = self.feature_pipeline.flatten_features(X_recent)[-1]
            
            # Predict
            prediction = model_instance.predict(X_latest)
            
            # Convert to response object
            signal_map = {
                SignalDirection.BUY: RecommendationType.BUY,
                SignalDirection.HOLD: RecommendationType.HOLD,
                SignalDirection.SELL: RecommendationType.SELL,
            }
            
            return ModelForecastOutput(
                model_name=model_info["name"],
                model_type=model_info["type"],
                signal=signal_map[prediction.signal],
                expected_return=prediction.expected_return,
                confidence=prediction.confidence,
                status=ForecastModelStatus.READY,
                accuracy=model_instance.training_accuracy * 100 if model_instance.training_accuracy else None,
                last_updated=model_instance.last_trained_at or datetime.utcnow(),
                description=model_info["description"],
            )
        
        except Exception as e:
            logger.error(f"Model {model_key} prediction failed: {e}")
            return self._create_error_forecast(model_info)
    
    def _create_error_forecast(self, model_info: Dict[str, Any]) -> ModelForecastOutput:
        """Create error/fallback forecast"""
        return ModelForecastOutput(
            model_name=model_info["name"],
            model_type=model_info["type"],
            signal=RecommendationType.HOLD,
            expected_return=0.0,
            confidence=0.0,
            status=ForecastModelStatus.ERROR,
            accuracy=None,
            last_updated=datetime.utcnow(),
            description="Model encountered error during prediction",
        )
    
    def _compute_consensus(
        self,
        model_forecasts: List[ModelForecastOutput],
    ) -> ForecastConsensus:
        """
        Compute consensus across model predictions
        
        Args:
            model_forecasts: List of ModelForecastOutput from all models
        
        Returns:
            ForecastConsensus with aggregated metrics
        """
        # Filter out error models
        valid_forecasts = [
            f for f in model_forecasts
            if f.status != ForecastModelStatus.ERROR
        ]
        
        if not valid_forecasts:
            # All models failed - neutral fallback
            return ForecastConsensus(
                consensus_signal=RecommendationType.HOLD,
                consensus_probability=0.0,
                average_confidence=0.0,
                average_return=0.0,
                best_model="None",
                most_optimistic="None",
                most_conservative="None",
                model_agreement="Low",
            )
        
        # Count signals
        buy_count = sum(1 for f in valid_forecasts if f.signal == RecommendationType.BUY)
        sell_count = sum(1 for f in valid_forecasts if f.signal == RecommendationType.SELL)
        hold_count = len(valid_forecasts) - buy_count - sell_count
        
        # Determine consensus signal
        max_count = max(buy_count, sell_count, hold_count)
        if buy_count == max_count:
            consensus_signal = RecommendationType.BUY
            consensus_prob = buy_count / len(valid_forecasts) * 100
        elif sell_count == max_count:
            consensus_signal = RecommendationType.SELL
            consensus_prob = sell_count / len(valid_forecasts) * 100
        else:
            consensus_signal = RecommendationType.HOLD
            consensus_prob = hold_count / len(valid_forecasts) * 100
        
        # Average metrics
        avg_confidence = np.mean([f.confidence for f in valid_forecasts])
        avg_return = np.mean([f.expected_return for f in valid_forecasts])
        
        # Best models
        best_model = max(
            valid_forecasts,
            key=lambda f: f.accuracy if f.accuracy else 0,
        ).model_name
        
        most_optimistic = max(
            valid_forecasts,
            key=lambda f: f.expected_return,
        ).model_name
        
        most_conservative = min(
            valid_forecasts,
            key=lambda f: f.expected_return,
        ).model_name
        
        # Model agreement
        if len(set([f.signal for f in valid_forecasts])) == 1:
            agreement = "High"
        elif len(set([f.signal for f in valid_forecasts])) == 2:
            agreement = "Medium"
        else:
            agreement = "Low"
        
        return ForecastConsensus(
            consensus_signal=consensus_signal,
            consensus_probability=round(consensus_prob, 1),
            average_confidence=round(avg_confidence, 1),
            average_return=round(avg_return, 2),
            best_model=best_model,
            most_optimistic=most_optimistic,
            most_conservative=most_conservative,
            model_agreement=agreement,
        )
    
    def add_model(
        self,
        model_key: str,
        model_instance: Any,
        model_name: str,
        model_type: str,
        description: str,
    ) -> None:
        """
        Add new model to ensemble
        
        Allows plugging in LSTM, GRU, TFT, or other models
        
        Args:
            model_key: Internal key (e.g., "lstm")
            model_instance: Model instance with predict() and train() methods
            model_name: Display name (e.g., "LSTM/GRU")
            model_type: Type string (e.g., "lstm")
            description: Model description
        """
        self.models[model_key] = {
            "instance": model_instance,
            "name": model_name,
            "type": model_type,
            "description": description,
            "is_trained": False,
        }
        logger.info(f"Added model: {model_name} ({model_type})")
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service metadata"""
        return {
            "service": "ForecastService",
            "models": list(self.models.keys()),
            "forecast_horizon_days": self.forecast_horizon_days,
            "min_data_points": self.min_data_points,
            "trained_models": [
                k for k, v in self.models.items()
                if v["is_trained"]
            ],
        }
