"""Backtest routes."""

from __future__ import annotations

from fastapi import APIRouter
from app.schemas.backtest import BacktestSummaryResponse
from app.services.backtest_service import get_backtest_summary

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.get("/summary", response_model=BacktestSummaryResponse)
async def backtest_summary():
    return await get_backtest_summary("SPY")
