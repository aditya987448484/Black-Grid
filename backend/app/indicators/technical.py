"""Reusable pandas-based technical indicator functions."""

from __future__ import annotations

import pandas as pd
import numpy as np


def sma(series: pd.Series, period: int = 20) -> pd.Series:
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int = 20) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> dict:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def rolling_volatility(series: pd.Series, period: int = 20) -> pd.Series:
    returns = series.pct_change()
    return returns.rolling(window=period).std() * np.sqrt(252) * 100


def compute_all_indicators(df: pd.DataFrame) -> dict:
    """Accept OHLCV DataFrame and return all technical indicators.

    Expected columns: open, high, low, close, volume
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rsi_val = rsi(close).iloc[-1]
    macd_data = macd(close)
    atr_val = atr(high, low, close).iloc[-1]
    vol_val = rolling_volatility(close).iloc[-1]
    ema_20 = ema(close, 20).iloc[-1]
    ema_50 = ema(close, 50).iloc[-1]

    rsi_signal = "bullish" if rsi_val < 40 else ("bearish" if rsi_val > 60 else "neutral")
    macd_signal = "bullish" if macd_data["histogram"].iloc[-1] > 0 else "bearish"
    price = close.iloc[-1]
    ema_signal = "bullish" if price > ema_20 else "bearish"

    return {
        "rsi": round(float(rsi_val), 2) if not pd.isna(rsi_val) else 50.0,
        "rsi_signal": rsi_signal,
        "macd_val": round(float(macd_data["macd"].iloc[-1]), 4) if not pd.isna(macd_data["macd"].iloc[-1]) else 0.0,
        "macd_signal_val": round(float(macd_data["signal"].iloc[-1]), 4) if not pd.isna(macd_data["signal"].iloc[-1]) else 0.0,
        "macd_histogram": round(float(macd_data["histogram"].iloc[-1]), 4) if not pd.isna(macd_data["histogram"].iloc[-1]) else 0.0,
        "macd_signal": macd_signal,
        "atr": round(float(atr_val), 2) if not pd.isna(atr_val) else 0.0,
        "volatility": round(float(vol_val), 2) if not pd.isna(vol_val) else 20.0,
        "ema_20": round(float(ema_20), 2) if not pd.isna(ema_20) else price,
        "ema_50": round(float(ema_50), 2) if not pd.isna(ema_50) else price,
        "ema_signal": ema_signal,
    }
