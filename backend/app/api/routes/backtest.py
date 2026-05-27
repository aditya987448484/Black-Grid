"""
Backtesting endpoints for strategy analysis
"""
from fastapi import APIRouter, HTTPException, Path, Query
import logging

from app.schemas.schemas import BacktestResult, BacktestSummaryResponse
from app.services.backtest_service import BacktestService
from app.api.service_factory import ServiceFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtests", tags=["backtest"])


@router.get(
    "/summary",
    response_model=BacktestSummaryResponse,
    summary="Run backtest for default tickers",
)
async def get_backtest_summary(
    limit: int = Query(10, ge=1, le=20, description="Maximum number of tickers to backtest"),
) -> BacktestSummaryResponse:
    """
    Run rolling walk-forward backtests for a set of default tickers and return
    aggregate results.

    Each result includes:
    - Total / annualised return
    - Sharpe & Sortino ratio
    - Max drawdown & volatility
    - Win rate & next-day direction accuracy
    - Trade count
    - Strategy description (for frontend display)

    Tickers that cannot produce a valid backtest (insufficient data,
    provider error) are silently excluded from the response.
    """
    try:
        market_service = ServiceFactory.get_market_data_service()
        backtest_service = BacktestService(market_service.provider)

        logger.info(f"Running backtest summary (limit={limit})")
        return await backtest_service.run_summary(limit=limit)

    except Exception as exc:
        logger.error(f"Backtest summary failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to run backtest")


@router.get(
    "/{ticker}",
    response_model=BacktestResult,
    summary="Run backtest for a single ticker",
)
async def get_ticker_backtest(
    ticker: str = Path(..., min_length=1, max_length=10, description="Asset ticker symbol"),
) -> BacktestResult:
    """
    Run a full rolling walk-forward backtest for a single ticker symbol.

    Returns:
    - Rolling Baseline Momentum strategy metrics
    - Direction accuracy vs actual next-day moves
    - Max drawdown, Sharpe, win rate, volatility
    - Strategy description for display

    Returns HTTP 422 if there is insufficient historical data for the ticker.
    """
    try:
        market_service = ServiceFactory.get_market_data_service()
        backtest_service = BacktestService(market_service.provider)

        logger.info(f"Running backtest for {ticker.upper()}")
        return await backtest_service.run_backtest(ticker)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Backtest failed for {ticker}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run backtest for {ticker}",
        )
