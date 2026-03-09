from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class PricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class AssetDetailResponse(BaseModel):
    ticker: str
    name: str
    sector: str
    price: float
    change: float
    changePercent: float
    volume: int
    marketCap: int
    signal: str
    signalScore: float
    priceHistory: list[PricePoint]


class TechnicalIndicator(BaseModel):
    name: str
    value: float
    signal: str
    description: str


class EMAValue(BaseModel):
    period: int
    value: float


class MACDValue(BaseModel):
    macd: float
    signal: float
    histogram: float


class AssetTechnicalResponse(BaseModel):
    ticker: str
    indicators: list[TechnicalIndicator]
    ema: list[EMAValue]
    rsi: float
    macd: MACDValue
    atr: float
    volatility: float


class ForecastModelOutput(BaseModel):
    modelName: str
    status: str  # "live" | "simulated" | "coming_soon"
    directionProbability: float
    predictedDirection: str
    expectedReturn: float
    confidence: float
    explanation: str


class AssetForecastResponse(BaseModel):
    ticker: str
    models: list[ForecastModelOutput]
    bullishFactors: list[str]
    bearishFactors: list[str]
    riskLevel: str
    aiSummary: str
