"""
Baseline Forecasting Model
Simple, production-ready implementation using Logistic Regression and Gradient Boosting
Designed to be easily replaced with LSTM, GRU, or Transformer models
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class SignalDirection(str, Enum):
    """Forecasted direction"""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


@dataclass
class BaselinePrediction:
    """Output from baseline model"""
    signal: SignalDirection
    expected_return: float
    confidence: float
    direction_proba: Dict[str, float]
    explanation: str


class BaselineModel:
    """
    Simple baseline forecasting model using sklearn
    
    Architecture:
    - Direction Classification: Logistic Regression
    - Return Estimation: Gradient Boosting Regressor
    
    Target Variables:
    - Direction: 1 if next_day_return > threshold (0.5%), else 0
    - Expected Return: Actual forward return percentage
    
    Design Principles:
    - Simple, interpretable baseline
    - No hyperparameter tuning (production defaults)
    - Easy to replace with DL models (same interface)
    - Graceful degradation on insufficient data
    """
    
    def __init__(
        self,
        direction_threshold: float = 0.005,  # 0.5% for up/down classification
        lookahead_period: int = 5,  # 5-day forward return
    ):
        """
        Initialize baseline model
        
        Args:
            direction_threshold: Threshold for classifying up/down (as decimal)
            lookahead_period: Days ahead to forecast
        """
        self.direction_threshold = direction_threshold
        self.lookahead_period = lookahead_period
        
        # Models
        self.direction_classifier = LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight="balanced",  # Handle class imbalance
        )
        self.return_regressor = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            random_state=42,
            verbose=0,
        )
        
        # Feature scaler
        self.scaler = StandardScaler()
        
        # Training state
        self.is_trained = False
        self.training_accuracy = None
        self.training_rmse = None
        self.n_features = None
        self.last_trained_at = None
    
    def prepare_training_data(
        self,
        df: pd.DataFrame,
        feature_cols: list,
        min_required_rows: int = 50,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare training data from features and price data
        
        Args:
            df: DataFrame with features and Close price
            feature_cols: List of feature column names
            min_required_rows: Minimum rows needed for training
        
        Returns:
            Tuple of (X_features, y_direction, y_return)
        
        Raises:
            ValueError: If insufficient data
        """
        if len(df) < self.lookahead_period + min_required_rows:
            raise ValueError(
                f"Insufficient data: {len(df)} rows. Need "
                f"at least {self.lookahead_period + min_required_rows}"
            )
        
        # Extract features
        X = df[feature_cols].values
        
        # Calculate forward returns (shift by lookahead_period into past)
        forward_returns = df["Close"].pct_change(periods=-self.lookahead_period).shift(-self.lookahead_period)
        
        # Remove rows with NaN labels
        valid_idx = ~forward_returns.isna()
        X = X[valid_idx]
        forward_returns = forward_returns[valid_idx].values
        
        # Generate direction labels: 1 if up, 0 if down
        y_direction = (forward_returns > self.direction_threshold).astype(int)
        
        # Generate return labels (actual forward returns)
        y_return = forward_returns * 100  # Convert to percentage
        
        logger.debug(
            f"Prepared training data: {X.shape} features, "
            f"direction: {np.mean(y_direction):.1%} positive, "
            f"returns: μ={np.mean(y_return):.2f}%, σ={np.std(y_return):.2f}%"
        )
        
        return X, y_direction, y_return
    
    def train(
        self,
        df: pd.DataFrame,
        feature_cols: list,
        test_size: float = 0.2,
    ) -> Dict[str, float]:
        """
        Train both direction classifier and return regressor
        
        Args:
            df: DataFrame with features
            feature_cols: List of feature column names
            test_size: Fraction of data to use for validation
        
        Returns:
            Dictionary with training metrics (accuracy, rmse)
        """
        try:
            # Prepare data
            X, y_direction, y_return = self.prepare_training_data(df, feature_cols)
            
            # Split data
            X_train, X_test, y_dir_train, y_dir_test, y_ret_train, y_ret_test = train_test_split(
                X, y_direction, y_return,
                test_size=test_size,
                random_state=42,
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train direction classifier
            self.direction_classifier.fit(X_train_scaled, y_dir_train)
            direction_accuracy = self.direction_classifier.score(X_test_scaled, y_dir_test)
            
            # Train return regressor
            self.return_regressor.fit(X_train_scaled, y_ret_train)
            y_ret_pred = self.return_regressor.predict(X_test_scaled)
            mse = np.mean((y_ret_test - y_ret_pred) ** 2)
            rmse = np.sqrt(mse)
            
            # Store training info
            self.is_trained = True
            self.training_accuracy = direction_accuracy
            self.training_rmse = rmse
            self.n_features = X.shape[1]
            
            from datetime import datetime
            self.last_trained_at = datetime.utcnow()
            
            logger.info(
                f"Baseline model trained: accuracy={direction_accuracy:.2%}, "
                f"rmse={rmse:.3f}%, features={self.n_features}"
            )
            
            return {
                "accuracy": float(direction_accuracy),
                "rmse": float(rmse),
                "n_samples": len(X),
                "n_features": self.n_features,
            }
        
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise
    
    def predict(
        self,
        X: np.ndarray,
        return_proba: bool = True,
    ) -> BaselinePrediction:
        """
        Make prediction on new data
        
        Args:
            X: Feature array of shape (n_features,) or (1, n_features)
            return_proba: Whether to return probabilities
        
        Returns:
            BaselinePrediction with signal, expected_return, confidence
        
        Raises:
            ValueError: If model not trained or shape mismatch
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        
        # Reshape if needed
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        if X.shape[1] != self.n_features:
            raise ValueError(
                f"Feature mismatch: expected {self.n_features}, got {X.shape[1]}"
            )
        
        # Scale
        X_scaled = self.scaler.transform(X)
        
        # Direction prediction
        y_dir_pred = self.direction_classifier.predict(X_scaled)[0]
        if return_proba:
            proba = self.direction_classifier.predict_proba(X_scaled)[0]
            prob_negative = float(proba[0])
            prob_positive = float(proba[1])
        else:
            prob_negative = 0.5
            prob_positive = 0.5
        
        # Return prediction
        y_ret_pred = self.return_regressor.predict(X_scaled)[0]
        expected_return = float(y_ret_pred)
        
        # Convert direction to signal
        if y_dir_pred == 1:
            signal = SignalDirection.BUY if prob_positive > 0.65 else SignalDirection.HOLD
            confidence = round(prob_positive * 100, 1)
        else:
            signal = SignalDirection.SELL if prob_negative > 0.65 else SignalDirection.HOLD
            confidence = round(prob_negative * 100, 1)
        
        # Create explanation
        explanation = self._explain_prediction(signal, expected_return, confidence)
        
        return BaselinePrediction(
            signal=signal,
            expected_return=expected_return,
            confidence=confidence,
            direction_proba={
                "BUY": round(prob_positive * 100, 1),
                "SELL": round(prob_negative * 100, 1),
            },
            explanation=explanation,
        )
    
    def _explain_prediction(
        self,
        signal: SignalDirection,
        expected_return: float,
        confidence: float,
    ) -> str:
        """Generate human-readable explanation of prediction"""
        if signal == SignalDirection.BUY:
            return (
                f"Model predicts upside with {confidence:.0f}% confidence. "
                f"Expected {self.lookahead_period}-day return: +{expected_return:.1f}%."
            )
        elif signal == SignalDirection.SELL:
            return (
                f"Model predicts downside with {confidence:.0f}% confidence. "
                f"Expected {self.lookahead_period}-day return: {expected_return:.1f}%."
            )
        else:
            return (
                f"Model is neutral (mixed signals). "
                f"Expected {self.lookahead_period}-day return: {expected_return:.1f}%."
            )
    
    def get_feature_importance(self, top_n: int = 5) -> Dict[str, float]:
        """
        Get top N important features from return regressor
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            return {}
        
        importances = self.return_regressor.feature_importances_
        
        # This will be meaningful once we have feature names
        # For now, just return raw importances
        return {
            f"feature_{i}": float(imp)
            for i, imp in enumerate(importances[:top_n])
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata"""
        return {
            "model_name": "Baseline",
            "model_type": "baseline",
            "is_trained": self.is_trained,
            "n_features": self.n_features,
            "training_accuracy": self.training_accuracy,
            "training_rmse": self.training_rmse,
            "lookahead_period": self.lookahead_period,
            "direction_threshold": self.direction_threshold,
            "last_trained_at": self.last_trained_at.isoformat() if self.last_trained_at else None,
        }
