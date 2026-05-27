"""
API v1 router - aggregates all route modules
"""
from fastapi import APIRouter
from app.api.routes import market, asset, report, backtest, portfolio, forecast
from app.api.routes import analyst_export

api_router = APIRouter()

# Include all route modules (prefixes already defined in routers)
api_router.include_router(market.router)
api_router.include_router(asset.router)
api_router.include_router(report.router)
api_router.include_router(backtest.router)
api_router.include_router(portfolio.router)
api_router.include_router(forecast.router)
api_router.include_router(analyst_export.router)
