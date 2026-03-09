from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class ReportSection(BaseModel):
    title: str
    content: str


class AnalystReportResponse(BaseModel):
    ticker: str
    name: str
    generatedAt: str
    rating: str
    confidenceScore: float
    sector: Optional[str] = None
    analystName: str = "BlackGrid Research"
    sections: list[ReportSection]
    executiveSummary: str
    keyHighlights: str = ""
    technicalView: str
    fundamentalSnapshot: str
    macroContext: str
    forecastView: str
    valuationScenarios: str = ""
    competitiveLandscape: str = ""
    bullCase: str
    bearCase: str
    risksCatalysts: str
    analystConclusion: str = ""
    disclaimer: str = ""
