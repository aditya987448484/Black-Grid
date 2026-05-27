"""Execute a compiled strategy through a deterministic backtest loop.

Runs the compiled boolean signals bar-by-bar, handling:
- Filter mask gating
- Entry signal detection (long and short)
- Exit signal detection
- Risk rules: stop loss, take profit, trailing stop
- Trade tracking, equity curve, and performance metrics

Returns a dict matching the BacktestModelResult shape used by the rest of
the BlackGrid pipeline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.strategy_engine.compiler import CompiledStrategy
from app.strategy_engine.schemas import RiskRuleSet, StrategySpec


# ---------------------------------------------------------------------------
# ATR helper -- try to import; fall back to local implementation.
# ---------------------------------------------------------------------------
try:
    from app.indicators.technical import atr as _compute_atr
except ImportError:
    def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        prev_close = close.shift(1)
        tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        return tr.ewm(com=period - 1, min_periods=period, adjust=False).mean()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(v: float, default: float = 0.0) -> float:
    """Return *v* if it is a finite float, otherwise *default*."""
    try:
        f = float(v)
        return f if not (np.isnan(f) or np.isinf(f)) else default
    except (TypeError, ValueError):
        return default


def _compute_position_size(
    spec: StrategySpec,
    price: float,
    atr_val: float,
    volatility: float,
) -> float:
    """Determine position size as a fraction of equity (0 .. 1)."""
    mode = spec.risk.sizing_mode
    risk_pct = spec.risk.risk_per_trade_pct / 100.0

    if mode == "atr_based":
        if atr_val > 0 and price > 0:
            stop_distance = 2.0 * atr_val / price
            if stop_distance > 1e-6:
                return min(1.0, risk_pct / stop_distance)
        return 0.5

    if mode == "volatility_scaled":
        if volatility > 0:
            target_vol = 0.15  # 15% annualised target
            return min(1.0, target_vol / volatility)
        return 0.5

    # "fixed" -- equal-weight
    return 1.0


def _compute_metrics(
    daily_returns: list[float],
    equity: list[float],
    trades: list[dict],
) -> dict:
    """Compute performance metrics from daily returns and the equity curve."""
    dr = np.array(daily_returns, dtype=float)
    eq = np.array(equity, dtype=float)

    # Cumulative return
    cum_return = (eq[-1] / eq[0]) - 1.0 if eq[0] > 0 else 0.0

    # Win rate (based on completed trades)
    if trades:
        winning = sum(1 for t in trades if t["pnl_pct"] > 0)
        win_rate = winning / len(trades)
    else:
        active = dr[dr != 0]
        win_rate = float(np.mean(active > 0)) if len(active) > 0 else 0.5

    # Sharpe ratio (annualised)
    if dr.std() > 1e-10:
        sharpe = float((dr.mean() / dr.std()) * np.sqrt(252))
    else:
        sharpe = 0.0

    # Max drawdown
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / np.where(peak > 0, peak, 1.0)
    max_dd = float(abs(dd.min())) if len(dd) > 0 else 0.0

    # Annualised volatility
    vol = float(dr.std() * np.sqrt(252))

    # Calmar ratio
    calmar = round(cum_return / max_dd, 2) if max_dd > 1e-6 else 0.0

    total_trades = len(trades)

    return {
        "cumulativeReturn": round(cum_return, 4),
        "sharpeRatio": round(sharpe, 2),
        "winRate": round(win_rate, 4),
        "maxDrawdown": round(max_dd, 4),
        "volatility": round(vol, 4),
        "calmarRatio": calmar,
        "totalTrades": total_trades,
    }


def _build_equity_curve(
    dates: list[str],
    equity: list[float],
    offset: int,
) -> list[dict]:
    """Build the equityCurve list of {date, value} dicts."""
    curve: list[dict] = []
    for i, val in enumerate(equity[1:]):  # skip the initial 100.0
        idx = offset + i
        if idx < len(dates):
            curve.append({"date": dates[idx], "value": round(val, 2)})
    return curve


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_strategy(compiled: CompiledStrategy, df: pd.DataFrame) -> dict:
    """Run a compiled strategy through a deterministic backtest loop.

    The executor:
    1. Iterates through bars
    2. On each bar, checks filter_mask first
    3. If no position: check entry signals
    4. If in position: check exit signals AND risk rules (stop loss,
       take profit, trailing stop)
    5. Tracks: trades, equity curve, positions
    6. Computes metrics: cumulative return, sharpe, win rate, max drawdown,
       volatility, calmar ratio, total trades
    7. Returns dict matching BacktestModelResult shape

    Parameters
    ----------
    compiled : CompiledStrategy
        Output of ``compile_strategy()``.
    df : pd.DataFrame
        OHLCV DataFrame with columns: date, open, high, low, close, volume.

    Returns
    -------
    dict
        A BacktestModelResult-compatible dict with keys: modelName,
        strategyKey, category, description, cumulativeReturn, sharpeRatio,
        winRate, maxDrawdown, volatility, calmarRatio, totalTrades,
        equityCurve, isCustom.
    """
    spec = compiled.spec
    risk = spec.risk

    close_arr = df["close"].values.astype(float)
    high_arr = df["high"].values.astype(float)
    low_arr = df["low"].values.astype(float)
    n = len(df)

    # Pre-compute ATR for sizing / trailing-stop-atr
    atr_series = _compute_atr(df["high"], df["low"], df["close"], 14).values

    # Pre-compute rolling volatility (annualised, decimal) for sizing
    ret_series = pd.Series(close_arr).pct_change().fillna(0)
    vol_series = (ret_series.rolling(20).std() * np.sqrt(252)).fillna(0.15).values

    # Bar returns
    bar_returns = ret_series.values

    # Signal arrays (aligned with df index)
    long_entry = compiled.long_entry_signals.values.astype(bool)
    short_entry = compiled.short_entry_signals.values.astype(bool)
    long_exit = compiled.long_exit_signals.values.astype(bool)
    short_exit = compiled.short_exit_signals.values.astype(bool)
    filter_ok = compiled.filter_mask.values.astype(bool)

    # Risk parameters (convert percentages to decimals for price comparison)
    sl_pct = risk.stop_loss_pct / 100.0 if risk.stop_loss_pct else None
    tp_pct = risk.take_profit_pct / 100.0 if risk.take_profit_pct else None
    trail_pct = risk.trailing_stop_pct / 100.0 if risk.trailing_stop_pct else None
    trail_atr_mult = risk.trailing_stop_atr_mult

    # State
    position = 0        # 1 = long, -1 = short, 0 = flat
    entry_price = 0.0
    trailing_stop = 0.0
    peak_price = 0.0    # for trailing stop (long: highest since entry)
    trough_price = 0.0  # for trailing stop (short: lowest since entry)
    size = 1.0

    daily_returns: list[float] = []
    trades: list[dict] = []
    current_trade_entry_bar = -1

    for i in range(1, n):
        price = close_arr[i]
        hi = high_arr[i]
        lo = low_arr[i]
        atr_val = atr_series[i] if not np.isnan(atr_series[i]) else 0.0
        vol_val = vol_series[i] if not np.isnan(vol_series[i]) else 0.15

        # -- If in a position, check exits and risk rules first ------------
        if position != 0:
            should_exit = False
            exit_reason = ""

            # Signal-based exits
            if position == 1 and long_exit[i]:
                should_exit = True
                exit_reason = "long_exit_signal"
            elif position == -1 and short_exit[i]:
                should_exit = True
                exit_reason = "short_exit_signal"

            # Stop loss
            if not should_exit and sl_pct is not None:
                if position == 1 and price <= entry_price * (1.0 - sl_pct):
                    should_exit = True
                    exit_reason = "stop_loss"
                elif position == -1 and price >= entry_price * (1.0 + sl_pct):
                    should_exit = True
                    exit_reason = "stop_loss"

            # Take profit
            if not should_exit and tp_pct is not None:
                if position == 1 and price >= entry_price * (1.0 + tp_pct):
                    should_exit = True
                    exit_reason = "take_profit"
                elif position == -1 and price <= entry_price * (1.0 - tp_pct):
                    should_exit = True
                    exit_reason = "take_profit"

            # Trailing stop (percentage-based)
            if not should_exit and trail_pct is not None:
                if position == 1:
                    peak_price = max(peak_price, hi)
                    trailing_stop = max(trailing_stop, peak_price * (1.0 - trail_pct))
                    if price <= trailing_stop:
                        should_exit = True
                        exit_reason = "trailing_stop"
                elif position == -1:
                    trough_price = min(trough_price, lo)
                    trail_short = trough_price * (1.0 + trail_pct)
                    if trailing_stop == 0.0:
                        trailing_stop = trail_short
                    else:
                        trailing_stop = min(trailing_stop, trail_short)
                    if price >= trailing_stop:
                        should_exit = True
                        exit_reason = "trailing_stop"

            # Trailing stop (ATR-based)
            if not should_exit and trail_atr_mult is not None and atr_val > 0:
                if position == 1:
                    peak_price = max(peak_price, hi)
                    atr_trail = peak_price - trail_atr_mult * atr_val
                    trailing_stop = max(trailing_stop, atr_trail)
                    if price <= trailing_stop:
                        should_exit = True
                        exit_reason = "trailing_stop_atr"
                elif position == -1:
                    trough_price = min(trough_price, lo)
                    atr_trail_short = trough_price + trail_atr_mult * atr_val
                    if trailing_stop == 0.0:
                        trailing_stop = atr_trail_short
                    else:
                        trailing_stop = min(trailing_stop, atr_trail_short)
                    if price >= trailing_stop:
                        should_exit = True
                        exit_reason = "trailing_stop_atr"

            if should_exit:
                # Record trade
                if position == 1:
                    trade_pnl = (price - entry_price) / entry_price if entry_price > 0 else 0
                else:
                    trade_pnl = (entry_price - price) / entry_price if entry_price > 0 else 0

                trades.append({
                    "entry_bar": current_trade_entry_bar,
                    "exit_bar": i,
                    "direction": "long" if position == 1 else "short",
                    "entry_price": entry_price,
                    "exit_price": price,
                    "pnl_pct": trade_pnl,
                    "exit_reason": exit_reason,
                })
                position = 0
                entry_price = 0.0
                trailing_stop = 0.0

            # Daily P&L while in position
            if position != 0:
                daily_returns.append(_safe(bar_returns[i]) * position * size)
            else:
                daily_returns.append(0.0)

        else:
            # -- Flat: check for entries -----------------------------------
            if filter_ok[i]:
                if long_entry[i] and spec.direction != "short_only":
                    position = 1
                    entry_price = price
                    peak_price = hi
                    trailing_stop = 0.0
                    current_trade_entry_bar = i
                    size = _compute_position_size(spec, price, atr_val, vol_val)
                elif short_entry[i] and spec.direction != "long_only":
                    position = -1
                    entry_price = price
                    trough_price = lo
                    trailing_stop = 0.0
                    current_trade_entry_bar = i
                    size = _compute_position_size(spec, price, atr_val, vol_val)

            # No P&L on entry bar (enter at close, returns start next bar)
            daily_returns.append(0.0)

    # Close any open position at the end
    if position != 0 and n > 1:
        if position == 1:
            trade_pnl = (close_arr[-1] - entry_price) / entry_price if entry_price > 0 else 0
        else:
            trade_pnl = (entry_price - close_arr[-1]) / entry_price if entry_price > 0 else 0
        trades.append({
            "entry_bar": current_trade_entry_bar,
            "exit_bar": n - 1,
            "direction": "long" if position == 1 else "short",
            "entry_price": entry_price,
            "exit_price": close_arr[-1],
            "pnl_pct": trade_pnl,
            "exit_reason": "end_of_data",
        })

    # -- Build equity curve ------------------------------------------------
    equity = [100.0]
    for r in daily_returns:
        equity.append(equity[-1] * (1.0 + _safe(r)))

    # -- Compute metrics ---------------------------------------------------
    metrics = _compute_metrics(daily_returns, equity, trades)

    # -- Build date-indexed equity curve -----------------------------------
    if "date" in df.columns:
        dates = df["date"].astype(str).str[:10].tolist()
    else:
        dates = [str(d)[:10] for d in df.index]
    offset = max(0, len(dates) - len(daily_returns))
    equity_curve = _build_equity_curve(dates, equity, offset)

    # -- Assemble BacktestModelResult-compatible dict ----------------------
    result = {
        "modelName": spec.name,
        "strategyKey": f"custom_{spec.name.lower().replace(' ', '_')}",
        "category": "Custom",
        "description": spec.notes or f"Custom strategy: {spec.name}",
        "cumulativeReturn": metrics["cumulativeReturn"],
        "sharpeRatio": metrics["sharpeRatio"],
        "winRate": metrics["winRate"],
        "maxDrawdown": metrics["maxDrawdown"],
        "volatility": metrics["volatility"],
        "calmarRatio": metrics["calmarRatio"],
        "totalTrades": metrics["totalTrades"],
        "equityCurve": equity_curve,
        "isCustom": True,
    }

    return result
