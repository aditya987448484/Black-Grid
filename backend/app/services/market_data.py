"""Market data service — Alpha Vantage + Finnhub + Twelve Data with retry and cache."""

from __future__ import annotations

from typing import Optional
import asyncio
import time as _time
import httpx
import pandas as pd
from app.core.config import ALPHA_VANTAGE_API_KEY, FINNHUB_API_KEY, TWELVE_DATA_API_KEY

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


# ── Retry helper ─────────────────────────────────────────────────────────────

async def _retry_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 3,
    backoff: float = 1.0,
    **kwargs,
) -> httpx.Response:
    """Execute an HTTP request with exponential backoff retries."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = await getattr(client, method)(url, **kwargs)
            # Retry on rate limit (429) or server error (5xx)
            if resp.status_code == 429:
                wait = backoff * (2 ** attempt)
                print(f"[market_data] Rate limited (429), retrying in {wait:.1f}s...")
                await asyncio.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = backoff * (2 ** attempt)
                print(f"[market_data] Server error ({resp.status_code}), retrying in {wait:.1f}s...")
                await asyncio.sleep(wait)
                continue
            return resp
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_exc = e
            if attempt < max_retries - 1:
                wait = backoff * (2 ** attempt)
                print(f"[market_data] Request failed ({type(e).__name__}), retrying in {wait:.1f}s...")
                await asyncio.sleep(wait)
    raise last_exc or httpx.TimeoutException("All retries exhausted")


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
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await _retry_request(client, "get", url, params=params, max_retries=2)
            data = resp.json()

        # Detect rate limiting via response body
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
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await _retry_request(client, "get", url, params=params, max_retries=2)
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
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await _retry_request(client, "get", url, params=params, max_retries=2)
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
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await _retry_request(client, "get", url, params=params, max_retries=2)
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


# ── Twelve Data (new provider) ───────────────────────────────────────────────

async def _twelve_data_history(ticker: str, outputsize: int = 100) -> Optional[pd.DataFrame]:
    if not TWELVE_DATA_API_KEY:
        return None

    cache_key = f"td_hist_{ticker}_{outputsize}"
    cached = _get_cached(cache_key)
    if cached is not None:
        print(f"[market_data:td] Cache hit for {ticker} history")
        return cached

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": ticker,
        "interval": "1day",
        "outputsize": outputsize,
        "apikey": TWELVE_DATA_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await _retry_request(client, "get", url, params=params, max_retries=2)
            data = resp.json()

        if data.get("status") == "error":
            print(f"[market_data:td] Error for {ticker}: {data.get('message', '')[:120]}")
            return None

        values = data.get("values", [])
        if not values:
            return None

        rows = []
        for v in values:
            rows.append({
                "date": v["datetime"],
                "open": float(v["open"]),
                "high": float(v["high"]),
                "low": float(v["low"]),
                "close": float(v["close"]),
                "volume": int(v.get("volume", 0)),
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        print(f"[market_data:td] Got {len(df)} rows for {ticker}")
        _set_cached(cache_key, df)
        return df
    except Exception as e:
        print(f"[market_data:td] Error {ticker}: {e}")
        return None


async def _twelve_data_quote(ticker: str) -> Optional[dict]:
    if not TWELVE_DATA_API_KEY:
        return None

    cache_key = f"td_quote_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    url = "https://api.twelvedata.com/quote"
    params = {"symbol": ticker, "apikey": TWELVE_DATA_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await _retry_request(client, "get", url, params=params, max_retries=2)
            data = resp.json()

        if data.get("status") == "error" or not data.get("close"):
            return None

        price = float(data["close"])
        prev_close = float(data.get("previous_close", price))
        change = round(price - prev_close, 2)
        change_pct = round((change / prev_close * 100) if prev_close else 0, 2)
        result = {
            "price": price,
            "change": change,
            "changePercent": change_pct,
            "volume": int(data.get("volume", 0)),
        }
        _set_cached(cache_key, result)
        return result
    except Exception as e:
        print(f"[market_data:td] Quote error {ticker}: {e}")
        return None


# ── yfinance (free, unlimited, covers all Nasdaq/NYSE) ───────────────────────

async def _yfinance_history(ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """yfinance fallback — free, covers virtually all US-listed stocks."""
    cache_key = f"yf_hist_{ticker}_{period}"
    cached = _get_cached(cache_key)
    if cached is not None:
        print(f"[market_data:yf] Cache hit for {ticker}")
        return cached

    try:
        import yfinance as yf
        import asyncio

        def _fetch():
            t = yf.Ticker(ticker)
            return t.history(period=period, auto_adjust=True, actions=False)

        loop = asyncio.get_event_loop()
        hist = await loop.run_in_executor(None, _fetch)

        if hist is None or len(hist) == 0:
            print(f"[market_data:yf] No data for {ticker}")
            return None

        rows = []
        for date, row in hist.iterrows():
            rows.append({
                "date": str(date.date()),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        print(f"[market_data:yf] Got {len(df)} rows for {ticker}")
        _set_cached(cache_key, df)
        return df
    except ImportError:
        print("[market_data:yf] yfinance not installed — skipping")
        return None
    except Exception as e:
        print(f"[market_data:yf] Error {ticker}: {e}")
        return None


async def _yfinance_history_range(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """yfinance with exact start/end date range."""
    cache_key = f"yf_range_{ticker}_{start}_{end}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    try:
        import yfinance as yf
        import asyncio

        def _fetch():
            t = yf.Ticker(ticker)
            return t.history(start=start, end=end, auto_adjust=True, actions=False)

        loop = asyncio.get_event_loop()
        hist = await loop.run_in_executor(None, _fetch)
        if hist is None or len(hist) == 0:
            return None
        rows = []
        for date, row in hist.iterrows():
            rows.append({
                "date": str(date.date()),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        print(f"[market_data:yf] {len(df)} rows for {ticker} {start}\u2192{end}")
        _set_cached(cache_key, df)
        return df
    except ImportError:
        return None
    except Exception as e:
        print(f"[market_data:yf] Range error {ticker}: {e}")
        return None


def _derive_quote_from_df(df: pd.DataFrame) -> dict:
    """Derive a quote dict from the last two rows of a price history DataFrame."""
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    change = float(last["close"] - prev["close"])
    pct = round(change / float(prev["close"]) * 100, 2) if prev["close"] else 0
    return {
        "price": float(last["close"]),
        "change": round(change, 2),
        "changePercent": pct,
        "volume": int(last["volume"]),
    }


# ── Public API ───────────────────────────────────────────────────────────────

async def fetch_price_history(ticker: str, outputsize: str = "full") -> Optional[pd.DataFrame]:
    """Fetch OHLCV history.
    Priority: yfinance (free, max history) → AV → Finnhub → Twelve Data.
    yfinance is first because it provides the most data (up to 20 years) for free.
    """
    # 1. yfinance — primary, free, 5-20 years of data
    period = "2y" if outputsize == "compact" else "max"
    df = await _yfinance_history(ticker, period=period)
    if df is not None and len(df) > 50:
        return df

    # 2. Alpha Vantage fallback
    df = await _av_price_history(ticker, outputsize)
    if df is not None and len(df) > 0:
        return df

    # 3. Finnhub fallback
    days = 100 if outputsize == "compact" else 730
    df = await _finnhub_candles(ticker, days)
    if df is not None and len(df) > 0:
        return df

    # 4. Twelve Data fallback
    sz = 100 if outputsize == "compact" else 365
    df = await _twelve_data_history(ticker, outputsize=sz)
    if df is not None and len(df) > 0:
        return df

    print(f"[market_data] All providers failed for {ticker} history.")
    return None


async def fetch_price_history_range(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data for a specific date range.
    yfinance supports exact ranges natively; fallback providers are sliced by date.
    """
    from datetime import date as _date
    if not start_date:
        start_date = "2000-01-01"
    if not end_date:
        end_date = str(_date.today())

    # 1. yfinance — native date range support
    df = await _yfinance_history_range(ticker, start_date, end_date)
    if df is not None and len(df) > 50:
        return df

    # 2-4. Fallback providers: fetch full history then slice
    df = await fetch_price_history(ticker, outputsize="full")
    if df is not None and len(df) > 0:
        df = df[(df["date"] >= pd.Timestamp(start_date)) &
                (df["date"] <= pd.Timestamp(end_date))].reset_index(drop=True)
        if len(df) > 50:
            return df

    print(f"[market_data] All providers failed for {ticker} {start_date}\u2192{end_date}")
    return None


async def fetch_quote(ticker: str) -> Optional[dict]:
    """Fetch latest quote. Tries AV → Finnhub → Twelve Data."""
    quote = await _av_quote(ticker)
    if quote:
        return quote

    quote = await _finnhub_quote(ticker)
    if quote:
        return quote

    quote = await _twelve_data_quote(ticker)
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
        quote = _derive_quote_from_df(df)
        print(f"[market_data] Derived quote for {ticker} from history: ${quote['price']}")

    return quote, df
