"""BlackGrid Backend - FastAPI entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_market import router as market_router
from app.api.routes_asset import router as asset_router
from app.api.routes_backtests import router as backtests_router
from app.api.routes_portfolio import router as portfolio_router
from app.api.routes_world_hub import router as world_hub_router
from app.api.routes_search import router as search_router
from app.api.routes_ai_analyst import router as ai_analyst_router
from app.core.config import log_config_status

app = FastAPI(
    title="BlackGrid API",
    description="AI-powered financial research platform backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)
app.include_router(asset_router)
app.include_router(backtests_router)
app.include_router(portfolio_router)
app.include_router(world_hub_router)
app.include_router(search_router)
app.include_router(ai_analyst_router)


@app.on_event("startup")
async def startup():
    log_config_status()
    # Pre-warm the ticker universe
    from app.services.market_universe import ensure_universe_loaded
    await ensure_universe_loaded()


@app.get("/")
async def root():
    return {"name": "BlackGrid API", "version": "1.0.0", "status": "running"}
