"""
Rolling Backtest Pipeline
Executes historical walk-forward simulation using the baseline forecast model.

Design:
- Strict walk-forward split: model only sees data up to step t when predicting t+1
- Reuses FeaturePipeline and BaselineModel unchanged — no data leakage
- Each step in the simulation represents one trading day
- Position sizing: 100% capital per signal (long/flat, no shorting)

Simulation rules:
  BUY  → enter long next-day open, exit after lookahead_period days
  SELL → stay flat (no shorting)
  HOLD → stay flat

Supported metrics (all computed in-module):
  - direction_accuracy  : % of days model predicted the correct next-day move
  - cumulative_return   : total portfolio return over the period (%)
  - win_rate            : % of closed trades with positive P&L
  - sharpe_ratio        : annualised risk-adjusted return (252 trading days)
  - sortino_ratio       : like Sharpe but only penalises downside volatility
  - max_drawdown        : largest peak-to-trough drawdown (%)
  - volatility          : annualised daily return std-dev (%)
  - trades_count        : total number of completed trades
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from app.pipelines.features import FeaturePipeline
from app.models.baseline_model import BaselineModel, SignalDirection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE_ANNUAL = 0.045        # 4.5 % annual risk-free rate
RISK_FREE_DAILY = RISK_FREE_RATE_ANNUAL / TRADING_DAYS_PER_YEAR
MIN_TRAIN_ROWS = 120                  # minimum rows needed to start rolling window
MIN_TEST_STEPS = 20                   # minimum test steps to produce a meaningful result


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TradeRecord:
    """One completed trade"""
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    pnl_pct: float          # gross P&L as percentage of entry price


@dataclass
class BacktestResult:
    """Full backtest output before schema conversion"""
    ticker: str
    strategy: str
    strategy_description: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_value: float
    total_return: float          # %
    annual_return: float         # %
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float          # %, negative
    volatility: float            # % annualised
    win_rate: float              # %
    direction_accuracy: float    # %
    trades_count: int
    daily_returns: List[float] = field(default_factory=list)  # kept for debugging


# ---------------------------------------------------------------------------
# Pure metric helpers
# ---------------------------------------------------------------------------

def _sharpe(daily_returns: np.ndarray) -> float:
    """
    Annualised Sharpe ratio.

    sharpe = (mean_daily_excess_return / std_daily_return) * sqrt(252)

    Returns 0.0 if std is zero or there are fewer than 2 returns.
    """
    if len(daily_returns) < 2:
        return 0.0
    excess = daily_returns - RISK_FREE_DAILY
    std = np.std(excess, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(TRADING_DAYS_PER_YEAR))


def _sortino(daily_returns: np.ndarray) -> float:
    """
    Annualised Sortino ratio — penalises only downside deviation.

    sortino = mean_excess_return / downside_std * sqrt(252)
    """
    if len(daily_returns) < 2:
        return 0.0
    excess = daily_returns - RISK_FREE_DAILY
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float(np.mean(excess) * np.sqrt(TRADING_DAYS_PER_YEAR))
    downside_std = np.std(downside, ddof=1)
    if downside_std == 0:
        return 0.0
    return float(np.mean(excess) / downside_std * np.sqrt(TRADING_DAYS_PER_YEAR))


def _max_drawdown(equity_curve: np.ndarray) -> float:
    """
    Maximum peak-to-trough drawdown as a percentage (negative).

    max_dd = min( (trough - peak) / peak ) * 100
    """
    if len(equity_curve) < 2:
        return 0.0
    peaks = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - peaks) / peaks
    return float(np.min(drawdowns) * 100)


def _annual_return(total_return_pct: float, n_trading_days: int) -> float:
    """
    Compound annual growth rate from total return and number of trading days.

    CAGR = (1 + total_return)^(252/n_days) - 1
    """
    if n_trading_days <= 0:
        return 0.0
    growth = 1.0 + total_return_pct / 100.0
    if growth <= 0:
        return -100.0
    years = n_trading_days / TRADING_DAYS_PER_YEAR
    return float((growth ** (1.0 / years) - 1.0) * 100.0)


def _win_rate(trades: List[TradeRecord]) -> float:
    """Percentage of closed trades with positive P&L."""
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.pnl_pct > 0)
    return float(wins / len(trades) * 100.0)


def _direction_accuracy(
    predicted_signals: List[SignalDirection],
    actual_next_day_returns: List[float],
) -> float:
    """
    Percentage of steps where the model's direction matched the actual
    next-day price move.

    Mapping:
      BUY  → predict UP  (actual > 0 is correct)
      SELL → predict DOWN (actual < 0 is correct)
      HOLD → treated as neutral; correct if |actual| < 0.5%
    """
    if not predicted_signals or len(predicted_signals) != len(actual_next_day_returns):
        return 0.0

    correct = 0
    for sig, ret in zip(predicted_signals, actual_next_day_returns):
        if sig == SignalDirection.BUY and ret > 0:
            correct += 1
        elif sig == SignalDirection.SELL and ret < 0:
            correct += 1
        elif sig == SignalDirection.HOLD and abs(ret) < 0.005:
            correct += 1

    return float(correct / len(predicted_signals) * 100.0)


# ---------------------------------------------------------------------------
# Rolling simulation engine
# ---------------------------------------------------------------------------

class RollingBacktestEngine:
    """
    Walk-forward rolling backtest engine.

    For each step t (from train_window onward):
      1. Train model on df[0 : t]
      2. Predict signal at t
      3. Record actual next-day return at t+1
      4. Track portfolio equity accordingly

    Position sizing: 100% capital for BUY; flat for HOLD/SELL (no shorting).
    Hold period: model's lookahead_period days (default 5).
    """

    def __init__(
        self,
        train_window: int = MIN_TRAIN_ROWS,
        lookahead_period: int = 5,
        initial_capital: float = 100_000.0,
    ) -> None:
        self.train_window = train_window
        self.lookahead_period = lookahead_period
        self.initial_capital = initial_capital
        self.feature_pipeline = FeaturePipeline()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        df: pd.DataFrame,
        ticker: str,
    ) -> BacktestResult:
        """
        Execute rolling backtest on OHLCV DataFrame.

        Args:
            df : DataFrame indexed by date with columns [Open, High, Low, Close, Volume].
                 Must already be sorted ascending.
            ticker: Ticker symbol (for labelling only).

        Returns:
            BacktestResult with all computed metrics.

        Raises:
            ValueError: If data is insufficient for a valid backtest.
        """
        self._validate(df)

        # Build features on the full dataset once; we slice below per step
        features_df, feature_cols = self.feature_pipeline.build_features(df)

        n = len(features_df)
        if n - self.train_window < MIN_TEST_STEPS:
            raise ValueError(
                f"Insufficient test steps after warm-up: need {MIN_TEST_STEPS}, "
                f"got {n - self.train_window}. Provide more data."
            )

        logger.info(
            f"[{ticker}] Rolling backtest: {n} rows, "
            f"train_window={self.train_window}, steps={n - self.train_window}"
        )

        predicted_signals: List[SignalDirection] = []
        actual_next_day_returns: List[float] = []
        portfolio_daily_returns: List[float] = []
        trades: List[TradeRecord] = []

        # Track open position state
        in_position: bool = False
        entry_price: float = 0.0
        entry_date: Optional[datetime] = None
        hold_days_remaining: int = 0

        equity = self.initial_capital
        equity_curve: List[float] = [equity]

        # Rolling loop — step through each test bar
        for step in range(self.train_window, n - 1):
            train_slice = features_df.iloc[:step]
            current_close = float(features_df["Close"].iloc[step])
            next_close = float(features_df["Close"].iloc[step + 1])
            current_date = features_df.index[step]
            next_date = features_df.index[step + 1]

            # Actual next-day return (decimal, not %)
            actual_ret = (next_close - current_close) / current_close
            actual_next_day_returns.append(actual_ret)

            # --- Predict ---
            signal = self._predict_step(train_slice, feature_cols)
            predicted_signals.append(signal)

            # --- Position management ---
            day_pnl_pct = 0.0

            if in_position:
                hold_days_remaining -= 1
                day_pnl_pct = actual_ret  # portfolio moves with market while held

                if hold_days_remaining <= 0:
                    # Close position
                    trade_pnl = (next_close - entry_price) / entry_price * 100.0
                    trades.append(TradeRecord(
                        entry_date=entry_date,
                        exit_date=next_date,
                        entry_price=entry_price,
                        exit_price=next_close,
                        pnl_pct=trade_pnl,
                    ))
                    in_position = False

            else:
                # Not in position — check for entry
                if signal == SignalDirection.BUY:
                    in_position = True
                    entry_price = next_close  # enter at next open (approx as next close)
                    entry_date = next_date
                    hold_days_remaining = self.lookahead_period
                    # No P&L on entry day itself
                    day_pnl_pct = 0.0

            # Update equity
            equity = equity * (1.0 + day_pnl_pct)
            equity_curve.append(equity)
            portfolio_daily_returns.append(day_pnl_pct)

        # --- Aggregate metrics ---
        equity_arr = np.array(equity_curve)
        returns_arr = np.array(portfolio_daily_returns)

        total_return = (equity - self.initial_capital) / self.initial_capital * 100.0
        n_test_days = len(portfolio_daily_returns)
        ann_return = _annual_return(total_return, n_test_days)
        sharpe = _sharpe(returns_arr)
        sortino = _sortino(returns_arr)
        mdd = _max_drawdown(equity_arr)
        vol = float(np.std(returns_arr, ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR) * 100.0) if n_test_days > 1 else 0.0
        win_rt = _win_rate(trades)
        dir_acc = _direction_accuracy(predicted_signals, actual_next_day_returns)

        start_date = features_df.index[self.train_window]
        end_date = features_df.index[n - 1]

        logger.info(
            f"[{ticker}] Backtest complete: return={total_return:.1f}%, "
            f"sharpe={sharpe:.2f}, max_dd={mdd:.1f}%, trades={len(trades)}, "
            f"dir_acc={dir_acc:.1f}%"
        )

        return BacktestResult(
            ticker=ticker.upper(),
            strategy="Baseline Momentum",
            strategy_description=(
                "Rolling walk-forward simulation using the Baseline model "
                "(Logistic Regression direction + Gradient Boosting return estimate). "
                "Enters long on BUY signal; holds flat on HOLD/SELL. "
                f"Hold period: {self.lookahead_period} trading days. "
                "Model is retrained at each step on all preceding data."
            ),
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_value=round(equity, 2),
            total_return=round(total_return, 2),
            annual_return=round(ann_return, 2),
            sharpe_ratio=round(sharpe, 3),
            sortino_ratio=round(sortino, 3),
            max_drawdown=round(mdd, 2),
            volatility=round(vol, 2),
            win_rate=round(win_rt, 1),
            direction_accuracy=round(dir_acc, 1),
            trades_count=len(trades),
            daily_returns=portfolio_daily_returns,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate(self, df: pd.DataFrame) -> None:
        required = {"Open", "High", "Low", "Close", "Volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing columns: {missing}")
        if len(df) < self.train_window + MIN_TEST_STEPS + self.lookahead_period + 10:
            raise ValueError(
                f"Insufficient data for backtest: {len(df)} rows. "
                f"Need at least {self.train_window + MIN_TEST_STEPS + self.lookahead_period + 10}."
            )

    def _predict_step(
        self,
        train_slice: pd.DataFrame,
        feature_cols: List[str],
    ) -> SignalDirection:
        """
        Train a fresh BaselineModel on train_slice and return the
        signal for the last available row.

        If training fails (e.g. too few rows after feature warm-up),
        returns HOLD gracefully.
        """
        try:
            model = BaselineModel(lookahead_period=self.lookahead_period)
            model.train(train_slice, feature_cols)

            # Predict on the last row of the training slice (latest observation)
            X_last = train_slice[feature_cols].iloc[-1].values
            prediction = model.predict(X_last)
            return prediction.signal

        except Exception as exc:
            logger.debug(f"Step prediction failed (returning HOLD): {exc}")
            return SignalDirection.HOLD
