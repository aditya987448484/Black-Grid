from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

# Market data providers
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
MARKET_DATA_PROVIDER = os.getenv("MARKET_DATA_PROVIDER", "alpha_vantage")

# Macro / fundamentals
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "BlackGrid research@blackgrid.dev")

# News / sentiment
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_PROVIDER = os.getenv("NEWS_PROVIDER", "newsapi")

# Tiingo — institutional-grade OHLCV + fundamentals
TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "")

# EODHD — End of Day Historical Data (global markets, fundamentals)
EODHD_API_KEY = os.getenv("EODHD_API_KEY", "")

# Reasoning / AI
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
REASONING_PROVIDER = os.getenv("REASONING_PROVIDER", "anthropic")

# Flight tracking
OPENSKY_USERNAME = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASSWORD = os.getenv("OPENSKY_PASSWORD", "")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "")
FLIGHT_DATA_PROVIDER = os.getenv("FLIGHT_DATA_PROVIDER", "aviationstack")

# Vessel / ship tracking
AISSTREAM_API_KEY = os.getenv("AISSTREAM_API_KEY", "")
MARINETRAFFIC_API_KEY = os.getenv("MARINETRAFFIC_API_KEY", "")
SHIP_DATA_PROVIDER = os.getenv("SHIP_DATA_PROVIDER", "aisstream")

# Geopolitical
GDELT_API_BASE_URL = os.getenv("GDELT_API_BASE_URL", "https://api.gdeltproject.org/api/v2")

# Map (frontend-only but stored for reference)
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "")


def log_config_status():
    """Log which API keys are configured at startup for diagnostics."""
    keys = {
        "TIINGO_API_KEY": TIINGO_API_KEY,
        "EODHD_API_KEY": EODHD_API_KEY,
        "ALPHA_VANTAGE_API_KEY": ALPHA_VANTAGE_API_KEY,
        "TWELVE_DATA_API_KEY": TWELVE_DATA_API_KEY,
        "FINNHUB_API_KEY": FINNHUB_API_KEY,
        "FRED_API_KEY": FRED_API_KEY,
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "GROQ_API_KEY": GROQ_API_KEY,
        "NEWS_API_KEY": NEWS_API_KEY,
        "AVIATIONSTACK_API_KEY": AVIATIONSTACK_API_KEY,
        "AISSTREAM_API_KEY": AISSTREAM_API_KEY,
    }
    configured = [k for k, v in keys.items() if v]
    missing = [k for k, v in keys.items() if not v]
    print(f"[config] API keys configured: {', '.join(configured) if configured else 'NONE'}")
    if missing:
        print(f"[config] API keys missing: {', '.join(missing)}")
    print(f"[config] Market provider: {MARKET_DATA_PROVIDER} | Reasoning: {REASONING_PROVIDER}")
