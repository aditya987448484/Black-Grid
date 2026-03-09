"""Market universe service — loads, ranks, indexes, and caches company listings."""

from __future__ import annotations

import time as _time
from typing import Optional
import httpx
from app.core.config import ALPHA_VANTAGE_API_KEY, FINNHUB_API_KEY

# ── In-memory stores ─────────────────────────────────────────────────────────
_universe: list[dict] = []
_by_symbol: dict[str, dict] = {}
_universe_loaded_at: float = 0
UNIVERSE_TTL = 3600 * 6

# Top ~5000 tickers by importance. Finnhub returns ~29K symbols including
# OTC, penny stocks, etc. We rank by type (Common Stock first) and symbol
# length (shorter = more prominent), then cap at 5000.
TARGET_SIZE = 5000


def _priority_tickers() -> list[str]:
    """Top ~250 most important US-listed tickers including popular retail names."""
    return [
        # Mega-cap tech
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO", "TSM",
        "ORCL", "ADBE", "CRM", "AMD", "INTC", "QCOM", "TXN", "NOW", "INTU", "ISRG",
        "ASML", "AMAT", "LRCX", "KLAC", "MU", "SNPS", "CDNS", "MRVL", "NXPI", "ADI",
        # High-growth / popular tech
        "PLTR", "CRWD", "DDOG", "NET", "ZS", "PANW", "SNOW", "SHOP", "SQ", "COIN",
        "UBER", "LYFT", "ABNB", "DASH", "RBLX", "U", "TWLO", "MDB", "HUBS", "TEAM",
        "HOOD", "SOFI", "AFRM", "RIVN", "LCID", "IONQ", "SMCI", "ARM", "BIRK",
        # Financials
        "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP",
        "C", "USB", "PNC", "TFC", "CME", "ICE", "PYPL", "FIS", "FISV", "SYF",
        # Healthcare
        "UNH", "JNJ", "LLY", "PFE", "MRK", "ABT", "TMO", "ABBV", "DHR", "BMY",
        "AMGN", "GILD", "VRTX", "REGN", "ZTS", "SYK", "BDX", "MDT", "EW", "DXCM",
        # Consumer / retail-popular
        "WMT", "PG", "COST", "HD", "LOW", "NKE", "MCD", "SBUX", "TGT", "TJX",
        "NFLX", "DIS", "CMCSA", "BKNG", "MAR", "HLT", "YUM", "CMG", "DPZ", "EL",
        "GME", "AMC", "BBBY", "CHWY", "PTON", "W", "ETSY", "ROKU",
        # Industrials
        "BA", "GE", "HON", "CAT", "DE", "RTX", "LMT", "NOC", "GD", "UPS",
        "UNP", "CSX", "FDX", "WM", "RSG", "EMR", "ITW", "ETN", "PH", "ROK",
        # Energy
        "XOM", "CVX", "COP", "SLB", "EOG", "PXD", "MPC", "PSX", "VLO", "OXY",
        # Materials / REITs
        "LIN", "APD", "SHW", "ECL", "FCX", "NEM", "AMT", "PLD", "CCI", "EQIX",
        # Communication
        "T", "VZ", "TMUS", "CHTR",
        # ETFs
        "SPY", "QQQ", "IWM", "DIA", "GLD", "TLT", "XLK", "XLF", "XLE", "XLV",
        # Berkshire
        "BRK.B",
    ]


async def _load_finnhub_symbols() -> list[dict]:
    if not FINNHUB_API_KEY:
        return []
    url = "https://finnhub.io/api/v1/stock/symbol"
    params = {"exchange": "US", "token": FINNHUB_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
        if not isinstance(data, list):
            return []
        raw = []
        for item in data:
            sym = item.get("symbol", "")
            if not sym or len(sym) > 5:
                continue
            # Skip warrants, units, rights
            desc = (item.get("description") or "").upper()
            if any(x in desc for x in ["WARRANT", "UNIT", "RIGHT", "WHEN ISSUED"]):
                continue
            # Allow dots for BRK.B etc, but skip symbols with dashes or plus
            if any(x in sym for x in ["-", "+"]):
                continue
            raw.append({
                "symbol": sym,
                "name": item.get("description", sym),
                "exchange": item.get("mic", "US"),
                "sector": None,
                "industry": None,
                "country": "US",
                "assetType": item.get("type", "Common Stock"),
                "currency": item.get("currency", "USD"),
            })

        # Build a priority set of well-known tickers that must be included
        priority = _priority_tickers()
        priority_set = set(priority)

        # Partition: priority tickers first (in order), then the rest
        priority_list = [c for c in raw if c["symbol"] in priority_set]
        priority_list.sort(key=lambda c: priority.index(c["symbol"]) if c["symbol"] in priority else 9999)

        rest = [c for c in raw if c["symbol"] not in priority_set]
        # Sort rest: Common Stock/ADR first, then by symbol alpha
        type_rank = {"Common Stock": 0, "ADR": 1, "ETP": 2, "ETF": 2}
        rest.sort(key=lambda c: (type_rank.get(c["assetType"], 3), c["symbol"]))

        companies = priority_list + rest
        companies = companies[:TARGET_SIZE]
        print(f"[universe:fh] Loaded {len(raw)} raw → ranked top {len(companies)} (with {len(priority_list)} priority)")
        return companies
    except Exception as e:
        print(f"[universe:fh] Error: {e}")
        return []


def _seed_fallback() -> list[dict]:
    """Fallback universe — top 100 most important US tickers."""
    tickers = [
        ("AAPL", "Apple Inc.", "XNAS", "Technology"), ("MSFT", "Microsoft Corp.", "XNAS", "Technology"),
        ("GOOGL", "Alphabet Inc.", "XNAS", "Technology"), ("AMZN", "Amazon.com Inc.", "XNAS", "Consumer Cyclical"),
        ("NVDA", "NVIDIA Corp.", "XNAS", "Technology"), ("META", "Meta Platforms Inc.", "XNAS", "Technology"),
        ("TSLA", "Tesla Inc.", "XNAS", "Consumer Cyclical"), ("BRK.B", "Berkshire Hathaway", "XNYS", "Financials"),
        ("JPM", "JPMorgan Chase & Co.", "XNYS", "Financials"), ("V", "Visa Inc.", "XNYS", "Financials"),
        ("JNJ", "Johnson & Johnson", "XNYS", "Healthcare"), ("UNH", "UnitedHealth Group", "XNYS", "Healthcare"),
        ("XOM", "Exxon Mobil Corp.", "XNYS", "Energy"), ("WMT", "Walmart Inc.", "XNYS", "Consumer Defensive"),
        ("PG", "Procter & Gamble", "XNYS", "Consumer Defensive"), ("MA", "Mastercard Inc.", "XNYS", "Financials"),
        ("HD", "Home Depot Inc.", "XNYS", "Consumer Cyclical"), ("DIS", "Walt Disney Co.", "XNYS", "Communication Services"),
        ("NFLX", "Netflix Inc.", "XNAS", "Communication Services"), ("AMD", "Advanced Micro Devices", "XNAS", "Technology"),
        ("CRM", "Salesforce Inc.", "XNYS", "Technology"), ("INTC", "Intel Corp.", "XNAS", "Technology"),
        ("BA", "Boeing Co.", "XNYS", "Industrials"), ("GS", "Goldman Sachs", "XNYS", "Financials"),
        ("COST", "Costco Wholesale", "XNAS", "Consumer Defensive"), ("AVGO", "Broadcom Inc.", "XNAS", "Technology"),
        ("ASML", "ASML Holding NV", "XNAS", "Technology"), ("UBER", "Uber Technologies Inc.", "XNYS", "Technology"),
        ("PLTR", "Palantir Technologies", "XNYS", "Technology"), ("ADBE", "Adobe Inc.", "XNAS", "Technology"),
        ("TSM", "Taiwan Semiconductor ADR", "XNYS", "Technology"), ("ORCL", "Oracle Corp.", "XNYS", "Technology"),
        ("CSCO", "Cisco Systems Inc.", "XNAS", "Technology"), ("ACN", "Accenture plc", "XNYS", "Technology"),
        ("ABT", "Abbott Laboratories", "XNYS", "Healthcare"), ("MRK", "Merck & Co. Inc.", "XNYS", "Healthcare"),
        ("PFE", "Pfizer Inc.", "XNYS", "Healthcare"), ("LLY", "Eli Lilly & Co.", "XNYS", "Healthcare"),
        ("NKE", "Nike Inc.", "XNYS", "Consumer Cyclical"), ("MCD", "McDonald's Corp.", "XNYS", "Consumer Cyclical"),
        ("SBUX", "Starbucks Corp.", "XNAS", "Consumer Cyclical"), ("TXN", "Texas Instruments", "XNAS", "Technology"),
        ("QCOM", "Qualcomm Inc.", "XNAS", "Technology"), ("NOW", "ServiceNow Inc.", "XNYS", "Technology"),
        ("INTU", "Intuit Inc.", "XNAS", "Technology"), ("ISRG", "Intuitive Surgical", "XNAS", "Healthcare"),
        ("GE", "GE Aerospace", "XNYS", "Industrials"), ("CAT", "Caterpillar Inc.", "XNYS", "Industrials"),
        ("DE", "Deere & Co.", "XNYS", "Industrials"), ("RTX", "RTX Corp.", "XNYS", "Industrials"),
        ("LMT", "Lockheed Martin", "XNYS", "Industrials"), ("LOW", "Lowe's Companies", "XNYS", "Consumer Cyclical"),
        ("SPY", "SPDR S&P 500 ETF", "XASE", "ETF"), ("QQQ", "Invesco QQQ Trust", "XNAS", "ETF"),
        ("IWM", "iShares Russell 2000", "XASE", "ETF"), ("DIA", "SPDR Dow Jones ETF", "XASE", "ETF"),
        ("GLD", "SPDR Gold Shares", "XASE", "ETF"), ("TLT", "iShares 20+ Year Treasury", "XNAS", "ETF"),
        ("SHOP", "Shopify Inc.", "XNYS", "Technology"), ("SQ", "Block Inc.", "XNYS", "Technology"),
        ("PYPL", "PayPal Holdings", "XNAS", "Financials"), ("COIN", "Coinbase Global", "XNAS", "Financials"),
        ("SNOW", "Snowflake Inc.", "XNYS", "Technology"), ("CRWD", "CrowdStrike Holdings", "XNAS", "Technology"),
        ("ZS", "Zscaler Inc.", "XNAS", "Technology"), ("DDOG", "Datadog Inc.", "XNAS", "Technology"),
        ("NET", "Cloudflare Inc.", "XNYS", "Technology"), ("PANW", "Palo Alto Networks", "XNAS", "Technology"),
    ]
    return [
        {"symbol": t[0], "name": t[1], "exchange": t[2], "sector": t[3],
         "industry": None, "country": "US", "assetType": "Stock", "currency": "USD"}
        for t in tickers
    ]


async def get_universe() -> list[dict]:
    global _universe, _by_symbol, _universe_loaded_at
    if _universe and (_time.time() - _universe_loaded_at) < UNIVERSE_TTL:
        return _universe

    companies = await _load_finnhub_symbols()
    if not companies:
        companies = _seed_fallback()
        print("[universe] Using fallback seed universe")

    _universe = companies
    _by_symbol = {c["symbol"]: c for c in companies}
    _universe_loaded_at = _time.time()
    return _universe


def get_company_info_from_universe(ticker: str) -> Optional[dict]:
    return _by_symbol.get(ticker.upper())


async def ensure_universe_loaded():
    """Pre-warm the universe on startup or first request."""
    if not _universe:
        await get_universe()
