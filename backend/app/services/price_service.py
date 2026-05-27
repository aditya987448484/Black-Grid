"""
Real-time price service with yfinance primary, Alpha Vantage fallback, and mock last resort.
Uses an in-process TTL cache (15 minutes) to avoid hammering external APIs.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# ── Ticker aliases ────────────────────────────────────────────────────────────

TICKER_ALIASES: dict[str, str] = {
    "TSMC":      "TSM",
    "ALIBABA":   "BABA",
    "GOOGLE":    "GOOGL",
    "ALPHABET":  "GOOGL",
    "FACEBOOK":  "META",
    "BERKSHIRE": "BRK-B",
    "BRK":       "BRK-B",
    "SAMSUNG":   "SSNLF",
    "TOYOTA":    "TM",
}

# ── In-process TTL cache ──────────────────────────────────────────────────────

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_TTL = 900  # 15 minutes


def _cache_get(ticker: str) -> dict[str, Any] | None:
    entry = _CACHE.get(ticker)
    if entry and (time.time() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(ticker: str, data: dict[str, Any]) -> None:
    _CACHE[ticker] = (time.time(), data)


# ── yfinance (sync — run in thread pool) ─────────────────────────────────────

def _fetch_yfinance_sync(symbol: str) -> dict[str, Any]:
    import yfinance as yf  # imported lazily so startup still works if missing

    info = yf.Ticker(symbol).fast_info
    price = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None)
    if not price:
        raise ValueError(f"yfinance returned no price for {symbol}")

    prev_close = getattr(info, "previous_close", None) or price
    change = price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    return {
        "symbol":         symbol,
        "price":          round(float(price), 2),
        "change":         round(float(change), 2),
        "change_percent": round(float(change_pct), 4),
        "source":         "yfinance",
    }


# ── Alpha Vantage fallback (async) ────────────────────────────────────────────

async def _fetch_alpha_vantage(symbol: str, api_key: str) -> dict[str, Any]:
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            data = await resp.json()

    gq = data.get("Global Quote", {})
    price_str = gq.get("05. price", "")
    if not price_str:
        raise ValueError(f"Alpha Vantage returned no price for {symbol}")

    price      = float(price_str)
    change     = float(gq.get("09. change", 0) or 0)
    change_pct = float((gq.get("10. change percent", "0%") or "0%").rstrip("%"))

    return {
        "symbol":         symbol,
        "price":          round(price, 2),
        "change":         round(change, 2),
        "change_percent": round(change_pct, 4),
        "source":         "alpha_vantage",
    }


# ── Mock fallback ─────────────────────────────────────────────────────────────

_MOCK_PRICES: dict[str, tuple[float, float]] = {
    "AAPL":  (207.83,  1.24),
    "MSFT":  (453.72,  2.85),
    "NVDA":  (138.85,  3.10),
    "GOOGL": (175.93, -0.42),
    "AMZN":  (226.34,  1.76),
    "META":  (646.78,  4.21),
    "TSLA":  (352.56, -2.14),
    "TSM":   (183.42,  1.07),
    "BABA":  (97.65,  -0.88),
    "SPY":   (584.12,  0.68),
    "QQQ":   (503.77,  1.02),
    "IWM":   (218.34, -0.31),
    "VIX":   (13.82,  -5.20),
    "BRK-B": (462.10,  0.55),
    "TM":    (175.55,  0.22),
    "SSNLF": (52.30,  -1.10),
}


def _mock_price(symbol: str) -> dict[str, Any]:
    price, change = _MOCK_PRICES.get(symbol, (100.0, 0.0))
    change_pct = (change / (price - change) * 100) if (price - change) else 0.0
    return {
        "symbol":         symbol,
        "price":          round(price, 2),
        "change":         round(change, 2),
        "change_percent": round(change_pct, 4),
        "source":         "mock",
    }


# ── Public API ────────────────────────────────────────────────────────────────

async def get_price(ticker: str) -> dict[str, Any]:
    """
    Return price data for a single ticker.
    Resolution order: alias → cache → yfinance → alpha_vantage → mock.
    """
    symbol = TICKER_ALIASES.get(ticker.upper(), ticker.upper())

    # Cache hit
    cached = _cache_get(symbol)
    if cached:
        logger.debug(f"Cache hit for {symbol}")
        return cached

    # yfinance (runs in thread pool to avoid blocking the event loop)
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch_yfinance_sync, symbol)
        _cache_set(symbol, data)
        logger.info(f"yfinance price for {symbol}: {data['price']}")
        return data
    except Exception as exc:
        logger.warning(f"yfinance failed for {symbol}: {exc}")

    # Alpha Vantage fallback
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if settings.alpha_vantage_key:
            data = await _fetch_alpha_vantage(symbol, settings.alpha_vantage_key)
            _cache_set(symbol, data)
            logger.info(f"Alpha Vantage price for {symbol}: {data['price']}")
            return data
    except Exception as exc:
        logger.warning(f"Alpha Vantage failed for {symbol}: {exc}")

    # Mock fallback
    logger.info(f"Using mock price for {symbol}")
    data = _mock_price(symbol)
    _cache_set(symbol, data)
    return data


async def get_prices_bulk(tickers: list[str]) -> list[dict[str, Any]]:
    """
    Fetch prices for multiple tickers concurrently.
    Errors per ticker are caught and replaced with mock data.
    """
    results = await asyncio.gather(
        *[get_price(t) for t in tickers],
        return_exceptions=True,
    )
    output: list[dict[str, Any]] = []
    for ticker, result in zip(tickers, results):
        if isinstance(result, Exception):
            logger.warning(f"get_price failed for {ticker}, using mock: {result}")
            output.append(_mock_price(TICKER_ALIASES.get(ticker.upper(), ticker.upper())))
        else:
            output.append(result)
    return output
