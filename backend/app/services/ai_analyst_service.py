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

SYSTEM_PROMPT = (
    "You are AXIOM, an expert AI financial analyst. "
    "You provide institutional-grade analysis of equities, ETFs, bonds, and macro indicators. "
    "Be concise, data-driven, and direct. Cite numbers when available. "
    "Avoid generic disclaimers — the user is a sophisticated investor."
)


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

        reply = await service.chat(messages, model=model)
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
