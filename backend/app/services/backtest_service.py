"""Backtest service — uses yfinance data + 27-strategy pipeline."""
from __future__ import annotations

from typing import Optional
from app.services.market_data import fetch_price_history_range
from app.pipelines.backtest import run_all_strategies, STRATEGY_REGISTRY


async def get_backtest_summary(
    ticker: str = "SPY",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    strategy_keys: Optional[list[str]] = None,
) -> dict:
    """Run all selected strategies on real price data from yfinance."""
    ticker = ticker.upper().strip()

    # Fetch real OHLCV data
    df = await fetch_price_history_range(ticker, start_date, end_date)

    if df is None or len(df) < 40:
        print(f"[backtest_service] Insufficient data for {ticker}: {len(df) if df is not None else 0} bars")
        return {
            "models": [],
            "benchmarkReturn": 0.0,
            "period": "N/A",
            "ticker": ticker,
            "dataPoints": 0,
            "error": f"Could not fetch sufficient price data for {ticker}. "
                     "Ensure yfinance is installed: pip install yfinance",
        }

    print(f"[backtest_service] Running strategies on {ticker}: {len(df)} bars")

    try:
        keys = strategy_keys or [
            "rsi_mean_rev", "macd_trend", "bollinger_squeeze",
            "atr_channel", "rsi_macd_conf", "buy_hold",
            "ema_crossover", "supertrend", "donchian",
        ]
        results = run_all_strategies(df, keys=keys)
    except Exception as e:
        print(f"[backtest_service] Pipeline error for {ticker}: {e}")
        import traceback; traceback.print_exc()
        return {
            "models": [],
            "benchmarkReturn": 0.0,
            "period": "N/A",
            "ticker": ticker,
            "dataPoints": len(df),
            "error": str(e),
        }

    if not results:
        return {
            "models": [],
            "benchmarkReturn": 0.0,
            "period": "N/A",
            "ticker": ticker,
            "dataPoints": len(df),
            "error": "No strategies produced results — insufficient data for selected date range",
        }

    benchmark = next((r for r in results if r.get("strategyKey") == "buy_hold"), None)
    benchmark_return = benchmark["cumulativeReturn"] if benchmark else 0.0

    period_str = (
        f"{str(df['date'].iloc[0])[:10]} to {str(df['date'].iloc[-1])[:10]}"
    )

    return {
        "models": results,
        "benchmarkReturn": round(benchmark_return, 4),
        "period": period_str,
        "ticker": ticker,
        "dataPoints": len(df),
    }
