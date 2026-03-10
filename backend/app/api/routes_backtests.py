"""Backtest API routes."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.schemas.backtest import BacktestSummaryResponse
from app.services.backtest_service import get_backtest_summary
from app.pipelines.backtest import STRATEGY_REGISTRY, run_custom_strategy
from app.services.market_data import fetch_price_history_range

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.get("/summary", response_model=BacktestSummaryResponse)
async def backtest_summary(
    ticker: str = Query(default="SPY", min_length=1, max_length=10),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
):
    return await get_backtest_summary(ticker.upper().strip(), start_date, end_date)


@router.get("/strategies/list")
async def list_strategies():
    """Return all available strategy keys with metadata."""
    return {
        key: {
            "name": entry["name"],
            "category": entry["category"],
            "description": entry["description"],
            "defaultParams": entry["params"],
        }
        for key, entry in STRATEGY_REGISTRY.items()
    }


class RunCustomRequest(BaseModel):
    ticker: str
    strategy_key: str
    params: dict = {}
    custom_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/strategies/run-custom")
async def run_custom(req: RunCustomRequest):
    """Run a single custom strategy with user-specified params."""
    df = await fetch_price_history_range(req.ticker.upper(), req.start_date, req.end_date)
    if df is None or len(df) < 60:
        return {"error": f"Insufficient data for {req.ticker}"}
    return run_custom_strategy(df, req.strategy_key, req.params, req.custom_name)
