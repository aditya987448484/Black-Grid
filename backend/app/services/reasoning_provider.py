"""Reasoning provider abstraction — Anthropic, Groq, and mock fallback with retries."""

from __future__ import annotations

import asyncio
import httpx
from abc import ABC, abstractmethod
from app.core.config import GROQ_API_KEY, ANTHROPIC_API_KEY, REASONING_PROVIDER

SYSTEM_PROMPT = (
    "You are a senior financial analyst at a top-tier institutional research firm. "
    "Write in a professional, precise, institutional tone. Be concise and evidence-based. "
    "Never fabricate data or statistics. If data is missing, acknowledge the gap. "
    "This is a research tool — not financial advice. Acknowledge uncertainty where appropriate."
)


class BaseReasoningProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass


class AnthropicReasoningProvider(BaseReasoningProvider):
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        self.model = "claude-sonnet-4-20250514"

    async def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("No Anthropic API key configured.")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }

        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    data = resp.json()

                if resp.status_code == 429:
                    wait = 2 * (attempt + 1)
                    print(f"[anthropic] Rate limited, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code == 529:
                    wait = 3 * (attempt + 1)
                    print(f"[anthropic] Overloaded (529), retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code != 200:
                    error_msg = data.get("error", {}).get("message", str(data))
                    raise ValueError(f"Anthropic API error ({resp.status_code}): {error_msg}")

                content = data.get("content", [])
                if content and content[0].get("type") == "text":
                    return content[0]["text"]
                raise ValueError(f"Anthropic returned unexpected format: {data}")

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < 2:
                    wait = 2 * (attempt + 1)
                    print(f"[anthropic] Connection error, retrying in {wait}s: {e}")
                    await asyncio.sleep(wait)

        raise last_error or ValueError("All Anthropic retries exhausted")


class GroqReasoningProvider(BaseReasoningProvider):
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.model = "llama-3.3-70b-versatile"

    async def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("No Groq API key configured.")

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    data = resp.json()

                if resp.status_code == 429:
                    wait = 2 * (attempt + 1)
                    print(f"[groq] Rate limited, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue

                choices = data.get("choices", [])
                if choices:
                    return choices[0]["message"]["content"]
                raise ValueError(f"Groq returned no choices: {data}")

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < 2:
                    print(f"[groq] Connection error, retrying: {e}")
                    await asyncio.sleep(1)

        raise last_error or ValueError("All Groq retries exhausted")


class MockReasoningProvider(BaseReasoningProvider):
    async def generate(self, prompt: str) -> str:
        return (
            "[Template analysis] This section was generated using template-based analysis "
            "as no AI reasoning provider is currently active. Configure ANTHROPIC_API_KEY "
            "or GROQ_API_KEY for live AI-generated institutional research."
        )


def get_reasoning_provider() -> BaseReasoningProvider:
    """Select reasoning provider by REASONING_PROVIDER env var with auto-detection."""
    if REASONING_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
        print("[reasoning] Using Anthropic Claude provider.")
        return AnthropicReasoningProvider()

    if REASONING_PROVIDER == "groq" and GROQ_API_KEY:
        print("[reasoning] Using Groq provider.")
        return GroqReasoningProvider()

    # Auto-detect: prefer Anthropic if key exists
    if ANTHROPIC_API_KEY:
        print("[reasoning] Auto-detected Anthropic key. Using Anthropic provider.")
        return AnthropicReasoningProvider()
    if GROQ_API_KEY:
        print("[reasoning] Auto-detected Groq key. Using Groq provider.")
        return GroqReasoningProvider()

    print("[reasoning] No reasoning provider keys found. Using mock.")
    return MockReasoningProvider()
