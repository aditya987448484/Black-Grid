"""
Macro Data Service
Provides macroeconomic data via FRED (Federal Reserve Economic Data)
Handles economic indicators like interest rates, inflation, unemployment, etc.
Falls back to deterministic mock values when FRED API key is not configured.
"""

import httpx
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EconomicIndicator(str, Enum):
    """Common economic indicators from FRED"""
    # Unemployment
    UNEMPLOYMENT_RATE = "UNRATE"

    # GDP
    REAL_GDP = "A191RL1Q225SBEA"
    GDP_GROWTH = "A191RG3Q086SBEA"

    # Inflation
    CPI = "CPIAUCSL"
    PCE = "PCEPILFE"

    # Interest Rates
    FED_FUNDS = "FEDFUNDS"
    TREASURY_10Y = "GS10"         # 10-Year Treasury Constant Maturity Rate
    T10Y2Y = "T10Y2Y"             # 10Y minus 2Y spread (yield curve)

    # Broader Economic
    CONSUMER_SENTIMENT = "UMCSENT"
    INDUSTRIAL_PRODUCTION = "INDPRO"
    RETAIL_SALES = "RSXFS"
    INITIAL_JOBLESS_CLAIMS = "ICNSA"
    MORTGAGE_RATE = "MORTGAGE30US"
    PPI = "PPIAUCSL"


@dataclass
class MacroContext:
    """Normalized snapshot of key macroeconomic indicators"""
    treasury_10y: Optional[float]       # % — 10-Year Treasury yield
    fed_funds_rate: Optional[float]     # % — Effective federal funds rate
    cpi_yoy: Optional[float]            # % — CPI year-over-year inflation
    unemployment_rate: Optional[float]  # % — Civilian unemployment rate
    yield_curve_spread: Optional[float] # % — 10Y minus 2Y spread (negative = inverted)
    data_source: str                    # "fred" | "mock"
    fetched_at: str


class MacroDataProvider:
    """Abstract base for macroeconomic data providers"""

    async def get_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_multiple_series(
        self,
        series_ids: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        raise NotImplementedError

    async def get_macro_context(self) -> MacroContext:
        raise NotImplementedError


class FREDProvider(MacroDataProvider):
    """
    FRED (Federal Reserve Economic Data) API integration
    https://fred.stlouisfed.org/

    Free tier: Unlimited requests
    Requires FRED_API_KEY environment variable.
    """

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.fred_api_key
        self.base_url = "https://api.stlouisfed.org/fred"
        self.client = httpx.AsyncClient(timeout=30.0)

        if not self.api_key:
            logger.warning("FRED API key not configured — macro context will use mock fallback.")

    async def get_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        units: str = "lin",
    ) -> Dict[str, Any]:
        """
        Fetch a FRED time series.

        Args:
            series_id: FRED series ID (e.g. "FEDFUNDS")
            start_date: ISO date (YYYY-MM-DD)
            end_date: ISO date (YYYY-MM-DD)
            units: Transformation — "lin" (levels), "pch" (% change), etc.
        """
        if not self.api_key:
            raise ValueError("FRED API key not configured")

        params: Dict[str, Any] = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "units": units,
        }
        if start_date:
            params["observation_start"] = start_date
        if end_date:
            params["observation_end"] = end_date

        try:
            response = await self.client.get(f"{self.base_url}/series/observations", params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("error_code"):
                raise ValueError(f"FRED error: {data.get('error_message')}")
            return data
        except Exception as e:
            logger.error(f"Error fetching FRED series {series_id}: {e}")
            raise

    async def get_multiple_series(
        self,
        series_ids: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Optional[Dict[str, Any]]] = {}
        for series_id in series_ids:
            try:
                results[series_id] = await self.get_series(series_id, start_date, end_date)
            except Exception as e:
                logger.error(f"Failed to fetch {series_id}: {e}")
                results[series_id] = None
        return results  # type: ignore[return-value]

    async def get_latest_value(self, series_id: str) -> Optional[float]:
        """Return the most recent numeric observation for a series."""
        try:
            data = await self.get_series(series_id)
            for obs in reversed(data.get("observations", [])):
                raw = obs.get("value", ".")
                if raw != ".":
                    return float(raw)
        except Exception as e:
            logger.error(f"Error getting latest value for {series_id}: {e}")
        return None

    @staticmethod
    def _compute_yoy_cpi(observations: List[Dict[str, Any]]) -> Optional[float]:
        """
        Compute YoY CPI inflation from a list of monthly observations.
        Uses the most recent month vs same month one year prior.
        Returns percentage change rounded to 2 decimal places.
        """
        if len(observations) < 13:
            return None
        try:
            # Take observations with valid values
            valid = [
                o for o in observations
                if o.get("value", ".") != "."
            ]
            if len(valid) < 13:
                return None
            current = float(valid[-1]["value"])
            prior_year = float(valid[-13]["value"])
            if prior_year == 0:
                return None
            return round((current - prior_year) / prior_year * 100, 2)
        except (ValueError, IndexError):
            return None

    async def get_macro_context(self) -> MacroContext:
        """
        Fetch key macro indicators from FRED and return a normalized MacroContext.
        Fetches the last 14 months of CPI to compute YoY change.
        """
        fetched_at = datetime.utcnow().isoformat()

        # For CPI we need 14 months of history to compute YoY
        fourteen_months_ago = (datetime.utcnow() - timedelta(days=430)).strftime("%Y-%m-%d")

        # Fetch each series; failures become None, don't abort the whole context
        treasury_10y = await self.get_latest_value(EconomicIndicator.TREASURY_10Y.value)
        fed_funds_rate = await self.get_latest_value(EconomicIndicator.FED_FUNDS.value)
        unemployment_rate = await self.get_latest_value(EconomicIndicator.UNEMPLOYMENT_RATE.value)
        yield_curve_spread = await self.get_latest_value(EconomicIndicator.T10Y2Y.value)

        # CPI — need history for YoY
        cpi_yoy: Optional[float] = None
        try:
            cpi_data = await self.get_series(
                EconomicIndicator.CPI.value,
                start_date=fourteen_months_ago,
            )
            cpi_yoy = self._compute_yoy_cpi(cpi_data.get("observations", []))
        except Exception as e:
            logger.error(f"Failed to compute CPI YoY: {e}")

        return MacroContext(
            treasury_10y=treasury_10y,
            fed_funds_rate=fed_funds_rate,
            cpi_yoy=cpi_yoy,
            unemployment_rate=unemployment_rate,
            yield_curve_spread=yield_curve_spread,
            data_source="fred",
            fetched_at=fetched_at,
        )

    async def close(self):
        await self.client.aclose()


class MacroDataService:
    """
    Service layer for macroeconomic data.
    Automatically falls back to mock when FRED API key is absent.
    """

    def __init__(self, provider: Optional[MacroDataProvider] = None):
        settings = get_settings()
        if provider:
            self.provider = provider
        elif settings.fred_api_key:
            self.provider = FREDProvider()
        else:
            logger.info("FRED API key not set — using mock macro provider")
            self.provider = MockMacroDataProvider()

    async def get_unemployment(self) -> Optional[float]:
        ctx = await self.provider.get_macro_context()
        return ctx.unemployment_rate

    async def get_inflation(self) -> Optional[float]:
        ctx = await self.provider.get_macro_context()
        return ctx.cpi_yoy

    async def get_fed_funds_rate(self) -> Optional[float]:
        ctx = await self.provider.get_macro_context()
        return ctx.fed_funds_rate

    async def get_treasury_10y(self) -> Optional[float]:
        ctx = await self.provider.get_macro_context()
        return ctx.treasury_10y

    async def get_macro_context(self) -> MacroContext:
        """Return a complete macro snapshot (live or mock, depending on config)."""
        return await self.provider.get_macro_context()

    async def get_series_history(
        self,
        indicator: EconomicIndicator,
        months: int = 12,
    ) -> Dict[str, Any]:
        """Fetch historical observations for a FRED indicator."""
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=months * 30)).strftime("%Y-%m-%d")
        return await self.provider.get_series(indicator.value, start_date=start_date, end_date=end_date)

    async def get_economic_snapshot(self) -> Dict[str, Optional[float]]:
        """Legacy helper — returns flat dict of key indicators."""
        ctx = await self.provider.get_macro_context()
        return {
            "unemployment": ctx.unemployment_rate,
            "cpi_yoy": ctx.cpi_yoy,
            "fed_funds_rate": ctx.fed_funds_rate,
            "treasury_10y": ctx.treasury_10y,
            "yield_curve_spread": ctx.yield_curve_spread,
        }

    async def close(self):
        if hasattr(self.provider, "close"):
            await self.provider.close()


# ---------------------------------------------------------------------------
# Mock implementation — deterministic, no network calls
# ---------------------------------------------------------------------------

_MOCK_MACRO = MacroContext(
    treasury_10y=4.28,
    fed_funds_rate=5.33,
    cpi_yoy=3.2,
    unemployment_rate=3.7,
    yield_curve_spread=-0.42,
    data_source="mock",
    fetched_at="",  # filled at call time
)


class MockMacroDataProvider(MacroDataProvider):
    """Deterministic mock — stable values, no network calls"""

    async def get_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "series_id": series_id,
            "units": "Percent",
            "observations": [
                {"date": "2024-02-01", "value": "3.9"},
                {"date": "2024-03-01", "value": "3.8"},
            ],
        }

    async def get_multiple_series(
        self,
        series_ids: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        return {sid: await self.get_series(sid) for sid in series_ids}

    async def get_macro_context(self) -> MacroContext:
        return MacroContext(
            treasury_10y=_MOCK_MACRO.treasury_10y,
            fed_funds_rate=_MOCK_MACRO.fed_funds_rate,
            cpi_yoy=_MOCK_MACRO.cpi_yoy,
            unemployment_rate=_MOCK_MACRO.unemployment_rate,
            yield_curve_spread=_MOCK_MACRO.yield_curve_spread,
            data_source="mock",
            fetched_at=datetime.utcnow().isoformat(),
        )
