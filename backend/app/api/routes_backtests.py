"""Backtest routes."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from app.schemas.backtest import BacktestSummaryResponse
from app.services.backtest_service import get_backtest_summary

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.get("/summary", response_model=BacktestSummaryResponse)
async def backtest_summary(
    ticker: str = Query(default="SPY", min_length=1, max_length=10, description="Ticker symbol"),
    start_date: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
):
    return await get_backtest_summary(
        ticker.upper().strip(),
        start_date=start_date,
        end_date=end_date,
    )
