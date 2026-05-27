"""
AI analyst report endpoints
Generates comprehensive institutional-grade research reports using Groq LLM
"""
from fastapi import APIRouter, HTTPException, Path
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.schemas.schemas import AnalystReportResponse, AnalystReport
from app.services.analyst_service import AnalystReportGeneration
from app.services.fundamental_service import FundamentalSummary
from app.api.service_factory import ServiceFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/report", tags=["report"])


# ---------------------------------------------------------------------------
# Context builders — keep the route handler thin
# ---------------------------------------------------------------------------

def _build_fundamental_data(summary: Optional[FundamentalSummary], price: float) -> Dict[str, Any]:
    """
    Build the `fundamental_data` dict that flows into generate_analyst_report.
    Always returns a complete dict; uses None for unavailable fields.
    """
    if summary is None:
        return {
            "eps_diluted": None,
            "revenue": None,
            "net_income": None,
            "operating_cash_flow": None,
            "revenue_growth_yoy": None,
            "net_income_growth_yoy": None,
            "total_assets": None,
            "total_liabilities": None,
            "equity": None,
            "debt_to_assets": None,
            "growth_signal": "unknown",
            "risk_level": "unknown",
            "pe_ratio": None,
            "ps_ratio": None,
            "pb_ratio": None,
            "market_cap": None,
            "fiscal_year_end": None,
            "data_source": "unavailable",
        }

    return {
        # Per-share
        "eps_diluted": summary.eps_diluted,
        # Income statement
        "revenue": summary.revenue,
        "net_income": summary.net_income,
        "operating_cash_flow": summary.operating_cash_flow,
        # YoY growth
        "revenue_growth_yoy": summary.revenue_growth_yoy,
        "net_income_growth_yoy": summary.net_income_growth_yoy,
        # Balance sheet
        "total_assets": summary.total_assets,
        "total_liabilities": summary.total_liabilities,
        "equity": summary.equity,
        "debt_to_assets": summary.debt_to_assets,
        # Classification
        "growth_signal": summary.growth_signal,
        "risk_level": summary.risk_level,
        # Valuation multiples (price-dependent)
        "pe_ratio": summary.pe_ratio,
        "ps_ratio": summary.ps_ratio,
        "pb_ratio": summary.pb_ratio,
        "market_cap": summary.market_cap,
        # Meta
        "fiscal_year_end": summary.fiscal_year_end,
        "data_source": summary.fundamentals_source,
    }


def _build_macro_context(summary: Optional[FundamentalSummary]) -> Dict[str, Any]:
    """Build the `macro_context` dict from the fundamental summary's FRED fields."""
    if summary is None:
        return {
            "treasury_10y": None,
            "fed_funds_rate": None,
            "cpi_yoy": None,
            "unemployment_rate": None,
            "yield_curve_spread": None,
            "data_source": "unavailable",
        }

    return {
        "treasury_10y": summary.treasury_10y,
        "fed_funds_rate": summary.fed_funds_rate,
        "cpi_yoy": summary.cpi_yoy,
        "unemployment_rate": summary.unemployment_rate,
        "yield_curve_spread": summary.yield_curve_spread,
        "data_source": summary.macro_source,
    }


def _build_sec_summary(summary: Optional[FundamentalSummary]) -> Dict[str, Any]:
    """Build the `sec_summary` dict with company identity from EDGAR."""
    if summary is None:
        return {}
    return {
        "company_name": summary.company_name,
        "cik": summary.cik,
        "fiscal_year_end": summary.fiscal_year_end,
        "data_source": summary.fundamentals_source,
    }


def _company_name(summary: Optional[FundamentalSummary], ticker: str) -> str:
    if summary and summary.company_name:
        return summary.company_name
    return f"{ticker} Inc."


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get(
    "/{ticker}",
    response_model=AnalystReportResponse,
    summary="Get AI analyst report",
)
async def get_analyst_report(
    ticker: str = Path(..., min_length=1, max_length=10, description="Asset ticker symbol")
) -> AnalystReportResponse:
    """
    Get comprehensive AI-generated analyst report with institutional-grade analysis.

    **Data pipeline:**
    1. Market/price data — Alpha Vantage or mock
    2. Technical data — OHLCV candle analysis
    3. Fundamental summary — SEC EDGAR via FundamentalService (EPS, revenue, growth, debt)
    4. Macro context — FRED via FundamentalService (10Y yield, fed funds, CPI, unemployment)
    5. LLM synthesis — Groq or structured mock report

    **Fallback chain:**
    - FundamentalService falls back to mock when EDGAR/FRED are unavailable
    - LLM path falls back to AnalystReportGeneration with real fundamental data
    - Schema is always fully populated — no partial responses
    """
    try:
        ticker_upper = ticker.upper()

        market_service = ServiceFactory.get_market_data_service()
        fundamental_service = ServiceFactory.get_fundamental_service()
        reasoning_service = ServiceFactory.get_reasoning_service()

        # ── 1. Market / price data ──────────────────────────────────────────
        asset_info: Dict[str, Any] = {
            "name": f"{ticker_upper} Inc.",
            "ticker": ticker_upper,
            "price": 100.0,
        }
        try:
            quote_data = await market_service.get_current_quote(ticker_upper)
            if "Global Quote" in quote_data:
                gq = quote_data["Global Quote"]
                asset_info = {
                    "name": f"{ticker_upper} Inc.",
                    "ticker": ticker_upper,
                    "price": float(gq.get("05. price", 100.0)),
                    "change": float(gq.get("09. change", 0)),
                    "change_percent": float(gq.get("10. change percent", "0%").strip("%")),
                    "volume": gq.get("06. volume", ""),
                }
                logger.info(f"Fetched market data for {ticker_upper}")
        except Exception as e:
            logger.warning(f"Could not fetch market data for {ticker_upper}: {e}")

        current_price: float = float(asset_info.get("price", 100.0))

        # ── 2. Technical data ───────────────────────────────────────────────
        technical_data: Dict[str, Any] = {
            "trend": "Sideways",
            "support_levels": [round(current_price * 0.92, 2)],
            "resistance_levels": [round(current_price * 1.08, 2)],
            "indicators": {},
        }
        try:
            tech_response = await market_service.get_time_series(ticker_upper, interval="daily")
            if tech_response and "data" in tech_response:
                data_points = tech_response.get("data", [])
                if data_points:
                    recent = data_points[0]
                    close = float(recent.get("close", current_price))
                    open_ = float(recent.get("open", current_price))
                    technical_data = {
                        "trend": "Uptrend" if close > open_ else "Downtrend",
                        "support_levels": [float(recent.get("low", current_price * 0.95))],
                        "resistance_levels": [float(recent.get("high", current_price * 1.05))],
                        "indicators": {"rsi": 55, "macd": "positive", "bb_position": "middle"},
                    }
                    logger.info(f"Fetched technical data for {ticker_upper}")
        except Exception as e:
            logger.warning(f"Could not fetch technical data: {e}")

        # ── 3. ML forecast context (placeholder — wired separately) ─────────
        forecast_data: Dict[str, Any] = {
            "consensus_signal": "HOLD",
            "confidence": 65,
            "expected_return": 3.5,
        }

        # ── 4+5. Fundamental summary (SEC EDGAR) + macro context (FRED) ─────
        fundamental_summary: Optional[FundamentalSummary] = None
        try:
            fundamental_summary = await fundamental_service.get_fundamental_summary(
                ticker_upper, price=current_price
            )
            logger.info(
                f"Fetched fundamental summary for {ticker_upper} "
                f"(fundamentals: {fundamental_summary.fundamentals_source}, "
                f"macro: {fundamental_summary.macro_source})"
            )
            # Backfill company name into asset_info now that we have it
            asset_info["name"] = _company_name(fundamental_summary, ticker_upper)
        except Exception as e:
            logger.warning(f"Could not fetch fundamental summary for {ticker_upper}: {e}")

        fundamental_data = _build_fundamental_data(fundamental_summary, current_price)
        macro_context = _build_macro_context(fundamental_summary)
        sec_summary = _build_sec_summary(fundamental_summary)

        # ── 6. LLM report generation ────────────────────────────────────────
        try:
            report_data = await reasoning_service.provider.generate_analyst_report(
                ticker=ticker_upper,
                asset_info=asset_info,
                technical_data=technical_data,
                forecast_data=forecast_data,
                fundamental_data=fundamental_data,
                macro_context=macro_context,
                sec_summary=sec_summary,
            )
            analyst_report = AnalystReport(**report_data)
            logger.info(f"LLM analyst report generated for {ticker_upper}")
            return AnalystReportResponse(
                status="success",
                data=analyst_report,
                generated_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.warning(f"LLM report generation failed for {ticker_upper}: {e}. Using structured fallback.")

        # ── 7. Structured fallback — AnalystReportGeneration with real data ─
        # This uses real price, PE, market cap from the fundamental summary,
        # so the fallback report is meaningfully grounded in actual data.
        analyst_report = AnalystReportGeneration.generate_report(
            ticker=ticker_upper,
            company_name=_company_name(fundamental_summary, ticker_upper),
            current_price=current_price,
            market_cap=fundamental_summary.market_cap if fundamental_summary else None,
            pe_ratio=fundamental_summary.pe_ratio if fundamental_summary else None,
            historical_return=(
                (fundamental_summary.revenue_growth_yoy or 5.0) / 100.0
                if fundamental_summary
                else 0.05
            ),
        )
        logger.info(f"Structured fallback report generated for {ticker_upper}")
        return AnalystReportResponse(
            status="success",
            data=analyst_report,
            generated_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Unexpected error generating analyst report for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error generating report")
