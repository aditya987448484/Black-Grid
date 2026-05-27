from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class ChatMessage(BaseModel):
    role: str
    content: str


class AttachmentMeta(BaseModel):
    filename: str
    contentType: str
    size: int
    summary: Optional[str] = None


class AiAnalystRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    model: str = "claude-sonnet-4-20250514"
    attachments: list[AttachmentMeta] = []


class QuotePayload(BaseModel):
    price: float
    change: float
    changePercent: float
    volume: int = 0


class PricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class AnalysisSection(BaseModel):
    key: str
    title: str
    content: str


class AiAnalystResponse(BaseModel):
    reply: str
    ticker: Optional[str] = None
    companyName: Optional[str] = None
    sector: Optional[str] = None
    rating: Optional[str] = None
    confidenceScore: Optional[float] = None
    quote: Optional[QuotePayload] = None
    chart: list[PricePoint] = []
    analysisSections: list[AnalysisSection] = []
    disclaimer: str = ""
    modelUsed: str = ""


class UploadResponse(BaseModel):
    filename: str
    contentType: str
    size: int
    summary: str
