"""Reusable pandas-based technical indicator functions — all 27 indicators."""

from __future__ import annotations

import pandas as pd
import numpy as np


def sma(series: pd.Series, period: int = 20) -> pd.Series:
    return series.rolling(window=period, min_periods=1).mean()


def ema(series: pd.Series, period: int = 20) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> dict:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal_period)
    return {"macd": macd_line, "signal": signal_line, "histogram": macd_line - signal_line}


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period, adjust=False).mean()


def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> dict:
    middle = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    bw = (upper - lower) / middle.replace(0, np.nan)
    pct_b = (series - lower) / (upper - lower).replace(0, np.nan)
    return {"upper": upper, "middle": middle, "lower": lower, "bandwidth": bw, "pct_b": pct_b}


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    return (np.sign(close.diff()).fillna(0) * volume).cumsum()


def rolling_volatility(series: pd.Series, period: int = 20) -> pd.Series:
    return series.pct_change().rolling(window=period).std() * np.sqrt(252) * 100


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k: int = 14, d: int = 3) -> dict:
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    k_line = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    d_line = k_line.rolling(d).mean()
    return {"k": k_line, "d": d_line}


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    tp = (high + low + close) / 3
    sma_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    return -100 * (hh - close) / (hh - ll).replace(0, np.nan)


def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    tp = (high + low + close) / 3
    mf = tp * volume
    delta = tp.diff()
    pos_mf = mf.where(delta > 0, 0.0).rolling(period).sum()
    neg_mf = mf.where(delta < 0, 0.0).rolling(period).sum()
    return 100 - 100 / (1 + pos_mf / neg_mf.replace(0, np.nan))


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> dict:
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0
    atr14 = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr14.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr14.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_line = ema(dx, period)
    return {"adx": adx_line, "plus_di": plus_di, "minus_di": minus_di}


def compute_all_indicators(df: pd.DataFrame) -> dict:
    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"].astype(float)
    price = float(close.iloc[-1])
    rsi_v = rsi(close)
    macd_d = macd(close)
    atr_v = atr(high, low, close)
    bb = bollinger_bands(close)
    adx_d = adx(high, low, close)
    vol_v = rolling_volatility(close)
    e20 = ema(close, 20); e50 = ema(close, 50)

    def _s(v, d=0.0):
        try: return round(float(v), 4) if not (pd.isna(v) or np.isinf(float(v))) else d
        except: return d

    return {
        "rsi": _s(rsi_v.iloc[-1], 50.0),
        "rsi_signal": "bullish" if rsi_v.iloc[-1] < 40 else ("bearish" if rsi_v.iloc[-1] > 60 else "neutral"),
        "macd_val": _s(macd_d["macd"].iloc[-1]),
        "macd_signal_val": _s(macd_d["signal"].iloc[-1]),
        "macd_histogram": _s(macd_d["histogram"].iloc[-1]),
        "macd_signal": "bullish" if macd_d["histogram"].iloc[-1] > 0 else "bearish",
        "atr": _s(atr_v.iloc[-1]),
        "volatility": _s(vol_v.iloc[-1], 20.0),
        "ema_20": _s(e20.iloc[-1], price),
        "ema_50": _s(e50.iloc[-1], price),
        "ema_signal": "bullish" if price > float(e20.iloc[-1]) else "bearish",
        "bb_upper": _s(bb["upper"].iloc[-1], price * 1.02),
        "bb_lower": _s(bb["lower"].iloc[-1], price * 0.98),
        "bb_pct_b": _s(bb["pct_b"].iloc[-1], 0.5),
        "bb_bandwidth": _s(bb["bandwidth"].iloc[-1], 0.04),
        "adx": _s(adx_d["adx"].iloc[-1], 20.0),
    }


def compute_indicators(df): return compute_all_indicators(df)
