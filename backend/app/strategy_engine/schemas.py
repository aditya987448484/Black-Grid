"""Pydantic v2 models for the strategy engine (Python 3.9 + Pydantic 2.4 compatible)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class IndicatorReference(BaseModel):
    indicator_key: str
    params: Dict[str, Any] = {}
    alias: Optional[str] = None


class Condition(BaseModel):
    """A single comparison condition.

    left / right can be:
      - An IndicatorReference dict  {"indicator_key": "rsi", "params": {"period": 14}}
      - A price field string        "close", "open", "high", "low", "volume"
      - A numeric literal           30, 70.5
    """
    left: Any  # IndicatorReference | str | float
    operator: str  # gt, lt, gte, lte, eq, crosses_above, crosses_below, between
    right: Any  # IndicatorReference | str | float
    right_upper: Optional[float] = None  # for "between" operator


class ConditionGroup(BaseModel):
    logic: str = "and"  # "and" or "or"
    conditions: List[Condition] = []


class EntryRuleSet(BaseModel):
    long_conditions: List[ConditionGroup] = []
    short_conditions: List[ConditionGroup] = []


class ExitRuleSet(BaseModel):
    long_exit_conditions: List[ConditionGroup] = []
    short_exit_conditions: List[ConditionGroup] = []


class RiskRuleSet(BaseModel):
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    trailing_stop_atr_mult: Optional[float] = None
    max_positions: int = 1
    sizing_mode: str = "fixed"
    risk_per_trade_pct: float = 1.0


class StrategySpec(BaseModel):
    name: str = "Custom Strategy"
    ticker: Optional[str] = None
    direction: str = "long_only"
    timeframe: str = "1d"
    entry: EntryRuleSet = EntryRuleSet()
    exit: ExitRuleSet = ExitRuleSet()
    risk: RiskRuleSet = RiskRuleSet()
    filters: List[ConditionGroup] = []
    notes: str = ""


class StrategyParseResponse(BaseModel):
    reply: str
    strategy_spec: Optional[StrategySpec] = None
    interpretation_summary: str = ""
    assumptions: List[str] = []
    unsupported_clauses: List[str] = []
    confidence: float = 0.0
    can_run_immediately: bool = False


class StrategyRunRequest(BaseModel):
    strategy_spec: StrategySpec
    ticker: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class StrategyRunResponse(BaseModel):
    result: Optional[dict] = None
    compiled_conditions_summary: List[str] = []
    error: Optional[str] = None


class StrategyParseRequest(BaseModel):
    message: str
    history: List[dict] = []
    ticker: str = "SPY"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    api_key: Optional[str] = None
    file_context: Optional[str] = None


class StrategyValidateRequest(BaseModel):
    strategy_spec: StrategySpec
