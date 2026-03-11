"""
BlackGrid indicator library — 100 technical indicator primitives.

Modules:
    technical    – core pandas-based indicator functions (original 13+)
    registry     – INDICATOR_CATALOG with metadata for all 100 indicators
    calculations – vectorised computation for every indicator + condition engine
"""

from app.indicators.technical import (      # noqa: F401
    sma,
    ema,
    rsi,
    macd,
    atr,
    bollinger_bands,
    obv,
    rolling_volatility,
    stochastic,
    cci,
    williams_r,
    mfi,
    adx,
    compute_all_indicators,
    compute_indicators,
)

from app.indicators.registry import (       # noqa: F401
    INDICATOR_CATALOG,
    CATEGORIES,
    get_indicator_meta,
    list_by_category,
    search_indicators,
)

from app.indicators.calculations import (   # noqa: F401
    compute_indicator,
)
