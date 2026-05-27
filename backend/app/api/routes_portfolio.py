"""Portfolio/watchlist routes."""

from __future__ import annotations

from fastapi import APIRouter
from app.schemas.portfolio import WatchlistResponse
from app.services.portfolio_service import get_watchlist_intelligence

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/watchlist", response_model=WatchlistResponse)
async def portfolio_watchlist():
    return await get_watchlist_intelligence()
