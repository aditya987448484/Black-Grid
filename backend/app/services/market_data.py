"""Market data service — Alpha Vantage + Finnhub + Twelve Data + Tiingo + EODHD with retry and cache."""

from __future__ import annotations

from typing import Optional
import asyncio
import time as _time
import httpx
import pandas as pd
from app.core.config import (
    ALPHA_VANTAGE_API_KEY,
    FINNHUB_API_KEY,
    TWELVE_DATA_API_KEY,
    TIINGO_API_KEY,
    EODHD_API_KEY,
)

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

async def _yfinance_history(ticker: str, period: str = "max") -> Optional[pd.DataFrame]:
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


# ── Tiingo (institutional quality, adjusted prices) ─────────────────────────

async def _tiingo_history(ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
    if not TIINGO_API_KEY:
        return None
    cache_key = f"tiingo_{ticker}_{start_date}_{end_date}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
    params = {"token": TIINGO_API_KEY}
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await _retry_request(client, "get", url, params=params, max_retries=2)
            if resp.status_code != 200:
                return None
            data = resp.json()
        if not data or not isinstance(data, list):
            return None
        rows = []
        for bar in data:
            rows.append({
                "date": bar["date"][:10],
                "open": float(bar.get("adjOpen", bar.get("open", 0))),
                "high": float(bar.get("adjHigh", bar.get("high", 0))),
                "low": float(bar.get("adjLow", bar.get("low", 0))),
                "close": float(bar.get("adjClose", bar.get("close", 0))),
                "volume": int(bar.get("adjVolume", bar.get("volume", 0))),
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        print(f"[market_data:tiingo] Got {len(df)} bars for {ticker}")
        _set_cached(cache_key, df)
        return df
    except Exception as e:
        print(f"[market_data:tiingo] Error {ticker}: {e}")
        return None


# ── EODHD (global markets, good coverage) ───────────────────────────────────

async def _eodhd_history(ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
    if not EODHD_API_KEY:
        return None
    cache_key = f"eodhd_{ticker}_{start_date}_{end_date}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    symbol = f"{ticker}.US"
    url = f"https://eodhd.com/api/eod/{symbol}"
    params = {"api_token": EODHD_API_KEY, "fmt": "json"}
    if start_date:
        params["from"] = start_date
    if end_date:
        params["to"] = end_date
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await _retry_request(client, "get", url, params=params, max_retries=2)
            if resp.status_code != 200:
                return None
            data = resp.json()
        if not data or not isinstance(data, list):
            return None
        rows = []
        for bar in data:
            rows.append({
                "date": bar["date"],
                "open": float(bar.get("open", 0)),
                "high": float(bar.get("high", 0)),
                "low": float(bar.get("low", 0)),
                "close": float(bar.get("adjusted_close", bar.get("close", 0))),
                "volume": int(bar.get("volume", 0)),
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        print(f"[market_data:eodhd] Got {len(df)} bars for {ticker}")
        _set_cached(cache_key, df)
        return df
    except Exception as e:
        print(f"[market_data:eodhd] Error {ticker}: {e}")
        return None


# ── Public API ───────────────────────────────────────────────────────────────

async def fetch_price_history(ticker: str, outputsize: str = "full") -> Optional[pd.DataFrame]:
    """Fetch OHLCV history. Tiingo -> EODHD -> yfinance -> AV -> Finnhub -> Twelve Data."""
    # 1. Tiingo (institutional quality, adjusted prices)
    df = await _tiingo_history(ticker)
    if df is not None and len(df) > 0:
        return df

    # 2. EODHD (global markets, good coverage)
    df = await _eodhd_history(ticker)
    if df is not None and len(df) > 0:
        return df

    # 3. yfinance: free, unlimited, covers all Nasdaq/NYSE
    period = "3mo" if outputsize == "compact" else "max"
    df = await _yfinance_history(ticker, period=period)
    if df is not None and len(df) > 0:
        return df

    # 4. Alpha Vantage
    df = await _av_price_history(ticker, outputsize)
    if df is not None and len(df) > 0:
        return df

    # 5. Finnhub candles
    days = 100 if outputsize == "compact" else 365
    df = await _finnhub_candles(ticker, days)
    if df is not None and len(df) > 0:
        return df

    # 6. Twelve Data
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
    """Fetch OHLCV for an explicit date range.

    Waterfall: Tiingo -> EODHD -> yfinance -> Alpha Vantage slice.
    This is the primary data fetcher for the Backtest Lab.
    """
    from datetime import date as _date
    if not start_date:
        start_date = "2010-01-01"
    if not end_date:
        end_date = str(_date.today())

    cache_key = f"range_{ticker}_{start_date}_{end_date}"
    cached = _get_cached(cache_key)
    if cached is not None:
        print(f"[market_data] Cache hit for {ticker} {start_date}->{end_date}")
        return cached

    # 1. Tiingo (institutional quality, adjusted prices)
    df = await _tiingo_history(ticker, start_date, end_date)
    if df is not None and len(df) >= 20:
        _set_cached(cache_key, df)
        return df

    # 2. EODHD (global markets, good coverage)
    df = await _eodhd_history(ticker, start_date, end_date)
    if df is not None and len(df) >= 20:
        _set_cached(cache_key, df)
        return df

    # 3. yfinance with exact date range
    try:
        import yfinance as yf
        import asyncio as _asyncio

        def _fetch_range():
            t = yf.Ticker(ticker)
            return t.history(start=start_date, end=end_date, auto_adjust=True, actions=False)

        loop = _asyncio.get_event_loop()
        hist = await loop.run_in_executor(None, _fetch_range)

        if hist is not None and len(hist) >= 20:
            rows = []
            for date_idx, row in hist.iterrows():
                rows.append({
                    "date": str(date_idx.date()),
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]),
                })
            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            print(f"[market_data:yf] {len(df)} bars for {ticker} {start_date}->{end_date}")
            _set_cached(cache_key, df)
            return df
        else:
            print(f"[market_data:yf] Empty response for {ticker} range {start_date}->{end_date}")
    except ImportError:
        print("[market_data:yf] yfinance not installed — run: pip install yfinance")
    except Exception as e:
        print(f"[market_data:yf_range] {ticker}: {e}")

    # 4. Alpha Vantage full history, then slice
    df = await _av_price_history(ticker, "full")
    if df is not None and len(df) > 0:
        mask = (df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))
        sliced = df[mask].reset_index(drop=True)
        if len(sliced) >= 20:
            print(f"[market_data:av_slice] {len(sliced)} bars for {ticker}")
            _set_cached(cache_key, sliced)
            return sliced

    print(f"[market_data] All providers failed for {ticker} {start_date}->{end_date}")
    return None


async def fetch_quote(ticker: str) -> Optional[dict]:
    """Fetch latest quote. Tiingo -> yfinance -> AV -> Finnhub -> Twelve Data."""
    # Try Tiingo first — derive quote from last 5 days of history
    df = await _tiingo_history(ticker)
    if df is not None and len(df) >= 2:
        return _derive_quote_from_df(df.tail(5).reset_index(drop=True))

    # Try yfinance — derive quote from recent history
    df = await _yfinance_history(ticker, period="5d")
    if df is not None and len(df) >= 2:
        return _derive_quote_from_df(df)

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


async def fetch_quote_and_history(ticker: str) -> tuple:
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


# ── Raw indicator snapshot for Claude context injection ──────────────────────

async def fetch_raw_indicator_snapshot(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Optional[dict]:
    """Fetch OHLCV and compute 30+ indicator values for Claude context injection."""
    df = await fetch_price_history_range(ticker, start_date, end_date)
    if df is None or len(df) < 40:
        return None

    data_source = "unknown"
    # Determine which source was used based on cache key pattern
    for prefix in ["tiingo", "eodhd", "yf", "av"]:
        ck = f"{prefix}_{ticker}"
        if any(ck in k for k in _cache.keys()):
            data_source = prefix
            break

    # Compute indicators using ta library
    snapshot = {}
    try:
        import ta as ta_lib
        import numpy as np
        df_ta = df.copy()
        df_ta = ta_lib.add_all_ta_features(df_ta, open="open", high="high", low="low", close="close", volume="volume", fillna=True)
        last = df_ta.iloc[-1]

        # Map ta column names to clean names
        indicator_map = {
            "momentum_rsi": "rsi_14",
            "trend_macd": "macd_line",
            "trend_macd_signal": "macd_signal",
            "trend_macd_diff": "macd_histogram",
            "volatility_bbh": "bb_upper",
            "volatility_bbl": "bb_lower",
            "volatility_bbm": "bb_middle",
            "volatility_bbw": "bb_width",
            "volatility_bbp": "bb_pctb",
            "volatility_atr": "atr_14",
            "trend_adx": "adx_14",
            "volume_obv": "obv",
            "momentum_stoch": "stoch_k",
            "momentum_stoch_signal": "stoch_d",
            "momentum_cci": "cci_20",
            "momentum_wr": "williams_r",
            "volume_mfi": "mfi_14",
            "trend_ema_fast": "ema_12",
            "trend_sma_fast": "sma_20",
            "trend_sma_slow": "sma_50",
            "momentum_roc": "roc_12",
            "volatility_kch": "keltner_upper",
            "volatility_kcl": "keltner_lower",
            "trend_vortex_ind_pos": "vortex_pos",
            "trend_vortex_ind_neg": "vortex_neg",
            "trend_psar_up": "psar_up",
            "trend_psar_down": "psar_down",
            "volume_cmf": "cmf",
            "volume_vwap": "vwap",
            "trend_ichimoku_a": "ichimoku_a",
            "trend_ichimoku_b": "ichimoku_b",
        }
        for ta_col, clean_name in indicator_map.items():
            if ta_col in df_ta.columns:
                val = last[ta_col]
                if isinstance(val, (int, float)) and not (val != val):  # not NaN
                    snapshot[clean_name] = round(float(val), 4)

        # Add EMA 20/50/200 manually
        from app.indicators.technical import sma, ema
        close = df["close"]
        for p in [20, 50, 200]:
            e = ema(close, p)
            s = sma(close, p)
            if len(e) > 0:
                v = float(e.iloc[-1])
                if v == v:
                    snapshot[f"ema_{p}"] = round(v, 4)
            if len(s) > 0:
                v = float(s.iloc[-1])
                if v == v:
                    snapshot[f"sma_{p}"] = round(v, 4)

        # Volatility
        from app.indicators.technical import rolling_volatility
        vol = rolling_volatility(close, 20)
        if len(vol) > 0:
            v = float(vol.iloc[-1])
            if v == v:
                snapshot["volatility_20d"] = round(v, 4)

    except Exception as e:
        print(f"[indicator_snapshot] ta compute error: {e}")
        snapshot = {}

    # Last 5 OHLCV bars
    ohlcv_rows = []
    for _, row in df.tail(5).iterrows():
        ohlcv_rows.append({
            "date": str(row["date"])[:10] if "date" in df.columns else "",
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
            "volume": int(row["volume"]),
        })

    return {
        "ticker": ticker,
        "bar_count": len(df),
        "data_source": data_source,
        "ohlcv_rows": ohlcv_rows,
        "indicator_snapshot": snapshot,
    }
