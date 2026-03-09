from __future__ import annotations

from pydantic import BaseModel


class EquityPoint(BaseModel):
    date: str
    value: float


class BacktestModelResult(BaseModel):
    modelName: str
    accuracy: float
    cumulativeReturn: float
    winRate: float
    sharpeRatio: float
    maxDrawdown: float
    volatility: float
    calmarRatio: float = 0.0
    totalTrades: int = 0
    description: str
    equityCurve: list[EquityPoint]


class BacktestSummaryResponse(BaseModel):
    models: list[BacktestModelResult]
    benchmarkReturn: float
    period: str
    ticker: str
    dataPoints: int = 0
