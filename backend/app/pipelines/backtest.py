"""27 rule-based trading strategies for Backtest Lab."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.indicators.technical import (
    ema, rsi, macd, atr, bollinger_bands, sma, obv,
    rolling_volatility, stochastic, cci, williams_r, mfi, adx
)


# ── Shared helpers ──────────────────────────────────────────────────────────

def _safe(v, default=0.0):
    try:
        f = float(v)
        return f if not (np.isnan(f) or np.isinf(f)) else default
    except:
        return default


def _metrics(daily_returns: list, eq: list) -> dict:
    dr = np.array(daily_returns)
    cum_return = (eq[-1] / eq[0]) - 1 if eq[0] > 0 else 0.0
    active = dr[dr != 0]
    win_rate = float(np.mean(active > 0)) if len(active) > 0 else 0.5
    sharpe = float((dr.mean() / dr.std()) * np.sqrt(252)) if dr.std() > 1e-10 else 0.0
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    max_dd = float(abs(dd.min())) if len(dd) > 0 else 0.0
    vol = float(dr.std() * np.sqrt(252))
    calmar = round(cum_return / max_dd, 2) if max_dd > 1e-6 else 0.0
    trades = int(np.sum(np.abs(np.diff([1 if r > 0 else -1 if r < 0 else 0 for r in daily_returns])) > 0)) if len(daily_returns) > 1 else 0
    return {
        "cumulativeReturn": round(cum_return, 4),
        "winRate": round(win_rate, 4),
        "sharpeRatio": round(sharpe, 2),
        "maxDrawdown": round(max_dd, 4),
        "volatility": round(vol, 4),
        "calmarRatio": calmar,
        "totalTrades": trades,
        "accuracy": round(win_rate, 4),
    }


def _curve(df: pd.DataFrame, daily_returns: list) -> list[dict]:
    dates = df["date"].astype(str).str[:10].tolist()
    equity = [100.0]
    for r in daily_returns:
        equity.append(equity[-1] * (1 + r))
    offset = max(0, len(dates) - len(daily_returns))
    result = []
    for i, v in enumerate(equity[1:]):
        idx = offset + i
        if idx < len(dates):
            result.append({"date": dates[idx], "value": round(v, 2)})
    return result


def _size(price: float, atr_val: float, risk: float = 0.01) -> float:
    if price <= 0 or atr_val <= 0:
        return 0.5
    stop = 2 * atr_val / price
    return min(1.0, risk / stop) if stop > 1e-6 else 0.5


def _run_loop(df, signal_fn) -> dict:
    """Generic bar-by-bar simulation. signal_fn(i) -> (position, size)"""
    close = df["close"].values
    ret = pd.Series(close).pct_change().fillna(0).values
    daily = []
    pos, sz = 0, 1.0
    for i in range(1, len(df)):
        try:
            new_pos, new_sz = signal_fn(i)
            pos, sz = new_pos, new_sz
        except:
            pass
        daily.append(_safe(ret[i]) * pos * sz)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(daily, eq)
    m["equityCurve"] = _curve(df, daily)
    return m


# ══════════════════════════════════════════════════
# TREND STRATEGIES
# ══════════════════════════════════════════════════

def s_sma_crossover(df: pd.DataFrame, params: dict = None) -> dict:
    """SMA Golden/Death Cross. Long when fast SMA > slow SMA."""
    p = params or {}
    fast = sma(df["close"], int(p.get("fast_period", 50))).values
    slow = sma(df["close"], int(p.get("slow_period", 200))).values
    pos = 0
    def signal(i):
        nonlocal pos
        if np.isnan(fast[i]) or np.isnan(slow[i]):
            return 0, 1.0
        pos = 1 if fast[i] > slow[i] else -1
        return pos, 1.0
    return _run_loop(df, signal)


def s_ema_crossover(df: pd.DataFrame, params: dict = None) -> dict:
    """EMA crossover — faster response than SMA."""
    p = params or {}
    fast = ema(df["close"], int(p.get("fast_period", 12))).values
    slow = ema(df["close"], int(p.get("slow_period", 26))).values
    pos = 0
    def signal(i):
        nonlocal pos
        pos = 1 if fast[i] > slow[i] else -1
        return pos, 1.0
    return _run_loop(df, signal)


def s_triple_ema(df: pd.DataFrame, params: dict = None) -> dict:
    """Triple EMA — all three must be stacked bullishly."""
    p = params or {}
    e1 = ema(df["close"], int(p.get("e1", 8))).values
    e2 = ema(df["close"], int(p.get("e2", 21))).values
    e3 = ema(df["close"], int(p.get("e3", 55))).values
    def signal(i):
        if e1[i] > e2[i] > e3[i]:
            return 1, 1.0
        elif e1[i] < e2[i] < e3[i]:
            return -1, 1.0
        return 0, 1.0
    return _run_loop(df, signal)


def s_macd_trend(df: pd.DataFrame, params: dict = None) -> dict:
    """MACD histogram crossover with EMA trend filter."""
    p = params or {}
    m = macd(df["close"], int(p.get("fast", 12)), int(p.get("slow", 26)), int(p.get("signal", 9)))
    hist = m["histogram"].values
    trend = ema(df["close"], int(p.get("trend_ema", 50))).values
    close = df["close"].values
    pos = 0
    def signal(i):
        nonlocal pos
        if np.isnan(hist[i]) or np.isnan(hist[i-1]):
            return pos, 1.0
        cross_up = hist[i-1] <= 0 and hist[i] > 0
        cross_dn = hist[i-1] >= 0 and hist[i] < 0
        if cross_up and close[i] > trend[i]:
            pos = 1
        elif cross_dn and close[i] < trend[i]:
            pos = -1
        elif (pos == 1 and hist[i] < 0) or (pos == -1 and hist[i] > 0):
            pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


def s_adx_trend(df: pd.DataFrame, params: dict = None) -> dict:
    """ADX — only trade when trend is strong (ADX > threshold)."""
    p = params or {}
    adx_d = adx(df["high"], df["low"], df["close"], int(p.get("period", 14)))
    adx_v = adx_d["adx"].values
    plus_di = adx_d["plus_di"].values
    minus_di = adx_d["minus_di"].values
    threshold = float(p.get("threshold", 25))
    def signal(i):
        if np.isnan(adx_v[i]):
            return 0, 1.0
        if adx_v[i] > threshold:
            return (1 if plus_di[i] > minus_di[i] else -1), 1.0
        return 0, 1.0
    return _run_loop(df, signal)


def s_supertrend(df: pd.DataFrame, params: dict = None) -> dict:
    """SuperTrend — ATR-based dynamic trailing support/resistance."""
    p = params or {}
    period = int(p.get("period", 10))
    multiplier = float(p.get("multiplier", 3.0))
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    atr_v = atr(df["high"], df["low"], df["close"], period).values
    upper_band = np.full(len(close), np.nan)
    lower_band = np.full(len(close), np.nan)
    direction = np.ones(len(close))
    for i in range(period, len(close)):
        hl2 = (high[i] + low[i]) / 2
        upper_band[i] = hl2 + multiplier * atr_v[i]
        lower_band[i] = hl2 - multiplier * atr_v[i]
        if not np.isnan(upper_band[i-1]):
            upper_band[i] = upper_band[i] if upper_band[i] < upper_band[i-1] or close[i-1] > upper_band[i-1] else upper_band[i-1]
            lower_band[i] = lower_band[i] if lower_band[i] > lower_band[i-1] or close[i-1] < lower_band[i-1] else lower_band[i-1]
        if direction[i-1] == -1 and close[i] > upper_band[i]:
            direction[i] = 1
        elif direction[i-1] == 1 and close[i] < lower_band[i]:
            direction[i] = -1
        else:
            direction[i] = direction[i-1]
    def signal(i):
        return int(direction[i]), 1.0
    return _run_loop(df, signal)


def s_ichimoku(df: pd.DataFrame, params: dict = None) -> dict:
    """Ichimoku Cloud — above cloud = bullish, below = bearish."""
    p = params or {}
    tenkan_p = int(p.get("tenkan", 9))
    kijun_p = int(p.get("kijun", 26))
    senkou_b_p = int(p.get("senkou_b", 52))
    h, l, c = df["high"], df["low"], df["close"]
    tenkan = ((h.rolling(tenkan_p).max() + l.rolling(tenkan_p).min()) / 2)
    kijun = ((h.rolling(kijun_p).max() + l.rolling(kijun_p).min()) / 2)
    span_a = ((tenkan + kijun) / 2).shift(kijun_p).values
    span_b = ((h.rolling(senkou_b_p).max() + l.rolling(senkou_b_p).min()) / 2).shift(kijun_p).values
    close = c.values
    def signal(i):
        if np.isnan(span_a[i]) or np.isnan(span_b[i]):
            return 0, 1.0
        cloud_top = max(span_a[i], span_b[i])
        cloud_bot = min(span_a[i], span_b[i])
        if close[i] > cloud_top:
            return 1, 1.0
        elif close[i] < cloud_bot:
            return -1, 1.0
        return 0, 1.0
    return _run_loop(df, signal)


def s_parabolic_sar(df: pd.DataFrame, params: dict = None) -> dict:
    """Parabolic SAR trailing stop reversal system."""
    p = params or {}
    af_start = float(p.get("af_start", 0.02))
    af_max = float(p.get("af_max", 0.2))
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    sar = np.full(len(close), np.nan)
    trend = np.zeros(len(close))
    af, ep, bull = af_start, high[0], True
    sar[0] = low[0]
    for i in range(1, len(close)):
        if bull:
            sar[i] = sar[i-1] + af * (ep - sar[i-1])
            sar[i] = min(sar[i], low[i-1], low[i-2] if i > 1 else low[i-1])
            if low[i] < sar[i]:
                bull, sar[i], ep, af = False, ep, low[i], af_start
            else:
                if high[i] > ep:
                    ep = high[i]; af = min(af + af_start, af_max)
                trend[i] = 1
        else:
            sar[i] = sar[i-1] - af * (sar[i-1] - ep)
            sar[i] = max(sar[i], high[i-1], high[i-2] if i > 1 else high[i-1])
            if high[i] > sar[i]:
                bull, sar[i], ep, af = True, ep, high[i], af_start
            else:
                if low[i] < ep:
                    ep = low[i]; af = min(af + af_start, af_max)
                trend[i] = -1
    def signal(i):
        return int(trend[i]), 1.0
    return _run_loop(df, signal)


# ══════════════════════════════════════════════════
# OSCILLATOR STRATEGIES
# ══════════════════════════════════════════════════

def s_rsi_mean_reversion(df: pd.DataFrame, params: dict = None) -> dict:
    """RSI Mean Reversion — buy oversold, short overbought."""
    p = params or {}
    rsi_v = rsi(df["close"], int(p.get("period", 14))).values
    atr_v = atr(df["high"], df["low"], df["close"], 14).values
    close = df["close"].values
    oversold = float(p.get("oversold", 30))
    overbought = float(p.get("overbought", 70))
    exit_band = float(p.get("exit_band", 50))
    pos, sz = 0, 0.5
    def signal(i):
        nonlocal pos, sz
        r = rsi_v[i-1]
        if np.isnan(r):
            return 0, 0.5
        if pos == 0:
            if r < oversold:
                pos = 1; sz = _size(close[i-1], atr_v[i-1])
            elif r > overbought:
                pos = -1; sz = _size(close[i-1], atr_v[i-1])
        elif pos == 1 and r > exit_band:
            pos = 0
        elif pos == -1 and r < exit_band:
            pos = 0
        return pos, sz
    return _run_loop(df, signal)


def s_stochastic(df: pd.DataFrame, params: dict = None) -> dict:
    """Stochastic %K/%D crossover in extreme zones."""
    p = params or {}
    st = stochastic(df["high"], df["low"], df["close"],
                    int(p.get("k_period", 14)), int(p.get("d_period", 3)))
    k, d = st["k"].values, st["d"].values
    oversold = float(p.get("oversold", 20))
    overbought = float(p.get("overbought", 80))
    pos = 0
    def signal(i):
        nonlocal pos
        if np.isnan(k[i]) or np.isnan(d[i]):
            return pos, 1.0
        cross_up = k[i] > d[i] and k[i-1] <= d[i-1]
        cross_dn = k[i] < d[i] and k[i-1] >= d[i-1]
        if pos == 0:
            if cross_up and k[i] < oversold + 20: pos = 1
            elif cross_dn and k[i] > overbought - 20: pos = -1
        elif pos == 1 and k[i] > overbought: pos = 0
        elif pos == -1 and k[i] < oversold: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


def s_cci_strategy(df: pd.DataFrame, params: dict = None) -> dict:
    """CCI — Commodity Channel Index overbought/oversold."""
    p = params or {}
    cci_v = cci(df["high"], df["low"], df["close"], int(p.get("period", 20))).values
    ob = float(p.get("overbought", 100))
    os_ = float(p.get("oversold", -100))
    pos = 0
    def signal(i):
        nonlocal pos
        v = cci_v[i]
        if np.isnan(v): return pos, 1.0
        if pos == 0:
            if v > ob: pos = 1
            elif v < os_: pos = -1
        elif pos == 1 and v < 0: pos = 0
        elif pos == -1 and v > 0: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


def s_williams_r_strategy(df: pd.DataFrame, params: dict = None) -> dict:
    """Williams %R — fast overbought/oversold reversal."""
    p = params or {}
    wr = williams_r(df["high"], df["low"], df["close"], int(p.get("period", 14))).values
    pos = 0
    def signal(i):
        nonlocal pos
        v = wr[i]
        if np.isnan(v): return pos, 1.0
        if pos == 0:
            if v < -80: pos = 1
            elif v > -20: pos = -1
        elif pos == 1 and v > -50: pos = 0
        elif pos == -1 and v < -50: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


def s_mfi_strategy(df: pd.DataFrame, params: dict = None) -> dict:
    """Money Flow Index — volume-weighted RSI."""
    p = params or {}
    mfi_v = mfi(df["high"], df["low"], df["close"], df["volume"].astype(float),
                int(p.get("period", 14))).values
    pos = 0
    def signal(i):
        nonlocal pos
        v = mfi_v[i]
        if np.isnan(v): return pos, 1.0
        if pos == 0:
            if v < 20: pos = 1
            elif v > 80: pos = -1
        elif pos == 1 and v > 50: pos = 0
        elif pos == -1 and v < 50: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


# ══════════════════════════════════════════════════
# VOLATILITY STRATEGIES
# ══════════════════════════════════════════════════

def s_bollinger_squeeze(df: pd.DataFrame, params: dict = None) -> dict:
    """Bollinger Band Squeeze Breakout."""
    p = params or {}
    bb = bollinger_bands(df["close"], int(p.get("period", 20)), float(p.get("std_dev", 2.0)))
    bw = bb["bandwidth"]
    bw_rank = bw.rolling(100, min_periods=20).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    upper = bb["upper"].values; lower = bb["lower"].values; middle = bb["middle"].values
    bw_rank_v = bw_rank.values; close = df["close"].values
    pos = 0
    squeeze_pct = float(p.get("squeeze_pct", 20)) / 100
    def signal(i):
        nonlocal pos
        if np.isnan(bw_rank_v[i]): return pos, 1.0
        sq = bw_rank_v[i] < squeeze_pct
        if pos == 0 and sq:
            if close[i] > upper[i]: pos = 1
            elif close[i] < lower[i]: pos = -1
        elif pos == 1 and close[i] < middle[i]: pos = 0
        elif pos == -1 and close[i] > middle[i]: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


def s_bollinger_mean_rev(df: pd.DataFrame, params: dict = None) -> dict:
    """Bollinger Bands Mean Reversion — buy lower, short upper."""
    p = params or {}
    bb = bollinger_bands(df["close"], int(p.get("period", 20)), float(p.get("std_dev", 2.0)))
    upper = bb["upper"].values; lower = bb["lower"].values; middle = bb["middle"].values
    close = df["close"].values
    pos = 0
    def signal(i):
        nonlocal pos
        if np.isnan(upper[i]): return pos, 1.0
        if pos == 0:
            if close[i] < lower[i]: pos = 1
            elif close[i] > upper[i]: pos = -1
        elif pos == 1 and close[i] > middle[i]: pos = 0
        elif pos == -1 and close[i] < middle[i]: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


def s_keltner_channel(df: pd.DataFrame, params: dict = None) -> dict:
    """Keltner Channel breakout — ATR envelope around EMA."""
    p = params or {}
    period = int(p.get("ema_period", 20))
    mult = float(p.get("atr_multiplier", 2.0))
    mid = ema(df["close"], period).values
    atr_v = atr(df["high"], df["low"], df["close"], period).values
    close = df["close"].values
    pos = 0
    def signal(i):
        nonlocal pos
        if np.isnan(mid[i]) or np.isnan(atr_v[i]): return pos, 1.0
        upper = mid[i] + mult * atr_v[i]
        lower = mid[i] - mult * atr_v[i]
        if pos == 0:
            if close[i] > upper: pos = 1
            elif close[i] < lower: pos = -1
        elif pos == 1 and close[i] < mid[i]: pos = 0
        elif pos == -1 and close[i] > mid[i]: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


def s_atr_channel(df: pd.DataFrame, params: dict = None) -> dict:
    """ATR Volatility Channel with trailing stop."""
    p = params or {}
    atr_v = atr(df["high"], df["low"], df["close"], int(p.get("atr_period", 10))).values
    vol_v = rolling_volatility(df["close"], 20).values
    roll_p = int(p.get("roll_period", 14))
    entry_m = float(p.get("entry_mult", 0.3))
    trail_m = float(p.get("trail_mult", 1.5))
    rh = df["high"].rolling(roll_p).max().values
    rl = df["low"].rolling(roll_p).min().values
    close = df["close"].values
    pos, stop = 0, 0.0
    def signal(i):
        nonlocal pos, stop
        if np.isnan(atr_v[i]) or np.isnan(rh[i]): return pos, 1.0
        pv, at = close[i], atr_v[i]
        sz = min(1.0, 10.0 / vol_v[i]) if not np.isnan(vol_v[i]) and vol_v[i] > 0 else 0.5
        if pos == 0:
            if pv > rh[i] + entry_m * at: pos = 1; stop = pv - trail_m * at
            elif pv < rl[i] - entry_m * at: pos = -1; stop = pv + trail_m * at
        elif pos == 1:
            stop = max(stop, pv - trail_m * at)
            if pv < stop: pos = 0
        elif pos == -1:
            stop = min(stop, pv + trail_m * at)
            if pv > stop: pos = 0
        return pos, sz
    return _run_loop(df, signal)


def s_donchian(df: pd.DataFrame, params: dict = None) -> dict:
    """Donchian Channel — classic Turtle Trading breakout."""
    p = params or {}
    entry_p = int(p.get("entry_period", 20))
    exit_p = int(p.get("exit_period", 10))
    close = df["close"].values
    entry_high = df["high"].rolling(entry_p).max().shift(1).values
    entry_low = df["low"].rolling(entry_p).min().shift(1).values
    exit_high = df["high"].rolling(exit_p).max().shift(1).values
    exit_low = df["low"].rolling(exit_p).min().shift(1).values
    pos = 0
    def signal(i):
        nonlocal pos
        if np.isnan(entry_high[i]): return pos, 1.0
        if pos == 0:
            if close[i] > entry_high[i]: pos = 1
            elif close[i] < entry_low[i]: pos = -1
        elif pos == 1 and close[i] < exit_low[i]: pos = 0
        elif pos == -1 and close[i] > exit_high[i]: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


# ══════════════════════════════════════════════════
# VOLUME STRATEGIES
# ══════════════════════════════════════════════════

def s_obv_trend(df: pd.DataFrame, params: dict = None) -> dict:
    """OBV Trend — On-Balance Volume EMA crossover."""
    p = params or {}
    obv_s = obv(df["close"], df["volume"].astype(float))
    fast = ema(obv_s, int(p.get("fast", 10))).values
    slow = ema(obv_s, int(p.get("slow", 30))).values
    def signal(i):
        return (1 if fast[i] > slow[i] else -1), 1.0
    return _run_loop(df, signal)


def s_vwap_reversion(df: pd.DataFrame, params: dict = None) -> dict:
    """VWAP Reversion — mean revert when price deviates from VWAP."""
    p = params or {}
    dev = float(p.get("std_devs", 1.5))
    close, vol = df["close"], df["volume"].astype(float)
    cum_vp = (close * vol).rolling(20).sum()
    cum_v = vol.rolling(20).sum()
    vwap = (cum_vp / cum_v.replace(0, np.nan)).values
    std = (close - pd.Series(vwap)).rolling(20).std().values
    close_v = close.values
    pos = 0
    def signal(i):
        nonlocal pos
        if np.isnan(vwap[i]) or np.isnan(std[i]): return pos, 1.0
        upper = vwap[i] + dev * std[i]
        lower = vwap[i] - dev * std[i]
        if pos == 0:
            if close_v[i] < lower: pos = 1
            elif close_v[i] > upper: pos = -1
        elif pos == 1 and close_v[i] > vwap[i]: pos = 0
        elif pos == -1 and close_v[i] < vwap[i]: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


def s_volume_breakout(df: pd.DataFrame, params: dict = None) -> dict:
    """Volume-confirmed price breakout."""
    p = params or {}
    price_p = int(p.get("price_period", 20))
    vol_mult = float(p.get("vol_multiplier", 2.0))
    close, vol = df["close"].values, df["volume"].astype(float)
    price_high = pd.Series(close).rolling(price_p).max().shift(1).values
    price_low = pd.Series(close).rolling(price_p).min().shift(1).values
    vol_avg = vol.rolling(20).mean().values
    pos = 0
    def signal(i):
        nonlocal pos
        if np.isnan(vol_avg[i]): return pos, 1.0
        vol_surge = float(vol.iloc[i]) > vol_mult * vol_avg[i]
        if pos == 0:
            if close[i] > price_high[i] and vol_surge: pos = 1
            elif close[i] < price_low[i] and vol_surge: pos = -1
        return pos, 1.0
    return _run_loop(df, signal)


# ══════════════════════════════════════════════════
# CONFLUENCE + MOMENTUM
# ══════════════════════════════════════════════════

def s_rsi_macd_confluence(df: pd.DataFrame, params: dict = None) -> dict:
    """RSI + MACD + Volume — all three must confirm."""
    p = params or {}
    rsi_v = rsi(df["close"], int(p.get("rsi_period", 14))).values
    macd_d = macd(df["close"])
    hist = macd_d["histogram"].values
    vol = df["volume"].astype(float)
    vol_avg = vol.rolling(20).mean().values
    obv_s = obv(df["close"], vol)
    obv_ma = obv_s.rolling(10).mean().values
    atr_v = atr(df["high"], df["low"], df["close"], 14).values
    close = df["close"].values
    oversold = float(p.get("rsi_oversold", 45))
    overbought = float(p.get("rsi_overbought", 55))
    vol_ratio = float(p.get("vol_ratio", 1.2))
    pos = 0
    def signal(i):
        nonlocal pos
        if i < 2 or np.isnan(rsi_v[i]) or np.isnan(hist[i]): return pos, 1.0
        r = rsi_v[i]; h0, h1 = hist[i], hist[i-1]
        vr = float(vol.iloc[i]) / vol_avg[i] if vol_avg[i] > 0 else 0
        obv_up = float(obv_s.iloc[i]) > float(obv_ma[i])
        sz = _size(close[i], atr_v[i], 0.015)
        if pos == 0:
            if r < oversold and h1 < 0 and h0 > 0 and vr > vol_ratio and obv_up: pos = 1
            elif r > overbought and h1 > 0 and h0 < 0 and vr > vol_ratio: pos = -1
        elif pos == 1 and r > 60: pos = 0
        elif pos == -1 and r < 40: pos = 0
        return pos, sz
    return _run_loop(df, signal)


def s_triple_screen(df: pd.DataFrame, params: dict = None) -> dict:
    """Elder Triple Screen — weekly trend + daily oscillator."""
    p = params or {}
    weekly = ema(df["close"], int(p.get("weekly_ema", 65))).values
    vol = df["volume"].astype(float)
    force_raw = (df["close"].diff() * vol).values
    force = pd.Series(force_raw).ewm(span=int(p.get("force_ema", 2)), adjust=False).mean().values
    close = df["close"].values
    pos = 0
    def signal(i):
        nonlocal pos
        if np.isnan(weekly[i]) or np.isnan(force[i]): return pos, 1.0
        long_cond = close[i] > weekly[i] and force[i] < 0 and force[i-1] > 0
        short_cond = close[i] < weekly[i] and force[i] > 0 and force[i-1] < 0
        if long_cond: pos = 1
        elif short_cond: pos = -1
        elif pos == 1 and close[i] < weekly[i]: pos = 0
        elif pos == -1 and close[i] > weekly[i]: pos = 0
        return pos, 1.0
    return _run_loop(df, signal)


def s_roc_momentum(df: pd.DataFrame, params: dict = None) -> dict:
    """Rate of Change — buy positive momentum."""
    p = params or {}
    period = int(p.get("period", 12))
    roc = df["close"].pct_change(period).values * 100
    threshold = float(p.get("threshold", 0.0))
    def signal(i):
        if np.isnan(roc[i]): return 0, 1.0
        return (1 if roc[i] > threshold else -1 if roc[i] < -threshold else 0), 1.0
    return _run_loop(df, signal)


def s_buy_hold(df: pd.DataFrame, params: dict = None) -> dict:
    """Buy & Hold — passive benchmark."""
    ret = df["close"].pct_change().fillna(0).values
    eq = [100.0]
    for r in ret:
        eq.append(eq[-1] * (1 + _safe(r)))
    m = _metrics(list(ret), eq)
    m["equityCurve"] = [{"date": str(df["date"].iloc[i])[:10], "value": round(v, 2)} for i, v in enumerate(eq[1:])]
    return m


# ══════════════════════════════════════════════════
# STRATEGY REGISTRY
# ══════════════════════════════════════════════════

STRATEGY_REGISTRY: dict[str, dict] = {
    "sma_crossover":    {"fn": s_sma_crossover,       "category": "Trend",      "name": "SMA Golden Cross",          "params": {"fast_period": 50, "slow_period": 200},                       "description": "Long when SMA(fast) > SMA(slow). Classic 50/200 golden cross system."},
    "ema_crossover":    {"fn": s_ema_crossover,        "category": "Trend",      "name": "EMA Crossover",             "params": {"fast_period": 12, "slow_period": 26},                        "description": "EMA crossover — faster response than SMA. Default EMA12 vs EMA26."},
    "triple_ema":       {"fn": s_triple_ema,           "category": "Trend",      "name": "Triple EMA",                "params": {"e1": 8, "e2": 21, "e3": 55},                                 "description": "All 3 EMAs must be stacked: EMA8 > EMA21 > EMA55 for long."},
    "macd_trend":       {"fn": s_macd_trend,           "category": "Trend",      "name": "MACD Trend",                "params": {"fast": 12, "slow": 26, "signal": 9, "trend_ema": 50},        "description": "MACD histogram zero-line cross filtered by EMA50 trend direction."},
    "adx_trend":        {"fn": s_adx_trend,            "category": "Trend",      "name": "ADX Trend Strength",        "params": {"period": 14, "threshold": 25},                               "description": "Only trades when ADX > 25 (strong trend). +DI/-DI gives direction."},
    "supertrend":       {"fn": s_supertrend,           "category": "Trend",      "name": "SuperTrend",                "params": {"period": 10, "multiplier": 3.0},                             "description": "ATR-based dynamic support/resistance. Popular TradingView indicator."},
    "ichimoku":         {"fn": s_ichimoku,             "category": "Trend",      "name": "Ichimoku Cloud",            "params": {"tenkan": 9, "kijun": 26, "senkou_b": 52},                    "description": "Price above/below Ichimoku Cloud determines bias."},
    "parabolic_sar":    {"fn": s_parabolic_sar,        "category": "Trend",      "name": "Parabolic SAR",             "params": {"af_start": 0.02, "af_max": 0.2},                             "description": "SAR reversal system. Flips long/short when price crosses SAR."},
    "rsi_mean_rev":     {"fn": s_rsi_mean_reversion,   "category": "Oscillator", "name": "RSI Mean Reversion",        "params": {"period": 14, "oversold": 30, "overbought": 70, "exit_band": 50}, "description": "Buy RSI<30, short RSI>70, exit at RSI 50."},
    "stochastic":       {"fn": s_stochastic,           "category": "Oscillator", "name": "Stochastic %K/%D",          "params": {"k_period": 14, "d_period": 3, "oversold": 20, "overbought": 80}, "description": "%K/%D crossover in oversold/overbought zones."},
    "cci":              {"fn": s_cci_strategy,         "category": "Oscillator", "name": "CCI",                       "params": {"period": 20, "overbought": 100, "oversold": -100},           "description": "Commodity Channel Index — mean deviation from typical price."},
    "williams_r":       {"fn": s_williams_r_strategy,  "category": "Oscillator", "name": "Williams %R",               "params": {"period": 14},                                                "description": "Fast reversal oscillator. Oversold < -80, overbought > -20."},
    "mfi":              {"fn": s_mfi_strategy,         "category": "Oscillator", "name": "Money Flow Index",          "params": {"period": 14},                                                "description": "Volume-weighted RSI. MFI < 20 = oversold, > 80 = overbought."},
    "bollinger_squeeze":{"fn": s_bollinger_squeeze,    "category": "Volatility", "name": "Bollinger Squeeze",         "params": {"period": 20, "std_dev": 2.0, "squeeze_pct": 20},             "description": "Trades breakout from bandwidth compression below 20th percentile."},
    "bollinger_rev":    {"fn": s_bollinger_mean_rev,   "category": "Volatility", "name": "Bollinger Mean Rev",        "params": {"period": 20, "std_dev": 2.0},                                "description": "Buy at lower band, short upper band, exit at middle SMA."},
    "keltner":          {"fn": s_keltner_channel,      "category": "Volatility", "name": "Keltner Channel",           "params": {"ema_period": 20, "atr_multiplier": 2.0},                     "description": "ATR-based envelope. Breakout above/below triggers entry."},
    "atr_channel":      {"fn": s_atr_channel,          "category": "Volatility", "name": "ATR Volatility Channel",    "params": {"atr_period": 10, "roll_period": 14, "entry_mult": 0.3, "trail_mult": 1.5}, "description": "ATR channel breakout with 1.5-ATR trailing stop."},
    "donchian":         {"fn": s_donchian,             "category": "Volatility", "name": "Donchian Channel",          "params": {"entry_period": 20, "exit_period": 10},                       "description": "Classic Turtle Trading. 20-day high/low entry, 10-day exit."},
    "obv_trend":        {"fn": s_obv_trend,            "category": "Volume",     "name": "OBV Trend",                 "params": {"fast": 10, "slow": 30},                                      "description": "On-Balance Volume EMA crossover. Volume leads price."},
    "vwap_reversion":   {"fn": s_vwap_reversion,       "category": "Volume",     "name": "VWAP Reversion",            "params": {"std_devs": 1.5},                                             "description": "Mean revert to VWAP when price deviates 1.5+ standard deviations."},
    "volume_breakout":  {"fn": s_volume_breakout,      "category": "Volume",     "name": "Volume Breakout",           "params": {"price_period": 20, "vol_multiplier": 2.0},                   "description": "Price breakout confirmed by 2x average volume surge."},
    "rsi_macd_conf":    {"fn": s_rsi_macd_confluence,  "category": "Confluence", "name": "RSI+MACD+Volume",           "params": {"rsi_period": 14, "rsi_oversold": 45, "rsi_overbought": 55, "vol_ratio": 1.2}, "description": "All three agree: RSI extreme + MACD cross + volume surge + OBV."},
    "triple_screen":    {"fn": s_triple_screen,        "category": "Confluence", "name": "Elder Triple Screen",       "params": {"weekly_ema": 65, "force_ema": 2},                            "description": "Elder's system: weekly EMA trend + daily Force Index pullback."},
    "roc_momentum":     {"fn": s_roc_momentum,         "category": "Momentum",   "name": "Rate of Change",            "params": {"period": 12, "threshold": 0.0},                              "description": "Buy positive ROC, short negative. Simple price change over N bars."},
    "buy_hold":         {"fn": s_buy_hold,             "category": "Benchmark",  "name": "Buy & Hold",                "params": {},                                                            "description": "Passive benchmark — 100% invested, no signals."},
}

DEFAULT_STRATEGY_KEYS = [
    "rsi_mean_rev", "macd_trend", "bollinger_squeeze",
    "atr_channel", "rsi_macd_conf", "buy_hold"
]

STRATEGY_MIN_BARS = {
    "sma_crossover": 220, "ema_crossover": 60, "triple_ema": 80,
    "macd_trend": 80, "adx_trend": 60, "supertrend": 40, "ichimoku": 80,
    "parabolic_sar": 20, "rsi_mean_rev": 60, "stochastic": 40,
    "cci": 40, "williams_r": 30, "mfi": 30, "bollinger_squeeze": 80,
    "bollinger_rev": 40, "keltner": 40, "atr_channel": 40,
    "donchian": 40, "obv_trend": 40, "vwap_reversion": 40,
    "volume_breakout": 40, "rsi_macd_conf": 60, "triple_screen": 80,
    "roc_momentum": 20, "buy_hold": 2,
}


def run_all_strategies(df: pd.DataFrame, keys: list[str] | None = None) -> list[dict]:
    if len(df) < 40:
        return []
    target_keys = keys or DEFAULT_STRATEGY_KEYS
    results = []
    for key in target_keys:
        entry = STRATEGY_REGISTRY.get(key)
        if not entry:
            continue
        min_bars = STRATEGY_MIN_BARS.get(key, 60)
        if len(df) < min_bars:
            results.append({
                "modelName": entry["name"], "description": entry["description"],
                "strategyKey": key, "category": entry["category"],
                "cumulativeReturn": 0.0, "winRate": 0.5, "sharpeRatio": 0.0,
                "maxDrawdown": 0.0, "volatility": 0.0, "calmarRatio": 0.0,
                "totalTrades": 0, "accuracy": 0.5, "equityCurve": [],
                "insufficientData": True,
            })
            continue
        try:
            r = entry["fn"](df, entry["params"].copy())
            r.update({"modelName": entry["name"], "description": entry["description"],
                      "strategyKey": key, "category": entry["category"], "insufficientData": False})
            results.append(r)
        except Exception as e:
            print(f"[backtest] '{key}' failed: {e}")
    results.sort(key=lambda x: x.get("sharpeRatio", 0), reverse=True)
    return results


def run_custom_strategy(df: pd.DataFrame, strategy_key: str, params: dict, custom_name: str = None) -> dict:
    entry = STRATEGY_REGISTRY.get(strategy_key)
    if not entry:
        return {"error": f"Unknown strategy: {strategy_key}"}
    if len(df) < STRATEGY_MIN_BARS.get(strategy_key, 40):
        return {"error": f"Need {STRATEGY_MIN_BARS.get(strategy_key, 40)}+ bars for this strategy"}
    try:
        merged = {**entry["params"], **params}
        r = entry["fn"](df, merged)
        r.update({"modelName": custom_name or entry["name"], "description": entry["description"],
                  "strategyKey": strategy_key, "category": entry["category"],
                  "insufficientData": False, "params": merged})
        return r
    except Exception as e:
        return {"error": str(e)}


def run_backtest(df, **_):
    results = run_all_strategies(df)
    return results[0] if results else {"error": "Insufficient data"}
