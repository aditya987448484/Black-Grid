"""Backtest routes — strategies list, run-custom, Claude-powered chat, strategy engine v2."""

from __future__ import annotations

import json
import traceback
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.schemas.backtest import BacktestSummaryResponse
from app.services.backtest_service import get_backtest_summary
from app.pipelines.backtest import STRATEGY_REGISTRY, run_custom_strategy
from app.services.market_data import fetch_price_history_range
from app.core.config import ANTHROPIC_API_KEY
from app.indicators.registry import INDICATOR_CATALOG

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


def _format_snapshot(snap: dict) -> str:
    if not snap:
        return "No live data available."
    lines = [
        f"LIVE MARKET DATA for {snap['ticker']} ({snap['bar_count']} bars, source: {snap['data_source']})",
        "Last 5 bars (OHLCV):",
    ]
    for bar in snap.get("ohlcv_rows", []):
        lines.append(f"  {bar['date']}: O={bar['open']} H={bar['high']} L={bar['low']} C={bar['close']} V={bar['volume']}")
    lines.append("\nCurrent indicator values (last bar):")
    for k, v in snap.get("indicator_snapshot", {}).items():
        if v is not None:
            lines.append(f"  {k}: {round(float(v), 4) if isinstance(v, (int, float)) else v}")
    return "\n".join(lines)


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

    # Inject live indicator data into system prompt
    from app.services.market_data import fetch_raw_indicator_snapshot
    snap = await fetch_raw_indicator_snapshot(req.ticker.upper(), req.start_date, req.end_date)
    data_context = _format_snapshot(snap) if snap else "No live data available."
    system_prompt += f"""

## LIVE MARKET DATA (use this to ground your strategy)

{data_context}

Use the indicator values above to:
- Detect the current market regime (trending/ranging/volatile)
- Recommend strategy types appropriate for current conditions
- Set realistic thresholds based on actual current indicator levels
- Note whether strategy conditions would currently be ACTIVE or INACTIVE
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


# ── Strategy Engine v2 endpoints ────────────────────────────────────────


@router.get("/indicator-catalog")
async def indicator_catalog():
    """Return the full 100-indicator catalog. Computed from Tiingo/EODHD/yfinance OHLCV data."""
    return {
        key: {
            "key": key,
            "display_name": v["display_name"],
            "category": v["category"],
            "parameters": v.get("parameters", {}),
            "description": v["description"],
            "supported_operators": v.get("supported_operators", []),
            "required_fields": v.get("required_fields", []),
            "output_type": v.get("output_type", "line"),
            "data_source": "tiingo_eodhd",
        }
        for key, v in INDICATOR_CATALOG.items()
    }


@router.get("/indicator-snapshot")
async def indicator_snapshot(
    ticker: str = Query(default="SPY"),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
):
    """Fetch live OHLCV and compute 30+ indicator values for Claude context."""
    from app.services.market_data import fetch_raw_indicator_snapshot
    snap = await fetch_raw_indicator_snapshot(ticker.upper(), start_date, end_date)
    if snap is None:
        return {"error": f"No data for {ticker}"}
    return snap


class StrategyParseRequest(BaseModel):
    message: str
    history: list[dict] = []
    ticker: str = "SPY"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    api_key: Optional[str] = None
    file_context: Optional[str] = None


@router.post("/strategies/parse")
async def parse_strategy_endpoint(req: StrategyParseRequest):
    """Parse natural language into a StrategySpec via Claude."""
    from app.strategy_engine.parser import parse_strategy

    effective_key = req.api_key or ANTHROPIC_API_KEY
    print(f"[parse] Parsing strategy for {req.ticker} | model={req.model}")

    # Inject live indicator data
    from app.services.market_data import fetch_raw_indicator_snapshot
    snap = await fetch_raw_indicator_snapshot(req.ticker.upper(), req.start_date, req.end_date)
    data_context = _format_snapshot(snap) if snap else ""
    combined_context = (req.file_context or "") + ("\n\n" + data_context if data_context else "")

    result = await parse_strategy(
        message=req.message,
        history=req.history,
        ticker=req.ticker,
        model=req.model,
        api_key=effective_key,
        file_context=combined_context if combined_context.strip() else None,
    )
    return result.model_dump()


class StrategyValidateRequest(BaseModel):
    strategy_spec: dict


@router.post("/strategies/validate")
async def validate_strategy_endpoint(req: StrategyValidateRequest):
    """Validate a StrategySpec against the indicator catalog."""
    from app.strategy_engine.schemas import StrategySpec
    from app.strategy_engine.validator import validate_strategy

    try:
        spec = StrategySpec.model_validate(req.strategy_spec)
        result = validate_strategy(spec)
        return {"valid": result.valid, "errors": result.errors, "warnings": result.warnings}
    except Exception as e:
        return {"valid": False, "errors": [f"Invalid spec: {str(e)}"], "warnings": []}


class StrategyRunSpecRequest(BaseModel):
    strategy_spec: dict
    ticker: str = "SPY"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/strategies/run-spec")
async def run_strategy_spec_endpoint(req: StrategyRunSpecRequest):
    """Compile and execute a StrategySpec through the deterministic backtest engine."""
    from app.strategy_engine.schemas import StrategySpec
    from app.strategy_engine.validator import validate_strategy
    from app.strategy_engine.compiler import compile_strategy
    from app.strategy_engine.executor import execute_strategy

    try:
        spec = StrategySpec.model_validate(req.strategy_spec)
    except Exception as e:
        return {"result": None, "compiled_conditions_summary": [], "error": f"Invalid spec: {str(e)}"}

    # Validate
    validation = validate_strategy(spec)
    if not validation.valid:
        return {"result": None, "compiled_conditions_summary": [], "error": f"Validation errors: {'; '.join(validation.errors)}"}

    # Fetch data
    ticker = req.ticker.upper().strip()
    print(f"[run-spec] Running {spec.name} on {ticker}")
    df = await fetch_price_history_range(ticker, req.start_date, req.end_date)
    if df is None or len(df) < 40:
        return {"result": None, "compiled_conditions_summary": [], "error": f"Insufficient data for {ticker} ({len(df) if df is not None else 0} bars)"}

    try:
        # Compile
        compiled = compile_strategy(spec, df)
        # Execute
        result = execute_strategy(compiled, df)
        return {
            "result": result,
            "compiled_conditions_summary": compiled.compiled_conditions_summary,
            "error": None,
        }
    except Exception as e:
        traceback.print_exc()
        return {"result": None, "compiled_conditions_summary": [], "error": f"Engine error: {str(e)}"}
