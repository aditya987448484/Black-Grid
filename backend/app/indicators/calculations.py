"""
Unified indicator computation engine.

Provides ``compute_indicator(df, indicator_key, params)`` which can compute
any of the 100 indicators defined in the catalog and returns a pandas Series.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Reuse existing helpers from technical.py
# ---------------------------------------------------------------------------
from .technical import (
    sma as _sma,
    ema as _ema,
    rsi as _rsi,
    macd as _macd,
    atr as _atr,
    bollinger_bands as _bollinger_bands,
    obv as _obv,
    stochastic as _stochastic,
    cci as _cci,
    williams_r as _williams_r,
    mfi as _mfi,
    adx as _adx,
    rolling_volatility as _rolling_volatility,
)

from .registry import INDICATOR_CATALOG


# ===================================================================
# Internal helper functions
# ===================================================================

def _wma(series: pd.Series, period: int) -> pd.Series:
    """Linearly weighted moving average."""
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(window=period, min_periods=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def _rma(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing / Running Moving Average (alpha = 1/period)."""
    return series.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Single-bar true range."""
    prev_c = close.shift(1)
    return pd.concat(
        [high - low, (high - prev_c).abs(), (low - prev_c).abs()], axis=1
    ).max(axis=1)


def _clv(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Close Location Value."""
    hl = (high - low).replace(0, np.nan)
    return ((close - low) - (high - close)) / hl


def _consecutive(condition: pd.Series) -> pd.Series:
    """Running count of consecutive True values; resets on False."""
    groups = (~condition).cumsum()
    return condition.groupby(groups).cumsum().astype(float)


def _ichimoku_line(high: pd.Series, low: pd.Series, period: int) -> pd.Series:
    """(Highest high + Lowest low) / 2 over *period*."""
    return (high.rolling(period, min_periods=1).max()
            + low.rolling(period, min_periods=1).min()) / 2


def _keltner(high: pd.Series, low: pd.Series, close: pd.Series,
             ema_period: int, atr_period: int, multiplier: float) -> dict:
    """Return dict with keys 'upper', 'lower', 'middle'."""
    mid = _ema(close, ema_period)
    atr_val = _atr(high, low, close, atr_period)
    return {
        "upper": mid + multiplier * atr_val,
        "lower": mid - multiplier * atr_val,
        "middle": mid,
    }


def _merge_params(indicator_key: str, user_params: dict | None) -> dict:
    """Merge catalog defaults with user overrides; user wins."""
    meta = INDICATOR_CATALOG.get(indicator_key, {})
    defaults = dict(meta.get("parameters", {}))
    if user_params:
        defaults.update(user_params)
    return defaults


# ===================================================================
# TREND (1-10)
# ===================================================================

def _calc_sma(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return _sma(close, period)


def _calc_ema(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return _ema(close, period)


def _calc_wma(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return _wma(close, period)


def _calc_hma(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    half = max(int(period / 2), 1)
    sqrt_p = max(int(math.sqrt(period)), 1)
    wma_half = _wma(close, half)
    wma_full = _wma(close, period)
    diff = 2 * wma_half - wma_full
    return _wma(diff, sqrt_p)


def _calc_dema(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    e1 = _ema(close, period)
    e2 = _ema(e1, period)
    return 2 * e1 - e2


def _calc_tema(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    e1 = _ema(close, period)
    e2 = _ema(e1, period)
    e3 = _ema(e2, period)
    return 3 * e1 - 3 * e2 + e3


def _calc_vwma(close: pd.Series, volume: pd.Series, period: int = 20, **_kw) -> pd.Series:
    cv = (close * volume).rolling(window=period, min_periods=1).sum()
    v_sum = volume.rolling(window=period, min_periods=1).sum()
    return cv / v_sum.replace(0, np.nan)


def _calc_rma(close: pd.Series, period: int = 14, **_kw) -> pd.Series:
    return _rma(close, period)


def _calc_alma(close: pd.Series, period: int = 20, offset_pct: float = 0.85,
               sigma: float = 6.0, **_kw) -> pd.Series:
    m = offset_pct * (period - 1)
    s = period / sigma
    w = np.exp(-((np.arange(period) - m) ** 2) / (2 * s * s))
    w /= w.sum()
    return close.rolling(window=period, min_periods=period).apply(
        lambda x: np.dot(x, w), raw=True
    )


def _calc_kama(close: pd.Series, period: int = 10, fast_period: int = 2,
               slow_period: int = 30, **_kw) -> pd.Series:
    fast_sc = 2.0 / (fast_period + 1)
    slow_sc = 2.0 / (slow_period + 1)
    direction = (close - close.shift(period)).abs()
    volatility = close.diff().abs().rolling(window=period, min_periods=period).sum()
    er = direction / volatility.replace(0, np.nan)
    er = er.fillna(0)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama_values = close.copy().astype(float)
    kama_values[:] = np.nan
    first_valid = period
    while first_valid < len(close) and pd.isna(sc.iloc[first_valid]):
        first_valid += 1
    if first_valid < len(close):
        kama_values.iloc[first_valid] = close.iloc[first_valid]
        for i in range(first_valid + 1, len(close)):
            if pd.isna(sc.iloc[i]):
                kama_values.iloc[i] = kama_values.iloc[i - 1]
            else:
                kama_values.iloc[i] = (kama_values.iloc[i - 1]
                                       + sc.iloc[i] * (close.iloc[i] - kama_values.iloc[i - 1]))
    return kama_values


# ===================================================================
# MOMENTUM (11-20)
# ===================================================================

def _calc_rsi(close: pd.Series, period: int = 14, **_kw) -> pd.Series:
    return _rsi(close, period)


def _calc_stoch_k(high: pd.Series, low: pd.Series, close: pd.Series,
                  k_period: int = 14, d_period: int = 3, **_kw) -> pd.Series:
    return _stochastic(high, low, close, k_period, d_period)["k"]


def _calc_stoch_d(high: pd.Series, low: pd.Series, close: pd.Series,
                  k_period: int = 14, d_period: int = 3, **_kw) -> pd.Series:
    return _stochastic(high, low, close, k_period, d_period)["d"]


def _calc_stoch_rsi(close: pd.Series, rsi_period: int = 14,
                    stoch_period: int = 14, smooth_k: int = 3, **_kw) -> pd.Series:
    r = _rsi(close, rsi_period)
    ll = r.rolling(stoch_period).min()
    hh = r.rolling(stoch_period).max()
    stoch_rsi_raw = (r - ll) / (hh - ll).replace(0, np.nan)
    return stoch_rsi_raw.rolling(smooth_k).mean() * 100


def _calc_cci(high: pd.Series, low: pd.Series, close: pd.Series,
              period: int = 20, **_kw) -> pd.Series:
    return _cci(high, low, close, period)


def _calc_williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = 14, **_kw) -> pd.Series:
    return _williams_r(high, low, close, period)


def _calc_roc(close: pd.Series, period: int = 12, **_kw) -> pd.Series:
    prev = close.shift(period)
    return ((close - prev) / prev.replace(0, np.nan)) * 100


def _calc_momentum(close: pd.Series, period: int = 10, **_kw) -> pd.Series:
    prev = close.shift(period)
    return close / prev.replace(0, np.nan)


def _calc_tsi(close: pd.Series, long_period: int = 25, short_period: int = 13,
              **_kw) -> pd.Series:
    delta = close.diff()
    double_smoothed = _ema(_ema(delta, long_period), short_period)
    double_smoothed_abs = _ema(_ema(delta.abs(), long_period), short_period)
    return 100 * double_smoothed / double_smoothed_abs.replace(0, np.nan)


def _calc_ultimate_osc(high: pd.Series, low: pd.Series, close: pd.Series,
                       period1: int = 7, period2: int = 14, period3: int = 28,
                       **_kw) -> pd.Series:
    prev_close = close.shift(1)
    bp = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    tr = _true_range(high, low, close)
    avg1 = bp.rolling(period1).sum() / tr.rolling(period1).sum().replace(0, np.nan)
    avg2 = bp.rolling(period2).sum() / tr.rolling(period2).sum().replace(0, np.nan)
    avg3 = bp.rolling(period3).sum() / tr.rolling(period3).sum().replace(0, np.nan)
    return 100 * (4 * avg1 + 2 * avg2 + avg3) / 7


# ===================================================================
# OSCILLATOR (21-30)
# ===================================================================

def _calc_macd_line(close: pd.Series, fast: int = 12, slow: int = 26,
                    signal_period: int = 9, **_kw) -> pd.Series:
    return _macd(close, fast, slow, signal_period)["macd"]


def _calc_macd_signal(close: pd.Series, fast: int = 12, slow: int = 26,
                      signal_period: int = 9, **_kw) -> pd.Series:
    return _macd(close, fast, slow, signal_period)["signal"]


def _calc_macd_histogram(close: pd.Series, fast: int = 12, slow: int = 26,
                         signal_period: int = 9, **_kw) -> pd.Series:
    return _macd(close, fast, slow, signal_period)["histogram"]


def _calc_ppo(close: pd.Series, fast: int = 12, slow: int = 26,
              signal_period: int = 9, **_kw) -> pd.Series:
    fast_ema = _ema(close, fast)
    slow_ema = _ema(close, slow)
    return ((fast_ema - slow_ema) / slow_ema.replace(0, np.nan)) * 100


def _calc_trix(close: pd.Series, period: int = 15, **_kw) -> pd.Series:
    e1 = _ema(close, period)
    e2 = _ema(e1, period)
    e3 = _ema(e2, period)
    prev = e3.shift(1)
    return ((e3 - prev) / prev.replace(0, np.nan)) * 100


def _calc_ao(high: pd.Series, low: pd.Series, fast: int = 5, slow: int = 34,
             **_kw) -> pd.Series:
    median = (high + low) / 2
    return _sma(median, fast) - _sma(median, slow)


def _calc_ac(high: pd.Series, low: pd.Series, fast: int = 5, slow: int = 34,
             smooth: int = 5, **_kw) -> pd.Series:
    ao_val = _calc_ao(high, low, fast, slow)
    return ao_val - _sma(ao_val, smooth)


def _calc_fisher_transform(high: pd.Series, low: pd.Series, period: int = 10,
                           **_kw) -> pd.Series:
    median = (high + low) / 2
    ll = median.rolling(period).min()
    hh = median.rolling(period).max()
    raw = 2 * ((median - ll) / (hh - ll).replace(0, np.nan)) - 1
    raw = raw.clip(-0.999, 0.999).fillna(0)
    return 0.5 * np.log((1 + raw) / (1 - raw).replace(0, np.nan))


def _calc_coppock(close: pd.Series, wma_period: int = 10,
                  roc_long: int = 14, roc_short: int = 11, **_kw) -> pd.Series:
    roc_l = _calc_roc(close, roc_long)
    roc_s = _calc_roc(close, roc_short)
    return _wma(roc_l + roc_s, wma_period)


def _calc_detrended_price(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    shift_n = period // 2 + 1
    return close - _sma(close, period).shift(shift_n)


# ===================================================================
# VOLATILITY (31-40)
# ===================================================================

def _calc_bbands_upper(close: pd.Series, period: int = 20, std_dev: float = 2.0,
                       **_kw) -> pd.Series:
    return _bollinger_bands(close, period, std_dev)["upper"]


def _calc_bbands_lower(close: pd.Series, period: int = 20, std_dev: float = 2.0,
                       **_kw) -> pd.Series:
    return _bollinger_bands(close, period, std_dev)["lower"]


def _calc_bbands_middle(close: pd.Series, period: int = 20, std_dev: float = 2.0,
                        **_kw) -> pd.Series:
    return _bollinger_bands(close, period, std_dev)["middle"]


def _calc_bbands_width(close: pd.Series, period: int = 20, std_dev: float = 2.0,
                       **_kw) -> pd.Series:
    return _bollinger_bands(close, period, std_dev)["bandwidth"]


def _calc_bbands_pctb(close: pd.Series, period: int = 20, std_dev: float = 2.0,
                      **_kw) -> pd.Series:
    return _bollinger_bands(close, period, std_dev)["pct_b"]


def _calc_keltner_upper(high: pd.Series, low: pd.Series, close: pd.Series,
                        ema_period: int = 20, atr_period: int = 14,
                        multiplier: float = 2.0, **_kw) -> pd.Series:
    return _keltner(high, low, close, ema_period, atr_period, multiplier)["upper"]


def _calc_keltner_lower(high: pd.Series, low: pd.Series, close: pd.Series,
                        ema_period: int = 20, atr_period: int = 14,
                        multiplier: float = 2.0, **_kw) -> pd.Series:
    return _keltner(high, low, close, ema_period, atr_period, multiplier)["lower"]


def _calc_atr(high: pd.Series, low: pd.Series, close: pd.Series,
              period: int = 14, **_kw) -> pd.Series:
    return _atr(high, low, close, period)


def _calc_natr(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 14, **_kw) -> pd.Series:
    atr_val = _atr(high, low, close, period)
    return (atr_val / close.replace(0, np.nan)) * 100


def _calc_historical_vol(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return _rolling_volatility(close, period)


# ===================================================================
# VOLUME (41-50)
# ===================================================================

def _calc_obv(close: pd.Series, volume: pd.Series, **_kw) -> pd.Series:
    return _obv(close, volume)


def _calc_cmf(high: pd.Series, low: pd.Series, close: pd.Series,
              volume: pd.Series, period: int = 20, **_kw) -> pd.Series:
    clv = _clv(high, low, close)
    mf_volume = clv * volume
    return mf_volume.rolling(period).sum() / volume.rolling(period).sum().replace(0, np.nan)


def _calc_mfi(high: pd.Series, low: pd.Series, close: pd.Series,
              volume: pd.Series, period: int = 14, **_kw) -> pd.Series:
    return _mfi(high, low, close, volume, period)


def _calc_vwap(high: pd.Series, low: pd.Series, close: pd.Series,
               volume: pd.Series, period: int = 20, **_kw) -> pd.Series:
    tp = (high + low + close) / 3
    tp_vol = (tp * volume).rolling(period, min_periods=1).sum()
    vol_sum = volume.rolling(period, min_periods=1).sum()
    return tp_vol / vol_sum.replace(0, np.nan)


def _calc_ad_line(high: pd.Series, low: pd.Series, close: pd.Series,
                  volume: pd.Series, **_kw) -> pd.Series:
    clv = _clv(high, low, close)
    return (clv * volume).cumsum()


def _calc_eom(high: pd.Series, low: pd.Series, volume: pd.Series,
              period: int = 14, **_kw) -> pd.Series:
    distance_moved = ((high + low) / 2) - ((high.shift(1) + low.shift(1)) / 2)
    box_ratio = (volume / 1e6) / (high - low).replace(0, np.nan)
    raw_eom = distance_moved / box_ratio.replace(0, np.nan)
    return raw_eom.rolling(period).mean()


def _calc_volume_sma(volume: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return _sma(volume, period)


def _calc_volume_ratio(volume: pd.Series, period: int = 20, **_kw) -> pd.Series:
    vol_sma = _sma(volume, period)
    return volume / vol_sma.replace(0, np.nan)


def _calc_pvt(close: pd.Series, volume: pd.Series, **_kw) -> pd.Series:
    pct_chg = close.pct_change().fillna(0)
    return (pct_chg * volume).cumsum()


def _calc_nvi(close: pd.Series, volume: pd.Series, **_kw) -> pd.Series:
    pct_chg = close.pct_change().fillna(0)
    vol_decrease = volume < volume.shift(1)
    nvi = pd.Series(np.nan, index=close.index, dtype=float)
    nvi.iloc[0] = 1000.0
    for i in range(1, len(close)):
        if vol_decrease.iloc[i]:
            nvi.iloc[i] = nvi.iloc[i - 1] * (1 + pct_chg.iloc[i])
        else:
            nvi.iloc[i] = nvi.iloc[i - 1]
    return nvi


# ===================================================================
# MARKET STRUCTURE (51-60)
# ===================================================================

def _calc_donchian_upper(high: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return high.rolling(period, min_periods=1).max()


def _calc_donchian_lower(low: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return low.rolling(period, min_periods=1).min()


def _calc_rolling_high(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return close.rolling(period, min_periods=1).max()


def _calc_rolling_low(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return close.rolling(period, min_periods=1).min()


def _calc_higher_high(high: pd.Series, period: int = 5, **_kw) -> pd.Series:
    prev_max = high.shift(1).rolling(period, min_periods=1).max()
    return (high > prev_max).astype(float)


def _calc_lower_low(low: pd.Series, period: int = 5, **_kw) -> pd.Series:
    prev_min = low.shift(1).rolling(period, min_periods=1).min()
    return (low < prev_min).astype(float)


def _calc_breakout_up(high: pd.Series, close: pd.Series, period: int = 20,
                      **_kw) -> pd.Series:
    prev_high = high.shift(1).rolling(period, min_periods=1).max()
    return (close > prev_high).astype(float)


def _calc_breakout_down(low: pd.Series, close: pd.Series, period: int = 20,
                        **_kw) -> pd.Series:
    prev_low = low.shift(1).rolling(period, min_periods=1).min()
    return (close < prev_low).astype(float)


def _calc_pivot_high(high: pd.Series, left: int = 5, right: int = 5,
                     **_kw) -> pd.Series:
    result = pd.Series(0.0, index=high.index)
    for i in range(left, len(high) - right):
        window_left = high.iloc[i - left: i]
        window_right = high.iloc[i + 1: i + right + 1]
        if (high.iloc[i] > window_left.max()) and (high.iloc[i] > window_right.max()):
            result.iloc[i] = 1.0
    return result


def _calc_pivot_low(low: pd.Series, left: int = 5, right: int = 5,
                    **_kw) -> pd.Series:
    result = pd.Series(0.0, index=low.index)
    for i in range(left, len(low) - right):
        window_left = low.iloc[i - left: i]
        window_right = low.iloc[i + 1: i + right + 1]
        if (low.iloc[i] < window_left.min()) and (low.iloc[i] < window_right.min()):
            result.iloc[i] = 1.0
    return result


# ===================================================================
# MEAN REVERSION (61-70)
# ===================================================================

def _calc_zscore(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    mean = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    return (close - mean) / std.replace(0, np.nan)


def _calc_pct_from_sma(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    s = _sma(close, period)
    return ((close - s) / s.replace(0, np.nan)) * 100


def _calc_pct_from_ema(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    e = _ema(close, period)
    return ((close - e) / e.replace(0, np.nan)) * 100


def _calc_mean_rev_signal(close: pd.Series, period: int = 20,
                          entry_z: float = -2.0, exit_z: float = 0.0,
                          **_kw) -> pd.Series:
    z = _calc_zscore(close, period)
    return (z <= entry_z).astype(float)


def _calc_rsi_divergence(close: pd.Series, rsi_period: int = 14,
                         lookback: int = 10, **_kw) -> pd.Series:
    """Simplified divergence: sign(rsi_change) - sign(price_change).

    Positive = bullish divergence (price fell, RSI rose).
    Negative = bearish divergence (price rose, RSI fell).
    """
    r = _rsi(close, rsi_period)
    price_delta = close - close.shift(lookback)
    rsi_delta = r - r.shift(lookback)
    return np.sign(rsi_delta) - np.sign(price_delta)


def _calc_price_channel_position(close: pd.Series, period: int = 20,
                                 **_kw) -> pd.Series:
    rh = close.rolling(period, min_periods=1).max()
    rl = close.rolling(period, min_periods=1).min()
    rng = (rh - rl).replace(0, np.nan)
    return (close - rl) / rng


def _calc_bb_position(close: pd.Series, period: int = 20, std_dev: float = 2.0,
                      **_kw) -> pd.Series:
    return _bollinger_bands(close, period, std_dev)["pct_b"]


def _calc_keltner_position(high: pd.Series, low: pd.Series, close: pd.Series,
                           ema_period: int = 20, atr_period: int = 14,
                           multiplier: float = 2.0, **_kw) -> pd.Series:
    kc = _keltner(high, low, close, ema_period, atr_period, multiplier)
    rng = (kc["upper"] - kc["lower"]).replace(0, np.nan)
    return (close - kc["lower"]) / rng


def _calc_stdev_channel_upper(close: pd.Series, period: int = 20,
                              multiplier: float = 2.0, **_kw) -> pd.Series:
    mean = _sma(close, period)
    std = close.rolling(period).std(ddof=0)
    return mean + multiplier * std


def _calc_stdev_channel_lower(close: pd.Series, period: int = 20,
                              multiplier: float = 2.0, **_kw) -> pd.Series:
    mean = _sma(close, period)
    std = close.rolling(period).std(ddof=0)
    return mean - multiplier * std


# ===================================================================
# BREADTH / RELATIVE (71-80)
# ===================================================================

def _calc_relative_strength(close: pd.Series, period: int = 20,
                            **_kw) -> pd.Series:
    """Rolling return ratio vs benchmark. Without a benchmark column, returns 1 + return."""
    benchmark = _kw.get("benchmark")
    asset_ret = close.pct_change(period).fillna(0)
    if benchmark is not None and isinstance(benchmark, pd.Series):
        bench_ret = benchmark.pct_change(period).fillna(0).replace(0, np.nan)
        return asset_ret / bench_ret
    return 1 + asset_ret


def _calc_return_over_n(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    prev = close.shift(period)
    return ((close - prev) / prev.replace(0, np.nan)) * 100


def _calc_gap_pct(open_: pd.Series, close: pd.Series, **_kw) -> pd.Series:
    prev_close = close.shift(1)
    return ((open_ - prev_close) / prev_close.replace(0, np.nan)) * 100


def _calc_true_range(high: pd.Series, low: pd.Series, close: pd.Series,
                     **_kw) -> pd.Series:
    return _true_range(high, low, close)


def _calc_avg_true_range_pct(high: pd.Series, low: pd.Series, close: pd.Series,
                             period: int = 14, **_kw) -> pd.Series:
    atr_val = _atr(high, low, close, period)
    return (atr_val / close.replace(0, np.nan)) * 100


def _calc_up_down_ratio(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    diff = close.diff()
    up = (diff > 0).astype(float).rolling(period).sum()
    down = (diff < 0).astype(float).rolling(period).sum()
    return up / down.replace(0, np.nan)


def _calc_positive_bars_pct(close: pd.Series, period: int = 20,
                            **_kw) -> pd.Series:
    diff = close.diff()
    return (diff > 0).astype(float).rolling(period).mean() * 100


def _calc_consecutive_up(close: pd.Series, **_kw) -> pd.Series:
    return _consecutive(close > close.shift(1))


def _calc_consecutive_down(close: pd.Series, **_kw) -> pd.Series:
    return _consecutive(close < close.shift(1))


def _calc_bar_range_pct(high: pd.Series, low: pd.Series, close: pd.Series,
                        **_kw) -> pd.Series:
    return ((high - low) / close.replace(0, np.nan)) * 100


# ===================================================================
# BASELINE (81-90)
# ===================================================================

def _supertrend_core(high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = 10, multiplier: float = 3.0) -> dict:
    atr_val = _atr(high, low, close, period)
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    st = pd.Series(np.nan, index=close.index)
    direction = pd.Series(1, index=close.index, dtype=int)

    st.iloc[0] = lower_band.iloc[0] if not pd.isna(lower_band.iloc[0]) else close.iloc[0]

    for i in range(1, len(close)):
        if pd.isna(upper_band.iloc[i]):
            st.iloc[i] = st.iloc[i - 1]
            direction.iloc[i] = direction.iloc[i - 1]
            continue

        prev_st = st.iloc[i - 1]
        prev_dir = direction.iloc[i - 1]
        curr_lower = lower_band.iloc[i]
        curr_upper = upper_band.iloc[i]

        if prev_dir == 1:  # bullish
            if curr_lower < prev_st:
                curr_lower = prev_st
            if close.iloc[i] < curr_lower:
                st.iloc[i] = curr_upper
                direction.iloc[i] = -1
            else:
                st.iloc[i] = curr_lower
                direction.iloc[i] = 1
        else:  # bearish
            if curr_upper > prev_st:
                curr_upper = prev_st
            if close.iloc[i] > curr_upper:
                st.iloc[i] = curr_lower
                direction.iloc[i] = 1
            else:
                st.iloc[i] = curr_upper
                direction.iloc[i] = -1

    return {"line": st, "direction": direction.astype(float)}


def _calc_supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = 10, multiplier: float = 3.0, **_kw) -> pd.Series:
    return _supertrend_core(high, low, close, period, multiplier)["line"]


def _calc_supertrend_direction(high: pd.Series, low: pd.Series, close: pd.Series,
                               period: int = 10, multiplier: float = 3.0,
                               **_kw) -> pd.Series:
    return _supertrend_core(high, low, close, period, multiplier)["direction"]


def _calc_ichimoku_tenkan(high: pd.Series, low: pd.Series,
                          tenkan_period: int = 9, **_kw) -> pd.Series:
    return _ichimoku_line(high, low, tenkan_period)


def _calc_ichimoku_kijun(high: pd.Series, low: pd.Series,
                         kijun_period: int = 26, **_kw) -> pd.Series:
    return _ichimoku_line(high, low, kijun_period)


def _calc_ichimoku_span_a(high: pd.Series, low: pd.Series,
                          tenkan_period: int = 9, kijun_period: int = 26,
                          **_kw) -> pd.Series:
    tenkan = _ichimoku_line(high, low, tenkan_period)
    kijun = _ichimoku_line(high, low, kijun_period)
    return (tenkan + kijun) / 2


def _calc_ichimoku_span_b(high: pd.Series, low: pd.Series,
                          senkou_b_period: int = 52, **_kw) -> pd.Series:
    return _ichimoku_line(high, low, senkou_b_period)


def _calc_ichimoku_chikou(close: pd.Series, chikou_offset: int = 26,
                          **_kw) -> pd.Series:
    return close.shift(chikou_offset)


def _calc_adx_value(high: pd.Series, low: pd.Series, close: pd.Series,
                    period: int = 14, **_kw) -> pd.Series:
    return _adx(high, low, close, period)["adx"]


def _calc_plus_di(high: pd.Series, low: pd.Series, close: pd.Series,
                  period: int = 14, **_kw) -> pd.Series:
    return _adx(high, low, close, period)["plus_di"]


def _calc_minus_di(high: pd.Series, low: pd.Series, close: pd.Series,
                   period: int = 14, **_kw) -> pd.Series:
    return _adx(high, low, close, period)["minus_di"]


# ===================================================================
# RISK / POSITION FILTERS (91-100)
# ===================================================================

def _psar_core(high: pd.Series, low: pd.Series, close: pd.Series,
               af_start: float = 0.02, af_step: float = 0.02,
               af_max: float = 0.2) -> dict:
    n = len(close)
    psar = pd.Series(np.nan, index=close.index)
    direction = pd.Series(1, index=close.index, dtype=int)

    is_long = True
    af = af_start
    ep = high.iloc[0]
    psar.iloc[0] = low.iloc[0]

    for i in range(1, n):
        prev_psar = psar.iloc[i - 1]
        if pd.isna(prev_psar):
            prev_psar = close.iloc[i - 1]

        if is_long:
            psar_val = prev_psar + af * (ep - prev_psar)
            psar_val = min(psar_val, low.iloc[i - 1])
            if i >= 2:
                psar_val = min(psar_val, low.iloc[i - 2])

            if low.iloc[i] < psar_val:
                is_long = False
                psar_val = ep
                ep = low.iloc[i]
                af = af_start
            else:
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + af_step, af_max)
        else:
            psar_val = prev_psar + af * (ep - prev_psar)
            psar_val = max(psar_val, high.iloc[i - 1])
            if i >= 2:
                psar_val = max(psar_val, high.iloc[i - 2])

            if high.iloc[i] > psar_val:
                is_long = True
                psar_val = ep
                ep = high.iloc[i]
                af = af_start
            else:
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + af_step, af_max)

        psar.iloc[i] = psar_val
        direction.iloc[i] = 1 if is_long else -1

    return {"line": psar, "direction": direction.astype(float)}


def _calc_psar(high: pd.Series, low: pd.Series, close: pd.Series,
               af_start: float = 0.02, af_step: float = 0.02,
               af_max: float = 0.2, **_kw) -> pd.Series:
    return _psar_core(high, low, close, af_start, af_step, af_max)["line"]


def _calc_psar_direction(high: pd.Series, low: pd.Series, close: pd.Series,
                         af_start: float = 0.02, af_step: float = 0.02,
                         af_max: float = 0.2, **_kw) -> pd.Series:
    return _psar_core(high, low, close, af_start, af_step, af_max)["direction"]


def _calc_max_drawdown_n(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    def _max_dd(window):
        peak = np.maximum.accumulate(window)
        dd = (window - peak) / np.where(peak == 0, np.nan, peak)
        return np.nanmin(dd) * 100
    return close.rolling(period, min_periods=2).apply(_max_dd, raw=True)


def _calc_volatility_rank(close: pd.Series, short_period: int = 20,
                          long_period: int = 252, **_kw) -> pd.Series:
    short_vol = close.pct_change().rolling(short_period).std()
    rank = short_vol.rolling(long_period, min_periods=short_period).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=True
    )
    return rank * 100


def _calc_atr_stop(high: pd.Series, low: pd.Series, close: pd.Series,
                   period: int = 14, multiplier: float = 2.0, **_kw) -> pd.Series:
    atr_val = _atr(high, low, close, period)
    return close - multiplier * atr_val


def _calc_trailing_high(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return close.rolling(period, min_periods=1).max()


def _calc_trailing_low(close: pd.Series, period: int = 20, **_kw) -> pd.Series:
    return close.rolling(period, min_periods=1).min()


def _calc_volume_spike(volume: pd.Series, period: int = 20,
                       threshold: float = 2.0, **_kw) -> pd.Series:
    vol_sma = _sma(volume, period)
    return (volume > threshold * vol_sma).astype(float)


def _calc_price_above_ma(close: pd.Series, period: int = 200,
                         ma_type: str = "sma", **_kw) -> pd.Series:
    if ma_type == "ema":
        ma = _ema(close, period)
    else:
        ma = _sma(close, period)
    return (close > ma).astype(float)


def _calc_adx_filter(high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = 14, threshold: int = 25, **_kw) -> pd.Series:
    adx_val = _adx(high, low, close, period)["adx"]
    return (adx_val > threshold).astype(float)


# ===================================================================
# Dispatch table: indicator key -> calculation function
# ===================================================================

_CALC_DISPATCH: dict[str, callable] = {
    # Trend
    "sma": _calc_sma,
    "ema": _calc_ema,
    "wma": _calc_wma,
    "hma": _calc_hma,
    "dema": _calc_dema,
    "tema": _calc_tema,
    "vwma": _calc_vwma,
    "rma": _calc_rma,
    "alma": _calc_alma,
    "kama": _calc_kama,
    # Momentum
    "rsi": _calc_rsi,
    "stoch_k": _calc_stoch_k,
    "stoch_d": _calc_stoch_d,
    "stoch_rsi": _calc_stoch_rsi,
    "cci": _calc_cci,
    "williams_r": _calc_williams_r,
    "roc": _calc_roc,
    "momentum": _calc_momentum,
    "tsi": _calc_tsi,
    "ultimate_osc": _calc_ultimate_osc,
    # Oscillator
    "macd_line": _calc_macd_line,
    "macd_signal": _calc_macd_signal,
    "macd_histogram": _calc_macd_histogram,
    "ppo": _calc_ppo,
    "trix": _calc_trix,
    "ao": _calc_ao,
    "ac": _calc_ac,
    "fisher_transform": _calc_fisher_transform,
    "coppock": _calc_coppock,
    "detrended_price": _calc_detrended_price,
    # Volatility
    "bbands_upper": _calc_bbands_upper,
    "bbands_lower": _calc_bbands_lower,
    "bbands_middle": _calc_bbands_middle,
    "bbands_width": _calc_bbands_width,
    "bbands_pctb": _calc_bbands_pctb,
    "keltner_upper": _calc_keltner_upper,
    "keltner_lower": _calc_keltner_lower,
    "atr": _calc_atr,
    "natr": _calc_natr,
    "historical_vol": _calc_historical_vol,
    # Volume
    "obv": _calc_obv,
    "cmf": _calc_cmf,
    "mfi": _calc_mfi,
    "vwap": _calc_vwap,
    "ad_line": _calc_ad_line,
    "eom": _calc_eom,
    "volume_sma": _calc_volume_sma,
    "volume_ratio": _calc_volume_ratio,
    "pvt": _calc_pvt,
    "nvi": _calc_nvi,
    # Market Structure
    "donchian_upper": _calc_donchian_upper,
    "donchian_lower": _calc_donchian_lower,
    "rolling_high": _calc_rolling_high,
    "rolling_low": _calc_rolling_low,
    "higher_high": _calc_higher_high,
    "lower_low": _calc_lower_low,
    "breakout_up": _calc_breakout_up,
    "breakout_down": _calc_breakout_down,
    "pivot_high": _calc_pivot_high,
    "pivot_low": _calc_pivot_low,
    # Mean Reversion
    "zscore": _calc_zscore,
    "pct_from_sma": _calc_pct_from_sma,
    "pct_from_ema": _calc_pct_from_ema,
    "mean_rev_signal": _calc_mean_rev_signal,
    "rsi_divergence": _calc_rsi_divergence,
    "price_channel_position": _calc_price_channel_position,
    "bb_position": _calc_bb_position,
    "keltner_position": _calc_keltner_position,
    "stdev_channel_upper": _calc_stdev_channel_upper,
    "stdev_channel_lower": _calc_stdev_channel_lower,
    # Breadth
    "relative_strength": _calc_relative_strength,
    "return_over_n": _calc_return_over_n,
    "gap_pct": _calc_gap_pct,
    "true_range": _calc_true_range,
    "avg_true_range_pct": _calc_avg_true_range_pct,
    "up_down_ratio": _calc_up_down_ratio,
    "positive_bars_pct": _calc_positive_bars_pct,
    "consecutive_up": _calc_consecutive_up,
    "consecutive_down": _calc_consecutive_down,
    "bar_range_pct": _calc_bar_range_pct,
    # Baseline
    "supertrend": _calc_supertrend,
    "supertrend_direction": _calc_supertrend_direction,
    "ichimoku_tenkan": _calc_ichimoku_tenkan,
    "ichimoku_kijun": _calc_ichimoku_kijun,
    "ichimoku_span_a": _calc_ichimoku_span_a,
    "ichimoku_span_b": _calc_ichimoku_span_b,
    "ichimoku_chikou": _calc_ichimoku_chikou,
    "adx_value": _calc_adx_value,
    "plus_di": _calc_plus_di,
    "minus_di": _calc_minus_di,
    # Risk
    "psar": _calc_psar,
    "psar_direction": _calc_psar_direction,
    "max_drawdown_n": _calc_max_drawdown_n,
    "volatility_rank": _calc_volatility_rank,
    "atr_stop": _calc_atr_stop,
    "trailing_high": _calc_trailing_high,
    "trailing_low": _calc_trailing_low,
    "volume_spike": _calc_volume_spike,
    "price_above_ma": _calc_price_above_ma,
    "adx_filter": _calc_adx_filter,
}


# ===================================================================
# Argument extraction: map DataFrame columns + params to function kwargs
# ===================================================================

def _extract_args(indicator_key: str, df: pd.DataFrame, params: dict) -> dict:
    """Build the keyword arguments expected by a calc function from *df* and merged *params*."""
    meta = INDICATOR_CATALOG.get(indicator_key, {})
    required = meta.get("required_fields", [])
    merged = params  # already merged by caller

    kwargs: dict = {}
    for field in required:
        if field == "open" and "open" in df.columns:
            kwargs["open_"] = df["open"].astype(float)
        elif field in df.columns:
            kwargs[field] = df[field].astype(float)

    kwargs.update(merged)
    return kwargs


# ===================================================================
# Public API
# ===================================================================

def compute_indicator(
    df: pd.DataFrame,
    indicator_key: str,
    params: dict | None = None,
) -> pd.Series:
    """Compute *indicator_key* on *df* and return a pandas Series.

    Parameters
    ----------
    df : DataFrame with columns ``open, high, low, close, volume`` (all lowercase).
    indicator_key : One of the 100 keys from ``INDICATOR_CATALOG``.
    params : Optional dict of parameter overrides (merged over catalog defaults).

    Returns
    -------
    pd.Series -- the computed indicator values, or NaN-filled Series if the key
    is unknown.
    """
    if indicator_key not in _CALC_DISPATCH:
        return pd.Series(np.nan, index=df.index, dtype=float)

    merged = _merge_params(indicator_key, params)
    kwargs = _extract_args(indicator_key, df, merged)
    result = _CALC_DISPATCH[indicator_key](**kwargs)

    if isinstance(result, pd.Series):
        return result
    # Shouldn't happen, but fall back gracefully
    return pd.Series(np.nan, index=df.index, dtype=float)
