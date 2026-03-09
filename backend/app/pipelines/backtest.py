"""Rolling backtest pipeline for baseline model."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from app.pipelines.features import build_features
from app.models.baseline_model import FEATURE_COLS


def run_backtest(df: pd.DataFrame, train_window: int = 120, test_window: int = 1) -> dict:
    """Run rolling walk-forward backtest.

    Returns metrics and equity curve.
    """
    features = build_features(df)

    if len(features) < train_window + 20:
        return _empty_result("Insufficient data for backtesting.")

    X = features[FEATURE_COLS].values
    y = features["target"].values
    dates = features.index if isinstance(features.index, pd.DatetimeIndex) else pd.to_datetime(df["date"].iloc[features.index])
    returns = features["return_1d"].values

    predictions = []
    actuals = []
    daily_returns = []
    equity = [100.0]
    equity_dates = []

    for i in range(train_window, len(X) - 1):
        X_train = X[i - train_window:i]
        y_train = y[i - train_window:i]
        X_pred = X[i:i + 1]

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_pred_scaled = scaler.transform(X_pred)

        model = LogisticRegression(max_iter=500, C=0.1, random_state=42)
        model.fit(X_train_scaled, y_train)

        pred = model.predict(X_pred_scaled)[0]
        actual = y[i]
        actual_return = returns[i + 1] if i + 1 < len(returns) else 0.0

        predictions.append(pred)
        actuals.append(actual)

        # If model predicts up, go long; if down, stay flat
        strat_return = actual_return if pred == 1 else 0.0
        daily_returns.append(strat_return)
        equity.append(equity[-1] * (1 + strat_return))

        try:
            d = dates.iloc[i] if hasattr(dates, 'iloc') else dates[i]
            equity_dates.append(str(d)[:10])
        except Exception:
            equity_dates.append(f"day_{i}")

    if not predictions:
        return _empty_result("No predictions generated.")

    predictions = np.array(predictions)
    actuals = np.array(actuals)
    daily_returns = np.array(daily_returns)

    accuracy = float(np.mean(predictions == actuals))
    cum_return = (equity[-1] / equity[0]) - 1
    win_rate = float(np.mean(daily_returns[daily_returns != 0] > 0)) if np.any(daily_returns != 0) else 0.5

    # Sharpe ratio (annualized)
    if daily_returns.std() > 0:
        sharpe = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252))
    else:
        sharpe = 0.0

    # Max drawdown
    equity_arr = np.array(equity[1:])
    peak = np.maximum.accumulate(equity_arr)
    drawdown = (equity_arr - peak) / peak
    max_dd = float(abs(drawdown.min()))

    # Volatility
    vol = float(np.std(daily_returns) * np.sqrt(252))

    equity_curve = [{"date": d, "value": round(v, 2)} for d, v in zip(equity_dates, equity[1:])]

    return {
        "accuracy": round(accuracy, 4),
        "cumulativeReturn": round(cum_return, 4),
        "winRate": round(win_rate, 4),
        "sharpeRatio": round(sharpe, 2),
        "maxDrawdown": round(max_dd, 4),
        "volatility": round(vol, 4),
        "equityCurve": equity_curve,
    }


def _empty_result(reason: str) -> dict:
    return {
        "accuracy": 0.5,
        "cumulativeReturn": 0.0,
        "winRate": 0.5,
        "sharpeRatio": 0.0,
        "maxDrawdown": 0.0,
        "volatility": 0.0,
        "equityCurve": [],
        "reason": reason,
    }
