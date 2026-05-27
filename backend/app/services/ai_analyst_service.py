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
            # Build the full message list with system prompt prepended
            full_system = system or SYSTEM_PROMPT
            # DeepSeekReasoningProvider.reason() prepends a fixed system message;
            # we use a single user message carrying the full context instead.
            combined_user = "\n\n".join(
                f"[{m['role'].upper()}]: {m['content']}" for m in messages
            )
            reply = await self._provider.reason(
                combined_user,
                context=None,
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
