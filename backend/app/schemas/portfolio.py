from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class PortfolioItem(BaseModel):
    ticker: str
    name: str
    price: float
    change1d: float
    change5d: float
    change1m: float
    signalScore: float
    confidence: float
    riskScore: float
    alert: Optional[str] = None
    allocation: float


class PortfolioSummary(BaseModel):
    totalValue: float
    dailyChange: float
    dailyChangePercent: float
    topSignal: str
    riskLevel: str


class WatchlistResponse(BaseModel):
    items: list[PortfolioItem]
    summary: PortfolioSummary
