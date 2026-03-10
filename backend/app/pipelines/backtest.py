"""30+ parameterized trading strategies covering all major TradingView indicator categories."""

from __future__ import annotations

import numpy as np
import pandas as pd
from app.indicators.technical import ema, rsi, macd, atr, bollinger_bands, sma, obv, rolling_volatility


# ── Shared helpers ──────────────────────────────────────────────────────────

def _metrics(daily_returns, equity):
    dr = np.array(daily_returns, dtype=float)
    eq = np.array(equity[1:], dtype=float)
    cum_return = (equity[-1] / equity[0]) - 1 if equity[0] > 0 else 0.0
    active = dr[dr != 0]
    win_rate = float(np.mean(active > 0)) if len(active) > 0 else 0.5
    # Sharpe on ALL days (industry standard for strategy comparison)
    sharpe = float((dr.mean() / dr.std()) * np.sqrt(252)) if dr.std() > 1e-9 else 0.0
    peak = np.maximum.accumulate(eq) if len(eq) > 0 else np.array([100.0])
    dd = (eq - peak) / np.where(peak > 0, peak, 1.0)
    max_dd = float(abs(dd.min())) if len(dd) > 0 else 0.0
    vol = float(dr.std() * np.sqrt(252))
    calmar = round(cum_return / max_dd, 2) if max_dd > 1e-6 else 0.0
    # Count trades: each transition in position (0→long, long→short, short→0, etc.)
    positions = np.where(dr != 0, np.sign(dr), 0)
    trades = int(np.sum(np.diff(positions) != 0)) if len(positions) > 1 else 0
    return {
        "cumulativeReturn": round(cum_return, 4), "winRate": round(win_rate, 4),
        "sharpeRatio": round(sharpe, 2), "maxDrawdown": round(max_dd, 4),
        "volatility": round(vol, 4), "calmarRatio": calmar,
        "totalTrades": trades, "accuracy": round(win_rate, 4),
    }


def _curve(df, daily_returns):
    """Build equity curve aligned to the FULL date range of df.
    Warmup bars (before the strategy starts) are flat at 100.
    Every strategy produces exactly len(df) points.
    """
    dates = df["date"].astype(str).str[:10].tolist()
    n = len(dates)
    offset = n - len(daily_returns)

    # Build full equity array — flat at 100 during warmup, then compound
    equity = [100.0] * (offset + 1)  # warmup bars all at 100
    for r in daily_returns:
        equity.append(equity[-1] * (1 + r))

    # equity now has exactly n+1 values (index 0 = start, index n = last bar)
    return [{"date": dates[i], "value": round(equity[i + 1], 2)} for i in range(n)]


def _size(price, atr_val, risk=0.01):
    stop = 2 * atr_val / price if price > 0 else 0.02
    return min(1.0, risk / stop) if stop > 1e-6 else 0.5


def _run(df, signals, size_series=None):
    """Generic run loop from a signal series (1=long, -1=short, 0=flat)."""
    ret = df["close"].pct_change().fillna(0)
    daily = []
    for i in range(len(signals)):
        sig = int(signals.iloc[i]) if not pd.isna(signals.iloc[i]) else 0
        sz = float(size_series.iloc[i]) if size_series is not None and not pd.isna(size_series.iloc[i]) else 1.0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * sig * sz)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(daily, eq)
    m["equityCurve"] = _curve(df, daily)
    return m


def _hold_run(df, entry_signals, exit_long, exit_short):
    """Run loop that holds position until explicit exit."""
    ret = df["close"].pct_change().fillna(0)
    daily, pos = [], 0
    for i in range(len(entry_signals)):
        if entry_signals.iloc[i] == 1:
            pos = 1
        elif entry_signals.iloc[i] == -1:
            pos = -1
        if pos == 1 and exit_long.iloc[i]:
            pos = 0
        elif pos == -1 and exit_short.iloc[i]:
            pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(daily, eq)
    m["equityCurve"] = _curve(df, daily)
    return m


# ══════════════════════════════════════════════════
# TREND FOLLOWING (8 strategies)
# ══════════════════════════════════════════════════

def s_sma_crossover(df, params=None):
    p = params or {}
    f = sma(df["close"], int(p.get("fast_period", 50)))
    s = sma(df["close"], int(p.get("slow_period", 200)))
    sig = pd.Series(0, index=df["close"].index)
    sig[f > s] = 1
    sig[f < s] = -1
    return _run(df, sig)


def s_ema_crossover(df, params=None):
    p = params or {}
    f = ema(df["close"], int(p.get("fast_period", 12)))
    s = ema(df["close"], int(p.get("slow_period", 26)))
    sig = pd.Series(0, index=df["close"].index)
    sig[f > s] = 1
    sig[f < s] = -1
    return _run(df, sig)


def s_triple_ema(df, params=None):
    p = params or {}
    e1 = ema(df["close"], int(p.get("e1", 8)))
    e2 = ema(df["close"], int(p.get("e2", 21)))
    e3 = ema(df["close"], int(p.get("e3", 55)))
    sig = pd.Series(0, index=df["close"].index)
    sig[(e1 > e2) & (e2 > e3)] = 1
    sig[(e1 < e2) & (e2 < e3)] = -1
    return _run(df, sig)


def s_macd_trend(df, params=None):
    p = params or {}
    close = df["close"]
    m = macd(close, int(p.get("fast", 12)), int(p.get("slow", 26)), int(p.get("signal", 9)))
    hist = m["histogram"]
    trend = ema(close, int(p.get("trend_ema", 50)))
    cross_up = (hist > 0) & (hist.shift(1) <= 0)
    cross_dn = (hist < 0) & (hist.shift(1) >= 0)
    entry = pd.Series(0, index=close.index)
    entry[cross_up & (close > trend)] = 1
    entry[cross_dn & (close < trend)] = -1
    exit_l = hist < 0
    exit_s = hist > 0
    return _hold_run(df, entry, exit_l, exit_s)


def s_supertrend(df, params=None):
    p = params or {}
    period = int(p.get("period", 10))
    mult = float(p.get("multiplier", 3.0))
    high, low, close = df["high"], df["low"], df["close"]
    hl2 = (high + low) / 2
    atr_s = atr(high, low, close, period)
    upper = hl2 + mult * atr_s
    lower = hl2 - mult * atr_s
    direction = pd.Series(1, index=close.index)
    for i in range(1, len(close)):
        if pd.isna(upper.iloc[i]):
            continue
        if direction.iloc[i - 1] == -1 and close.iloc[i] > upper.iloc[i]:
            direction.iloc[i] = 1
        elif direction.iloc[i - 1] == 1 and close.iloc[i] < lower.iloc[i]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
    return _run(df, direction)


def s_ichimoku(df, params=None):
    p = params or {}
    tenkan = int(p.get("tenkan", 9))
    kijun = int(p.get("kijun", 26))
    senkou_b = int(p.get("senkou_b", 52))
    high, low, close = df["high"], df["low"], df["close"]
    tenkan_s = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
    kijun_s = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
    span_a = ((tenkan_s + kijun_s) / 2).shift(kijun)
    span_b_s = ((high.rolling(senkou_b).max() + low.rolling(senkou_b).min()) / 2).shift(kijun)
    cloud_top = pd.concat([span_a, span_b_s], axis=1).max(axis=1)
    cloud_bot = pd.concat([span_a, span_b_s], axis=1).min(axis=1)
    sig = pd.Series(0, index=close.index)
    sig[close > cloud_top] = 1
    sig[close < cloud_bot] = -1
    return _run(df, sig)


def s_parabolic_sar(df, params=None):
    p = params or {}
    af_start = float(p.get("af_start", 0.02))
    af_max = float(p.get("af_max", 0.2))
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    n = len(close)
    trend = np.zeros(n)
    sar = np.full(n, np.nan)
    sar[0] = low[0]
    ep = high[0]
    af = af_start
    bull = True
    for i in range(1, n):
        if bull:
            sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
            sar[i] = min(sar[i], low[i - 1], low[max(0, i - 2)])
            if low[i] < sar[i]:
                bull = False
                sar[i] = ep
                ep = low[i]
                af = af_start
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_start, af_max)
                trend[i] = 1
        else:
            sar[i] = sar[i - 1] - af * (sar[i - 1] - ep)
            sar[i] = max(sar[i], high[i - 1], high[max(0, i - 2)])
            if high[i] > sar[i]:
                bull = True
                sar[i] = ep
                ep = high[i]
                af = af_start
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_start, af_max)
                trend[i] = -1
    return _run(df, pd.Series(trend, index=df["close"].index))


def s_adx_trend(df, params=None):
    p = params or {}
    period = int(p.get("period", 14))
    threshold = float(p.get("threshold", 25))
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0
    atr14 = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr14.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr14.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = ema(dx, period)
    sig = pd.Series(0, index=close.index)
    sig[(adx > threshold) & (plus_di > minus_di)] = 1
    sig[(adx > threshold) & (minus_di > plus_di)] = -1
    return _run(df, sig)


# ══════════════════════════════════════════════════
# OSCILLATORS / MEAN REVERSION (5 strategies)
# ══════════════════════════════════════════════════

def s_rsi_mean_reversion(df, params=None):
    p = params or {}
    period = int(p.get("period", 14))
    oversold = float(p.get("oversold", 30))
    overbought = float(p.get("overbought", 70))
    exit_band = float(p.get("exit_band", 50))
    close, high, low = df["close"], df["high"], df["low"]
    rsi_s = rsi(close, period)
    atr14 = atr(high, low, close, 14)
    ret = close.pct_change()
    daily, pos, sz = [], 0, 0.5
    for i in range(1, len(df)):
        r = rsi_s.iloc[i - 1]
        at = atr14.iloc[i - 1]
        pv = close.iloc[i - 1]
        if pd.isna(r) or pd.isna(at):
            daily.append(0.0)
            continue
        if pos == 0:
            if r < oversold:
                pos = 1
                sz = _size(pv, at)
            elif r > overbought:
                pos = -1
                sz = _size(pv, at)
        elif pos == 1 and r > exit_band:
            pos = 0
        elif pos == -1 and r < exit_band:
            pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos * sz)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(daily, eq)
    m["equityCurve"] = _curve(df, daily)
    return m


def s_stochastic(df, params=None):
    p = params or {}
    k_period = int(p.get("k_period", 14))
    d_period = int(p.get("d_period", 3))
    oversold = float(p.get("oversold", 20))
    overbought = float(p.get("overbought", 80))
    high, low, close = df["high"], df["low"], df["close"]
    ll = low.rolling(k_period).min()
    hh = high.rolling(k_period).max()
    k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    d = sma(k, d_period)
    cross_up = (k > d) & (k.shift(1) <= d.shift(1)) & (k < oversold + 20)
    cross_dn = (k < d) & (k.shift(1) >= d.shift(1)) & (k > overbought - 20)
    entry = pd.Series(0, index=close.index)
    entry[cross_up] = 1
    entry[cross_dn] = -1
    exit_l = k > overbought
    exit_s = k < oversold
    return _hold_run(df, entry, exit_l, exit_s)


def s_cci(df, params=None):
    p = params or {}
    period = int(p.get("period", 20))
    ob = float(p.get("overbought", 100))
    os_ = float(p.get("oversold", -100))
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci_s = (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))
    entry = pd.Series(0, index=df["close"].index)
    entry[cci_s > ob] = 1
    entry[cci_s < os_] = -1
    exit_l = cci_s < 0
    exit_s = cci_s > 0
    return _hold_run(df, entry, exit_l, exit_s)


def s_williams_r(df, params=None):
    p = params or {}
    period = int(p.get("period", 14))
    high, low, close = df["high"], df["low"], df["close"]
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    wr = -100 * (hh - close) / (hh - ll).replace(0, np.nan)
    entry = pd.Series(0, index=close.index)
    entry[wr < -80] = 1
    entry[wr > -20] = -1
    exit_l = wr > -50
    exit_s = wr < -50
    return _hold_run(df, entry, exit_l, exit_s)


def s_mfi(df, params=None):
    p = params or {}
    period = int(p.get("period", 14))
    high, low, close, vol = df["high"], df["low"], df["close"], df["volume"].astype(float)
    tp = (high + low + close) / 3
    mf = tp * vol
    delta = tp.diff()
    pos_mf = mf.where(delta > 0, 0.0).rolling(period).sum()
    neg_mf = mf.where(delta < 0, 0.0).rolling(period).sum()
    mfi_s = 100 - 100 / (1 + pos_mf / neg_mf.replace(0, np.nan))
    entry = pd.Series(0, index=close.index)
    entry[mfi_s < 20] = 1
    entry[mfi_s > 80] = -1
    exit_l = mfi_s > 50
    exit_s = mfi_s < 50
    return _hold_run(df, entry, exit_l, exit_s)


# ══════════════════════════════════════════════════
# VOLATILITY BREAKOUT (5 strategies)
# ══════════════════════════════════════════════════

def s_bollinger_squeeze(df, params=None):
    p = params or {}
    period = int(p.get("period", 20))
    std_dev = float(p.get("std_dev", 2.0))
    close = df["close"]
    bb = bollinger_bands(close, period, std_dev)
    bw_rank = bb["bandwidth"].rolling(50).rank(pct=True)
    ret = close.pct_change()
    daily, pos = [], 0
    for i in range(1, len(df)):
        if any(pd.isna(x.iloc[i - 1]) for x in [bw_rank, bb["upper"], bb["lower"], bb["middle"]]):
            daily.append(0.0)
            continue
        pv = close.iloc[i - 1]
        sq = bw_rank.iloc[i - 1] < float(p.get("squeeze_pct", 20)) / 100
        if pos == 0 and sq:
            if pv > bb["upper"].iloc[i - 1]:
                pos = 1
            elif pv < bb["lower"].iloc[i - 1]:
                pos = -1
        elif pos == 1 and pv < bb["middle"].iloc[i - 1]:
            pos = 0
        elif pos == -1 and pv > bb["middle"].iloc[i - 1]:
            pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(daily, eq)
    m["equityCurve"] = _curve(df, daily)
    return m


def s_bollinger_mean_rev(df, params=None):
    p = params or {}
    bb = bollinger_bands(df["close"], int(p.get("period", 20)), float(p.get("std_dev", 2.0)))
    close = df["close"]
    entry = pd.Series(0, index=close.index)
    entry[close < bb["lower"]] = 1
    entry[close > bb["upper"]] = -1
    exit_l = close > bb["middle"]
    exit_s = close < bb["middle"]
    return _hold_run(df, entry, exit_l, exit_s)


def s_keltner_channel(df, params=None):
    p = params or {}
    ema_p = int(p.get("ema_period", 20))
    atr_m = float(p.get("atr_multiplier", 2.0))
    close, high, low = df["close"], df["high"], df["low"]
    mid = ema(close, ema_p)
    atr_k = atr(high, low, close, ema_p)
    upper = mid + atr_m * atr_k
    lower = mid - atr_m * atr_k
    entry = pd.Series(0, index=close.index)
    entry[close > upper] = 1
    entry[close < lower] = -1
    exit_l = close < mid
    exit_s = close > mid
    return _hold_run(df, entry, exit_l, exit_s)


def s_atr_channel(df, params=None):
    p = params or {}
    atr_p = int(p.get("atr_period", 10))
    roll_p = int(p.get("roll_period", 14))
    trail = float(p.get("trail_mult", 1.5))
    close, high, low = df["close"], df["high"], df["low"]
    atr14 = atr(high, low, close, atr_p)
    vol_20 = rolling_volatility(close, 20)
    rh = high.rolling(roll_p).max().shift(1)
    rl = low.rolling(roll_p).min().shift(1)
    ret = close.pct_change()
    daily, pos, stop = [], 0, 0.0
    for i in range(1, len(df)):
        if any(pd.isna(x.iloc[i - 1]) for x in [atr14, rh, rl, vol_20]):
            daily.append(0.0)
            continue
        pv, at, v = close.iloc[i - 1], atr14.iloc[i - 1], vol_20.iloc[i - 1]
        sz = min(1.0, 10.0 / v) if v > 0 else 0.5
        if pos == 0:
            if pv > rh.iloc[i - 1]:
                pos = 1
                stop = pv - trail * at
            elif pv < rl.iloc[i - 1]:
                pos = -1
                stop = pv + trail * at
        elif pos == 1:
            stop = max(stop, pv - trail * at)
            if pv < stop:
                pos = 0
        elif pos == -1:
            stop = min(stop, pv + trail * at)
            if pv > stop:
                pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos * sz)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(daily, eq)
    m["equityCurve"] = _curve(df, daily)
    return m


def s_donchian_channel(df, params=None):
    p = params or {}
    entry_p = int(p.get("entry_period", 20))
    exit_p = int(p.get("exit_period", 10))
    close, high, low = df["close"], df["high"], df["low"]
    entry_high = high.rolling(entry_p).max().shift(1)
    entry_low = low.rolling(entry_p).min().shift(1)
    exit_low = low.rolling(exit_p).min().shift(1)
    exit_high = high.rolling(exit_p).max().shift(1)
    entry = pd.Series(0, index=close.index)
    entry[close > entry_high] = 1
    entry[close < entry_low] = -1
    exit_l = pd.Series(False, index=close.index)
    exit_s = pd.Series(False, index=close.index)
    exit_l[close < exit_low] = True
    exit_s[close > exit_high] = True
    return _hold_run(df, entry, exit_l, exit_s)


# ══════════════════════════════════════════════════
# VOLUME-BASED (3 strategies)
# ══════════════════════════════════════════════════

def s_obv_trend(df, params=None):
    p = params or {}
    close, vol = df["close"], df["volume"].astype(float)
    obv_s = obv(close, vol)
    f = ema(obv_s, int(p.get("fast", 10)))
    s = ema(obv_s, int(p.get("slow", 30)))
    sig = pd.Series(0, index=close.index)
    sig[f > s] = 1
    sig[f < s] = -1
    return _run(df, sig)


def s_vwap_reversion(df, params=None):
    p = params or {}
    dev = float(p.get("std_devs", 1.5))
    close, vol = df["close"], df["volume"].astype(float)
    vwap = (close * vol).rolling(20).sum() / vol.rolling(20).sum()
    std = close.rolling(20).std()
    entry = pd.Series(0, index=close.index)
    entry[close < vwap - dev * std] = 1
    entry[close > vwap + dev * std] = -1
    exit_l = close > vwap
    exit_s = close < vwap
    return _hold_run(df, entry, exit_l, exit_s)


def s_volume_breakout(df, params=None):
    p = params or {}
    price_p = int(p.get("price_period", 20))
    vol_mult = float(p.get("vol_multiplier", 2.0))
    close, vol = df["close"], df["volume"].astype(float)
    price_high = close.rolling(price_p).max().shift(1)
    price_low = close.rolling(price_p).min().shift(1)
    vol_avg = sma(vol, 20)
    vol_surge = vol > vol_mult * vol_avg
    sig = pd.Series(0, index=close.index)
    sig[(close > price_high) & vol_surge] = 1
    sig[(close < price_low) & vol_surge] = -1
    return _run(df, sig)


# ══════════════════════════════════════════════════
# CONFLUENCE (2 strategies)
# ══════════════════════════════════════════════════

def s_rsi_macd_confluence(df, params=None):
    p = params or {}
    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"].astype(float)
    rsi14 = rsi(close, int(p.get("rsi_period", 14)))
    macd_d = macd(close)
    hist = macd_d["histogram"]
    atr14 = atr(high, low, close, 14)
    vol_avg = sma(vol, 20)
    obv_s = obv(close, vol)
    obv_ma = obv_s.rolling(10).mean()
    ret = close.pct_change()
    os_ = float(p.get("rsi_oversold", 45))
    ob = float(p.get("rsi_overbought", 55))
    vr = float(p.get("vol_ratio", 1.2))
    daily, pos = [], 0
    for i in range(2, len(df)):
        if any(pd.isna(x.iloc[i - 1]) for x in [rsi14, hist, atr14, vol_avg, obv_ma]):
            daily.append(0.0)
            continue
        r = rsi14.iloc[i - 1]
        h0, h1 = hist.iloc[i - 1], hist.iloc[i - 2]
        vol_r = float(vol.iloc[i - 1]) / float(vol_avg.iloc[i - 1]) if vol_avg.iloc[i - 1] > 0 else 0
        obv_up = obv_s.iloc[i - 1] > obv_ma.iloc[i - 1]
        pv, at = close.iloc[i - 1], atr14.iloc[i - 1]
        sz = _size(pv, at, 0.015)
        if pos == 0:
            if r < os_ and h1 < 0 and h0 > 0 and vol_r > vr and obv_up:
                pos = 1
            elif r > ob and h1 > 0 and h0 < 0 and vol_r > vr:
                pos = -1
        elif pos == 1 and r > 60:
            pos = 0
        elif pos == -1 and r < 40:
            pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos * sz)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(daily, eq)
    m["equityCurve"] = _curve(df, daily)
    return m


def s_triple_screen(df, params=None):
    p = params or {}
    close, vol = df["close"], df["volume"].astype(float)
    weekly_trend = ema(close, int(p.get("weekly_ema", 65)))
    force = (close.diff() * vol).ewm(span=int(p.get("force_ema", 2)), adjust=False).mean()
    long_cond = (close > weekly_trend) & (force < 0) & (force.shift(1) > 0)
    short_cond = (close < weekly_trend) & (force > 0) & (force.shift(1) < 0)
    entry = pd.Series(0, index=close.index)
    entry[long_cond] = 1
    entry[short_cond] = -1
    exit_l = close < weekly_trend
    exit_s = close > weekly_trend
    return _hold_run(df, entry, exit_l, exit_s)


# ══════════════════════════════════════════════════
# MOMENTUM (3 strategies)
# ══════════════════════════════════════════════════

def s_roc_momentum(df, params=None):
    p = params or {}
    period = int(p.get("period", 12))
    close = df["close"]
    roc = close.pct_change(period) * 100
    sig = pd.Series(0, index=close.index)
    sig[roc > float(p.get("threshold", 0.0))] = 1
    sig[roc < -float(p.get("threshold", 0.0))] = -1
    return _run(df, sig)


def s_tsi(df, params=None):
    p = params or {}
    r_p = int(p.get("r", 25))
    s_p = int(p.get("s", 13))
    close = df["close"]
    diff = close.diff()
    ds = ema(ema(diff, r_p), s_p)
    dsa = ema(ema(diff.abs(), r_p), s_p)
    tsi_s = 100 * ds / dsa.replace(0, np.nan)
    signal_line = ema(tsi_s, int(p.get("signal", 7)))
    cross_up = (tsi_s > signal_line) & (tsi_s.shift(1) <= signal_line.shift(1))
    cross_dn = (tsi_s < signal_line) & (tsi_s.shift(1) >= signal_line.shift(1))
    entry = pd.Series(0, index=close.index)
    entry[cross_up] = 1
    entry[cross_dn] = -1
    exit_l = tsi_s < signal_line
    exit_s = tsi_s > signal_line
    return _hold_run(df, entry, exit_l, exit_s)


def s_dpo(df, params=None):
    p = params or {}
    period = int(p.get("period", 20))
    close = df["close"]
    shift = period // 2 + 1
    sma_p = sma(close, period).shift(shift)
    dpo_s = close - sma_p
    sig = pd.Series(0, index=close.index)
    sig[dpo_s > 0] = 1
    sig[dpo_s < 0] = -1
    return _run(df, sig)


# ══════════════════════════════════════════════════
# BENCHMARK
# ══════════════════════════════════════════════════

def s_buy_hold(df, params=None):
    """Buy & hold benchmark — 100% invested every day from bar 0."""
    ret = df["close"].pct_change().fillna(0).tolist()
    eq = [100.0]
    for r in ret:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(np.array(ret), eq)
    m.update({
        "accuracy": 0.5,
        "equityCurve": _curve(df, ret),  # use shared _curve so length matches all others
    })
    return m


# ══════════════════════════════════════════════════
# STRATEGY REGISTRY
# ══════════════════════════════════════════════════

STRATEGY_REGISTRY: dict[str, dict] = {
    # TREND
    "sma_crossover":  {"fn": s_sma_crossover,  "category": "Trend",      "name": "SMA Golden Cross",        "params": {"fast_period": 50, "slow_period": 200}, "description": "Classic SMA golden/death cross. Long when fast SMA > slow SMA."},
    "ema_crossover":  {"fn": s_ema_crossover,  "category": "Trend",      "name": "EMA Crossover",           "params": {"fast_period": 12, "slow_period": 26},  "description": "EMA crossover. Trend direction from EMA12 vs EMA26."},
    "triple_ema":     {"fn": s_triple_ema,      "category": "Trend",      "name": "Triple EMA",              "params": {"e1": 8, "e2": 21, "e3": 55},           "description": "Long only when EMA8 > EMA21 > EMA55 (triple alignment)."},
    "macd_trend":     {"fn": s_macd_trend,      "category": "Trend",      "name": "MACD Trend",              "params": {"fast": 12, "slow": 26, "signal": 9, "trend_ema": 50}, "description": "MACD histogram zero-line crossover filtered by EMA50 trend."},
    "supertrend":     {"fn": s_supertrend,      "category": "Trend",      "name": "SuperTrend",              "params": {"period": 10, "multiplier": 3.0},        "description": "ATR-based dynamic support/resistance trend signal."},
    "ichimoku":       {"fn": s_ichimoku,        "category": "Trend",      "name": "Ichimoku Cloud",          "params": {"tenkan": 9, "kijun": 26, "senkou_b": 52}, "description": "Price vs Ichimoku Cloud determines trend."},
    "parabolic_sar":  {"fn": s_parabolic_sar,   "category": "Trend",      "name": "Parabolic SAR",           "params": {"af_start": 0.02, "af_max": 0.2},       "description": "Acceleration factor trailing stop. Reverses on SAR cross."},
    "adx_trend":      {"fn": s_adx_trend,       "category": "Trend",      "name": "ADX Trend Strength",      "params": {"period": 14, "threshold": 25},         "description": "Only trades when ADX > 25. +DI/-DI gives direction."},
    # OSCILLATOR
    "rsi_mean_rev":   {"fn": s_rsi_mean_reversion, "category": "Oscillator", "name": "RSI Mean Reversion",  "params": {"period": 14, "oversold": 30, "overbought": 70, "exit_band": 50}, "description": "Buy RSI<30, short RSI>70, exit at RSI 50."},
    "stochastic":     {"fn": s_stochastic,      "category": "Oscillator", "name": "Stochastic %K/%D",        "params": {"k_period": 14, "d_period": 3, "oversold": 20, "overbought": 80}, "description": "%K/%D crossover in extreme zones."},
    "cci":            {"fn": s_cci,             "category": "Oscillator", "name": "CCI",                     "params": {"period": 20, "overbought": 100, "oversold": -100}, "description": "Commodity Channel Index — mean deviation oscillator."},
    "williams_r":     {"fn": s_williams_r,      "category": "Oscillator", "name": "Williams %R",             "params": {"period": 14}, "description": "Fast overbought/oversold. Range -100 to 0."},
    "mfi":            {"fn": s_mfi,             "category": "Oscillator", "name": "Money Flow Index",        "params": {"period": 14}, "description": "Volume-weighted RSI."},
    # VOLATILITY
    "bollinger_squeeze": {"fn": s_bollinger_squeeze, "category": "Volatility", "name": "Bollinger Squeeze",  "params": {"period": 20, "std_dev": 2.0, "squeeze_pct": 20}, "description": "Breakout from low-volatility squeeze."},
    "bollinger_rev":  {"fn": s_bollinger_mean_rev, "category": "Volatility", "name": "Bollinger Mean Rev",   "params": {"period": 20, "std_dev": 2.0}, "description": "Buy lower band, short upper band, exit at middle."},
    "keltner":        {"fn": s_keltner_channel, "category": "Volatility", "name": "Keltner Channel",         "params": {"ema_period": 20, "atr_multiplier": 2.0}, "description": "ATR-based envelope around EMA. Breakout entry."},
    "atr_channel":    {"fn": s_atr_channel,     "category": "Volatility", "name": "ATR Volatility Channel",  "params": {"atr_period": 10, "roll_period": 14, "trail_mult": 1.5}, "description": "ATR channel breakout with trailing stop. Vol-adjusted sizing."},
    "donchian":       {"fn": s_donchian_channel, "category": "Volatility", "name": "Donchian Channel",       "params": {"entry_period": 20, "exit_period": 10}, "description": "Classic Turtle Trading breakout."},
    # VOLUME
    "obv_trend":      {"fn": s_obv_trend,       "category": "Volume",     "name": "OBV Trend",               "params": {"fast": 10, "slow": 30}, "description": "On-Balance Volume EMA crossover."},
    "vwap_reversion": {"fn": s_vwap_reversion,  "category": "Volume",     "name": "VWAP Reversion",          "params": {"std_devs": 1.5}, "description": "Mean revert to VWAP when price deviates."},
    "volume_breakout": {"fn": s_volume_breakout, "category": "Volume",    "name": "Volume Breakout",         "params": {"price_period": 20, "vol_multiplier": 2.0}, "description": "Price breakout confirmed by 2x volume surge."},
    # CONFLUENCE
    "rsi_macd_conf":  {"fn": s_rsi_macd_confluence, "category": "Confluence", "name": "RSI+MACD+Volume",     "params": {"rsi_period": 14, "rsi_oversold": 45, "rsi_overbought": 55, "vol_ratio": 1.2}, "description": "RSI + MACD cross + volume surge must all agree."},
    "triple_screen":  {"fn": s_triple_screen,   "category": "Confluence", "name": "Elder Triple Screen",     "params": {"weekly_ema": 65, "force_ema": 2}, "description": "Weekly trend + daily Force Index pullback entry."},
    # MOMENTUM
    "roc_momentum":   {"fn": s_roc_momentum,    "category": "Momentum",   "name": "Rate of Change",          "params": {"period": 12, "threshold": 0.0}, "description": "Buy positive ROC, short negative."},
    "tsi":            {"fn": s_tsi,             "category": "Momentum",   "name": "True Strength Index",     "params": {"r": 25, "s": 13, "signal": 7}, "description": "Double-smoothed momentum. Signal line crossover."},
    "dpo":            {"fn": s_dpo,             "category": "Momentum",   "name": "Detrended Price Osc",     "params": {"period": 20}, "description": "Removes trend to isolate cycles."},
    # BENCHMARK
    "buy_hold":       {"fn": s_buy_hold,        "category": "Benchmark",  "name": "Buy & Hold",              "params": {}, "description": "Passive benchmark — fully invested."},
}


def run_all_strategies(df: pd.DataFrame) -> list[dict]:
    """Run the 6 default strategies."""
    if len(df) < 80:
        return []
    defaults = ["rsi_mean_rev", "macd_trend", "bollinger_squeeze", "atr_channel", "rsi_macd_conf", "buy_hold"]
    results = []
    for key in defaults:
        entry = STRATEGY_REGISTRY.get(key)
        if not entry:
            continue
        try:
            r = entry["fn"](df, entry["params"].copy())
            r["modelName"] = entry["name"]
            r["description"] = entry["description"]
            r["strategyKey"] = key
            r["category"] = entry["category"]
            r["insufficientData"] = False
            results.append(r)
        except Exception as e:
            print(f"[backtest] '{key}' failed: {e}")
    results.sort(key=lambda x: x.get("sharpeRatio", 0), reverse=True)
    return results


def run_custom_strategy(df: pd.DataFrame, strategy_key: str, params: dict, custom_name: str = None) -> dict:
    """Run a single strategy with user-provided params."""
    entry = STRATEGY_REGISTRY.get(strategy_key)
    if not entry:
        return {"error": f"Unknown strategy: {strategy_key}"}
    if len(df) < 60:
        return {"error": "Need 60+ bars"}
    try:
        merged = {**entry["params"], **params}
        r = entry["fn"](df, merged)
        r["modelName"] = custom_name or entry["name"]
        r["description"] = entry["description"]
        r["strategyKey"] = strategy_key
        r["category"] = entry["category"]
        r["insufficientData"] = False
        r["params"] = merged
        return r
    except Exception as e:
        return {"error": str(e)}


def run_backtest(df, **_):
    results = run_all_strategies(df)
    return results[0] if results else {"accuracy": 0.5, "cumulativeReturn": 0.0, "winRate": 0.5,
        "sharpeRatio": 0.0, "maxDrawdown": 0.0, "volatility": 0.0, "calmarRatio": 0.0,
        "totalTrades": 0, "equityCurve": []}
