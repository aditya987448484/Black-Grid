"""Backtest service — runs all 5 strategies for any ticker and date range."""

from __future__ import annotations

from typing import Optional
from app.services.market_data import fetch_price_history_range
from app.services.mock_data import mock_backtest_summary
from app.pipelines.backtest import run_all_strategies


async def get_backtest_summary(
    ticker: str = "SPY",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Run all strategies on a ticker's price history within a date range."""
    df = await fetch_price_history_range(ticker, start_date, end_date)

    if df is not None and len(df) >= 100:
        try:
            results = run_all_strategies(df)
            if results:
                actual_start = str(df["date"].iloc[0])[:10]
                actual_end = str(df["date"].iloc[-1])[:10]
                benchmark = next(
                    (r for r in results if r["modelName"] == "Buy & Hold"), None
                )
                return {
                    "models": results,
                    "benchmarkReturn": benchmark["cumulativeReturn"] if benchmark else 0.0,
                    "period": f"{actual_start} to {actual_end}",
                    "ticker": ticker.upper(),
                    "dataPoints": len(df),
                }
        except Exception as e:
            print(f"[backtest_service] Failed for {ticker}: {e}")

    return mock_backtest_summary()
