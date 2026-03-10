from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class CompanyInfo(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    assetType: Optional[str] = None
    currency: Optional[str] = "USD"


class CompanySearchResult(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = None
    sector: Optional[str] = None
    assetType: Optional[str] = None
    matchScore: Optional[float] = None


class CompanySearchResponse(BaseModel):
    query: str
    results: list[CompanySearchResult]
    count: int


class CompanyListResponse(BaseModel):
    companies: list[CompanyInfo]
    total: int
    page: int
    pageSize: int
