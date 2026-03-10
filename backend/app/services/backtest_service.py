"""Backtest service orchestrating data + backtest pipeline."""

from __future__ import annotations

from app.services.market_data import fetch_price_history
from app.services.mock_data import mock_backtest_summary, _generate_equity_curve
from app.pipelines.backtest import run_backtest


async def get_backtest_summary(ticker: str = "SPY") -> dict:
    """Run backtest pipeline for a ticker."""
    df = await fetch_price_history(ticker)

    if df is not None and len(df) >= 200:
        try:
            baseline_result = run_backtest(df)

            # Generate buy-and-hold benchmark
            returns = df["close"].pct_change().dropna()
            bh_cum = float((df["close"].iloc[-1] / df["close"].iloc[0]) - 1)
            bh_equity = [100.0]
            for r in returns:
                bh_equity.append(bh_equity[-1] * (1 + r))

            import numpy as np
            bh_returns = returns.values
            bh_sharpe = float((bh_returns.mean() / bh_returns.std()) * np.sqrt(252)) if bh_returns.std() > 0 else 0
            bh_peak = np.maximum.accumulate(np.array(bh_equity[1:]))
            bh_dd = (np.array(bh_equity[1:]) - bh_peak) / bh_peak
            bh_max_dd = float(abs(bh_dd.min()))

            bh_equity_curve = [
                {"date": str(df["date"].iloc[i + 1])[:10], "value": round(v, 2)}
                for i, v in enumerate(bh_equity[1:])
                if i + 1 < len(df)
            ]

            # Limit equity curve length
            if len(bh_equity_curve) > len(baseline_result.get("equityCurve", [])):
                step = len(bh_equity_curve) // max(len(baseline_result.get("equityCurve", [1])), 1)
                if step > 1:
                    bh_equity_curve = bh_equity_curve[::step]

            models = [
                {
                    "modelName": "Baseline (LogReg)",
                    "accuracy": baseline_result["accuracy"],
                    "cumulativeReturn": baseline_result["cumulativeReturn"],
                    "winRate": baseline_result["winRate"],
                    "sharpeRatio": baseline_result["sharpeRatio"],
                    "maxDrawdown": baseline_result["maxDrawdown"],
                    "volatility": baseline_result["volatility"],
                    "description": "Logistic regression with walk-forward validation on rolling 120-day windows.",
                    "equityCurve": baseline_result["equityCurve"],
                },
                {
                    "modelName": "Buy & Hold",
                    "accuracy": 0.5,
                    "cumulativeReturn": round(bh_cum, 4),
                    "winRate": float(np.mean(bh_returns > 0)),
                    "sharpeRatio": round(bh_sharpe, 2),
                    "maxDrawdown": round(bh_max_dd, 4),
                    "volatility": round(float(bh_returns.std() * np.sqrt(252)), 4),
                    "description": "Passive buy-and-hold benchmark. No signal-based trading.",
                    "equityCurve": bh_equity_curve[:len(baseline_result["equityCurve"])],
                },
            ]

            date_range = f"{str(df['date'].iloc[0])[:10]} to {str(df['date'].iloc[-1])[:10]}"

            return {
                "models": models,
                "benchmarkReturn": round(bh_cum, 4),
                "period": date_range,
                "ticker": ticker.upper(),
            }
        except Exception as e:
            print(f"[backtest] Live backtest failed for {ticker}: {e}")

    return mock_backtest_summary()
