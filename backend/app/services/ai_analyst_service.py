"""AI Analyst service — parses user intent, fetches data, generates analysis."""

from __future__ import annotations

import re
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx
from app.core.config import ANTHROPIC_API_KEY
from app.services.company_search import search_companies
from app.services.market_data import fetch_quote_and_history
from app.services.mock_data import get_asset_info
from app.services.sec_data import fetch_company_facts
from app.services.fundamental_service import build_fundamental_summary
from app.services.macro_data import fetch_macro_indicators
from app.indicators.technical import compute_all_indicators

ANALYST_SYSTEM = (
    "You are a top-decile sell-side equity research analyst. Your writing is precise, "
    "decisive, and investment-actionable. Every sentence carries signal. You state your "
    "view clearly and defend it with evidence. You do not hedge excessively or write "
    "filler. You write for portfolio managers who have 90 seconds to decide if they care. "
    "You never fabricate data. Where data is absent you say so plainly and move on. "
    "This is a research tool, not investment advice."
)

ANALYSIS_PROMPT = """Write an institutional equity research report for {name} ({ticker}).

{data_context}

IMPORTANT INSTRUCTIONS:
- Today's date is {report_date}. Do not reference events, earnings, or data after this date as if they have already occurred. Your training data has a cutoff — if you are unsure whether something has happened yet, say so.
- The currency for this security is shown in the data above. Use the provided currency symbol ({currency_symbol}) when quoting prices, revenue, and monetary values. Never use $ for non-USD securities.
- If the TECHNICALS section above says "not computed", do NOT invent RSI, MACD, or EMA values. Instead, describe only what can be inferred from the price and fundamental data. State clearly that real-time indicator data was not available.
- If financial data above is limited, use your training knowledge of this company's publicly reported financials. State clearly where you are using general knowledge vs provided data. Do not fabricate specific numbers you don't know — say "not provided" instead. Still write a complete, useful report.

WRITING STYLE:
- Write like the best analyst at Goldman Sachs or Morgan Stanley. Decisive. Opinionated. Tight.
- Lead every section with the most important insight, not background.
- Use short, punchy sentences for key points. Use longer sentences only for nuanced reasoning.
- Structure each section for visual scanning: lead with a bold thesis line, then support it.
- Separate distinct ideas with line breaks within sections. Do NOT write wall-of-text paragraphs.
- Never say "it is worth noting" or "it should be mentioned" or "in conclusion." Just state the point.
- Be specific. Replace "strong growth" with "revenue grew 33% YoY to $X." Replace "significant market share" with "commands ~65% of the advanced node TAM."
- If data is not provided, say "data not available" and move on. Do not guess or pad.

Use EXACTLY these section headers (=== HEADER ===):

=== COMPANY OVERVIEW ===
Two tight paragraphs. What the company does, core revenue mix, competitive position, and why it matters now. No history lesson — focus on what's investable today.

=== EXECUTIVE SUMMARY ===
This is the most important section. State the investment thesis in one decisive opening sentence. Then in 2-3 paragraphs: the key catalyst, the core risk, the risk-reward setup, and the rating. A PM reading only this section should know exactly what you think and why.

=== KEY INVESTMENT HIGHLIGHTS ===
Write exactly 5 highlights. Each one should be:
- A single bold thesis line (one sentence, the insight)
- Followed by 2-3 sentences of supporting evidence

Separate each highlight with a blank line. These should be the 5 most investable facts about this company right now. Think: product cycle inflection, margin expansion lever, TAM unlock, capital allocation edge, secular tailwind.

=== FINANCIAL SNAPSHOT ===
Structure this as data-dense analytical prose. Cover:
- Revenue scale and trajectory (growth rate, acceleration/deceleration)
- Margin architecture (gross, operating, net — and the trend)
- Cash generation and capital returns (FCF yield, buybacks, dividends)
- Balance sheet quality (net cash/debt, leverage ratio, current ratio)

Use specific numbers from provided data. Separate each topic with a line break. If financials are limited, state what's missing and analyze what's available.

=== VALUATION ANALYSIS ===
Three distinct scenarios, each as its own paragraph:

Bear Case: State the assumptions that break the thesis. Name a specific valuation framework (e.g., "12x forward P/E on trough EPS") and the implied downside.

Base Case: The most likely outcome. Use a specific multiple or DCF approach. State the expected return from current levels.

Bull Case: What has to go right. Name the upside catalyst and the valuation it implies.

=== TECHNICAL MOMENTUM ===
Two paragraphs. First: what the price action and momentum indicators say right now (RSI, MACD, EMA positioning). Second: what this setup means for entry timing and risk management. Use the provided technical data directly. Be specific about levels.

=== COMPETITIVE LANDSCAPE ===
Two paragraphs. First: who the real competitors are, who's gaining/losing share, and why. Second: the durability of the company's moat — what would it take to disrupt their position. Name competitors. Be direct about strengths and weaknesses.

=== BULL CASE ===
Write exactly 4 arguments. Each one:
- Opens with a single decisive sentence stating the thesis
- Followed by 2-3 sentences of evidence

These should be the 4 strongest reasons to own this stock. Not generic platitudes — specific, investable catalysts.

=== BEAR CASE ===
Write exactly 4 arguments, same structure as Bull Case. The 4 most credible threats to the investment thesis. Be honest about what could go wrong.

=== KEY RISKS AND MITIGANTS ===
Write 3 risk-mitigant pairs. For each:
- Name the risk clearly in one sentence
- Explain why it matters (1-2 sentences)
- State the mitigant or offset (1-2 sentences)

Separate each pair with a blank line.

=== RECOMMENDATION ===
Two paragraphs maximum. First paragraph: state the rating (BUY, HOLD, or SELL), the conviction level, and the 2-3 factors that would change your view. Second paragraph: what you're watching — the key monitoring points over the next 1-2 quarters. End with one definitive sentence.

ABSOLUTE RULES:
- No markdown formatting. No bullet points. No asterisks. No headers within sections.
- Every sentence must carry investment signal. Delete anything a PM would skip.
- Be opinionated. Take a clear view. Wishy-washy analysis is worse than wrong analysis.
- Do NOT fabricate numbers not in the provided data.
"""


ANALYSIS_KEYWORDS = [
    # Longest phrases first to avoid partial matches
    "give me a report on", "give me analysis of", "financial analysis of",
    "bull and bear case for", "investment thesis on",
    "write a report on", "deep dive into", "deep dive on",
    "what are the risks", "pull up", "show me",
    "bull case for", "bear case for",
    "analysis of", "overview of",
    "report on", "report for",
    "tell me about", "write about",
    "look at", "what about", "find",
    # American + British spellings
    "analyze", "analyse", "summarize", "summarise",
    "research", "generate", "evaluate", "review",
    "thesis on", "risks for", "check",
    "how is", "how does", "cover",
    "price of", "what is", "whats", "what's",
]

# Words that indicate a conversational message, NOT a ticker request
CONVERSATIONAL_WORDS = {
    "hello", "hi", "hey", "thanks", "thank", "yes", "no", "ok", "okay",
    "what", "how", "can", "do", "you", "help", "who", "are", "is",
    "please", "sure", "great", "good", "bye", "nice",
}


def _extract_ticker(message: str) -> Optional[str]:
    """Extract a potential ticker or company name from the user message.

    Returns None for conversational messages that aren't requesting analysis.
    """
    lower = message.lower().strip()
    words = set(re.findall(r'[a-z]+', lower))

    # If ALL words are conversational, this is not a ticker request
    if words and words.issubset(CONVERSATIONAL_WORDS):
        return None

    # Check for explicit $ ticker notation: $AAPL
    dollar_match = re.search(r'\$([A-Z]{1,5})\b', message.upper())
    if dollar_match:
        return dollar_match.group(1)

    # Check if the entire message is just a ticker (1-5 uppercase letters)
    stripped = message.strip()
    if re.fullmatch(r'[A-Z]{1,5}', stripped):
        return stripped

    # Check for analysis keywords followed by a subject (BEFORE bare name check)
    # Sort longest-first so "deep dive into" matches before "deep"
    sorted_kw = sorted(ANALYSIS_KEYWORDS, key=len, reverse=True)
    for kw in sorted_kw:
        idx = lower.find(kw)
        if idx >= 0:
            after = message[idx + len(kw):].strip().strip("\"'").strip()
            query = after.split("?")[0].split(".")[0].strip()
            if not query or len(query) < 2:
                continue
            # Clean up common trailing words
            query = re.sub(r'\b(stock|shares?|company|corp|inc|please|for me)\b', '', query, flags=re.IGNORECASE).strip()
            if not query:
                continue
            # Only treat as a bare ticker if it's ALL CAPS, ≤5 chars, and is the only word
            first_word = query.split()[0].strip(",")
            if re.fullmatch(r'[A-Z]{1,5}', first_word) and len(query.split()) == 1:
                return first_word
            # For everything else (company names, mixed case), take up to 5 words
            subject_words = query.split()[:5]
            phrase = " ".join(subject_words)
            # Short-circuit: if this phrase is a known alias, return the symbol directly
            # so _resolve_ticker() gets an exact ticker instead of a fuzzy phrase
            direct_ticker = TICKER_ALIASES.get(phrase.upper())
            if direct_ticker:
                return direct_ticker
            return phrase

    # Check if message is just a company name (1-5 words, all alpha, no analysis verb)
    stripped_words = stripped.split()
    if 1 <= len(stripped_words) <= 5 and all(re.fullmatch(r'[A-Za-z\'&.\-]+', w) for w in stripped_words):
        combined = " ".join(stripped_words)
        if not words.issubset(CONVERSATIONAL_WORDS):
            alias = TICKER_ALIASES.get(combined.upper())
            if alias:
                return alias
            if len(stripped_words) == 1 and len(stripped) <= 5 and stripped == stripped.upper():
                return stripped
            if len(stripped_words) >= 1:
                return combined

    # Check if message contains a company/ticker after common prepositions
    ticker_in_context = re.search(r'\b(?:for|on|of|about|into)\s+([A-Z]{2,5})\b', message)
    if ticker_in_context:
        return ticker_in_context.group(1)

    # Last resort: look for any uppercase 2-5 letter word that could be a ticker
    potential_tickers = re.findall(r'\b([A-Z]{2,5})\b', message)
    noise_words = {"THE", "AND", "FOR", "BUT", "NOT", "ARE", "WAS", "HAS", "HAD", "CAN",
                   "ALL", "HER", "HIS", "ITS", "OUR", "OUT", "WHO", "HOW", "WHY", "NEW",
                   "NOW", "WAY", "MAY", "DAY", "TOO", "ANY", "FEW", "GOT", "LET", "SAY",
                   "SHE", "HIM", "OLD", "SEE", "USE", "TWO", "BOY", "DID", "GET", "PUT",
                   "TOP", "RED", "BIG", "SET"}
    valid = [t for t in potential_tickers if t not in noise_words]
    if valid:
        return valid[0]

    # Last-resort fallback: extract non-conversational words from the message
    non_conv = [w for w in re.findall(r'[a-zA-Z]+', message) if w.lower() not in CONVERSATIONAL_WORDS and len(w) > 1]
    if non_conv:
        candidate = " ".join(non_conv[:5])
        # If this phrase is a known alias, return the ticker symbol directly
        direct = TICKER_ALIASES.get(candidate.upper())
        if direct:
            return direct
        return candidate

    return None


# Common name → ticker aliases for companies people refer to by non-standard names
TICKER_ALIASES = {
    # ── Mega-cap tech ────────────────────────────────────────────────────
    "TSMC": "TSM", "TAIWAN SEMICONDUCTOR": "TSM", "TAIWAN SEMI": "TSM",
    "GOOGLE": "GOOGL", "ALPHABET": "GOOGL", "FACEBOOK": "META",
    "AMAZON": "AMZN", "BROADCOM": "AVGO", "SALESFORCE": "CRM",
    "APPLE": "AAPL", "MICROSOFT": "MSFT", "NVIDIA": "NVDA",
    "TESLA": "TSLA", "ORACLE": "ORCL", "ADOBE": "ADBE",
    "INTEL": "INTC", "QUALCOMM": "QCOM", "MICRON": "MU",
    "CISCO": "CSCO", "ACCENTURE": "ACN",
    # ── High-growth tech ─────────────────────────────────────────────────
    "PALANTIR": "PLTR", "CROWDSTRIKE": "CRWD", "DATADOG": "DDOG",
    "CLOUDFLARE": "NET", "PALO ALTO": "PANW", "PALO ALTO NETWORKS": "PANW",
    "SERVICENOW": "NOW", "SNOWFLAKE": "SNOW", "SHOPIFY": "SHOP",
    "BLOCK": "SQ", "SQUARE": "SQ", "COINBASE": "COIN",
    "ROBINHOOD": "HOOD", "SOFI": "SOFI", "AFFIRM": "AFRM",
    "RIVIAN": "RIVN", "LUCID": "LCID", "SUPERMICRO": "SMCI",
    "AIRBNB": "ABNB", "DOORDASH": "DASH", "ROBLOX": "RBLX",
    "UNITY": "U", "TWILIO": "TWLO", "MONGODB": "MDB",
    "HUBSPOT": "HUBS", "ATLASSIAN": "TEAM", "OKTA": "OKTA",
    "PINTEREST": "PINS", "SNAP": "SNAP", "SNAPCHAT": "SNAP",
    "TRADE DESK": "TTD", "THE TRADE DESK": "TTD", "UIPATH": "PATH",
    "SENTINELONE": "S", "ELASTIC": "ESTC", "GITLAB": "GTLB",
    "DIGITALOCEAN": "DOCN", "CONFLUENT": "CFLT",
    "ARM": "ARM", "ARM HOLDINGS": "ARM", "IONQ": "IONQ",
    # ── Finance ──────────────────────────────────────────────────────────
    "JPMORGAN": "JPM", "JP MORGAN": "JPM", "BERKSHIRE": "BRK.B",
    "BERKSHIRE HATHAWAY": "BRK.B", "GOLDMAN": "GS", "GOLDMAN SACHS": "GS",
    "VISA": "V", "MASTERCARD": "MA", "PAYPAL": "PYPL",
    "FIDELITY": "FIS", "SCHWAB": "SCHW", "CHARLES SCHWAB": "SCHW",
    "MORGAN STANLEY": "MS", "BLACKROCK": "BLK", "BANK OF AMERICA": "BAC",
    "WELLS FARGO": "WFC", "AMERICAN EXPRESS": "AXP", "CITIGROUP": "C",
    "CITI": "C", "CAPITAL ONE": "COF", "DISCOVER": "DFS",
    "METLIFE": "MET", "PRUDENTIAL": "PRU", "ALLSTATE": "ALL",
    "CME": "CME", "CME GROUP": "CME", "INTERCONTINENTAL": "ICE",
    "SP GLOBAL": "SPGI", "S&P GLOBAL": "SPGI", "MOODYS": "MCO", "MOODY'S": "MCO",
    # ── Consumer / retail ────────────────────────────────────────────────
    "COSTCO": "COST", "WALMART": "WMT", "HOME DEPOT": "HD",
    "MCDONALDS": "MCD", "MCDONALD'S": "MCD", "STARBUCKS": "SBUX",
    "NIKE": "NKE", "DISNEY": "DIS", "WALT DISNEY": "DIS",
    "NETFLIX": "NFLX", "UBER": "UBER", "LYFT": "LYFT",
    "GAMESTOP": "GME", "AMC": "AMC", "CHEWY": "CHWY",
    "PELOTON": "PTON", "ETSY": "ETSY", "ROKU": "ROKU",
    "COCA COLA": "KO", "COCA-COLA": "KO", "COKE": "KO",
    "PEPSI": "PEP", "PEPSICO": "PEP", "LULULEMON": "LULU",
    "TARGET": "TGT", "LOWES": "LOW", "LOWE'S": "LOW",
    "BOOKING": "BKNG", "MARRIOTT": "MAR", "HILTON": "HLT",
    "CHIPOTLE": "CMG", "DOMINOS": "DPZ", "DOMINO'S": "DPZ",
    "WAYFAIR": "W", "FORD": "F", "GENERAL MOTORS": "GM",
    "WYNN": "WYNN", "MGM": "MGM",
    # ── Healthcare ───────────────────────────────────────────────────────
    "ELI LILLY": "LLY", "LILLY": "LLY", "MERCK": "MRK",
    "PFIZER": "PFE", "ABBOTT": "ABT", "INTUITIVE": "ISRG",
    "INTUITIVE SURGICAL": "ISRG", "THERMO FISHER": "TMO",
    "ABBVIE": "ABBV", "DANAHER": "DHR", "AMGEN": "AMGN",
    "GILEAD": "GILD", "VERTEX": "VRTX", "REGENERON": "REGN",
    "UNITEDHEALTH": "UNH", "UNITED HEALTH": "UNH",
    "MODERNA": "MRNA", "BIOGEN": "BIIB", "ILLUMINA": "ILMN",
    "CVS": "CVS", "CIGNA": "CI", "HUMANA": "HUM",
    "MEDTRONIC": "MDT", "STRYKER": "SYK", "DEXCOM": "DXCM",
    "EDWARDS": "EW", "EDWARDS LIFESCIENCES": "EW",
    # ── Industrial / Defense ─────────────────────────────────────────────
    "BOEING": "BA", "CATERPILLAR": "CAT", "DEERE": "DE",
    "JOHN DEERE": "DE", "LOCKHEED": "LMT", "LOCKHEED MARTIN": "LMT",
    "RTX": "RTX", "RAYTHEON": "RTX", "NORTHROP": "NOC",
    "NORTHROP GRUMMAN": "NOC", "GENERAL DYNAMICS": "GD",
    "GE": "GE", "GE AEROSPACE": "GE", "GENERAL ELECTRIC": "GE",
    "HONEYWELL": "HON", "3M": "MMM", "UPS": "UPS",
    "FEDEX": "FDX", "UNION PACIFIC": "UNP", "CSX": "CSX",
    "DELTA": "DAL", "DELTA AIR LINES": "DAL", "UNITED AIRLINES": "UAL",
    "AMERICAN AIRLINES": "AAL", "SOUTHWEST": "LUV", "SOUTHWEST AIRLINES": "LUV",
    # ── Energy ───────────────────────────────────────────────────────────
    "EXXON": "XOM", "EXXON MOBIL": "XOM", "EXXONMOBIL": "XOM",
    "CHEVRON": "CVX", "CONOCO": "COP", "CONOCOPHILLIPS": "COP",
    "SCHLUMBERGER": "SLB", "HALLIBURTON": "HAL",
    "MARATHON": "MPC", "OCCIDENTAL": "OXY",
    "ENPHASE": "ENPH", "SOLAREDGE": "SEDG", "FIRST SOLAR": "FSLR",
    "NEXTERA": "NEE", "NEXTERA ENERGY": "NEE",
    # ── Materials / REITs ────────────────────────────────────────────────
    "FREEPORT": "FCX", "FREEPORT MCMORAN": "FCX", "NEWMONT": "NEM",
    "SHERWIN WILLIAMS": "SHW", "SHERWIN-WILLIAMS": "SHW",
    "AMERICAN TOWER": "AMT", "PROLOGIS": "PLD", "CROWN CASTLE": "CCI",
    "EQUINIX": "EQIX", "REALTY INCOME": "O",
    "NUCOR": "NUE", "DOW": "DOW", "DUPONT": "DD",
    # ── Communication ────────────────────────────────────────────────────
    "ATT": "T", "AT&T": "T", "VERIZON": "VZ", "T-MOBILE": "TMUS", "TMOBILE": "TMUS",
    "COMCAST": "CMCSA", "CHARTER": "CHTR",
    "EA": "EA", "ELECTRONIC ARTS": "EA", "ACTIVISION": "ATVI",
    "TAKE TWO": "TTWO", "TAKE-TWO": "TTWO",
    # ── Utilities ────────────────────────────────────────────────────────
    "DUKE ENERGY": "DUK", "SOUTHERN COMPANY": "SO", "DOMINION": "D",
    # ── ETFs ─────────────────────────────────────────────────────────────
    "S&P 500": "SPY", "SP500": "SPY", "S&P": "SPY",
    "NASDAQ": "QQQ", "NASDAQ 100": "QQQ",
    "RUSSELL": "IWM", "RUSSELL 2000": "IWM",
    "DOW JONES": "DIA",
    "GOLD": "GLD", "SILVER": "SLV", "OIL": "USO",
    "BONDS": "TLT", "TREASURY": "TLT",
    "ARK": "ARKK", "ARK INNOVATION": "ARKK",
    "SEMICONDUCTOR ETF": "SOXX", "SEMIS ETF": "SOXX",
    # ── International / ADR ─────────────────────────────────────────────
    "ALIBABA": "BABA", "BABA": "BABA", "NIO": "NIO", "BAIDU": "BIDU",
    "JD": "JD", "JD.COM": "JD", "PINDUODUO": "PDD", "PDD": "PDD",
    "TENCENT": "TCEHY", "SAMSUNG": "SSNLF",
    "TOYOTA": "TM", "SONY": "SONY", "HONDA": "HMC",
    "SAP": "SAP", "NOVO NORDISK": "NVO", "NOVONORDISK": "NVO", "NOVO": "NVO",
    "SHELL": "SHEL", "BP": "BP", "UNILEVER": "UL", "NESTLE": "NSRGY",
    "LVMH": "LVMUY", "FERRARI": "RACE", "MERCADO LIBRE": "MELI",
    "SEA LIMITED": "SE", "GRAB": "GRAB", "COUPANG": "CPNG",
    "INFOSYS": "INFY", "WIPRO": "WIT", "RELIANCE": "RELIANCE",
    # ── Crypto / fintech proxies ─────────────────────────────────────────
    "BITCOIN": "COIN", "ETHEREUM": "COIN",
    "MICROSTRATEGY": "MSTR", "MICRO STRATEGY": "MSTR",
    # ── Popular mid-caps / recent IPOs ───────────────────────────────────
    "DUOLINGO": "DUOL", "REDDIT": "RDDT", "KLAVIYO": "KVYO",
    "INSTACART": "CART", "BIRKENSTOCK": "BIRK", "CAVA": "CAVA",
    "TOAST": "TOST", "DUTCH BROS": "BROS", "SWEETGREEN": "SG",
    "WARBY PARKER": "WRBY", "BUMBLE": "BMBL",
    "HIMS": "HIMS", "HIMS AND HERS": "HIMS",
    "WORKDAY": "WDAY", "VEEVA": "VEEV", "FORTINET": "FTNT",
    "CHECK POINT": "CHKP", "ZSCALER": "ZS",
    "APPLIED MATERIALS": "AMAT", "LAM RESEARCH": "LRCX",
    "ADVANCED MICRO DEVICES": "AMD", "ADVANCED MICRO": "AMD",
    "MICRON TECHNOLOGY": "MU", "TEXAS INSTRUMENTS": "TXN",
    "VERTEX PHARMACEUTICALS": "VRTX", "BOOKING HOLDINGS": "BKNG",
    "BOOKING.COM": "BKNG", "AIR BNB": "ABNB",
    "DOOR DASH": "DASH", "UNITY SOFTWARE": "U",
    # ── Private company → public proxy redirects ─────────────────────────
    "OPEN AI": "MSFT", "OPENAI": "MSFT",
    "STRIPE": "GPN", "SPACEX": "RTX",
    "TWITCH": "AMZN", "INSTAGRAM": "META", "WHATSAPP": "META",
    "THREADS": "META", "YOUTUBE": "GOOGL", "WAYMO": "GOOGL",
    "DEEPMIND": "GOOGL", "TESLA ENERGY": "TSLA", "TESLA SOLAR": "TSLA",
    # ── Aerospace / Space ────────────────────────────────────────────────
    "ROCKET LAB": "RKLB", "ROCKET LABS": "RKLB", "ROCKETLAB": "RKLB",
    "VIRGIN GALACTIC": "SPCE", "AEROJET": "AJRD", "AEROJET ROCKETDYNE": "AJRD",
    "L3HARRIS": "LHX", "L3 HARRIS": "LHX", "LEIDOS": "LDOS",
    # ── Common ticker format variants ────────────────────────────────────
    "BRK": "BRK.B", "BERKSHIRE A": "BRK.A", "BERKSHIRE B": "BRK.B",
    "GOOGLE CLASS A": "GOOGL", "GOOGLE CLASS C": "GOOG",
    "IBM": "IBM",
}


async def _resolve_ticker(query: str) -> Optional[dict]:
    """Resolve a query to a company symbol using aliases, search, and AV fallback."""
    q = query.strip().upper()

    # 1. Check aliases first (instant) — alias ALWAYS wins, never falls through to fuzzy
    alias = TICKER_ALIASES.get(q)
    if alias:
        # Return the aliased symbol DIRECTLY without any fuzzy search.
        # Do NOT call search_companies() here — it may return a wrong company if the
        # alias target (e.g. RKLB) isn't in the local universe, causing fallthrough to ALB.
        print(f"[ai_analyst] Alias match: '{query}' → {alias}")
        from app.services.market_universe import get_company_info_from_universe
        uni = get_company_info_from_universe(alias)
        name = uni.get("name", q.title()) if uni else q.title()
        return {
            "symbol": alias,
            "name": name,
            "exchange": uni.get("exchange", "US") if uni else "US",
            "sector": uni.get("sector") if uni else None,
            "assetType": uni.get("assetType", "Common Stock") if uni else "Common Stock",
            "matchScore": 1.0,
        }

    # 2. Direct universe search
    results = await search_companies(query, limit=5)
    if results:
        best = results[0]
        if best.get("matchScore", 0) >= 0.1:
            return best

    # 3. Try variations: remove common suffixes
    cleaned = re.sub(r'\b(inc|corp|co|ltd|plc|company|group|holdings)\b', '', q, flags=re.IGNORECASE).strip()
    if cleaned and cleaned != q:
        results = await search_companies(cleaned, limit=3)
        if results and results[0].get("matchScore", 0) >= 0.2:
            return results[0]

    # 4. Alpha Vantage SYMBOL_SEARCH fallback (catches companies outside local universe)
    from app.core.config import ALPHA_VANTAGE_API_KEY
    if ALPHA_VANTAGE_API_KEY:
        try:
            av_result = await _av_symbol_search(query)
            if av_result:
                print(f"[ai_analyst] AV symbol search resolved: '{query}' → {av_result['symbol']}")
                return av_result
        except Exception as e:
            print(f"[ai_analyst] AV symbol search failed: {e}")

    # 5. Last resort — if query looks like a valid ticker, use it directly
    upper = query.upper().strip()
    if re.fullmatch(r'[A-Z]{1,5}', upper):
        print(f"[ai_analyst] Using raw ticker as last resort: {upper}")
        return {"symbol": upper, "name": upper, "exchange": "US", "sector": "Unknown", "assetType": "Common Stock", "matchScore": 0.1}

    return None


async def _av_symbol_search(query: str) -> Optional[dict]:
    """Use Alpha Vantage SYMBOL_SEARCH to find a ticker not in the local universe."""
    from app.core.config import ALPHA_VANTAGE_API_KEY
    if not ALPHA_VANTAGE_API_KEY:
        return None
    url = "https://www.alphavantage.co/query"
    params = {"function": "SYMBOL_SEARCH", "keywords": query, "apikey": ALPHA_VANTAGE_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
        if "Note" in data or "Information" in data:
            return None
        matches = data.get("bestMatches", [])
        if not matches:
            return None
        best = matches[0]
        return {
            "symbol": best.get("1. symbol", ""),
            "name": best.get("2. name", best.get("1. symbol", "")),
            "exchange": best.get("4. region", "US"),
            "sector": None,
            "assetType": best.get("3. type", "Common Stock"),
            "matchScore": float(best.get("9. matchScore", 0.5)),
        }
    except Exception as e:
        print(f"[ai_analyst] AV symbol search error: {e}")
        return None


VALID_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-haiku-4-20250514",
]
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _resolve_model(requested: str) -> str:
    """Validate and resolve the requested model, falling back to default."""
    if requested in VALID_MODELS:
        return requested
    # Fuzzy match: user might say "opus" or "haiku"
    lower = requested.lower()
    for m in VALID_MODELS:
        if lower in m:
            return m
    print(f"[ai_analyst] Unknown model '{requested}', falling back to {DEFAULT_MODEL}")
    return DEFAULT_MODEL


async def _call_anthropic(system: str, messages: list[dict], model: str = DEFAULT_MODEL) -> str:
    """Call Anthropic API with conversation history and specified model, with retries."""
    if not ANTHROPIC_API_KEY:
        return "[No Anthropic API key configured. Set ANTHROPIC_API_KEY in backend .env]"

    resolved_model = _resolve_model(model)
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": resolved_model,
        "max_tokens": 8192,
        "system": system,
        "messages": messages,
    }

    last_error = None
    for attempt in range(3):
        try:
            print(f"[ai_analyst] Calling Anthropic model={resolved_model} (attempt {attempt+1})")
            async with httpx.AsyncClient(timeout=160) as client:
                resp = await client.post(url, headers=headers, json=payload)
                data = resp.json()

            if resp.status_code == 429:
                wait = 2 * (attempt + 1)
                print(f"[ai_analyst] Rate limited (429), waiting {wait}s...")
                await asyncio.sleep(wait)
                continue

            if resp.status_code == 529:
                wait = 3 * (attempt + 1)
                print(f"[ai_analyst] Overloaded (529), waiting {wait}s...")
                await asyncio.sleep(wait)
                continue

            if resp.status_code != 200:
                error_msg = data.get("error", {}).get("message", str(data))
                raise ValueError(f"Anthropic error ({resp.status_code}): {error_msg}")

            content = data.get("content", [])
            if content and content[0].get("type") == "text":
                return content[0]["text"]
            return "[No response generated]"

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = e
            if attempt < 2:
                print(f"[ai_analyst] Connection error, retrying: {e}")
                await asyncio.sleep(2)

    raise last_error or ValueError("All Anthropic retries exhausted")


def _generate_fallback_chart(base_price: float, days: int = 90) -> list[dict]:
    """Generate plausible fallback chart data anchored to the current price."""
    chart = []
    price = base_price * (1 - random.uniform(0.03, 0.10))
    target_ratio = base_price / price if price > 0 else 1.0
    daily_drift = (target_ratio - 1.0) / max(days, 1)
    for i in range(days):
        date = (datetime.now() - timedelta(days=days - i)).strftime("%Y-%m-%d")
        ret = daily_drift + random.gauss(0, 0.015)
        price *= (1 + ret)
        h = price * (1 + abs(random.gauss(0, 0.006)))
        lo = price * (1 - abs(random.gauss(0, 0.006)))
        chart.append({
            "date": date,
            "open": round(price * (1 + random.uniform(-0.003, 0.003)), 2),
            "high": round(h, 2),
            "low": round(lo, 2),
            "close": round(price, 2),
            "volume": random.randint(10_000_000, 60_000_000),
        })
    # Anchor last close exactly to base_price
    if chart:
        chart[-1]["close"] = round(base_price, 2)
    return chart


# ── Currency detection for international tickers ─────────────────────────────

EXCHANGE_CURRENCIES = {
    ".BSE": ("₹", "INR"), ".NS": ("₹", "INR"),       # India
    ".BO": ("₹", "INR"),                               # Bombay
    ".L": ("£", "GBP"),                                 # London
    ".TO": ("C$", "CAD"), ".V": ("C$", "CAD"),         # Toronto / TSX Venture
    ".HK": ("HK$", "HKD"),                             # Hong Kong
    ".AX": ("A$", "AUD"),                               # Australia
    ".T": ("¥", "JPY"), ".TYO": ("¥", "JPY"),          # Tokyo
    ".PA": ("€", "EUR"), ".DE": ("€", "EUR"),           # Paris / Frankfurt
    ".AS": ("€", "EUR"), ".MI": ("€", "EUR"),           # Amsterdam / Milan
    ".MC": ("€", "EUR"), ".BR": ("€", "EUR"),           # Madrid / Brussels
    ".SW": ("CHF", "CHF"),                              # Switzerland
    ".KS": ("₩", "KRW"), ".KQ": ("₩", "KRW"),         # Korea
    ".SS": ("¥", "CNY"), ".SZ": ("¥", "CNY"),          # Shanghai / Shenzhen
    ".SA": ("R$", "BRL"),                               # São Paulo
    ".MX": ("MX$", "MXN"),                              # Mexico
}


def _get_currency(ticker: str) -> tuple[str, str]:
    """Returns (symbol, code) e.g. ('₹', 'INR') for TCS.BSE, ('$', 'USD') for AAPL."""
    upper = ticker.upper()
    for suffix, (sym, code) in EXCHANGE_CURRENCIES.items():
        if upper.endswith(suffix.upper()):
            return sym, code
    return "$", "USD"


def _fmt_b(v, prefix="$"):
    """Format a number as $1.23T / $4.56B / $789M."""
    if v is None:
        return None
    if abs(v) >= 1e12:
        return f"{prefix}{v/1e12:.2f}T"
    if abs(v) >= 1e9:
        return f"{prefix}{v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"{prefix}{v/1e6:.1f}M"
    return f"{prefix}{v:,.0f}"


def _fmt_pct(v, already_pct=False):
    """Format a fraction or percentage.  yfinance sends fractions (0.25), SEC sends pct (25.0)."""
    if v is None:
        return None
    val = v * 100 if not already_pct and abs(v) < 1.5 else v  # heuristic: <1.5 is fraction
    return f"{val:+.1f}%" if val >= 0 or val < 0 else f"{val:.1f}%"


def _build_data_context(
    quote: Optional[dict],
    info: dict,
    technicals: Optional[dict] = None,
    fundamentals: Optional[dict] = None,
    macro: Optional[list] = None,
    ticker: str = "",
) -> str:
    """Build comprehensive data context for the analysis prompt using all available data."""
    csym, ccode = _get_currency(ticker)
    lines: list[str] = []

    lines.append(f"Company: {info.get('name', 'Unknown')}")
    sector = (fundamentals or {}).get("sector") or info.get("sector") or "Unknown"
    lines.append(f"Sector: {sector}")
    if fundamentals and fundamentals.get("industry"):
        lines.append(f"Industry: {fundamentals['industry']}")
    if fundamentals and fundamentals.get("country"):
        lines.append(f"Country: {fundamentals['country']}")
    if fundamentals and fundamentals.get("employees"):
        lines.append(f"Employees: {fundamentals['employees']:,}")
    lines.append(f"Currency: {ccode} ({csym})")

    lines.append("")
    lines.append("=== PRICE DATA ===")
    if quote:
        lines.append(f"Current Price: {csym}{quote['price']:.2f}")
        lines.append(f"Daily Change: {quote['change']:+.2f} ({quote['changePercent']:+.2f}%)")
        if quote.get("volume"):
            lines.append(f"Volume: {quote['volume']:,}")
    else:
        lines.append("Live price: not available")

    if fundamentals:
        h = fundamentals.get("fiftyTwoWeekHigh")
        lo = fundamentals.get("fiftyTwoWeekLow")
        if h is not None:
            lines.append(f"52-Week High: {csym}{h:.2f}")
        if lo is not None:
            lines.append(f"52-Week Low: {csym}{lo:.2f}")
        mc = _fmt_b(fundamentals.get("marketCap"), prefix=csym)
        if mc:
            lines.append(f"Market Cap: {mc}")
        if fundamentals.get("beta") is not None:
            lines.append(f"Beta: {fundamentals['beta']:.2f}")

    # ── Financials ────────────────────────────────────────────────────────
    has_fin = fundamentals and any(fundamentals.get(k) is not None for k in
        ("revenue", "netIncome", "eps", "grossMargin", "operatingMargin", "profitMargin",
         "operatingCashFlow", "freeCashFlow"))
    if has_fin:
        lines.append("")
        lines.append("=== FINANCIALS ===")
        rv = _fmt_b(fundamentals.get("revenue"), prefix=csym)
        if rv:
            lines.append(f"Revenue (TTM): {rv}")
        rg = fundamentals.get("revenueGrowth")
        if rg is not None:
            lines.append(f"Revenue Growth YoY: {_fmt_pct(rg)}")
        ni = _fmt_b(fundamentals.get("netIncome"), prefix=csym)
        if ni:
            lines.append(f"Net Income (TTM): {ni}")
        if fundamentals.get("eps") is not None:
            lines.append(f"EPS (TTM): {csym}{fundamentals['eps']:.2f}")
        if fundamentals.get("forwardEps") is not None:
            lines.append(f"EPS (Forward): {csym}{fundamentals['forwardEps']:.2f}")
        gm = _fmt_pct(fundamentals.get("grossMargin"))
        if gm:
            lines.append(f"Gross Margin: {gm}")
        om = _fmt_pct(fundamentals.get("operatingMargin"))
        if om:
            lines.append(f"Operating Margin: {om}")
        nm = _fmt_pct(fundamentals.get("profitMargin"))
        if nm:
            lines.append(f"Net Margin: {nm}")
        ocf = _fmt_b(fundamentals.get("operatingCashFlow"), prefix=csym)
        if ocf:
            lines.append(f"Operating Cash Flow: {ocf}")
        fcf = _fmt_b(fundamentals.get("freeCashFlow"), prefix=csym)
        if fcf:
            lines.append(f"Free Cash Flow: {fcf}")
        td = _fmt_b(fundamentals.get("totalDebt"), prefix=csym)
        if td:
            lines.append(f"Total Debt: {td}")
        cash = _fmt_b(fundamentals.get("cashAndEquivalents"), prefix=csym)
        if cash:
            lines.append(f"Cash & Equivalents: {cash}")
        roe = _fmt_pct(fundamentals.get("returnOnEquity"))
        if roe:
            lines.append(f"Return on Equity: {roe}")
        eg = fundamentals.get("earningsGrowth")
        if eg is not None:
            lines.append(f"Earnings Growth: {_fmt_pct(eg)}")

    # ── Valuation ─────────────────────────────────────────────────────────
    has_val = fundamentals and any(fundamentals.get(k) is not None for k in
        ("peRatio", "forwardPE", "pbRatio", "evToEbitda", "dividendYield"))
    if has_val:
        lines.append("")
        lines.append("=== VALUATION ===")
        if fundamentals.get("peRatio") is not None:
            lines.append(f"P/E Ratio (TTM): {fundamentals['peRatio']:.1f}x")
        if fundamentals.get("forwardPE") is not None:
            lines.append(f"P/E Ratio (Forward): {fundamentals['forwardPE']:.1f}x")
        if fundamentals.get("pbRatio") is not None:
            lines.append(f"Price/Book: {fundamentals['pbRatio']:.2f}x")
        if fundamentals.get("evToEbitda") is not None:
            lines.append(f"EV/EBITDA: {fundamentals['evToEbitda']:.1f}x")
        if fundamentals.get("dividendYield") is not None:
            lines.append(f"Dividend Yield: {fundamentals['dividendYield']*100:.2f}%")

    # ── Technicals ────────────────────────────────────────────────────────
    if technicals:
        lines.append("")
        lines.append("=== TECHNICALS ===")
        if technicals.get("rsi") is not None:
            lines.append(f"RSI (14): {technicals['rsi']:.1f} — {technicals.get('rsi_signal', 'N/A')}")
        if technicals.get("macd_val") is not None:
            lines.append(f"MACD: {technicals['macd_val']:.4f} / Signal: {technicals.get('macd_signal', 'N/A')}")
        if technicals.get("ema_20") is not None:
            lines.append(f"EMA-20: {csym}{technicals['ema_20']:.2f}")
        if technicals.get("ema_50") is not None:
            lines.append(f"EMA-50: {csym}{technicals['ema_50']:.2f}")
        if technicals.get("atr") is not None:
            lines.append(f"ATR (14): {csym}{technicals['atr']:.2f}")
        if technicals.get("volatility") is not None:
            lines.append(f"Annualized Volatility: {technicals['volatility']:.1f}%")
    else:
        lines.append("")
        lines.append("=== TECHNICALS ===")
        lines.append("Real-time technical indicator data was not computed for this security.")

    # ── Macro ─────────────────────────────────────────────────────────────
    if macro:
        lines.append("")
        lines.append("=== MACRO ENVIRONMENT ===")
        for m in macro[:5]:
            lines.append(f"{m.get('name', '')}: {m.get('value', '')}{m.get('unit', '')} ({m.get('trend', '')})")

    # ── Business description ──────────────────────────────────────────────
    if fundamentals and fundamentals.get("description"):
        lines.append("")
        lines.append("=== BUSINESS DESCRIPTION ===")
        lines.append(fundamentals["description"][:800])

    return "\n".join(lines)


def _parse_analysis_sections(text: str) -> list[dict]:
    """Parse structured analysis into sections."""
    section_map = {
        "COMPANY OVERVIEW": ("companyOverview", "Company Overview"),
        "EXECUTIVE SUMMARY": ("executiveSummary", "Executive Summary"),
        "KEY INVESTMENT HIGHLIGHTS": ("keyHighlights", "Key Investment Highlights"),
        "FINANCIAL SNAPSHOT": ("financialSnapshot", "Financial Snapshot"),
        "VALUATION ANALYSIS": ("valuationAnalysis", "Valuation Analysis"),
        "VALUATION SCENARIOS": ("valuationAnalysis", "Valuation Analysis"),
        "TECHNICAL MOMENTUM": ("technicalMomentum", "Technical Momentum"),
        "TECHNICAL VIEW": ("technicalMomentum", "Technical Momentum"),
        "COMPETITIVE LANDSCAPE": ("competitiveLandscape", "Competitive Landscape"),
        "BULL CASE": ("bullCase", "Bull Case"),
        "BEAR CASE": ("bearCase", "Bear Case"),
        "KEY RISKS AND MITIGANTS": ("risksCatalysts", "Key Risks & Mitigants"),
        "RISKS AND CATALYSTS": ("risksCatalysts", "Risks & Catalysts"),
        "RECOMMENDATION": ("recommendation", "Recommendation"),
    }

    sections = []
    current_key = None
    current_title = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip().strip("=").strip()
        mapped = section_map.get(stripped.upper())
        if mapped:
            if current_key:
                sections.append({"key": current_key, "title": current_title, "content": "\n".join(current_lines).strip()})
            current_key, current_title = mapped
            current_lines = []
        else:
            current_lines.append(line)

    if current_key:
        sections.append({"key": current_key, "title": current_title, "content": "\n".join(current_lines).strip()})

    return sections


def _determine_rating(sections: list[dict]) -> tuple[str, float]:
    """Extract rating from the recommendation section."""
    for s in sections:
        if s["key"] == "recommendation":
            text = s["content"].upper()
            if "STRONG BUY" in text: return "Strong Buy", 0.80
            if "BUY" in text: return "Buy", 0.70
            if "SELL" in text and "STRONG" in text: return "Strong Sell", 0.75
            if "SELL" in text: return "Sell", 0.65
    return "Hold", 0.55


DISCLAIMER = (
    "This analysis is produced by BlackGrid AI Analyst for informational and educational "
    "purposes only. It does not constitute investment advice. All analysis is based on "
    "publicly available data. Investors should conduct their own due diligence."
)


async def process_analyst_chat(
    message: str,
    history: list[dict],
    model: str = DEFAULT_MODEL,
    attachments: list[dict] | None = None,
) -> dict:
    """Process a user message in the AI Analyst chat."""
    resolved_model = _resolve_model(model)

    # Build attachment context if present
    attachment_context = ""
    if attachments:
        parts = ["The user has attached the following files:"]
        for a in attachments:
            parts.append(f"- {a.get('filename', 'unknown')} ({a.get('contentType', '?')}, {a.get('size', 0)} bytes)")
            if a.get("summary"):
                parts.append(f"  Content summary: {a['summary']}")
        attachment_context = "\n".join(parts) + "\n\n"

    # Step 1: Extract potential ticker/company from the message
    query = _extract_ticker(message)
    print(f"[ai_analyst] User: {message[:80]}... | Query: {query} | Model: {resolved_model}")

    if not query:
        # General conversation
        messages = [{"role": h["role"], "content": h["content"]} for h in history]
        user_content = attachment_context + message if attachment_context else message
        messages.append({"role": "user", "content": user_content})
        try:
            reply = await asyncio.wait_for(
                _call_anthropic(ANALYST_SYSTEM, messages, model=resolved_model),
                timeout=30,
            )
        except Exception as e:
            reply = f"I encountered an issue processing your request. Please try again. ({type(e).__name__})"
        return {"reply": reply, "disclaimer": DISCLAIMER, "modelUsed": resolved_model}

    # Step 2: Resolve the ticker
    resolved = await _resolve_ticker(query)
    if not resolved:
        return {
            "reply": f"I couldn't find a matching company for \"{query}\". Please try a ticker symbol (e.g., AAPL, NVDA) or a company name.",
            "disclaimer": DISCLAIMER,
        }

    ticker = resolved["symbol"]
    company_name = resolved.get("name", ticker)
    info = get_asset_info(ticker)
    # Prefer the universe-resolved name
    if company_name and company_name != ticker:
        info["name"] = company_name

    print(f"[ai_analyst] Resolved: {ticker} ({company_name})")

    # Step 3: Fetch market data + fundamentals + technicals in parallel
    quote, df = await fetch_quote_and_history(ticker)

    chart_data = []
    if df is not None and len(df) > 0:
        for _, row in df.iterrows():
            chart_data.append({
                "date": str(row["date"])[:10],
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": int(row["volume"]),
            })

    # ALWAYS provide chart data — generate fallback if live data is empty
    if not chart_data:
        base = quote["price"] if quote else info.get("base_price", 100)
        chart_data = _generate_fallback_chart(base)

    # Fetch technicals (lowered from 60 to 30 so more tickers get real indicators)
    technicals = None
    if df is not None and len(df) >= 30:
        try:
            technicals = compute_all_indicators(df)
            print(f"[ai_analyst] Computed technicals for {ticker}: RSI={technicals.get('rsi', 'N/A')}")
        except Exception as e:
            print(f"[ai_analyst] Technicals failed for {ticker}: {e}")

    # Fetch fundamentals: yfinance first (covers all tickers), SEC as supplement
    fundamentals = None
    try:
        from app.services.fundamental_service import fetch_fundamentals_yf
        fundamentals = await fetch_fundamentals_yf(ticker)
    except Exception as e:
        print(f"[ai_analyst] yfinance fundamentals failed for {ticker}: {e}")

    # If yfinance didn't return revenue, try SEC as supplement
    if not fundamentals or not fundamentals.get("revenue"):
        try:
            sec_data = await fetch_company_facts(ticker)
            if sec_data:
                sec_summary = build_fundamental_summary(sec_data, ticker)
                if fundamentals:
                    # Merge: fill gaps in yfinance data with SEC data
                    for k, v in sec_summary.items():
                        if v is not None and fundamentals.get(k) is None:
                            fundamentals[k] = v
                else:
                    fundamentals = sec_summary
        except Exception as e:
            print(f"[ai_analyst] SEC data failed for {ticker}: {e}")

    # Enrich company info from yfinance data
    if fundamentals:
        if fundamentals.get("fullName"):
            info["name"] = fundamentals["fullName"]
        if fundamentals.get("sector") and info.get("sector") in (None, "Unknown", ""):
            info["sector"] = fundamentals["sector"]
        if fundamentals.get("industry"):
            info["industry"] = fundamentals["industry"]
        if fundamentals.get("description"):
            info["description"] = fundamentals["description"]

    # Fetch macro context
    macro = None
    try:
        macro = await fetch_macro_indicators()
    except Exception as e:
        print(f"[ai_analyst] Macro data failed: {e}")

    # Step 4: Generate analysis with enriched data context
    data_context = _build_data_context(quote, info, technicals, fundamentals, macro, ticker=ticker)
    if attachment_context:
        data_context = attachment_context + data_context
    csym, ccode = _get_currency(ticker)
    prompt = ANALYSIS_PROMPT.format(
        name=info["name"], ticker=ticker, data_context=data_context,
        report_date=datetime.now().strftime("%B %d, %Y"),
        currency_symbol=f"{csym} ({ccode})",
    )

    # Append market-specific context for international tickers
    ticker_upper = ticker.upper()
    if ticker_upper.endswith((".BSE", ".NS", ".BO")):
        prompt += """
MARKET CONTEXT: This is an India-listed security. Include analysis of:
- INR/USD currency impact on revenue and margins
- RBI monetary policy implications
- India's macroeconomic environment (GDP growth, inflation)
- SEBI regulatory framework considerations
- Comparison to Indian sector peers (not just US peers)
- India-specific risks: political, regulatory, currency
"""
    elif ticker_upper.endswith(".L"):
        prompt += "\nMARKET CONTEXT: London-listed. Consider GBP impact, Bank of England policy, UK macro environment, and FCA regulatory framework.\n"
    elif ticker_upper.endswith((".PA", ".DE", ".AS", ".MI", ".MC", ".BR")):
        prompt += "\nMARKET CONTEXT: European-listed. Consider EUR impact, ECB policy, EU regulatory environment, and European macro conditions.\n"
    elif ticker_upper.endswith((".T", ".TYO")):
        prompt += "\nMARKET CONTEXT: Tokyo-listed. Consider JPY impact, BOJ policy, Japan's macro environment, and Japanese corporate governance reforms.\n"
    elif ticker_upper.endswith((".HK",)):
        prompt += "\nMARKET CONTEXT: Hong Kong-listed. Consider HKD/USD peg, HKMA policy, China macro exposure, and Greater China regulatory environment.\n"
    elif ticker_upper.endswith((".TO", ".V")):
        prompt += "\nMARKET CONTEXT: Canadian-listed. Consider CAD impact, Bank of Canada policy, and Canadian resource/tech sector dynamics.\n"
    elif ticker_upper.endswith((".AX",)):
        prompt += "\nMARKET CONTEXT: Australian-listed. Consider AUD impact, RBA policy, and Australia's resource-heavy economy.\n"

    try:
        raw_text = await asyncio.wait_for(
            _call_anthropic(ANALYST_SYSTEM, [{"role": "user", "content": prompt}], model=resolved_model),
            timeout=150,
        )
        sections = _parse_analysis_sections(raw_text)
        rating, confidence = _determine_rating(sections)
    except asyncio.TimeoutError:
        sections = []
        rating = "Hold"
        confidence = 0.5
        raw_text = f"Analysis generation timed out for {ticker}. The AI model took too long to respond. Please try again."
    except Exception as e:
        sections = []
        rating = "Hold"
        confidence = 0.5
        raw_text = f"Analysis generation encountered an error for {ticker}: {type(e).__name__}. Please try again."
        print(f"[ai_analyst] Error: {e}")

    # Build a SHORT chat reply — the report workspace is the real output
    if sections:
        reply = f"Research report for {info['name']} ({ticker}) is ready. Rating: {rating}. See the full analysis in the workspace."
    else:
        reply = f"I was unable to generate a complete report for {ticker}. {raw_text}"

    quote_payload = None
    if quote:
        quote_payload = {
            "price": quote["price"],
            "change": quote["change"],
            "changePercent": quote["changePercent"],
            "volume": quote.get("volume", 0),
        }

    return {
        "reply": reply,
        "ticker": ticker,
        "companyName": info["name"],
        "sector": info.get("sector"),
        "rating": rating,
        "confidenceScore": confidence,
        "quote": quote_payload,
        "chart": chart_data,
        "analysisSections": sections,
        "disclaimer": DISCLAIMER,
        "modelUsed": resolved_model,
    }
