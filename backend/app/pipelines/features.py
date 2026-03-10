"""Feature engineering pipeline for ML models."""

from __future__ import annotations

import pandas as pd
import numpy as np
from app.indicators.technical import sma, ema, rsi, macd, atr, rolling_volatility


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build feature matrix from OHLCV DataFrame.

    Returns a DataFrame with features aligned to original index.
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    features = pd.DataFrame(index=df.index)

    # Returns
    features["return_1d"] = close.pct_change()
    features["return_5d"] = close.pct_change(5)
    features["return_10d"] = close.pct_change(10)

    # Moving averages
    features["sma_20"] = sma(close, 20)
    features["sma_50"] = sma(close, 50)
    features["ema_20"] = ema(close, 20)
    features["ema_50"] = ema(close, 50)

    # Price relative to MAs
    features["price_sma20_ratio"] = close / features["sma_20"]
    features["price_ema20_ratio"] = close / features["ema_20"]
    features["sma20_sma50_cross"] = (features["sma_20"] > features["sma_50"]).astype(float)

    # RSI
    features["rsi_14"] = rsi(close, 14)

    # MACD
    macd_data = macd(close)
    features["macd_line"] = macd_data["macd"]
    features["macd_signal"] = macd_data["signal"]
    features["macd_histogram"] = macd_data["histogram"]

    # Volatility
    features["atr_14"] = atr(high, low, close, 14)
    features["volatility_20"] = rolling_volatility(close, 20)

    # Volume
    features["volume_change"] = volume.pct_change()
    features["volume_sma_ratio"] = volume / sma(volume.astype(float), 20)

    # Target: next day direction (1 = up, 0 = down)
    features["target"] = (close.shift(-1) > close).astype(float)

    return features.dropna()
