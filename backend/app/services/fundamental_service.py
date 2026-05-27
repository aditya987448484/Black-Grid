"""
Fundamental Service
Combines SEC EDGAR financials and FRED macro context into clean, structured
summaries for use in analyst reports, asset detail pages, and AI inference.

Public API:
  FundamentalService.get_fundamental_summary(ticker, price?)
  FundamentalService.get_valuation_summary(ticker, price, shares?)
  FundamentalService.get_growth_summary(ticker)
  FundamentalService.get_balance_sheet_risk(ticker)
  FundamentalService.get_macro_context()
"""

import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

from app.services.sec_data import SECDataService, FinancialsSummary, MockSECDataProvider
from app.services.macro_data import MacroDataService, MacroContext, MockMacroDataProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ValuationSummary:
    ticker: str
    price: Optional[float]
    market_cap: Optional[float]          # USD
    enterprise_value: Optional[float]    # USD (market cap + liabilities – cash proxy)
    pe_ratio: Optional[float]            # Price / EPS
    ps_ratio: Optional[float]            # Market cap / Revenue
    pb_ratio: Optional[float]            # Market cap / Equity
    price_to_ocf: Optional[float]        # Market cap / Operating Cash Flow
    data_source: str


@dataclass
class GrowthSummary:
    ticker: str
    revenue_growth_yoy: Optional[float]    # %
    net_income_growth_yoy: Optional[float] # %
    ocf_to_net_income: Optional[float]     # Cash conversion quality ratio
    growth_signal: str                     # "accelerating" | "decelerating" | "stable" | "unknown"
    signal_note: str
    data_source: str


@dataclass
class BalanceSheetRisk:
    ticker: str
    total_assets: Optional[float]
    total_liabilities: Optional[float]
    equity: Optional[float]
    debt_to_assets: Optional[float]       # 0–1
    debt_to_equity: Optional[float]
    equity_ratio: Optional[float]         # 1 - debt_to_assets
    risk_level: str                        # "low" | "medium" | "high" | "unknown"
    risk_note: str
    data_source: str


@dataclass
class FundamentalSummary:
    ticker: str
    company_name: str
    cik: str

    # Financials snapshot
    revenue: Optional[float]
    net_income: Optional[float]
    eps_diluted: Optional[float]
    operating_cash_flow: Optional[float]
    fiscal_year_end: Optional[str]

    # Growth
    revenue_growth_yoy: Optional[float]
    net_income_growth_yoy: Optional[float]
    growth_signal: str

    # Balance sheet
    total_assets: Optional[float]
    total_liabilities: Optional[float]
    equity: Optional[float]
    debt_to_assets: Optional[float]
    risk_level: str

    # Valuation (price-dependent; None if price not provided)
    price: Optional[float]
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    ps_ratio: Optional[float]
    pb_ratio: Optional[float]

    # Macro context
    treasury_10y: Optional[float]
    fed_funds_rate: Optional[float]
    cpi_yoy: Optional[float]
    unemployment_rate: Optional[float]
    yield_curve_spread: Optional[float]

    fundamentals_source: str   # "edgar" | "mock"
    macro_source: str          # "fred" | "mock"
    fetched_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _growth_signal(rev_growth: Optional[float], ni_growth: Optional[float]) -> tuple[str, str]:
    """Classify combined growth signal and return (signal, note)."""
    if rev_growth is None and ni_growth is None:
        return "unknown", "Insufficient data to assess growth trend."

    # Use whichever metric is available
    primary = rev_growth if rev_growth is not None else ni_growth
    secondary = ni_growth

    if primary >= 20:
        signal = "accelerating"
        note = f"Revenue growing strongly at {rev_growth:.1f}% YoY." if rev_growth else "Strong earnings growth."
    elif primary >= 5:
        signal = "stable"
        note = f"Steady growth — revenue +{rev_growth:.1f}% YoY." if rev_growth else "Steady earnings growth."
    elif primary >= 0:
        signal = "stable"
        note = "Modest positive growth — company holding ground."
    else:
        signal = "decelerating"
        note = f"Revenue declined {rev_growth:.1f}% YoY." if rev_growth else "Earnings contracted YoY."

    # Upgrade/downgrade if net income diverges sharply
    if secondary is not None and rev_growth is not None:
        if secondary > rev_growth + 15:
            note += " Margins expanding — profitability outpacing revenue."
        elif secondary < rev_growth - 15:
            note += " Margins compressing — profitability lagging revenue."

    return signal, note


def _risk_level(debt_to_assets: Optional[float]) -> tuple[str, str]:
    """Classify balance-sheet risk and return (level, note)."""
    if debt_to_assets is None:
        return "unknown", "Balance sheet data unavailable."
    if debt_to_assets < 0.35:
        return "low", f"Conservative leverage — liabilities are {debt_to_assets * 100:.0f}% of assets."
    if debt_to_assets < 0.60:
        return "medium", f"Moderate leverage — liabilities are {debt_to_assets * 100:.0f}% of assets."
    return "high", f"High leverage — liabilities are {debt_to_assets * 100:.0f}% of assets; watch debt service."


def _market_cap(price: Optional[float], shares: Optional[float]) -> Optional[float]:
    if price is None or shares is None:
        return None
    return round(price * shares, 0)


def _safe_ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(numerator / denominator, 2)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class FundamentalService:
    """
    Aggregates SEC EDGAR fundamentals and FRED macro context into clean
    summaries for downstream use (reports, UIs, AI context).

    Provider selection follows settings:
      - SECDataService uses EDGARProvider when live, MockSECDataProvider otherwise
      - MacroDataService uses FREDProvider when fred_api_key is set, mock otherwise
    """

    def __init__(
        self,
        sec_service: Optional[SECDataService] = None,
        macro_service: Optional[MacroDataService] = None,
    ):
        settings = get_settings()

        if sec_service:
            self.sec = sec_service
        else:
            # Default: use live EDGAR; set mock_fundamentals flag in env to override
            self.sec = SECDataService()

        if macro_service:
            self.macro = macro_service
        else:
            self.macro = MacroDataService()

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    async def _get_financials(self, ticker: str) -> FinancialsSummary:
        try:
            return await self.sec.get_financials_summary(ticker)
        except Exception as e:
            logger.warning(f"EDGAR lookup failed for {ticker} — falling back to mock: {e}")
            mock_provider = MockSECDataProvider()
            return await mock_provider.get_financials_summary(ticker)

    async def _get_macro(self) -> MacroContext:
        try:
            return await self.macro.get_macro_context()
        except Exception as e:
            logger.warning(f"Macro context fetch failed — using mock: {e}")
            mock_provider = MockMacroDataProvider()
            return await mock_provider.get_macro_context()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_valuation_summary(
        self, ticker: str, price: Optional[float] = None
    ) -> ValuationSummary:
        """
        Compute valuation multiples. If price is None, market-cap-based ratios
        will be None but the summary is still returned with what is available.
        """
        fin = await self._get_financials(ticker)
        mkt_cap = _market_cap(price, fin.shares_outstanding)
        ev = (
            round(mkt_cap + (fin.total_liabilities or 0) - (fin.operating_cash_flow or 0), 0)
            if mkt_cap is not None
            else None
        )
        return ValuationSummary(
            ticker=ticker.upper(),
            price=price,
            market_cap=mkt_cap,
            enterprise_value=ev,
            pe_ratio=_safe_ratio(price, fin.eps_diluted) if price else None,
            ps_ratio=_safe_ratio(mkt_cap, fin.revenue),
            pb_ratio=_safe_ratio(mkt_cap, fin.equity),
            price_to_ocf=_safe_ratio(mkt_cap, fin.operating_cash_flow),
            data_source=fin.data_source,
        )

    async def get_growth_summary(self, ticker: str) -> GrowthSummary:
        """Classify and describe company revenue / earnings growth."""
        fin = await self._get_financials(ticker)
        signal, note = _growth_signal(fin.revenue_growth_yoy, fin.net_income_growth_yoy)
        ocf_to_ni = _safe_ratio(fin.operating_cash_flow, fin.net_income)
        return GrowthSummary(
            ticker=ticker.upper(),
            revenue_growth_yoy=fin.revenue_growth_yoy,
            net_income_growth_yoy=fin.net_income_growth_yoy,
            ocf_to_net_income=ocf_to_ni,
            growth_signal=signal,
            signal_note=note,
            data_source=fin.data_source,
        )

    async def get_balance_sheet_risk(self, ticker: str) -> BalanceSheetRisk:
        """Classify balance-sheet leverage risk."""
        fin = await self._get_financials(ticker)
        risk_level, risk_note = _risk_level(fin.debt_to_assets)
        equity_ratio = round(1 - fin.debt_to_assets, 4) if fin.debt_to_assets is not None else None
        debt_to_equity = _safe_ratio(fin.total_liabilities, fin.equity)
        return BalanceSheetRisk(
            ticker=ticker.upper(),
            total_assets=fin.total_assets,
            total_liabilities=fin.total_liabilities,
            equity=fin.equity,
            debt_to_assets=fin.debt_to_assets,
            debt_to_equity=debt_to_equity,
            equity_ratio=equity_ratio,
            risk_level=risk_level,
            risk_note=risk_note,
            data_source=fin.data_source,
        )

    async def get_macro_context(self) -> MacroContext:
        """Return current macroeconomic context (live or mock)."""
        return await self._get_macro()

    async def get_fundamental_summary(
        self, ticker: str, price: Optional[float] = None
    ) -> FundamentalSummary:
        """
        Full combined summary: financials + valuation + growth + balance-sheet risk + macro.
        Safe to call even when individual data sources fail.
        """
        fin = await self._get_financials(ticker)
        macro = await self._get_macro()

        # Valuation multiples
        mkt_cap = _market_cap(price, fin.shares_outstanding)
        pe_ratio = _safe_ratio(price, fin.eps_diluted) if price else None
        ps_ratio = _safe_ratio(mkt_cap, fin.revenue)
        pb_ratio = _safe_ratio(mkt_cap, fin.equity)

        # Growth & risk classification
        growth_signal, _ = _growth_signal(fin.revenue_growth_yoy, fin.net_income_growth_yoy)
        risk_level, _ = _risk_level(fin.debt_to_assets)

        return FundamentalSummary(
            ticker=ticker.upper(),
            company_name=fin.company_name,
            cik=fin.cik,
            revenue=fin.revenue,
            net_income=fin.net_income,
            eps_diluted=fin.eps_diluted,
            operating_cash_flow=fin.operating_cash_flow,
            fiscal_year_end=fin.fiscal_year_end,
            revenue_growth_yoy=fin.revenue_growth_yoy,
            net_income_growth_yoy=fin.net_income_growth_yoy,
            growth_signal=growth_signal,
            total_assets=fin.total_assets,
            total_liabilities=fin.total_liabilities,
            equity=fin.equity,
            debt_to_assets=fin.debt_to_assets,
            risk_level=risk_level,
            price=price,
            market_cap=mkt_cap,
            pe_ratio=pe_ratio,
            ps_ratio=ps_ratio,
            pb_ratio=pb_ratio,
            treasury_10y=macro.treasury_10y,
            fed_funds_rate=macro.fed_funds_rate,
            cpi_yoy=macro.cpi_yoy,
            unemployment_rate=macro.unemployment_rate,
            yield_curve_spread=macro.yield_curve_spread,
            fundamentals_source=fin.data_source,
            macro_source=macro.data_source,
            fetched_at=fin.fetched_at,
        )

    def fundamental_summary_to_dict(self, summary: FundamentalSummary) -> Dict[str, Any]:
        """Serialize FundamentalSummary to a plain dict for API responses."""
        return asdict(summary)

    async def close(self):
        await self.sec.close()
        await self.macro.close()
