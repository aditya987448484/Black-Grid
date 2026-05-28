"""
AI Analyst Chat Service
Conversational AI analyst powered by DeepSeek.

Delegates to DeepSeekReasoningProvider for all HTTP calls so there is
exactly one httpx client, one set of retry/error-handling logic, and
one place to update the API endpoint.

Public API
----------
    service = AIAnalystService()
    reply   = await service.chat(messages=[{"role": "user", "content": "Analyse AAPL"}])
    reply   = await service.chat_with_context("What is the P/E?", history, ticker="AAPL")
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.services.reasoning_provider import DeepSeekReasoningProvider
from app.schemas.ai_analyst import AiAnalystResponse

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "deepseek-chat"
VALID_MODELS = ["deepseek-chat", "deepseek-reasoner"]

SYSTEM_PROMPT = """You are AXIOM, a Senior Managing Director-level financial analyst at a top-tier investment bank. You have 25 years of experience covering equities across all sectors. When asked to analyze a stock, you MUST produce a structured, deeply researched report covering ALL of the following sections using exact ## markdown headers. Use real, specific numbers. Never use vague language like "strong growth" — always say "+23% YoY". Do not add generic disclaimers. Minimum 1,400 words.

## Executive Summary
3 paragraphs: investment thesis, current market context, one-line verdict with BUY/HOLD/SELL and 12-month price target.

## Company Overview & Business Model
Revenue streams, competitive moat, market share, key products. Include TTM revenue, net income, market cap.

## Key Financial Metrics
Present as bullet list with specific numbers:
- Revenue (TTM): $X.XXB (+X% YoY)
- Net Income (TTM): $X.XXB | EPS: $X.XX
- Free Cash Flow: $X.XXB (X% FCF margin)
- Gross Margin: X% | Operating Margin: X% | Net Margin: X%
- P/E: Xx | EV/EBITDA: Xx | EV/Revenue: Xx | PEG: X.Xx
- Debt/Equity: X.Xx | Current Ratio: X.Xx | Interest Coverage: Xx
- ROE: X% | ROIC: X% | Asset Turnover: X.Xx

## Base Case (12-Month Target: $XXX | Probability: XX%)
Detailed base case. Specific revenue/earnings assumptions, catalysts, multiple expansion/compression thesis. Minimum 2 paragraphs.

## Bull Case (Target: $XXX | Probability: XX%)
Specific upside scenario. What needs to go right, by how much, by when. Include best-case EPS and revenue assumptions.

## Bear Case (Target: $XXX | Probability: XX%)
Specific downside scenario. What breaks the thesis. Worst-case assumptions. Floor price and why.

## Technical Analysis
- Primary trend (daily, weekly timeframe)
- Key support levels: $XX, $XX, $XX
- Key resistance levels: $XX, $XX, $XX
- RSI (14-day): XX (overbought/oversold/neutral)
- MACD: bullish/bearish crossover or divergence
- Volume: above/below 20-day average, significance
- 50-day MA: $XXX | 200-day MA: $XXX | Golden/Death cross status
- Short-term (1-4 weeks) and medium-term (3-6 months) technical outlook

## Geopolitical & Macro Impact
2+ paragraphs. Cover specifically: USD sensitivity, interest rate impact (Fed policy), trade war / tariff exposure for this company's supply chain and revenue geography, regional geopolitical risks (China/Taiwan/Europe/Middle East as relevant), regulatory risk in key jurisdictions. Be specific to this company, not generic.

## Competitive Landscape
Main 3-5 competitors with market share estimates. Where does this company win and lose? Moat assessment. Disruption risk.

## Key Risks to Monitor (minimum 6)
Format each as:
- [High/Medium/Low] Risk name: specific description of what to watch, what triggers concern, magnitude of impact

## Growth Catalysts & Future Outlook (minimum 5)
Format each as:
- [Near-term/Medium-term] Catalyst: specific description, expected timeline, estimated impact on revenue or EPS

## Valuation Analysis
Current valuation vs 5-year historical range, vs sector peers, vs growth rate (PEG). DCF assumptions if warranted. Is the multiple justified? Upside/downside to fair value.

## Investment Verdict & Position Sizing
BUY/HOLD/SELL with conviction (High/Medium/Low), 12-month price target, stop-loss level. Position sizing guidance:
- Conservative portfolio (low risk): X% allocation
- Balanced portfolio: X% allocation
- Aggressive / growth portfolio: X% allocation
"""


class AIAnalystService:
    """
    Conversational analyst backed by DeepSeekReasoningProvider.

    All HTTP calls go through a single shared DeepSeekReasoningProvider
    instance — no duplicate httpx.AsyncClient creation.
    """

    def __init__(self, model: Optional[str] = None):
        self._provider = DeepSeekReasoningProvider()
        self._model = model if model in VALID_MODELS else DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        model: Optional[str] = None,
    ) -> str:
        """
        Send a multi-turn conversation to DeepSeek and return the assistant reply.

        Args:
            messages:    Chat history — list of {"role": "user"|"assistant", "content": "..."}
            system:      Override system prompt (defaults to SYSTEM_PROMPT)
            max_tokens:  Maximum tokens in the reply
            temperature: Sampling temperature (lower = more deterministic)
            model:       Override model for this call

        Returns:
            Assistant reply as plain text
        """
        effective_model = model if model in VALID_MODELS else self._model

        # Temporarily swap the provider's model for this call
        original_model = self._provider.model
        self._provider.model = effective_model
        try:
            # Build a proper OpenAI-style messages array so DeepSeek receives
            # the full multi-turn context rather than a flattened string.
            full_messages: List[Dict[str, str]] = [
                {"role": "system", "content": system or SYSTEM_PROMPT},
                *messages,
            ]
            reply = await self._provider.chat_messages(
                full_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        finally:
            self._provider.model = original_model

        return reply

    async def chat_with_context(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        *,
        ticker: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Convenience wrapper that injects financial context into the conversation
        and appends the new user message to history before calling DeepSeek.

        Args:
            user_message: Latest user input
            history:      Prior chat turns
            ticker:       Optional ticker symbol for context enrichment
            context:      Optional dict of financial data to include
            model:        Override model for this call

        Returns:
            Assistant reply as plain text
        """
        # Build enriched system prompt if context is provided
        system = SYSTEM_PROMPT
        if ticker or context:
            extras: list[str] = []
            if ticker:
                extras.append(f"Current ticker in focus: {ticker.upper()}")
            if context:
                extras.append(
                    "Market data context:\n"
                    + json.dumps(context, separators=(",", ":"))
                )
            system = system + "\n\n" + "\n".join(extras)

        messages = [*history, {"role": "user", "content": user_message}]
        return await self.chat(messages, system=system, model=model)

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._provider.close()


_ANALYSIS_KEYWORDS = (
    "analyze", "analysis", "report", "research", "deep dive", "break down",
    "tell me about", "assess", "evaluate", "overview", "what is", "price target",
)


def _is_analysis_request(message: str) -> bool:
    """Return True when the message looks like a stock analysis request."""
    lower = message.lower()
    return any(kw in lower for kw in _ANALYSIS_KEYWORDS)


async def process_analyst_chat(
    message: str,
    history: list,
    model: str = "deepseek-chat",
    attachments: list = None,
) -> AiAnalystResponse:
    """
    Module-level entry point called by routes_ai_analyst.

    Instantiates AIAnalystService, builds the message list (optionally
    injecting attachment summaries), calls DeepSeek, and always tears
    down the HTTP client in a finally block.

    Returns an AiAnalystResponse — never raises to the caller.
    """
    is_analysis = _is_analysis_request(message)
    max_tokens  = 8192 if is_analysis else 8000
    temperature = 0.15 if is_analysis else 0.4

    service = AIAnalystService(model=model)
    try:
        # If attachments were uploaded, append a digest to the user turn
        user_content = message
        if attachments:
            summaries = "\n".join(
                f"- [{a.get('filename', 'file')}] {a.get('summary', '(no preview)')}"
                for a in attachments
            )
            user_content = f"{message}\n\nAttached files:\n{summaries}"

        messages: List[Dict[str, str]] = [
            *history,
            {"role": "user", "content": user_content},
        ]

        reply = await service.chat(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return AiAnalystResponse(
            reply=reply,
            modelUsed=model,
            disclaimer="For informational purposes only.",
        )

    except ValueError as exc:
        # Typically: DeepSeek API key not configured
        logger.warning("process_analyst_chat ValueError: %s", exc)
        reply = (
            "## API Key Required\n\n"
            "The AI Analyst could not connect to DeepSeek because no API key is configured.\n\n"
            "**To fix this:**\n"
            "1. Open `backend/.env`\n"
            "2. Add the line: `DEEPSEEK_API_KEY=your_key_here`\n"
            "3. Get a free key at [platform.deepseek.com](https://platform.deepseek.com)\n"
            "4. Restart the backend server\n"
        )
        return AiAnalystResponse(
            reply=reply,
            modelUsed=model,
            disclaimer="",
        )

    except Exception as exc:
        logger.exception("process_analyst_chat unexpected error: %s", exc)
        reply = (
            "## Something went wrong\n\n"
            f"The analyst encountered an unexpected error: `{exc}`\n\n"
            "**Backend checklist:**\n"
            "- `DEEPSEEK_API_KEY` is set in `backend/.env`\n"
            "- The backend server is running (`uvicorn app.main:app --reload`)\n"
            "- DeepSeek API is reachable (check https://status.deepseek.com)\n"
            "- Review backend logs for the full traceback\n"
        )
        return AiAnalystResponse(
            reply=reply,
            modelUsed=model,
            disclaimer="",
        )

    finally:
        await service.close()
