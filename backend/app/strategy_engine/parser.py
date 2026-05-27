"""Claude-powered strategy parser.

Takes a natural language strategy description, sends it to the Anthropic API
with a system prompt describing the 100-indicator catalog, and returns a
structured StrategySpec.
"""

from __future__ import annotations

import json
import os
import re

import httpx

from app.strategy_engine.schemas import (
    StrategyParseResponse,
    StrategySpec,
)

# ---------------------------------------------------------------------------
# Import the indicator catalog – built by the indicators agent.
# If it hasn't been created yet we fall back to an empty dict so the module
# can still be imported.
# ---------------------------------------------------------------------------
try:
    from app.indicators.registry import INDICATOR_CATALOG
except ImportError:
    INDICATOR_CATALOG: dict = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_indicator_catalog_text() -> str:
    """Build a human-readable description of every indicator in the catalog."""
    if not INDICATOR_CATALOG:
        return (
            "The indicator catalog is currently empty.  "
            "Use generic indicator keys such as 'sma', 'ema', 'rsi', 'macd_line', "
            "'macd_signal', 'macd_histogram', 'bollinger_upper', 'bollinger_lower', "
            "'bollinger_middle', 'atr', 'adx', 'plus_di', 'minus_di', 'obv', "
            "'stochastic_k', 'stochastic_d', 'cci', 'williams_r', 'mfi', "
            "'rolling_volatility' and include any required params."
        )

    lines: list[str] = []
    for key, meta in INDICATOR_CATALOG.items():
        params_str = ", ".join(
            f"{p}={v}" for p, v in meta.get("parameters", {}).items()
        )
        desc = meta.get("description", "")
        lines.append(f"  - {key}({params_str}): {desc}")
    return "\n".join(lines)


_SYSTEM_PROMPT_TEMPLATE = """\
You are a trading strategy parser for BlackGrid.  Your job is to convert
a plain-English strategy description into a structured JSON object that
our strategy engine can compile and execute.

## Available indicator keys

The following indicator keys are available.  You MUST only use keys from
this list.  Each key accepts the listed parameters (with defaults shown).

{catalog}

## Price fields

You may also reference these raw price columns as plain strings:
  "close", "open", "high", "low", "volume"

## JSON structure you must return

Return a JSON object (no markdown fences) with these top-level keys:

{{
  "strategy_spec": {{
    "name": "<short descriptive name>",
    "direction": "long_only" | "short_only" | "long_short",
    "timeframe": "1d",
    "entry": {{
      "long_conditions": [ {{ "logic": "and", "conditions": [ ... ] }} ],
      "short_conditions": [ {{ "logic": "and", "conditions": [ ... ] }} ]
    }},
    "exit": {{
      "long_exit_conditions": [ {{ "logic": "and", "conditions": [ ... ] }} ],
      "short_exit_conditions": [ {{ "logic": "and", "conditions": [ ... ] }} ]
    }},
    "risk": {{
      "stop_loss_pct": null,
      "take_profit_pct": null,
      "trailing_stop_pct": null,
      "trailing_stop_atr_mult": null,
      "max_positions": 1,
      "sizing_mode": "fixed",
      "risk_per_trade_pct": 1.0
    }},
    "filters": [],
    "notes": ""
  }},
  "interpretation_summary": "<1-2 sentence summary of what the strategy does>",
  "assumptions": ["<list assumptions you made>"],
  "unsupported_clauses": ["<list parts of the request you could not map>"],
  "confidence": 0.0 to 1.0,
  "can_run_immediately": true | false
}}

### Condition format

Each condition inside a condition group looks like:

{{
  "left": <IndicatorReference or price field string>,
  "operator": "gt" | "lt" | "gte" | "lte" | "eq" | "crosses_above" | "crosses_below" | "between",
  "right": <IndicatorReference or price field string or number>,
  "right_upper": <number or null, only for "between">
}}

An IndicatorReference looks like:
{{
  "indicator_key": "<key from catalog>",
  "params": {{ "period": 14 }},
  "alias": "optional_alias"
}}

## Rules

1. Use ONLY indicator keys from the catalog above.
2. If the user mentions an indicator or concept you cannot map, add it to
   "unsupported_clauses".
3. Infer reasonable defaults when the user is vague (e.g. "use RSI" → period 14,
   oversold 30, overbought 70).  Document these in "assumptions".
4. "crosses_above" means: previous bar value was <= threshold AND current bar
   value is > threshold.
5. "crosses_below" means: previous bar value was >= threshold AND current bar
   value is < threshold.
6. "between" requires both "right" (lower) and "right_upper" (upper).
7. If the user mentions stop loss / take profit / trailing stop, populate the
   "risk" block.
8. Set "can_run_immediately" to true only if you are confident the spec is
   complete and all indicators are supported.
9. Return ONLY the JSON object — no explanation text outside the JSON.
"""


def _build_system_prompt() -> str:
    catalog_text = _build_indicator_catalog_text()
    return _SYSTEM_PROMPT_TEMPLATE.format(catalog=catalog_text)


def _build_messages(
    message: str,
    history: list[dict] | None,
    file_context: str | None,
    ticker: str,
) -> list[dict]:
    """Build the messages list for the Anthropic API call."""
    messages: list[dict] = []

    # Replay prior conversation turns
    if history:
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    # Build current user message
    parts: list[str] = []
    if file_context:
        parts.append(f"[Uploaded file context]\n{file_context}\n")
    parts.append(f"Ticker: {ticker}\n")
    parts.append(message)

    messages.append({"role": "user", "content": "\n".join(parts)})
    return messages


def _extract_json(text: str) -> dict | None:
    """Extract a JSON object from Claude's response text."""
    # Try direct parse first
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try to find JSON in markdown code fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Last resort: find the outermost { ... }
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    start = None

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def parse_strategy(
    message: str,
    history: list[dict] | None = None,
    ticker: str = "SPY",
    model: str = "claude-sonnet-4-6",
    api_key: str | None = None,
    file_context: str | None = None,
) -> StrategyParseResponse:
    """Parse a natural language strategy description into a StrategySpec.

    Parameters
    ----------
    message:
        The user's strategy description in plain English.
    history:
        Optional prior conversation turns (list of ``{"role": ..., "content": ...}``).
    ticker:
        Default ticker symbol for context (e.g. ``"SPY"``).
    model:
        Anthropic model to use.
    api_key:
        Client-provided API key.  Falls back to the server ``ANTHROPIC_API_KEY``.
    file_context:
        Extracted text from an uploaded file to include as context.

    Returns
    -------
    StrategyParseResponse
    """
    resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not resolved_key:
        return StrategyParseResponse(
            reply="No Anthropic API key available. Please provide one or set the ANTHROPIC_API_KEY environment variable.",
            strategy_spec=None,
            confidence=0.0,
            can_run_immediately=False,
        )

    system_prompt = _build_system_prompt()
    messages = _build_messages(message, history, file_context, ticker)

    # Call Anthropic Messages API via httpx
    headers = {
        "x-api-key": resolved_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return StrategyParseResponse(
            reply=f"Anthropic API error: {exc.response.status_code} – {exc.response.text[:300]}",
            strategy_spec=None,
            confidence=0.0,
            can_run_immediately=False,
        )
    except httpx.RequestError as exc:
        return StrategyParseResponse(
            reply=f"Network error contacting Anthropic API: {exc}",
            strategy_spec=None,
            confidence=0.0,
            can_run_immediately=False,
        )

    # Extract text from the response
    content_blocks = data.get("content", [])
    raw_text = ""
    for block in content_blocks:
        if block.get("type") == "text":
            raw_text += block.get("text", "")

    if not raw_text:
        return StrategyParseResponse(
            reply="Received empty response from the model.",
            strategy_spec=None,
            confidence=0.0,
            can_run_immediately=False,
        )

    # Parse the structured JSON from Claude's response
    parsed = _extract_json(raw_text)
    if parsed is None:
        return StrategyParseResponse(
            reply=raw_text,
            strategy_spec=None,
            interpretation_summary="Could not extract structured JSON from the model response.",
            confidence=0.0,
            can_run_immediately=False,
        )

    # Build StrategySpec from the parsed dict
    spec_data = parsed.get("strategy_spec")
    strategy_spec: StrategySpec | None = None
    if spec_data and isinstance(spec_data, dict):
        try:
            strategy_spec = StrategySpec.model_validate(spec_data)
        except Exception:
            strategy_spec = None

    interpretation = parsed.get("interpretation_summary", "")
    assumptions = parsed.get("assumptions", [])
    unsupported = parsed.get("unsupported_clauses", [])
    confidence = float(parsed.get("confidence", 0.0))
    can_run = bool(parsed.get("can_run_immediately", False))

    # Build a friendly reply
    if strategy_spec:
        reply = (
            f"I've parsed your strategy: **{strategy_spec.name}**.\n\n"
            f"{interpretation}"
        )
        if assumptions:
            reply += "\n\n**Assumptions made:**\n" + "\n".join(
                f"- {a}" for a in assumptions
            )
        if unsupported:
            reply += "\n\n**Unsupported clauses:**\n" + "\n".join(
                f"- {u}" for u in unsupported
            )
        if can_run:
            reply += "\n\nThe strategy is ready to run."
        else:
            reply += "\n\nPlease review and confirm before running."
    else:
        reply = raw_text

    return StrategyParseResponse(
        reply=reply,
        strategy_spec=strategy_spec,
        interpretation_summary=interpretation,
        assumptions=assumptions if isinstance(assumptions, list) else [],
        unsupported_clauses=unsupported if isinstance(unsupported, list) else [],
        confidence=confidence,
        can_run_immediately=can_run,
    )
