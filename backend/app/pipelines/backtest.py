"""5 rule-based trading strategies using RSI, MACD, Bollinger, ATR, Volume."""

from __future__ import annotations

import numpy as np
import pandas as pd
from app.indicators.technical import ema, rsi, macd, atr, bollinger_bands, rolling_volatility, sma, obv


def _metrics(daily_returns: np.ndarray, equity: list) -> dict:
    dr = np.array(daily_returns, dtype=float)
    eq = np.array(equity[1:], dtype=float)
    cum_return = (equity[-1] / equity[0]) - 1 if equity[0] > 0 else 0.0
    win_rate = float(np.mean(dr[dr != 0] > 0)) if np.any(dr != 0) else 0.5
    sharpe = float((dr.mean() / dr.std()) * np.sqrt(252)) if dr.std() > 1e-9 else 0.0
    peak = np.maximum.accumulate(eq) if len(eq) > 0 else np.array([100.0])
    dd = (eq - peak) / np.where(peak > 0, peak, 1.0)
    max_dd = float(abs(dd.min())) if len(dd) > 0 else 0.0
    vol = float(dr.std() * np.sqrt(252))
    calmar = round(cum_return / max_dd, 2) if max_dd > 1e-6 else 0.0
    trades = int(np.sum(np.abs(np.diff(np.where(dr != 0, 1, 0))))) if len(dr) > 1 else 0
    return {
        "cumulativeReturn": round(cum_return, 4),
        "winRate": round(win_rate, 4),
        "sharpeRatio": round(sharpe, 2),
        "maxDrawdown": round(max_dd, 4),
        "volatility": round(vol, 4),
        "calmarRatio": calmar,
        "totalTrades": trades,
    }


def _curve(df: pd.DataFrame, daily_returns: list) -> list[dict]:
    dates = df["date"].astype(str).str[:10].tolist()
    equity = [100.0]
    for r in daily_returns:
        equity.append(equity[-1] * (1 + r))
    offset = len(dates) - len(daily_returns)
    return [{"date": dates[offset + i], "value": round(v, 2)}
            for i, v in enumerate(equity[1:])]


def _size(price: float, atr_val: float, risk: float = 0.01) -> float:
    stop = 2 * atr_val / price if price > 0 else 0.02
    return min(1.0, risk / stop) if stop > 1e-6 else 0.5


# ── Strategy 1: RSI Mean Reversion ──────────────────────────────────────────

def strategy_rsi_mean_reversion(df: pd.DataFrame) -> dict:
    close, high, low = df["close"], df["high"], df["low"]
    rsi_14 = rsi(close, 14)
    atr_14 = atr(high, low, close, 14)
    ret = close.pct_change()
    daily, pos, sz = [], 0, 0.5
    for i in range(1, len(df)):
        r, at, p = rsi_14.iloc[i - 1], atr_14.iloc[i - 1], close.iloc[i - 1]
        if pd.isna(r) or pd.isna(at):
            daily.append(0.0)
            continue
        if pos == 0:
            if r < 30:
                pos = 1
                sz = _size(p, at)
            elif r > 70:
                pos = -1
                sz = _size(p, at)
        elif pos == 1 and r > 55:
            pos = 0
        elif pos == -1 and r < 45:
            pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos * sz)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(np.array(daily), eq)
    m.update({"accuracy": m["winRate"], "equityCurve": _curve(df, daily)})
    return m


# ── Strategy 2: MACD Trend Following ────────────────────────────────────────

def strategy_macd_trend(df: pd.DataFrame) -> dict:
    close = df["close"]
    m = macd(close, 12, 26, 9)
    hist = m["histogram"]
    e50 = ema(close, 50)
    ret = close.pct_change()
    daily, pos = [], 0
    for i in range(2, len(df)):
        if pd.isna(hist.iloc[i - 1]) or pd.isna(e50.iloc[i - 1]):
            daily.append(0.0)
            continue
        h0, h1 = hist.iloc[i - 1], hist.iloc[i - 2]
        trend_up = close.iloc[i - 1] > e50.iloc[i - 1]
        if pos == 0:
            if h1 < 0 and h0 > 0 and trend_up:
                pos = 1
            elif h1 > 0 and h0 < 0 and not trend_up:
                pos = -1
        elif pos == 1 and h0 < 0:
            pos = 0
        elif pos == -1 and h0 > 0:
            pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    metrics = _metrics(np.array(daily), eq)
    metrics.update({"accuracy": metrics["winRate"], "equityCurve": _curve(df, daily)})
    return metrics


# ── Strategy 3: Bollinger Band Squeeze Breakout ──────────────────────────────

def strategy_bollinger_squeeze(df: pd.DataFrame) -> dict:
    close = df["close"]
    bb = bollinger_bands(close, 20, 2.0)
    bw_rank = bb["bandwidth"].rolling(50).rank(pct=True)
    ret = close.pct_change()
    daily, pos = [], 0
    for i in range(1, len(df)):
        if any(pd.isna(x.iloc[i - 1]) for x in [bw_rank, bb["upper"], bb["lower"], bb["middle"]]):
            daily.append(0.0)
            continue
        p = close.iloc[i - 1]
        squeeze = bw_rank.iloc[i - 1] < 0.20
        if pos == 0 and squeeze:
            if p > bb["upper"].iloc[i - 1]:
                pos = 1
            elif p < bb["lower"].iloc[i - 1]:
                pos = -1
        elif pos == 1 and p < bb["middle"].iloc[i - 1]:
            pos = 0
        elif pos == -1 and p > bb["middle"].iloc[i - 1]:
            pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    metrics = _metrics(np.array(daily), eq)
    metrics.update({"accuracy": metrics["winRate"], "equityCurve": _curve(df, daily)})
    return metrics


# ── Strategy 4: ATR Volatility Channel ──────────────────────────────────────

def strategy_atr_channel(df: pd.DataFrame) -> dict:
    close, high, low = df["close"], df["high"], df["low"]
    atr_14 = atr(high, low, close, 14)
    vol_20 = rolling_volatility(close, 20)
    rh = high.rolling(20).max()
    rl = low.rolling(20).min()
    ret = close.pct_change()
    daily, pos, stop = [], 0, 0.0
    for i in range(1, len(df)):
        if any(pd.isna(x.iloc[i - 1]) for x in [atr_14, rh, rl, vol_20]):
            daily.append(0.0)
            continue
        p, at, v = close.iloc[i - 1], atr_14.iloc[i - 1], vol_20.iloc[i - 1]
        sz = min(1.0, 10.0 / v) if v > 0 else 0.5
        if pos == 0:
            if p > rh.iloc[i - 1] + 0.5 * at:
                pos = 1
                stop = p - 2 * at
            elif p < rl.iloc[i - 1] - 0.5 * at:
                pos = -1
                stop = p + 2 * at
        elif pos == 1:
            stop = max(stop, p - 2 * at)
            if p < stop:
                pos = 0
        elif pos == -1:
            stop = min(stop, p + 2 * at)
            if p > stop:
                pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos * sz)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    metrics = _metrics(np.array(daily), eq)
    metrics.update({"accuracy": metrics["winRate"], "equityCurve": _curve(df, daily)})
    return metrics


# ── Strategy 5: RSI + MACD + Volume Confluence ───────────────────────────────

def strategy_confluence(df: pd.DataFrame) -> dict:
    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]
    rsi_14 = rsi(close, 14)
    macd_data = macd(close)
    hist = macd_data["histogram"]
    atr_14 = atr(high, low, close, 14)
    vol_avg = sma(volume.astype(float), 20)
    obv_s = obv(close, volume.astype(float))
    obv_ma = obv_s.rolling(10).mean()
    ret = close.pct_change()
    daily, pos = [], 0
    for i in range(2, len(df)):
        if any(pd.isna(x.iloc[i - 1]) for x in [rsi_14, hist, atr_14, vol_avg, obv_ma]):
            daily.append(0.0)
            continue
        r = rsi_14.iloc[i - 1]
        h0, h1 = hist.iloc[i - 1], hist.iloc[i - 2]
        vol_ratio = float(volume.iloc[i - 1]) / float(vol_avg.iloc[i - 1]) if vol_avg.iloc[i - 1] > 0 else 0
        obv_rising = obv_s.iloc[i - 1] > obv_ma.iloc[i - 1]
        p, at = close.iloc[i - 1], atr_14.iloc[i - 1]
        sz = _size(p, at, 0.015)
        if pos == 0:
            if r < 42 and h1 < 0 and h0 > 0 and vol_ratio > 1.5 and obv_rising:
                pos = 1
            elif r > 58 and h1 > 0 and h0 < 0 and vol_ratio > 1.5 and not obv_rising:
                pos = -1
        elif pos == 1 and r > 65:
            pos = 0
        elif pos == -1 and r < 35:
            pos = 0
        dr = float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        daily.append(dr * pos * sz)
    eq = [100.0]
    for r in daily:
        eq.append(eq[-1] * (1 + r))
    metrics = _metrics(np.array(daily), eq)
    metrics.update({"accuracy": metrics["winRate"], "equityCurve": _curve(df, daily)})
    return metrics


# ── Buy & Hold benchmark ─────────────────────────────────────────────────────

def strategy_buy_hold(df: pd.DataFrame) -> dict:
    ret = df["close"].pct_change().fillna(0).values
    eq = [100.0]
    for r in ret:
        eq.append(eq[-1] * (1 + r))
    m = _metrics(np.array(ret), eq)
    m.update({
        "accuracy": 0.5,
        "equityCurve": [
            {"date": str(df["date"].iloc[i])[:10], "value": round(eq[i + 1], 2)}
            for i in range(len(ret))
        ],
    })
    return m


# ── Registry ─────────────────────────────────────────────────────────────────

STRATEGIES: list[tuple[str, callable, str]] = [
    ("RSI Mean Reversion", strategy_rsi_mean_reversion,
     "Enters long when RSI(14) drops below 30 (oversold) and short above 70 (overbought). Exits when RSI crosses back through 50. Uses ATR-based 1% capital risk sizing per trade."),
    ("MACD Trend Following", strategy_macd_trend,
     "Enters on MACD histogram zero-line crossover in the direction of the EMA(50) trend. Bullish cross above zero = long; bearish cross below = short. Exits on reverse crossover."),
    ("Bollinger Band Squeeze", strategy_bollinger_squeeze,
     "Waits for Bollinger bandwidth to compress into the bottom 20th percentile (low volatility squeeze). Enters long on breakout above upper band, short below lower band. Exits at the middle band."),
    ("ATR Volatility Channel", strategy_atr_channel,
     "Uses Wilder ATR formula to define dynamic channels. Enters on 20-day high/low breakout + 0.5 ATR extension. Trailing 2-ATR stop loss. Position sized to target 10% annual volatility contribution."),
    ("RSI + MACD + Volume Confluence", strategy_confluence,
     "Only trades when RSI, MACD histogram crossover, AND a 1.5x volume surge all agree simultaneously. OBV trend provides final confirmation. High selectivity means fewer but higher-quality trades."),
    ("Buy & Hold", strategy_buy_hold,
     "Passive benchmark. 100% invested throughout the period with no signals or rebalancing."),
]


def run_all_strategies(df: pd.DataFrame) -> list[dict]:
    if len(df) < 100:
        return []
    results = []
    for name, fn, desc in STRATEGIES:
        try:
            r = fn(df)
            r["modelName"] = name
            r["description"] = desc
            results.append(r)
        except Exception as e:
            print(f"[backtest] '{name}' failed: {e}")
    results.sort(key=lambda x: x.get("sharpeRatio", 0), reverse=True)
    return results


def run_backtest(df: pd.DataFrame, **_) -> dict:
    results = run_all_strategies(df)
    return results[0] if results else _empty_result("Insufficient data")


def _empty_result(reason: str) -> dict:
    return {"accuracy": 0.5, "cumulativeReturn": 0.0, "winRate": 0.5,
            "sharpeRatio": 0.0, "maxDrawdown": 0.0, "volatility": 0.0,
            "calmarRatio": 0.0, "totalTrades": 0, "equityCurve": [], "reason": reason}
