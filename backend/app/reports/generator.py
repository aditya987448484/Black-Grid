"""Institutional equity research report generator.

Produces sell-side-quality analyst notes modeled after professional research
templates: structured sections, scenario-based valuation, clear recommendation,
and professional disclaimers.
"""

from __future__ import annotations

from typing import Optional, List
import asyncio
from datetime import datetime
from app.services.reasoning_provider import get_reasoning_provider
from app.services.mock_data import mock_report, get_asset_info

# Cache generated reports in memory to avoid regeneration
_report_cache: dict[str, tuple[float, dict]] = {}
REPORT_CACHE_TTL = 600  # 10 minutes


# ── Section mapping ──────────────────────────────────────────────────────────

SECTION_MAP = {
    "EXECUTIVE SUMMARY": "executiveSummary",
    "KEY INVESTMENT HIGHLIGHTS": "keyHighlights",
    "TECHNICAL VIEW": "technicalView",
    "FUNDAMENTAL SNAPSHOT": "fundamentalSnapshot",
    "MACRO CONTEXT": "macroContext",
    "FORECAST AND SCENARIO VIEW": "forecastView",
    "VALUATION SCENARIOS": "valuationScenarios",
    "COMPETITIVE LANDSCAPE": "competitiveLandscape",
    "BULL CASE": "bullCase",
    "BEAR CASE": "bearCase",
    "RISKS AND CATALYSTS": "risksCatalysts",
    "KEY RISKS AND MITIGANTS": "risksCatalysts",
    "ANALYST CONCLUSION": "analystConclusion",
    "ANALYST CONCLUSION AND RECOMMENDATION": "analystConclusion",
}

DISCLAIMER_TEXT = (
    "This report is produced by BlackGrid Research for informational and educational "
    "purposes only. It does not constitute investment advice, a solicitation, or a "
    "recommendation to buy, sell, or hold any security. All analysis is based on "
    "publicly available data and quantitative models that carry inherent limitations. "
    "Past performance is not indicative of future results. Forecasts and price targets "
    "are probabilistic estimates and should not be interpreted as guarantees. Investors "
    "should conduct their own due diligence and consult a qualified financial advisor "
    "before making investment decisions. BlackGrid Research and its affiliates may hold "
    "positions in securities discussed herein."
)


def _build_report_prompt(
    ticker: str,
    info: dict,
    technicals: Optional[dict],
    forecast: Optional[dict],
    fundamentals: Optional[dict],
    macro: Optional[List[dict]],
) -> str:
    """Build a comprehensive institutional research prompt."""
    parts = []

    parts.append(f"""You are writing a formal equity research initiation report for {info['name']} (Ticker: {ticker}).
Sector: {info.get('sector', 'N/A')}.
Report Date: {datetime.now().strftime('%B %d, %Y')}.
Analyst: BlackGrid Research.

Write in the professional, analytical style of a sell-side equity research note.
Use precise language, structured paragraphs, and data-driven reasoning.
Do NOT use markdown formatting or bullet-point-heavy writing.
Write in flowing, analytical prose with clear topic sentences.
""")

    if technicals:
        parts.append("=== PROVIDED TECHNICAL DATA ===")
        parts.append(f"Current Price: ${technicals.get('ema_20', 'N/A')} area (EMA-20)")
        parts.append(f"RSI (14-day): {technicals.get('rsi', 'N/A')}")
        parts.append(f"MACD: {technicals.get('macd_val', 'N/A')} (signal: {technicals.get('macd_signal', 'N/A')})")
        parts.append(f"EMA-20: {technicals.get('ema_20', 'N/A')}, EMA-50: {technicals.get('ema_50', 'N/A')}")
        parts.append(f"ATR (14): {technicals.get('atr', 'N/A')}")
        parts.append(f"Annualized Volatility: {technicals.get('volatility', 'N/A')}%")
        parts.append("")

    if forecast:
        models = forecast.get("models", [])
        if models:
            m = models[0]
            parts.append("=== PROVIDED FORECAST DATA ===")
            parts.append(f"Baseline Model Direction: {m.get('predictedDirection', 'N/A')}")
            parts.append(f"Direction Probability: {m.get('directionProbability', 0):.1%}")
            parts.append(f"Expected Return (5-day): {m.get('expectedReturn', 0):+.2f}%")
            parts.append(f"Model Confidence: {m.get('confidence', 0):.1%}")
            parts.append("")
        if forecast.get("bullishFactors"):
            parts.append(f"Identified Bullish Factors: {'; '.join(forecast['bullishFactors'][:5])}")
        if forecast.get("bearishFactors"):
            parts.append(f"Identified Bearish Factors: {'; '.join(forecast['bearishFactors'][:5])}")
        parts.append("")

    if fundamentals:
        parts.append("=== PROVIDED FUNDAMENTAL DATA ===")
        if fundamentals.get("revenue"):
            parts.append(f"Revenue: ${fundamentals['revenue']/1e9:.1f}B")
        if fundamentals.get("netIncome"):
            parts.append(f"Net Income: ${fundamentals['netIncome']/1e9:.1f}B")
        if fundamentals.get("eps"):
            parts.append(f"Diluted EPS: ${fundamentals['eps']:.2f}")
        if fundamentals.get("profitMargin"):
            parts.append(f"Net Margin: {fundamentals['profitMargin']:.1f}%")
        if fundamentals.get("debtRatio"):
            parts.append(f"Debt-to-Assets: {fundamentals['debtRatio']:.1f}%")
        if fundamentals.get("operatingCashFlow"):
            parts.append(f"Operating Cash Flow: ${fundamentals['operatingCashFlow']/1e9:.1f}B")
        parts.append("")

    if macro:
        parts.append("=== PROVIDED MACRO CONTEXT ===")
        for m in macro[:5]:
            parts.append(f"{m.get('name', '')}: {m.get('value', '')}{m.get('unit', '')} ({m.get('trend', '')})")
        parts.append("")

    parts.append(f"""
Now write the full research report using EXACTLY these section headers (prefixed by ===):

=== EXECUTIVE SUMMARY ===
Write 2-3 analytical paragraphs. State the investment thesis, the rating recommendation,
key drivers behind the view, and a brief summary of the risk-reward profile. Reference
the current price context and what the model data suggests. Write as if addressing
institutional portfolio managers.

=== KEY INVESTMENT HIGHLIGHTS ===
Write 4-6 thematic investment highlights as short analytical paragraphs (not bullet points).
Each highlight should identify a specific driver of value: product cycle, TAM expansion,
margin improvement, competitive moat, capital allocation, or structural tailwind.

=== TECHNICAL VIEW ===
Write 2 paragraphs analyzing the price action, momentum indicators, and support/resistance
levels using the provided technical data. Reference RSI, MACD, EMA trends, and volatility.
Discuss what the technical setup implies for near-term positioning.

=== FUNDAMENTAL SNAPSHOT ===
Write 2-3 paragraphs on revenue trajectory, margin profile, balance sheet quality, and
cash flow generation. Use the provided fundamental data. Compare performance to sector
norms where relevant. Identify any inflection points.

=== VALUATION SCENARIOS ===
Write 3 paragraphs covering Bear Case, Base Case, and Bull Case scenarios. For each
scenario, describe the assumptions, the implied valuation approach (e.g., P/E, EV/EBITDA,
DCF range), and the expected return profile. Be specific about the drivers that would
trigger each scenario.

=== MACRO CONTEXT ===
Write 1-2 paragraphs on the macro environment and how interest rates, inflation, GDP
growth, and sector-level dynamics affect this company specifically.

=== COMPETITIVE LANDSCAPE ===
Write 2 paragraphs on the company's competitive positioning, market share trajectory,
key competitors, and structural advantages or disadvantages. Discuss barriers to entry
and the company's strategic moat.

=== FORECAST AND SCENARIO VIEW ===
Write 2 paragraphs summarizing what the quantitative model outputs suggest about near-term
direction. Discuss the probability-weighted outlook and what would change the view.

=== BULL CASE ===
Write 3-5 clear analytical arguments for upside, each as a short paragraph.

=== BEAR CASE ===
Write 3-5 clear analytical arguments for downside risk, each as a short paragraph.

=== KEY RISKS AND MITIGANTS ===
Write 2-3 paragraphs identifying the top risk factors (macro, competitive, execution,
regulatory) and for each risk, describe a plausible mitigant or offset.

=== ANALYST CONCLUSION AND RECOMMENDATION ===
Write 2 paragraphs stating the final recommendation, the confidence level, key monitoring
points, and conditions under which the recommendation would change. End with a clear
statement of the rating.

CRITICAL RULES:
- Professional sell-side institutional tone throughout
- Do NOT fabricate specific financial numbers not provided in the data
- If a data point is unavailable, state that explicitly rather than guessing
- Write in flowing prose, not bullet-point lists
- This is a research tool, not investment advice — but write as if it were a real research note
- Each section should be substantive (minimum 2 paragraphs)
""")

    return "\n".join(parts)


def _parse_sections(text: str) -> dict:
    """Parse AI output into sections by === HEADER === delimiters."""
    result = {}
    current_key = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip().strip("=").strip()
        matched_key = SECTION_MAP.get(stripped.upper())
        if matched_key:
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = matched_key
            current_lines = []
        else:
            current_lines.append(line)

    if current_key:
        result[current_key] = "\n".join(current_lines).strip()

    # Fill missing sections
    for key in set(SECTION_MAP.values()):
        if key not in result:
            result[key] = ""

    return result


def _build_fallback_report(ticker: str, info: dict, forecast: Optional[dict] = None) -> dict:
    """Build a complete fallback report with all required fields."""
    fallback = mock_report(ticker)
    fallback["sector"] = info.get("sector")
    fallback["analystName"] = "BlackGrid Research"
    fallback["keyHighlights"] = ""
    fallback["valuationScenarios"] = ""
    fallback["competitiveLandscape"] = ""
    fallback["analystConclusion"] = ""
    fallback["disclaimer"] = DISCLAIMER_TEXT

    # Override rating from forecast if available
    if forecast and forecast.get("models"):
        prob = forecast["models"][0].get("directionProbability", 0.5)
        if prob > 0.65: fallback["rating"] = "Strong Buy"
        elif prob > 0.55: fallback["rating"] = "Buy"
        elif prob < 0.45: fallback["rating"] = "Sell"
        elif prob < 0.35: fallback["rating"] = "Strong Sell"

    return fallback


async def generate_report(
    ticker: str,
    technicals: Optional[dict] = None,
    forecast: Optional[dict] = None,
    macro: Optional[List[dict]] = None,
    fundamentals: Optional[dict] = None,
) -> dict:
    """Generate institutional equity research report with caching and timeout."""
    import time
    info = get_asset_info(ticker)

    # Check cache first
    cache_key = ticker.upper()
    cached = _report_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < REPORT_CACHE_TTL:
        print(f"[report] Cache hit for {ticker}")
        return cached[1]

    provider = get_reasoning_provider()
    prompt = _build_report_prompt(ticker, info, technicals, forecast, fundamentals, macro)

    try:
        print(f"[report] Generating report for {ticker} via {provider.__class__.__name__}...")

        # Use asyncio.wait_for to enforce a 90-second timeout
        raw_text = await asyncio.wait_for(
            provider.generate(prompt),
            timeout=90.0,
        )
        sections = _parse_sections(raw_text)

        # Determine rating
        rating = "Hold"
        if forecast and forecast.get("models"):
            prob = forecast["models"][0].get("directionProbability", 0.5)
            if prob > 0.65: rating = "Strong Buy"
            elif prob > 0.55: rating = "Buy"
            elif prob < 0.35: rating = "Strong Sell"
            elif prob < 0.45: rating = "Sell"

        confidence = forecast["models"][0].get("confidence", 0.5) if forecast and forecast.get("models") else 0.5

        result = {
            "ticker": ticker.upper(),
            "name": info["name"],
            "generatedAt": datetime.now().isoformat(),
            "rating": rating,
            "confidenceScore": round(confidence, 2),
            "sector": info.get("sector"),
            "analystName": "BlackGrid Research",
            "sections": [{"title": k, "content": v} for k, v in sections.items() if v],
            "disclaimer": DISCLAIMER_TEXT,
            **sections,
        }

        # Cache the successful result
        _report_cache[cache_key] = (time.time(), result)
        print(f"[report] Successfully generated and cached report for {ticker}")
        return result

    except asyncio.TimeoutError:
        print(f"[report] Timeout generating report for {ticker} (>90s). Using fallback.")
        return _build_fallback_report(ticker, info, forecast)
    except Exception as e:
        print(f"[report] Generation failed for {ticker}: {type(e).__name__}: {e}")
        return _build_fallback_report(ticker, info, forecast)
