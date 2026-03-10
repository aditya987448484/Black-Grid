from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class EquityPoint(BaseModel):
    date: str
    value: float


class BacktestModelResult(BaseModel):
    modelName: str
    accuracy: float = 0.5
    cumulativeReturn: float = 0.0
    winRate: float = 0.5
    sharpeRatio: float = 0.0
    maxDrawdown: float = 0.0
    volatility: float = 0.0
    calmarRatio: float = 0.0
    totalTrades: int = 0
    description: str = ""
    strategyKey: Optional[str] = None
    category: Optional[str] = None
    insufficientData: bool = False
    params: Optional[dict] = None
    equityCurve: list[EquityPoint] = []


class BacktestSummaryResponse(BaseModel):
    models: list[BacktestModelResult]
    benchmarkReturn: float
    period: str
    ticker: str
    dataPoints: int = 0
    error: Optional[str] = None
