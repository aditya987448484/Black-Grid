"""Market universe service — loads, ranks, indexes, and caches company listings."""

from __future__ import annotations

import asyncio
import time as _time
from typing import Optional
import httpx
from app.core.config import ALPHA_VANTAGE_API_KEY, FINNHUB_API_KEY

# ── In-memory stores ─────────────────────────────────────────────────────────
_universe: list[dict] = []
_by_symbol: dict[str, dict] = {}
_universe_loaded_at: float = 0
UNIVERSE_TTL = 3600 * 6

# Raised from 5000 to 8000 so all real Nasdaq/NYSE listings fit.
TARGET_SIZE = 8000


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
        "HOOD", "SOFI", "AFRM", "RIVN", "LCID", "IONQ", "SMCI", "ARM", "BIRK", "RKLB",
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

    # Fetch from multiple exchanges to include popular international tickers
    exchanges_to_fetch = ["US"]  # Primary: US. Add "L" (London), "T" (Tokyo) if needed.
    all_raw: list[dict] = []

    for exchange in exchanges_to_fetch:
        url = "https://finnhub.io/api/v1/stock/symbol"
        params = {"exchange": exchange, "token": FINNHUB_API_KEY}
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                resp = await client.get(url, params=params)
                data = resp.json()
            if not isinstance(data, list):
                continue
            for item in data:
                sym = item.get("symbol", "")
                if not sym or len(sym) > 7:  # Allow slightly longer for international
                    continue
                # Skip warrants, units, rights
                desc = (item.get("description") or "").upper()
                if any(x in desc for x in ["WARRANT", "UNIT", "RIGHT", "WHEN ISSUED"]):
                    continue
                # Allow dots for BRK.B etc, but skip symbols with plus or asterisk
                if any(x in sym for x in ["+", "*"]):
                    continue
                all_raw.append({
                    "symbol": sym,
                    "name": item.get("description", sym),
                    "exchange": item.get("mic", exchange),
                    "sector": None,
                    "industry": None,
                    "country": exchange,
                    "assetType": item.get("type", "Common Stock"),
                    "currency": item.get("currency", "USD"),
                })
        except Exception as e:
            print(f"[universe:fh] Error fetching exchange {exchange}: {e}")

    if not all_raw:
        return []

    # Deduplicate by symbol (US version wins)
    seen: dict[str, dict] = {}
    for c in all_raw:
        sym = c["symbol"]
        if sym not in seen or c["country"] == "US":
            seen[sym] = c
    raw = list(seen.values())

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

    # Always include all tickers listed on real exchanges (XNAS, XNYS, XASE, ARCX, BATS)
    real_exchanges = {"XNAS", "XNYS", "XASE", "ARCX", "BATS"}
    exchange_must_include = {c["symbol"] for c in raw if c.get("exchange") in real_exchanges}
    rest_exchange = [c for c in rest if c["symbol"] in exchange_must_include]
    rest_other = [c for c in rest if c["symbol"] not in exchange_must_include]
    companies = priority_list + rest_exchange + rest_other
    # Keep at least all real-exchange listings even if above TARGET_SIZE
    cap = max(TARGET_SIZE, len(priority_list) + len(rest_exchange))
    companies = companies[:cap]
    print(f"[universe:fh] Loaded {len(raw)} raw → kept {len(companies)} (priority={len(priority_list)}, exchange={len(rest_exchange)}, other={len(rest_other[:cap])})")
    return companies


def _seed_fallback() -> list[dict]:
    """Fallback universe — 500+ important US tickers across all sectors."""
    tickers = [
        # ── Mega-cap tech ────────────────────────────────────────────────
        ("AAPL", "Apple Inc.", "XNAS", "Technology"), ("MSFT", "Microsoft Corp.", "XNAS", "Technology"),
        ("GOOGL", "Alphabet Inc.", "XNAS", "Technology"), ("GOOG", "Alphabet Inc. Class C", "XNAS", "Technology"),
        ("AMZN", "Amazon.com Inc.", "XNAS", "Consumer Cyclical"), ("NVDA", "NVIDIA Corp.", "XNAS", "Technology"),
        ("META", "Meta Platforms Inc.", "XNAS", "Technology"), ("TSLA", "Tesla Inc.", "XNAS", "Consumer Cyclical"),
        ("BRK.B", "Berkshire Hathaway", "XNYS", "Financials"), ("AVGO", "Broadcom Inc.", "XNAS", "Technology"),
        ("TSM", "Taiwan Semiconductor ADR", "XNYS", "Technology"), ("ORCL", "Oracle Corp.", "XNYS", "Technology"),
        ("ADBE", "Adobe Inc.", "XNAS", "Technology"), ("CRM", "Salesforce Inc.", "XNYS", "Technology"),
        ("AMD", "Advanced Micro Devices", "XNAS", "Technology"), ("INTC", "Intel Corp.", "XNAS", "Technology"),
        ("QCOM", "Qualcomm Inc.", "XNAS", "Technology"), ("TXN", "Texas Instruments", "XNAS", "Technology"),
        ("NOW", "ServiceNow Inc.", "XNYS", "Technology"), ("INTU", "Intuit Inc.", "XNAS", "Technology"),
        ("ISRG", "Intuitive Surgical", "XNAS", "Healthcare"), ("ASML", "ASML Holding NV", "XNAS", "Technology"),
        ("AMAT", "Applied Materials", "XNAS", "Technology"), ("LRCX", "Lam Research", "XNAS", "Technology"),
        ("KLAC", "KLA Corp.", "XNAS", "Technology"), ("MU", "Micron Technology", "XNAS", "Technology"),
        ("SNPS", "Synopsys Inc.", "XNAS", "Technology"), ("CDNS", "Cadence Design Systems", "XNAS", "Technology"),
        ("MRVL", "Marvell Technology", "XNAS", "Technology"), ("NXPI", "NXP Semiconductors", "XNAS", "Technology"),
        ("ADI", "Analog Devices", "XNAS", "Technology"), ("CSCO", "Cisco Systems Inc.", "XNAS", "Technology"),
        ("ACN", "Accenture plc", "XNYS", "Technology"), ("IBM", "IBM Corp.", "XNYS", "Technology"),
        ("SAP", "SAP SE ADR", "XNYS", "Technology"),
        # ── High-growth / popular tech ───────────────────────────────────
        ("PLTR", "Palantir Technologies", "XNYS", "Technology"), ("CRWD", "CrowdStrike Holdings", "XNAS", "Technology"),
        ("DDOG", "Datadog Inc.", "XNAS", "Technology"), ("NET", "Cloudflare Inc.", "XNYS", "Technology"),
        ("ZS", "Zscaler Inc.", "XNAS", "Technology"), ("PANW", "Palo Alto Networks", "XNAS", "Technology"),
        ("SNOW", "Snowflake Inc.", "XNYS", "Technology"), ("SHOP", "Shopify Inc.", "XNYS", "Technology"),
        ("SQ", "Block Inc.", "XNYS", "Technology"), ("COIN", "Coinbase Global", "XNAS", "Financials"),
        ("UBER", "Uber Technologies Inc.", "XNYS", "Technology"), ("LYFT", "Lyft Inc.", "XNAS", "Technology"),
        ("ABNB", "Airbnb Inc.", "XNAS", "Consumer Cyclical"), ("DASH", "DoorDash Inc.", "XNAS", "Technology"),
        ("RBLX", "Roblox Corp.", "XNYS", "Technology"), ("U", "Unity Software", "XNYS", "Technology"),
        ("TWLO", "Twilio Inc.", "XNYS", "Technology"), ("MDB", "MongoDB Inc.", "XNAS", "Technology"),
        ("HUBS", "HubSpot Inc.", "XNYS", "Technology"), ("TEAM", "Atlassian Corp.", "XNAS", "Technology"),
        ("HOOD", "Robinhood Markets", "XNAS", "Financials"), ("SOFI", "SoFi Technologies", "XNAS", "Financials"),
        ("AFRM", "Affirm Holdings", "XNAS", "Financials"), ("RIVN", "Rivian Automotive", "XNAS", "Consumer Cyclical"),
        ("LCID", "Lucid Group", "XNAS", "Consumer Cyclical"), ("IONQ", "IonQ Inc.", "XNYS", "Technology"),
        ("SMCI", "Super Micro Computer", "XNAS", "Technology"), ("ARM", "Arm Holdings ADR", "XNAS", "Technology"),
        ("PINS", "Pinterest Inc.", "XNYS", "Technology"), ("SNAP", "Snap Inc.", "XNYS", "Technology"),
        ("TTD", "The Trade Desk", "XNAS", "Technology"), ("ZI", "ZoomInfo Technologies", "XNAS", "Technology"),
        ("OKTA", "Okta Inc.", "XNAS", "Technology"), ("BILL", "BILL Holdings", "XNYS", "Technology"),
        ("DOCN", "DigitalOcean Holdings", "XNYS", "Technology"), ("CFLT", "Confluent Inc.", "XNAS", "Technology"),
        ("PATH", "UiPath Inc.", "XNYS", "Technology"), ("GTLB", "GitLab Inc.", "XNAS", "Technology"),
        ("S", "SentinelOne Inc.", "XNYS", "Technology"), ("ESTC", "Elastic NV", "XNYS", "Technology"),
        # ── Financials ───────────────────────────────────────────────────
        ("JPM", "JPMorgan Chase & Co.", "XNYS", "Financials"), ("V", "Visa Inc.", "XNYS", "Financials"),
        ("MA", "Mastercard Inc.", "XNYS", "Financials"), ("BAC", "Bank of America Corp.", "XNYS", "Financials"),
        ("WFC", "Wells Fargo & Co.", "XNYS", "Financials"), ("GS", "Goldman Sachs Group", "XNYS", "Financials"),
        ("MS", "Morgan Stanley", "XNYS", "Financials"), ("BLK", "BlackRock Inc.", "XNYS", "Financials"),
        ("SCHW", "Charles Schwab Corp.", "XNYS", "Financials"), ("AXP", "American Express Co.", "XNYS", "Financials"),
        ("C", "Citigroup Inc.", "XNYS", "Financials"), ("USB", "U.S. Bancorp", "XNYS", "Financials"),
        ("PNC", "PNC Financial Services", "XNYS", "Financials"), ("TFC", "Truist Financial", "XNYS", "Financials"),
        ("CME", "CME Group Inc.", "XNAS", "Financials"), ("ICE", "Intercontinental Exchange", "XNYS", "Financials"),
        ("PYPL", "PayPal Holdings Inc.", "XNAS", "Financials"), ("FIS", "Fidelity National Info", "XNYS", "Financials"),
        ("FISV", "Fiserv Inc.", "XNYS", "Financials"), ("SYF", "Synchrony Financial", "XNYS", "Financials"),
        ("SPGI", "S&P Global Inc.", "XNYS", "Financials"), ("MCO", "Moody's Corp.", "XNYS", "Financials"),
        ("MMC", "Marsh & McLennan", "XNYS", "Financials"), ("AIG", "American Intl Group", "XNYS", "Financials"),
        ("MET", "MetLife Inc.", "XNYS", "Financials"), ("PRU", "Prudential Financial", "XNYS", "Financials"),
        ("AFL", "Aflac Inc.", "XNYS", "Financials"), ("ALL", "Allstate Corp.", "XNYS", "Financials"),
        ("COF", "Capital One Financial", "XNYS", "Financials"), ("DFS", "Discover Financial", "XNYS", "Financials"),
        # ── Healthcare ───────────────────────────────────────────────────
        ("UNH", "UnitedHealth Group", "XNYS", "Healthcare"), ("JNJ", "Johnson & Johnson", "XNYS", "Healthcare"),
        ("LLY", "Eli Lilly & Co.", "XNYS", "Healthcare"), ("PFE", "Pfizer Inc.", "XNYS", "Healthcare"),
        ("MRK", "Merck & Co. Inc.", "XNYS", "Healthcare"), ("ABT", "Abbott Laboratories", "XNYS", "Healthcare"),
        ("TMO", "Thermo Fisher Scientific", "XNYS", "Healthcare"), ("ABBV", "AbbVie Inc.", "XNYS", "Healthcare"),
        ("DHR", "Danaher Corp.", "XNYS", "Healthcare"), ("BMY", "Bristol-Myers Squibb", "XNYS", "Healthcare"),
        ("AMGN", "Amgen Inc.", "XNAS", "Healthcare"), ("GILD", "Gilead Sciences", "XNAS", "Healthcare"),
        ("VRTX", "Vertex Pharmaceuticals", "XNAS", "Healthcare"), ("REGN", "Regeneron Pharmaceuticals", "XNAS", "Healthcare"),
        ("ZTS", "Zoetis Inc.", "XNYS", "Healthcare"), ("SYK", "Stryker Corp.", "XNYS", "Healthcare"),
        ("BDX", "Becton Dickinson", "XNYS", "Healthcare"), ("MDT", "Medtronic plc", "XNYS", "Healthcare"),
        ("EW", "Edwards Lifesciences", "XNYS", "Healthcare"), ("DXCM", "DexCom Inc.", "XNAS", "Healthcare"),
        ("CVS", "CVS Health Corp.", "XNYS", "Healthcare"), ("CI", "Cigna Group", "XNYS", "Healthcare"),
        ("HUM", "Humana Inc.", "XNYS", "Healthcare"), ("MRNA", "Moderna Inc.", "XNAS", "Healthcare"),
        ("BIIB", "Biogen Inc.", "XNAS", "Healthcare"), ("ILMN", "Illumina Inc.", "XNAS", "Healthcare"),
        ("A", "Agilent Technologies", "XNYS", "Healthcare"), ("IQV", "IQVIA Holdings", "XNYS", "Healthcare"),
        # ── Consumer / retail ────────────────────────────────────────────
        ("WMT", "Walmart Inc.", "XNYS", "Consumer Defensive"), ("PG", "Procter & Gamble", "XNYS", "Consumer Defensive"),
        ("COST", "Costco Wholesale", "XNAS", "Consumer Defensive"), ("HD", "Home Depot Inc.", "XNYS", "Consumer Cyclical"),
        ("LOW", "Lowe's Companies", "XNYS", "Consumer Cyclical"), ("NKE", "Nike Inc.", "XNYS", "Consumer Cyclical"),
        ("MCD", "McDonald's Corp.", "XNYS", "Consumer Cyclical"), ("SBUX", "Starbucks Corp.", "XNAS", "Consumer Cyclical"),
        ("TGT", "Target Corp.", "XNYS", "Consumer Defensive"), ("TJX", "TJX Companies", "XNYS", "Consumer Cyclical"),
        ("NFLX", "Netflix Inc.", "XNAS", "Communication Services"), ("DIS", "Walt Disney Co.", "XNYS", "Communication Services"),
        ("CMCSA", "Comcast Corp.", "XNAS", "Communication Services"), ("BKNG", "Booking Holdings", "XNAS", "Consumer Cyclical"),
        ("MAR", "Marriott International", "XNAS", "Consumer Cyclical"), ("HLT", "Hilton Worldwide", "XNYS", "Consumer Cyclical"),
        ("YUM", "Yum! Brands", "XNYS", "Consumer Cyclical"), ("CMG", "Chipotle Mexican Grill", "XNYS", "Consumer Cyclical"),
        ("DPZ", "Domino's Pizza", "XNYS", "Consumer Cyclical"), ("EL", "Estee Lauder", "XNYS", "Consumer Defensive"),
        ("GME", "GameStop Corp.", "XNYS", "Consumer Cyclical"), ("AMC", "AMC Entertainment", "XNYS", "Communication Services"),
        ("CHWY", "Chewy Inc.", "XNYS", "Consumer Cyclical"), ("PTON", "Peloton Interactive", "XNAS", "Consumer Cyclical"),
        ("W", "Wayfair Inc.", "XNYS", "Consumer Cyclical"), ("ETSY", "Etsy Inc.", "XNAS", "Consumer Cyclical"),
        ("ROKU", "Roku Inc.", "XNAS", "Communication Services"), ("KO", "Coca-Cola Co.", "XNYS", "Consumer Defensive"),
        ("PEP", "PepsiCo Inc.", "XNAS", "Consumer Defensive"), ("PM", "Philip Morris Intl", "XNYS", "Consumer Defensive"),
        ("MO", "Altria Group", "XNYS", "Consumer Defensive"), ("CL", "Colgate-Palmolive", "XNYS", "Consumer Defensive"),
        ("KMB", "Kimberly-Clark", "XNYS", "Consumer Defensive"), ("MDLZ", "Mondelez Intl", "XNAS", "Consumer Defensive"),
        ("KHC", "Kraft Heinz Co.", "XNAS", "Consumer Defensive"), ("GIS", "General Mills", "XNYS", "Consumer Defensive"),
        ("SYY", "Sysco Corp.", "XNYS", "Consumer Defensive"), ("HSY", "Hershey Co.", "XNYS", "Consumer Defensive"),
        ("LULU", "Lululemon Athletica", "XNAS", "Consumer Cyclical"), ("DECK", "Deckers Outdoor", "XNYS", "Consumer Cyclical"),
        ("ROST", "Ross Stores", "XNAS", "Consumer Cyclical"), ("DLTR", "Dollar Tree", "XNAS", "Consumer Defensive"),
        ("DG", "Dollar General", "XNYS", "Consumer Defensive"), ("F", "Ford Motor Co.", "XNYS", "Consumer Cyclical"),
        ("GM", "General Motors Co.", "XNYS", "Consumer Cyclical"), ("WYNN", "Wynn Resorts", "XNAS", "Consumer Cyclical"),
        ("LVS", "Las Vegas Sands", "XNYS", "Consumer Cyclical"), ("MGM", "MGM Resorts Intl", "XNYS", "Consumer Cyclical"),
        # ── Industrials ──────────────────────────────────────────────────
        ("BA", "Boeing Co.", "XNYS", "Industrials"), ("GE", "GE Aerospace", "XNYS", "Industrials"),
        ("HON", "Honeywell Intl", "XNAS", "Industrials"), ("CAT", "Caterpillar Inc.", "XNYS", "Industrials"),
        ("DE", "Deere & Co.", "XNYS", "Industrials"), ("RTX", "RTX Corp.", "XNYS", "Industrials"),
        ("LMT", "Lockheed Martin", "XNYS", "Industrials"), ("NOC", "Northrop Grumman", "XNYS", "Industrials"),
        ("GD", "General Dynamics", "XNYS", "Industrials"), ("UPS", "United Parcel Service", "XNYS", "Industrials"),
        ("UNP", "Union Pacific Corp.", "XNYS", "Industrials"), ("CSX", "CSX Corp.", "XNAS", "Industrials"),
        ("FDX", "FedEx Corp.", "XNYS", "Industrials"), ("WM", "Waste Management", "XNYS", "Industrials"),
        ("RSG", "Republic Services", "XNYS", "Industrials"), ("EMR", "Emerson Electric", "XNYS", "Industrials"),
        ("ITW", "Illinois Tool Works", "XNYS", "Industrials"), ("ETN", "Eaton Corp.", "XNYS", "Industrials"),
        ("PH", "Parker-Hannifin", "XNYS", "Industrials"), ("ROK", "Rockwell Automation", "XNYS", "Industrials"),
        ("MMM", "3M Company", "XNYS", "Industrials"), ("DAL", "Delta Air Lines", "XNYS", "Industrials"),
        ("UAL", "United Airlines Holdings", "XNAS", "Industrials"), ("AAL", "American Airlines", "XNAS", "Industrials"),
        ("LUV", "Southwest Airlines", "XNYS", "Industrials"), ("CTAS", "Cintas Corp.", "XNAS", "Industrials"),
        ("CARR", "Carrier Global", "XNYS", "Industrials"), ("OTIS", "Otis Worldwide", "XNYS", "Industrials"),
        ("JCI", "Johnson Controls", "XNYS", "Industrials"), ("TT", "Trane Technologies", "XNYS", "Industrials"),
        # ── Energy ───────────────────────────────────────────────────────
        ("XOM", "Exxon Mobil Corp.", "XNYS", "Energy"), ("CVX", "Chevron Corp.", "XNYS", "Energy"),
        ("COP", "ConocoPhillips", "XNYS", "Energy"), ("SLB", "Schlumberger Ltd.", "XNYS", "Energy"),
        ("EOG", "EOG Resources", "XNYS", "Energy"), ("PXD", "Pioneer Natural Resources", "XNYS", "Energy"),
        ("MPC", "Marathon Petroleum", "XNYS", "Energy"), ("PSX", "Phillips 66", "XNYS", "Energy"),
        ("VLO", "Valero Energy", "XNYS", "Energy"), ("OXY", "Occidental Petroleum", "XNYS", "Energy"),
        ("HAL", "Halliburton Co.", "XNYS", "Energy"), ("DVN", "Devon Energy", "XNYS", "Energy"),
        ("FANG", "Diamondback Energy", "XNAS", "Energy"), ("HES", "Hess Corp.", "XNYS", "Energy"),
        ("BKR", "Baker Hughes", "XNAS", "Energy"), ("WMB", "Williams Companies", "XNYS", "Energy"),
        ("KMI", "Kinder Morgan", "XNYS", "Energy"), ("OKE", "ONEOK Inc.", "XNYS", "Energy"),
        ("ENPH", "Enphase Energy", "XNAS", "Energy"), ("SEDG", "SolarEdge Technologies", "XNAS", "Energy"),
        ("FSLR", "First Solar Inc.", "XNAS", "Energy"), ("NEE", "NextEra Energy", "XNYS", "Utilities"),
        # ── Materials / REITs ────────────────────────────────────────────
        ("LIN", "Linde plc", "XNAS", "Materials"), ("APD", "Air Products", "XNYS", "Materials"),
        ("SHW", "Sherwin-Williams", "XNYS", "Materials"), ("ECL", "Ecolab Inc.", "XNYS", "Materials"),
        ("FCX", "Freeport-McMoRan", "XNYS", "Materials"), ("NEM", "Newmont Corp.", "XNYS", "Materials"),
        ("AMT", "American Tower Corp.", "XNYS", "Real Estate"), ("PLD", "Prologis Inc.", "XNYS", "Real Estate"),
        ("CCI", "Crown Castle Intl", "XNYS", "Real Estate"), ("EQIX", "Equinix Inc.", "XNAS", "Real Estate"),
        ("O", "Realty Income Corp.", "XNYS", "Real Estate"), ("SPG", "Simon Property Group", "XNYS", "Real Estate"),
        ("PSA", "Public Storage", "XNYS", "Real Estate"), ("DLR", "Digital Realty Trust", "XNYS", "Real Estate"),
        ("WELL", "Welltower Inc.", "XNYS", "Real Estate"), ("AVB", "AvalonBay Communities", "XNYS", "Real Estate"),
        ("DOW", "Dow Inc.", "XNYS", "Materials"), ("DD", "DuPont de Nemours", "XNYS", "Materials"),
        ("NUE", "Nucor Corp.", "XNYS", "Materials"), ("CLF", "Cleveland-Cliffs", "XNYS", "Materials"),
        # ── Communication ────────────────────────────────────────────────
        ("T", "AT&T Inc.", "XNYS", "Communication Services"), ("VZ", "Verizon Communications", "XNYS", "Communication Services"),
        ("TMUS", "T-Mobile US Inc.", "XNAS", "Communication Services"), ("CHTR", "Charter Communications", "XNAS", "Communication Services"),
        ("EA", "Electronic Arts", "XNAS", "Communication Services"), ("ATVI", "Activision Blizzard", "XNAS", "Communication Services"),
        ("TTWO", "Take-Two Interactive", "XNAS", "Communication Services"), ("WBD", "Warner Bros Discovery", "XNAS", "Communication Services"),
        ("PARA", "Paramount Global", "XNAS", "Communication Services"), ("MTCH", "Match Group", "XNAS", "Communication Services"),
        # ── Utilities ────────────────────────────────────────────────────
        ("DUK", "Duke Energy Corp.", "XNYS", "Utilities"), ("SO", "Southern Co.", "XNYS", "Utilities"),
        ("D", "Dominion Energy", "XNYS", "Utilities"), ("AEP", "American Electric Power", "XNAS", "Utilities"),
        ("EXC", "Exelon Corp.", "XNAS", "Utilities"), ("SRE", "Sempra", "XNYS", "Utilities"),
        ("ES", "Eversource Energy", "XNYS", "Utilities"), ("ED", "Consolidated Edison", "XNYS", "Utilities"),
        ("XEL", "Xcel Energy", "XNAS", "Utilities"), ("WEC", "WEC Energy Group", "XNYS", "Utilities"),
        # ── ETFs ─────────────────────────────────────────────────────────
        ("SPY", "SPDR S&P 500 ETF", "XASE", "ETF"), ("QQQ", "Invesco QQQ Trust", "XNAS", "ETF"),
        ("IWM", "iShares Russell 2000", "XASE", "ETF"), ("DIA", "SPDR Dow Jones ETF", "XASE", "ETF"),
        ("GLD", "SPDR Gold Shares", "XASE", "ETF"), ("TLT", "iShares 20+ Year Treasury", "XNAS", "ETF"),
        ("XLK", "Technology Select Sector", "XASE", "ETF"), ("XLF", "Financial Select Sector", "XASE", "ETF"),
        ("XLE", "Energy Select Sector", "XASE", "ETF"), ("XLV", "Health Care Select Sector", "XASE", "ETF"),
        ("VTI", "Vanguard Total Stock Market", "XASE", "ETF"), ("VOO", "Vanguard S&P 500", "XASE", "ETF"),
        ("ARKK", "ARK Innovation ETF", "XASE", "ETF"), ("SOXX", "iShares Semiconductor", "XNAS", "ETF"),
        ("XBI", "SPDR Biotech ETF", "XASE", "ETF"), ("EEM", "iShares MSCI Emerging Markets", "XASE", "ETF"),
        ("HYG", "iShares High Yield Corporate Bond", "XASE", "ETF"), ("LQD", "iShares Investment Grade Corp Bond", "XASE", "ETF"),
        ("SLV", "iShares Silver Trust", "XASE", "ETF"), ("USO", "United States Oil Fund", "XASE", "ETF"),
    ]
    return [
        {"symbol": t[0], "name": t[1], "exchange": t[2], "sector": t[3],
         "industry": None, "country": "US", "assetType": "Stock" if t[3] != "ETF" else "ETF", "currency": "USD"}
        for t in tickers
    ]


async def _load_av_listings() -> list[dict]:
    """Alpha Vantage LISTING_STATUS — returns all active US-listed tickers as CSV."""
    if not ALPHA_VANTAGE_API_KEY:
        return []
    url = "https://www.alphavantage.co/query"
    params = {"function": "LISTING_STATUS", "state": "active", "apikey": ALPHA_VANTAGE_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
        text = resp.text.strip()
        # AV may return JSON error instead of CSV
        if text.startswith("{"):
            print(f"[universe:av] Rate limited or error: {text[:120]}")
            return []
        lines = text.split("\n")
        if len(lines) < 2:
            return []
        results = []
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) < 3:
                continue
            symbol = parts[0].strip()
            name = parts[1].strip()
            exchange = parts[2].strip()
            asset_type = parts[3].strip() if len(parts) > 3 else "Stock"
            if not symbol or len(symbol) > 6:
                continue
            if any(x in symbol for x in ["-", "+", " "]):
                continue
            results.append({
                "symbol": symbol,
                "name": name,
                "exchange": exchange,
                "sector": None,
                "industry": None,
                "country": "US",
                "assetType": asset_type,
                "currency": "USD",
            })
        print(f"[universe:av] Loaded {len(results)} active listings")
        return results
    except Exception as e:
        print(f"[universe:av] Error: {e}")
        return []


async def get_universe() -> list[dict]:
    global _universe, _by_symbol, _universe_loaded_at
    if _universe and (_time.time() - _universe_loaded_at) < UNIVERSE_TTL:
        return _universe

    # Load from both sources in parallel
    fh_companies, av_companies = await asyncio.gather(
        _load_finnhub_symbols(),
        _load_av_listings(),
    )

    if fh_companies or av_companies:
        # Merge: AV first (gap-fill), then Finnhub wins on shared symbols (richer metadata)
        merged: dict[str, dict] = {}
        for c in av_companies:
            merged[c["symbol"]] = c
        for c in fh_companies:
            merged[c["symbol"]] = c  # Finnhub overwrites AV for same symbol

        # Apply priority ordering on the merged set
        priority = _priority_tickers()
        priority_set = set(priority)
        all_companies = list(merged.values())
        priority_list = sorted(
            [c for c in all_companies if c["symbol"] in priority_set],
            key=lambda c: priority.index(c["symbol"]) if c["symbol"] in priority_set else 9999,
        )
        rest = [c for c in all_companies if c["symbol"] not in priority_set]
        type_rank = {"Common Stock": 0, "Stock": 0, "ADR": 1, "ETP": 2, "ETF": 2}
        rest.sort(key=lambda c: (type_rank.get(c.get("assetType", ""), 3), c["symbol"]))

        _universe = priority_list + rest
        print(f"[universe] Merged universe: {len(_universe)} companies (fh={len(fh_companies)}, av={len(av_companies)})")
    else:
        _universe = _seed_fallback()
        print("[universe] Using fallback seed universe")

    _by_symbol = {c["symbol"]: c for c in _universe}
    _universe_loaded_at = _time.time()
    return _universe


def get_company_info_from_universe(ticker: str) -> Optional[dict]:
    return _by_symbol.get(ticker.upper())


async def ensure_universe_loaded():
    """Pre-warm the universe on startup or first request."""
    if not _universe:
        await get_universe()
