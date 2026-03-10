"""Baseline logistic regression model for next-day direction prediction."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from app.pipelines.features import build_features

FEATURE_COLS = [
    "return_1d", "return_5d", "return_10d",
    "price_sma20_ratio", "price_ema20_ratio", "sma20_sma50_cross",
    "rsi_14", "macd_histogram",
    "atr_14", "volatility_20",
    "volume_change", "volume_sma_ratio",
]


def train_and_predict(df: pd.DataFrame) -> dict:
    """Train baseline model on historical data and predict next direction.

    Args:
        df: OHLCV DataFrame with columns: open, high, low, close, volume

    Returns:
        dict with direction, probability, confidence, expected_return
    """
    features = build_features(df)

    if len(features) < 60:
        return {
            "direction": "up",
            "probability": 0.5,
            "confidence": 0.0,
            "expected_return": 0.0,
            "explanation": "Insufficient data for model training.",
        }

    X = features[FEATURE_COLS].values
    y = features["target"].values

    # Walk-forward: train on all but last 20, predict on last
    train_size = len(X) - 20
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, C=0.1, random_state=42)
    model.fit(X_train_scaled, y_train)

    proba = model.predict_proba(X_test_scaled)[-1]
    prob_up = float(proba[1]) if len(proba) > 1 else 0.5
    direction = "up" if prob_up > 0.5 else "down"

    # Test accuracy on recent predictions
    preds = model.predict(X_test_scaled)
    accuracy = float(np.mean(preds == y_test))

    # Expected return estimate from recent returns
    recent_returns = features["return_1d"].iloc[-20:]
    expected_return = float(recent_returns.mean() * 100) * (1 if direction == "up" else -1)

    confidence = abs(prob_up - 0.5) * 2  # 0 at 50%, 1 at 100%

    return {
        "direction": direction,
        "probability": round(prob_up, 4),
        "confidence": round(confidence, 4),
        "expected_return": round(expected_return, 2),
        "explanation": f"Logistic regression on {len(FEATURE_COLS)} technical features. Recent walk-forward accuracy: {accuracy:.1%}. Direction probability: {prob_up:.1%}.",
    }
