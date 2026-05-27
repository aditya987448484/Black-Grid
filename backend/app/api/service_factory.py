"""
Service Factory and Utilities
Handles initialization of service providers with proper error handling and fallbacks
"""

import logging
from typing import Optional, TypeVar, Callable, Any
from app.core.config import get_settings
from app.services.market_data import MarketDataService, MockMarketDataProvider
from app.services.macro_data import MacroDataService, MockMacroDataProvider
from app.services.sec_data import SECDataService, MockSECDataProvider
from app.services.reasoning_provider import DeepSeekReasoningProvider, GroqReasoningProvider

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceFactory:
    """Factory for initializing services with proper configuration"""

    @staticmethod
    def get_market_data_service() -> MarketDataService:
        """
        Get market data service with configured provider.
        Falls back to mock if real provider unavailable.
        """
        settings = get_settings()
        try:
            if settings.market_data_provider == "mock" or not settings.alpha_vantage_key:
                logger.debug("Using mock market data provider")
                return MarketDataService(provider=MockMarketDataProvider())
            logger.debug(f"Using {settings.market_data_provider} market data provider")
            return MarketDataService()
        except Exception as e:
            logger.warning(f"Failed to initialize real market provider: {e}. Falling back to mock.")
            return MarketDataService(provider=MockMarketDataProvider())

    @staticmethod
    def get_macro_data_service() -> MacroDataService:
        """
        Get macro data service.
        MacroDataService auto-selects FRED or mock based on fred_api_key.
        """
        try:
            return MacroDataService()
        except Exception as e:
            logger.warning(f"Failed to initialize macro provider: {e}. Using mock.")
            return MacroDataService(provider=MockMacroDataProvider())

    @staticmethod
    def get_sec_data_service() -> SECDataService:
        """Get SEC data service (no API key required — EDGAR is public)."""
        try:
            return SECDataService()
        except Exception as e:
            logger.warning(f"Failed to initialize SEC provider: {e}. Using mock.")
            return SECDataService(provider=MockSECDataProvider())

    @staticmethod
    def get_fundamental_service():
        """
        Get FundamentalService — combines SEC EDGAR financials and FRED macro context.
        Both underlying services fall back to mock automatically when API keys are absent
        or requests fail, so this never raises.
        """
        from app.services.fundamental_service import FundamentalService
        try:
            return FundamentalService()
        except Exception as e:
            logger.warning(f"Failed to initialize FundamentalService: {e}. Using mock providers.")
            from app.services.fundamental_service import FundamentalService
            return FundamentalService(
                sec_service=SECDataService(provider=MockSECDataProvider()),
                macro_service=MacroDataService(provider=MockMacroDataProvider()),
            )

    @staticmethod
    def get_reasoning_service():
        """
        Get a reasoning service wrapper with a `.provider` attribute.

        Priority: DeepSeek → Groq → Mock
        Controlled by REASONING_PROVIDER env var (default: "deepseek").
        """
        settings = get_settings()
        from app.services.reasoning_provider import MockReasoningProvider

        class _ReasoningService:
            """Thin wrapper so route can access `.provider`."""
            def __init__(self, provider):
                self.provider = provider

        preferred = (settings.reasoning_provider or "deepseek").lower()

        # ── DeepSeek (primary) ────────────────────────────────────────────────
        if preferred == "deepseek" and settings.deepseek_api_key:
            try:
                provider = DeepSeekReasoningProvider()
                logger.debug("Using DeepSeek reasoning provider")
                return _ReasoningService(provider)
            except Exception as e:
                logger.warning(f"Failed to initialize DeepSeek provider: {e}. Trying Groq.")

        # ── Groq (fallback) ───────────────────────────────────────────────────
        if settings.groq_api_key:
            try:
                import httpx
                # GroqReasoningProvider's effective __init__ (the second one) accepts an
                # optional `provider` arg. Pass a mock so it doesn't recurse into itself.
                provider = GroqReasoningProvider(provider=MockReasoningProvider())
                # Patch the Groq-specific attributes that the first __init__ would have set.
                provider.api_key = settings.groq_api_key
                provider.base_url = "https://api.groq.com/openai/v1"
                provider.model = settings.groq_model
                provider.client = httpx.AsyncClient(timeout=60.0)
                logger.debug("Using Groq reasoning provider")
                return _ReasoningService(provider)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq provider: {e}. Using mock.")

        # ── Auto-fallback: try DeepSeek even if not "preferred" ───────────────
        if settings.deepseek_api_key:
            try:
                provider = DeepSeekReasoningProvider()
                logger.debug("Falling back to DeepSeek reasoning provider")
                return _ReasoningService(provider)
            except Exception as e:
                logger.warning(f"DeepSeek fallback failed: {e}. Using mock.")

        logger.debug("Using mock reasoning provider")
        return _ReasoningService(MockReasoningProvider())

    @staticmethod
    def get_reasoning_provider():
        """Legacy accessor — returns the provider directly (not wrapped in a service)."""
        return ServiceFactory.get_reasoning_service().provider


async def handle_service_call(
    func: Callable[..., Any],
    *args,
    **kwargs
) -> Optional[Any]:
    """
    Safe wrapper for service calls with error handling.

    Returns:
        Result from function or None if error
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Service call failed: {e}")
        return None


def log_provider_status():
    """Log current provider configuration status"""
    settings = get_settings()
    logger.info("=" * 70)
    logger.info("Data Provider Configuration")
    logger.info("=" * 70)
    logger.info(f"Market Data Provider: {settings.market_data_provider}")
    logger.info(f"Alpha Vantage Key: {'✓ Configured' if settings.alpha_vantage_key else '✗ Not configured'}")
    logger.info(f"FRED Key: {'✓ Configured' if settings.fred_api_key else '✗ Not configured'}")
    logger.info(f"Groq Key: {'✓ Configured' if settings.groq_api_key else '✗ Not configured'}")
    logger.info(f"SEC User-Agent: {settings.sec_user_agent}")
    logger.info("=" * 70)
