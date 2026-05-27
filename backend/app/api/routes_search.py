"""Search and company listing routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from app.schemas.universe import CompanySearchResponse, CompanyListResponse
from app.services.company_search import search_companies
from app.services.market_universe import get_universe

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search/companies", response_model=CompanySearchResponse)
async def search(q: str = Query("", min_length=1, max_length=30)):
    results = await search_companies(q)
    return {"query": q, "results": results, "count": len(results)}


@router.get("/companies", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    exchange: str = Query(""),
):
    universe = await get_universe()

    # Filter by exchange if specified
    if exchange:
        ex = exchange.upper()
        universe = [c for c in universe if (c.get("exchange") or "").upper() == ex]

    total = len(universe)
    start = (page - 1) * pageSize
    end = start + pageSize
    page_items = universe[start:end]

    return {"companies": page_items, "total": total, "page": page, "pageSize": pageSize}
