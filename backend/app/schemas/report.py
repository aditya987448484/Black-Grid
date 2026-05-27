from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class ReportSection(BaseModel):
    title: str
    content: str


class ReportPricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class ReportQuote(BaseModel):
    price: float
    change: float
    changePercent: float
    volume: int = 0


class AnalystReportResponse(BaseModel):
    ticker: str
    name: str
    generatedAt: str
    rating: str
    confidenceScore: float
    sector: Optional[str] = None
    analystName: str = "BlackGrid Research"
    sections: list[ReportSection] = []
    executiveSummary: str = ""
    keyHighlights: str = ""
    technicalView: str = ""
    fundamentalSnapshot: str = ""
    macroContext: str = ""
    forecastView: str = ""
    valuationScenarios: str = ""
    competitiveLandscape: str = ""
    bullCase: str = ""
    bearCase: str = ""
    risksCatalysts: str = ""
    analystConclusion: str = ""
    disclaimer: str = ""
    # Chart data and quote for frontend rendering
    quote: Optional[ReportQuote] = None
    chart: list[ReportPricePoint] = []
