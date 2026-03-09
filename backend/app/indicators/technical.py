"""Reusable pandas-based technical indicator functions."""

from __future__ import annotations

import pandas as pd
import numpy as np


def sma(series: pd.Series, period: int = 20) -> pd.Series:
    """SMA = (A1 + A2 + ... + An) / n"""
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int = 20) -> pd.Series:
    """EMA = Price*(2/(1+n)) + EMA_prev*(1 - 2/(1+n))"""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI = 100 - 100/(1+RS), RS = Wilder avg_gain / avg_loss"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> dict:
    """MACD Line = EMA(12) - EMA(26). Signal = EMA(9) of MACD. Histogram = MACD - Signal."""
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal_period)
    return {"macd": macd_line, "signal": signal_line, "histogram": macd_line - signal_line}


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder ATR using EWM with com=period-1."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period, adjust=False).mean()


def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> dict:
    """Bollinger Bands: Middle=SMA(20), Upper=Middle+2s, Lower=Middle-2s."""
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std(ddof=0)
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    pct_b = (series - lower) / (upper - lower).replace(0, np.nan)
    bandwidth = (upper - lower) / middle.replace(0, np.nan)
    return {"upper": upper, "middle": middle, "lower": lower,
            "pct_b": pct_b, "bandwidth": bandwidth}


def rolling_volatility(series: pd.Series, period: int = 20) -> pd.Series:
    """Annualised vol = StdDev(daily_returns, period) * sqrt(252) * 100"""
    return series.pct_change().rolling(window=period).std() * np.sqrt(252) * 100


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """OBV: cumulative volume — add on up days, subtract on down days."""
    return (np.sign(close.diff()).fillna(0) * volume).cumsum()


def compute_all_indicators(df: pd.DataFrame) -> dict:
    """Accept OHLCV DataFrame and return all technical indicators."""
    close, high, low = df["close"], df["high"], df["low"]
    price = float(close.iloc[-1])

    rsi_val = rsi(close).iloc[-1]
    macd_data = macd(close)
    atr_val = atr(high, low, close).iloc[-1]
    vol_val = rolling_volatility(close).iloc[-1]
    ema_20_val = ema(close, 20).iloc[-1]
    ema_50_val = ema(close, 50).iloc[-1]
    bb = bollinger_bands(close)

    def _s(v, d=0.0):
        return round(float(v), 4) if not pd.isna(v) else d

    rsi_signal = "bullish" if rsi_val < 40 else ("bearish" if rsi_val > 60 else "neutral")
    macd_signal = "bullish" if macd_data["histogram"].iloc[-1] > 0 else "bearish"
    ema_signal = "bullish" if price > ema_20_val else "bearish"

    return {
        "rsi": _s(rsi_val, 50.0),
        "rsi_signal": rsi_signal,
        "macd_val": _s(macd_data["macd"].iloc[-1]),
        "macd_signal_val": _s(macd_data["signal"].iloc[-1]),
        "macd_histogram": _s(macd_data["histogram"].iloc[-1]),
        "macd_signal": macd_signal,
        "atr": _s(atr_val),
        "volatility": _s(vol_val, 20.0),
        "ema_20": _s(ema_20_val, price),
        "ema_50": _s(ema_50_val, price),
        "ema_signal": ema_signal,
        "bb_upper": _s(bb["upper"].iloc[-1], price * 1.02),
        "bb_lower": _s(bb["lower"].iloc[-1], price * 0.98),
        "bb_pct_b": _s(bb["pct_b"].iloc[-1], 0.5),
        "bb_bandwidth": _s(bb["bandwidth"].iloc[-1], 0.04),
    }


# Backward-compatible alias
def compute_indicators(df: pd.DataFrame) -> dict:
    return compute_all_indicators(df)
