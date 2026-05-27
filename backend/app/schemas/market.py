from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class MarketMetric(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    changePercent: float
    volume: Optional[int] = None
    sparkline: Optional[list[float]] = None


class MacroIndicator(BaseModel):
    name: str
    value: float
    unit: str
    trend: str  # "rising" | "falling" | "stable"


class SignalItem(BaseModel):
    ticker: str
    name: str
    signal: str
    confidence: float
    expectedReturn: float


class WatchlistItemBrief(BaseModel):
    ticker: str
    name: str
    price: float
    change1d: float
    change5d: float
    change1m: float
    signal: str
    signalScore: float
    confidence: float
    riskScore: float
    alert: Optional[str] = None


class ReportSummary(BaseModel):
    ticker: str
    name: str
    rating: str
    confidence: float
    generatedAt: str
    summary: str


class MarketOverviewResponse(BaseModel):
    indices: list[MarketMetric]
    signals: list[SignalItem]
    macro: list[MacroIndicator]
    watchlist: list[WatchlistItemBrief]
    recentReports: list[ReportSummary]
