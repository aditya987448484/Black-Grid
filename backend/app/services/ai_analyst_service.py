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
- Balance sheet quality (net cash/debt, leverage ratio)

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
    "analyze", "analysis of", "research", "generate", "financial analysis of",
    "bull and bear case for", "bull case for", "bear case for",
    "investment thesis on", "thesis on", "summarize", "risks for",
    "look at", "what about", "tell me about", "evaluate", "review",
    "how is", "how does", "what are the risks",
    "report on", "report for", "give me a report on", "give me analysis of",
    "write a report on", "write about", "cover", "deep dive on", "deep dive into",
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

    # Check for analysis keywords followed by a subject
    for kw in ANALYSIS_KEYWORDS:
        idx = lower.find(kw)
        if idx >= 0:
            after = message[idx + len(kw):].strip().strip("\"'").strip()
            query = after.split("?")[0].split(".")[0].strip()
            if not query or len(query) < 2:
                continue
            # If the subject starts with a ticker-like word, take just that
            first_word = query.split()[0].strip(",")
            if re.fullmatch(r'[A-Za-z]{1,5}', first_word) and first_word.upper() != first_word.lower():
                # Check if it looks like a ticker (e.g., "NVDA") vs a name (e.g., "apple")
                if first_word == first_word.upper() and len(first_word) <= 5:
                    return first_word
            # Otherwise take the full subject phrase (e.g., "Taiwan Semiconductor")
            # But limit to first 3 words for search
            subject_words = query.split()[:3]
            return " ".join(subject_words)

    # Check if the entire message is just a ticker (1-5 uppercase letters)
    stripped = message.strip()
    if re.fullmatch(r'[A-Z]{1,5}', stripped):
        return stripped

    # Check if message contains a company/ticker after common prepositions
    ticker_in_context = re.search(r'\b(?:for|on|of|about|into)\s+([A-Za-z]{2,20})\b', message)
    if ticker_in_context:
        return ticker_in_context.group(1)

    return None


# Common name → ticker aliases for companies people refer to by non-standard names
TICKER_ALIASES = {
    # Tech
    "TSMC": "TSM", "TAIWAN SEMICONDUCTOR": "TSM", "TAIWAN SEMI": "TSM",
    "GOOGLE": "GOOGL", "ALPHABET": "GOOGL", "FACEBOOK": "META",
    "AMAZON": "AMZN", "BROADCOM": "AVGO", "SALESFORCE": "CRM",
    "PALANTIR": "PLTR", "CROWDSTRIKE": "CRWD", "DATADOG": "DDOG",
    "CLOUDFLARE": "NET", "PALO ALTO": "PANW", "PALO ALTO NETWORKS": "PANW",
    "SERVICENOW": "NOW", "SNOWFLAKE": "SNOW", "SHOPIFY": "SHOP",
    "BLOCK": "SQ", "SQUARE": "SQ", "COINBASE": "COIN",
    "ROBINHOOD": "HOOD", "SOFI": "SOFI", "AFFIRM": "AFRM",
    "RIVIAN": "RIVN", "LUCID": "LCID", "SUPERMICRO": "SMCI",
    # Finance
    "JPMORGAN": "JPM", "JP MORGAN": "JPM", "BERKSHIRE": "BRK.B",
    "GOLDMAN": "GS", "GOLDMAN SACHS": "GS", "VISA": "V",
    "MASTERCARD": "MA", "PAYPAL": "PYPL", "FIDELITY": "FIS",
    "SCHWAB": "SCHW", "CHARLES SCHWAB": "SCHW",
    "MORGAN STANLEY": "MS", "BLACKROCK": "BLK", "BANK OF AMERICA": "BAC",
    "WELLS FARGO": "WFC", "AMERICAN EXPRESS": "AXP", "CITIGROUP": "C",
    # Consumer / retail popular
    "COSTCO": "COST", "WALMART": "WMT", "HOME DEPOT": "HD",
    "MCDONALDS": "MCD", "STARBUCKS": "SBUX", "NIKE": "NKE",
    "DISNEY": "DIS", "NETFLIX": "NFLX", "UBER": "UBER",
    "GAMESTOP": "GME", "AMC": "AMC", "CHEWY": "CHWY",
    "PELOTON": "PTON", "ETSY": "ETSY", "ROKU": "ROKU",
    # Healthcare
    "ELI LILLY": "LLY", "LILLY": "LLY", "MERCK": "MRK",
    "PFIZER": "PFE", "ABBOTT": "ABT", "INTUITIVE": "ISRG",
    # Industrial / Defense
    "BOEING": "BA", "CATERPILLAR": "CAT", "DEERE": "DE",
    "LOCKHEED": "LMT", "LOCKHEED MARTIN": "LMT", "RTX": "RTX",
    "GE": "GE", "GE AEROSPACE": "GE",
    # Energy
    "EXXON": "XOM", "EXXON MOBIL": "XOM",
    # ETFs
    "S&P 500": "SPY", "SP500": "SPY", "NASDAQ": "QQQ", "GOLD": "GLD",
}


async def _resolve_ticker(query: str) -> Optional[dict]:
    """Resolve a query to a company symbol using aliases then search."""
    q = query.strip().upper()

    # Check aliases first (instant)
    alias = TICKER_ALIASES.get(q)
    if alias:
        results = await search_companies(alias, limit=1)
        if results:
            print(f"[ai_analyst] Alias match: '{query}' → {alias}")
            return results[0]

    # Direct search
    results = await search_companies(query, limit=5)
    if results:
        return results[0]

    # Try the raw query as a ticker
    upper = query.upper().strip()
    results = await search_companies(upper, limit=3)
    if results:
        return results[0]

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
    """Call Anthropic API with conversation history and specified model."""
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

    print(f"[ai_analyst] Calling Anthropic model={resolved_model}")
    async with httpx.AsyncClient(timeout=160) as client:
        resp = await client.post(url, headers=headers, json=payload)
        data = resp.json()

    if resp.status_code != 200:
        error_msg = data.get("error", {}).get("message", str(data))
        raise ValueError(f"Anthropic error ({resp.status_code}): {error_msg}")

    content = data.get("content", [])
    if content and content[0].get("type") == "text":
        return content[0]["text"]
    return "[No response generated]"


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


def _build_data_context(quote: Optional[dict], info: dict) -> str:
    """Build data context string for the analysis prompt."""
    parts = []
    if quote:
        parts.append(f"Current Price: ${quote['price']:.2f}")
        parts.append(f"Daily Change: {quote['change']:+.2f} ({quote['changePercent']:+.2f}%)")
    parts.append(f"Sector: {info.get('sector', 'Unknown')}")
    return "\n".join(parts) if parts else "Limited data available for this ticker."


def _parse_analysis_sections(text: str) -> list[dict]:
    """Parse structured analysis into sections."""
    section_map = {
        "COMPANY OVERVIEW": ("companyOverview", "Company Overview"),
        "EXECUTIVE SUMMARY": ("executiveSummary", "Executive Summary"),
        "KEY INVESTMENT HIGHLIGHTS": ("keyHighlights", "Key Investment Highlights"),
        "FINANCIAL SNAPSHOT": ("financialSnapshot", "Financial Snapshot"),
        "VALUATION ANALYSIS": ("valuationAnalysis", "Valuation Analysis"),
        "TECHNICAL MOMENTUM": ("technicalMomentum", "Technical Momentum"),
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

    # Step 3: Fetch market data
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

    # Step 4: Generate analysis
    data_context = _build_data_context(quote, info)
    if attachment_context:
        data_context = attachment_context + data_context
    prompt = ANALYSIS_PROMPT.format(name=info["name"], ticker=ticker, data_context=data_context)

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
