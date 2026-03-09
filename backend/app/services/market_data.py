"""Market data service — Alpha Vantage + Finnhub with in-memory cache."""

from __future__ import annotations

from typing import Optional
import time as _time
import httpx
import pandas as pd
from app.core.config import ALPHA_VANTAGE_API_KEY, FINNHUB_API_KEY

# ── Simple TTL cache to avoid rate-limit issues ─────────────────────────────
_cache: dict[str, tuple[float, object]] = {}
CACHE_TTL = 300  # 5 minutes — reduces provider load across 5000-company universe


def _get_cached(key: str):
    entry = _cache.get(key)
    if entry and (_time.time() - entry[0]) < CACHE_TTL:
        return entry[1]
    return None


def _set_cached(key: str, value):
    _cache[key] = (_time.time(), value)


# ── Alpha Vantage ────────────────────────────────────────────────────────────

async def _av_price_history(ticker: str, outputsize: str = "full") -> Optional[pd.DataFrame]:
    if not ALPHA_VANTAGE_API_KEY:
        return None

    cache_key = f"av_hist_{ticker}_{outputsize}"
    cached = _get_cached(cache_key)
    if cached is not None:
        print(f"[market_data:av] Cache hit for {ticker} history")
        return cached

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": outputsize,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        # Detect rate limiting
        if "Note" in data or "Information" in data:
            msg = data.get("Note", data.get("Information", ""))
            print(f"[market_data:av] Rate limited for {ticker}: {msg[:120]}")
            return None

        ts = data.get("Time Series (Daily)")
        if not ts:
            print(f"[market_data:av] No time series for {ticker}. Keys: {list(data.keys())}")
            return None

        rows = []
        for date_str, vals in ts.items():
            rows.append({
                "date": date_str,
                "open": float(vals["1. open"]),
                "high": float(vals["2. high"]),
                "low": float(vals["3. low"]),
                "close": float(vals["4. close"]),
                "volume": int(vals["5. volume"]),
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        print(f"[market_data:av] Got {len(df)} rows for {ticker}")
        _set_cached(cache_key, df)
        return df
    except Exception as e:
        print(f"[market_data:av] Error {ticker}: {e}")
        return None


async def _av_quote(ticker: str) -> Optional[dict]:
    if not ALPHA_VANTAGE_API_KEY:
        return None

    cache_key = f"av_quote_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    url = "https://www.alphavantage.co/query"
    params = {"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": ALPHA_VANTAGE_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        if "Note" in data or "Information" in data:
            print(f"[market_data:av] Rate limited on quote for {ticker}")
            return None

        quote = data.get("Global Quote", {})
        if not quote or not quote.get("05. price"):
            return None
        result = {
            "price": float(quote["05. price"]),
            "change": float(quote.get("09. change", 0)),
            "changePercent": float(quote.get("10. change percent", "0").replace("%", "")),
            "volume": int(quote.get("06. volume", 0)),
        }
        _set_cached(cache_key, result)
        return result
    except Exception as e:
        print(f"[market_data:av] Quote error {ticker}: {e}")
        return None


# ── Finnhub ──────────────────────────────────────────────────────────────────

async def _finnhub_quote(ticker: str) -> Optional[dict]:
    if not FINNHUB_API_KEY:
        return None

    cache_key = f"fh_quote_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    url = "https://finnhub.io/api/v1/quote"
    params = {"symbol": ticker, "token": FINNHUB_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
        if not data.get("c"):
            return None
        result = {
            "price": float(data["c"]),
            "change": float(data.get("d", 0) or 0),
            "changePercent": float(data.get("dp", 0) or 0),
            "volume": 0,
        }
        _set_cached(cache_key, result)
        return result
    except Exception as e:
        print(f"[market_data:fh] Quote error {ticker}: {e}")
        return None


async def _finnhub_candles(ticker: str, days: int = 365) -> Optional[pd.DataFrame]:
    if not FINNHUB_API_KEY:
        return None

    cache_key = f"fh_candles_{ticker}_{days}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    import time
    now = int(time.time())
    start = now - days * 86400
    url = "https://finnhub.io/api/v1/stock/candle"
    params = {"symbol": ticker, "resolution": "D", "from": start, "to": now, "token": FINNHUB_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
        if data.get("s") != "ok" or not data.get("c"):
            print(f"[market_data:fh] No candle data for {ticker}. Status: {data.get('s')}")
            return None
        from datetime import datetime
        rows = []
        for i in range(len(data["c"])):
            rows.append({
                "date": datetime.utcfromtimestamp(data["t"][i]).strftime("%Y-%m-%d"),
                "open": float(data["o"][i]),
                "high": float(data["h"][i]),
                "low": float(data["l"][i]),
                "close": float(data["c"][i]),
                "volume": int(data["v"][i]),
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        print(f"[market_data:fh] Got {len(df)} candles for {ticker}")
        _set_cached(cache_key, df)
        return df
    except Exception as e:
        print(f"[market_data:fh] Candle error {ticker}: {e}")
        return None


# ── Public API ───────────────────────────────────────────────────────────────

async def fetch_price_history(ticker: str, outputsize: str = "full") -> Optional[pd.DataFrame]:
    """Fetch OHLCV history. Tries AV then Finnhub."""
    df = await _av_price_history(ticker, outputsize)
    if df is not None and len(df) > 0:
        return df

    days = 100 if outputsize == "compact" else 365
    df = await _finnhub_candles(ticker, days)
    if df is not None and len(df) > 0:
        return df

    print(f"[market_data] All providers failed for {ticker} history.")
    return None


async def fetch_quote(ticker: str) -> Optional[dict]:
    """Fetch latest quote. Tries AV then Finnhub."""
    quote = await _av_quote(ticker)
    if quote:
        return quote

    quote = await _finnhub_quote(ticker)
    if quote:
        return quote

    print(f"[market_data] All providers failed for {ticker} quote.")
    return None


async def fetch_quote_and_history(ticker: str) -> tuple[Optional[dict], Optional[pd.DataFrame]]:
    """Fetch both quote and history in one call, minimizing API hits.

    Strategy: fetch history first (compact), derive quote from last row
    if the dedicated quote call fails due to rate limiting.
    """
    # Get history (this is the most valuable call)
    df = await fetch_price_history(ticker, outputsize="compact")

    # Get quote
    quote = await fetch_quote(ticker)

    # If quote failed but history succeeded, derive quote from history
    if not quote and df is not None and len(df) > 0:
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        derived_change = float(last["close"] - prev["close"])
        derived_pct = float(derived_change / prev["close"] * 100) if prev["close"] else 0
        quote = {
            "price": float(last["close"]),
            "change": round(derived_change, 2),
            "changePercent": round(derived_pct, 2),
            "volume": int(last["volume"]),
        }
        print(f"[market_data] Derived quote for {ticker} from history: ${quote['price']}")

    return quote, df
