"""Backtest routes — strategies list, run-custom, Claude-powered chat."""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.schemas.backtest import BacktestSummaryResponse
from app.services.backtest_service import get_backtest_summary
from app.pipelines.backtest import STRATEGY_REGISTRY, run_custom_strategy
from app.services.market_data import fetch_price_history_range
from app.core.config import ANTHROPIC_API_KEY

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.get("/summary")
async def backtest_summary(
    ticker: str = Query(default="SPY"),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    strategies: Optional[str] = Query(default=None),  # comma-separated keys
):
    keys = [k.strip() for k in strategies.split(",")] if strategies else None
    ticker_clean = ticker.upper().strip()
    print(f"[backtests] GET /summary ticker={ticker_clean} start={start_date} end={end_date}")
    result = await get_backtest_summary(
        ticker_clean,
        start_date,
        end_date,
        strategy_keys=keys,
    )
    if result.get("error"):
        print(f"[backtests] Error for {ticker_clean}: {result['error']}")
    else:
        print(f"[backtests] {ticker_clean}: {result.get('dataPoints', 0)} bars, {len(result.get('models', []))} strategies")
    return result


@router.get("/strategies/list")
async def list_strategies():
    return {
        key: {
            "name": v["name"],
            "category": v["category"],
            "description": v["description"],
            "defaultParams": v["params"],
        }
        for key, v in STRATEGY_REGISTRY.items()
    }


class RunCustomRequest(BaseModel):
    ticker: str
    strategy_key: str
    params: dict = {}
    custom_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/strategies/run-custom")
async def run_custom(req: RunCustomRequest):
    df = await fetch_price_history_range(req.ticker.upper(), req.start_date, req.end_date)
    if df is None or len(df) < 40:
        return {"error": f"Insufficient data for {req.ticker}"}
    return run_custom_strategy(df, req.strategy_key, req.params, req.custom_name)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    ticker: str = "SPY"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    api_key: Optional[str] = None


@router.post("/strategies/chat")
async def strategy_chat(req: ChatRequest):
    """
    Claude API powers this endpoint. Takes user's plain English message,
    returns structured JSON with: reply, strategy_key, params, run_immediately.
    Then optionally runs the strategy and returns full results.
    """
    import httpx

    strategy_keys = list(STRATEGY_REGISTRY.keys())
    strategy_info = "\n".join([
        f"  {k}: {v['name']} ({v['category']}) — params: {json.dumps(v['params'])}"
        for k, v in STRATEGY_REGISTRY.items()
    ])

    system_prompt = f"""You are BlackGrid's trading strategy assistant.
Users describe trading strategies in plain English. You parse their intent and
return ONLY valid JSON (no markdown, no explanation outside the JSON).

Available strategies and their default params:
{strategy_info}

Your response MUST be valid JSON with this exact structure:
{{
  "reply": "Your conversational response here — explain what you're doing, the strategy logic, expected behavior in different market conditions",
  "strategy_key": "the_registry_key_or_null",
  "params": {{"param_name": value}},
  "run_immediately": true,
  "confidence": 0.95,
  "market_context": "Brief note on when this strategy works best"
}}

Rules:
- strategy_key must be one of: {strategy_keys}
- Set strategy_key to null if you can't map the request to a known strategy
- params should only include values the user explicitly specified; omit the rest (defaults will be used)
- run_immediately should be true if the user clearly wants to run a backtest
- reply should be 2-3 sentences: what you're running, why, what to expect
- If the user asks something non-strategy (e.g. "what is RSI?"), answer in reply and set strategy_key to null
- Extract ticker symbols if mentioned (e.g. "backtest NVDA using RSI")
- Understand synonyms: "turtle trading" → donchian, "death cross" → sma_crossover, "cloud" → ichimoku
"""

    messages = []
    for h in req.history[-8:]:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": req.message})

    effective_key = req.api_key or ANTHROPIC_API_KEY
    if not effective_key:
        print("[strategy_chat] ERROR: No API key — neither client api_key nor server ANTHROPIC_API_KEY is set!")
        return {"reply": "No API key configured. Either set ANTHROPIC_API_KEY in the backend .env file, or enter your key in the Strategy Chat API key panel.", "strategy_key": None, "params": {}, "run_immediately": False}

    model_id = req.model or "claude-sonnet-4-6"
    key_source = "client" if req.api_key else "server .env"
    print(f"[strategy_chat] Using model: {model_id} | Ticker: {req.ticker} | Key source: {key_source}")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": effective_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model_id,
                    "max_tokens": 800,
                    "system": system_prompt,
                    "messages": messages,
                },
            )
        resp.raise_for_status()
        raw = resp.json()["content"][0]["text"].strip()

        # Parse JSON from Claude
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Extract JSON if Claude wrapped it somehow
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except:
                return {"reply": raw, "strategy_key": None, "params": {}, "run_immediately": False}
        else:
            return {"reply": raw, "strategy_key": None, "params": {}, "run_immediately": False}
    except Exception as e:
        print(f"[strategy_chat] Claude API error: {e}")
        return {"reply": f"I had trouble connecting to the AI. Error: {str(e)}", "strategy_key": None, "params": {}, "run_immediately": False}

    # If Claude identified a strategy and wants to run it, execute it
    result = None
    if parsed.get("strategy_key") and parsed.get("run_immediately"):
        df = await fetch_price_history_range(req.ticker.upper(), req.start_date, req.end_date)
        if df is not None and len(df) >= 40:
            result = run_custom_strategy(
                df,
                parsed["strategy_key"],
                parsed.get("params", {}),
                parsed.get("custom_name"),
            )

    return {
        "reply": parsed.get("reply", ""),
        "strategy_key": parsed.get("strategy_key"),
        "params": parsed.get("params", {}),
        "run_immediately": parsed.get("run_immediately", False),
        "confidence": parsed.get("confidence", 1.0),
        "market_context": parsed.get("market_context", ""),
        "strategyResult": result,
    }
