"""Compile a validated StrategySpec into executable boolean signal Series.

The compiler:
1. Iterates all conditions in entry/exit/filters
2. For each IndicatorReference, calls compute_indicator(df, key, params)
3. For each Condition, evaluates the operator via a dispatch table
4. Combines conditions within a group using logic ("and" = &, "or" = |)
5. Combines groups (entry groups are OR'd together -- any group triggering = entry)
6. Returns CompiledStrategy with all signal Series

Security: NEVER uses eval() or exec(). All lookups go through a fixed dispatch table.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.strategy_engine.schemas import (
    Condition,
    ConditionGroup,
    IndicatorReference,
    StrategySpec,
)

# ---------------------------------------------------------------------------
# Import the indicator catalog & compute function.
# Fall back gracefully so the module can be imported before they exist.
# ---------------------------------------------------------------------------
try:
    from app.indicators.registry import INDICATOR_CATALOG
except ImportError:
    INDICATOR_CATALOG: dict = {}

try:
    from app.indicators.calculations import compute_indicator
except ImportError:
    # Provide a thin fallback that wraps the legacy technical.py module.
    from app.indicators.technical import (
        sma, ema, rsi, macd, atr, bollinger_bands, obv,
        rolling_volatility, stochastic, cci, williams_r, mfi, adx,
    )

    def compute_indicator(key: str, df: pd.DataFrame, params: dict | None = None) -> pd.Series:
        """Minimal fallback when app.indicators.calculations is unavailable."""
        params = params or {}
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"].astype(float)

        _dispatch: dict[str, callable] = {
            "sma": lambda: sma(close, int(params.get("period", 20))),
            "ema": lambda: ema(close, int(params.get("period", 20))),
            "rsi": lambda: rsi(close, int(params.get("period", 14))),
            "atr": lambda: atr(high, low, close, int(params.get("period", 14))),
            "cci": lambda: cci(high, low, close, int(params.get("period", 20))),
            "williams_r": lambda: williams_r(high, low, close, int(params.get("period", 14))),
            "mfi": lambda: mfi(high, low, close, volume, int(params.get("period", 14))),
            "obv": lambda: obv(close, volume),
            "rolling_volatility": lambda: rolling_volatility(close, int(params.get("period", 20))),
        }

        # MACD sub-components
        def _macd_component(component: str) -> pd.Series:
            m = macd(
                close,
                int(params.get("fast", 12)),
                int(params.get("slow", 26)),
                int(params.get("signal_period", 9)),
            )
            return m[component]

        _dispatch["macd_line"] = lambda: _macd_component("macd")
        _dispatch["macd_signal"] = lambda: _macd_component("signal")
        _dispatch["macd_histogram"] = lambda: _macd_component("histogram")

        # Bollinger sub-components
        def _bb_component(component: str) -> pd.Series:
            bb = bollinger_bands(
                close,
                int(params.get("period", 20)),
                float(params.get("std_dev", 2.0)),
            )
            return bb[component]

        _dispatch["bbands_upper"] = lambda: _bb_component("upper")
        _dispatch["bbands_middle"] = lambda: _bb_component("middle")
        _dispatch["bbands_lower"] = lambda: _bb_component("lower")
        _dispatch["bbands_width"] = lambda: _bb_component("bandwidth")
        _dispatch["bbands_pctb"] = lambda: _bb_component("pct_b")

        # Legacy aliases
        _dispatch["bollinger_upper"] = _dispatch["bbands_upper"]
        _dispatch["bollinger_middle"] = _dispatch["bbands_middle"]
        _dispatch["bollinger_lower"] = _dispatch["bbands_lower"]
        _dispatch["bollinger_bandwidth"] = _dispatch["bbands_width"]
        _dispatch["bollinger_pct_b"] = _dispatch["bbands_pctb"]

        # Stochastic sub-components
        def _stoch_component(component: str) -> pd.Series:
            st = stochastic(
                high, low, close,
                int(params.get("k_period", 14)),
                int(params.get("d_period", 3)),
            )
            return st[component]

        _dispatch["stoch_k"] = lambda: _stoch_component("k")
        _dispatch["stoch_d"] = lambda: _stoch_component("d")
        _dispatch["stochastic_k"] = _dispatch["stoch_k"]
        _dispatch["stochastic_d"] = _dispatch["stoch_d"]

        # ADX sub-components
        def _adx_component(component: str) -> pd.Series:
            a = adx(high, low, close, int(params.get("period", 14)))
            return a[component]

        _dispatch["adx_value"] = lambda: _adx_component("adx")
        _dispatch["adx"] = _dispatch["adx_value"]
        _dispatch["plus_di"] = lambda: _adx_component("plus_di")
        _dispatch["minus_di"] = lambda: _adx_component("minus_di")

        fn = _dispatch.get(key)
        if fn is None:
            raise ValueError(f"Unknown indicator key in fallback compute: '{key}'")
        return fn()


# ---------------------------------------------------------------------------
# CompiledStrategy
# ---------------------------------------------------------------------------

@dataclass
class CompiledStrategy:
    """Holds the boolean signal Series produced by compiling a StrategySpec."""

    spec: StrategySpec
    long_entry_signals: pd.Series      # boolean Series -- True on long entry bars
    short_entry_signals: pd.Series     # boolean Series -- True on short entry bars
    long_exit_signals: pd.Series       # boolean Series -- True on long exit bars
    short_exit_signals: pd.Series      # boolean Series -- True on short exit bars
    filter_mask: pd.Series             # boolean Series -- True where filters pass
    indicators_computed: dict[str, pd.Series] = field(default_factory=dict)
    compiled_conditions_summary: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Price field helpers
# ---------------------------------------------------------------------------

_PRICE_FIELDS = {"close", "open", "high", "low", "volume"}


def _resolve_series(
    operand: IndicatorReference | str | float,
    df: pd.DataFrame,
    cache: dict[str, pd.Series],
    indicators_computed: dict[str, pd.Series],
) -> pd.Series:
    """Resolve an operand to a pd.Series aligned with *df*'s index.

    - IndicatorReference -> compute (or cache-hit) the indicator.
    - str price field    -> return that column.
    - float / int        -> return a constant Series.
    """
    # Coerce dict → IndicatorReference (from JSON deserialization with Any type)
    if isinstance(operand, dict) and "indicator_key" in operand:
        operand = IndicatorReference(**operand)

    if isinstance(operand, IndicatorReference):
        cache_key = f"{operand.indicator_key}|{sorted(operand.params.items())}"
        if cache_key not in cache:
            series = compute_indicator(df, operand.indicator_key, operand.params or {})
            cache[cache_key] = series
            label = operand.alias or operand.indicator_key
            indicators_computed[label] = series
        return cache[cache_key]

    if isinstance(operand, str):
        col = operand.lower()
        if col in _PRICE_FIELDS and col in df.columns:
            return df[col].astype(float)
        # Maybe it's a number as a string
        try:
            return pd.Series(float(operand), index=df.index)
        except (ValueError, TypeError):
            raise ValueError(f"Unknown price field '{operand}'.")

    # Numeric constant
    if isinstance(operand, (int, float)):
        return pd.Series(float(operand), index=df.index)

    raise ValueError(f"Cannot resolve operand: {operand!r}")


# ---------------------------------------------------------------------------
# Operator dispatch (no eval!)
# ---------------------------------------------------------------------------

_EPSILON = 1e-9


def _apply_operator(
    left: pd.Series,
    operator: str,
    right: pd.Series,
    right_upper: float | None,
    df: pd.DataFrame,
) -> pd.Series:
    """Return a boolean Series for one condition using a dispatch table."""
    left = left.astype(float)
    right = right.astype(float)

    if operator == "gt":
        return left > right
    if operator == "lt":
        return left < right
    if operator == "gte":
        return left >= right
    if operator == "lte":
        return left <= right
    if operator == "eq":
        return (left - right).abs() < _EPSILON

    if operator == "crosses_above":
        prev_left = left.shift(1)
        prev_right = right.shift(1)
        return (prev_left <= prev_right) & (left > right)

    if operator == "crosses_below":
        prev_left = left.shift(1)
        prev_right = right.shift(1)
        return (prev_left >= prev_right) & (left < right)

    if operator == "between":
        if right_upper is None:
            raise ValueError("Operator 'between' requires right_upper.")
        upper = pd.Series(float(right_upper), index=df.index)
        return (left >= right) & (left <= upper)

    raise ValueError(f"Unknown operator '{operator}'.")


# ---------------------------------------------------------------------------
# Condition / group evaluation
# ---------------------------------------------------------------------------

def _eval_condition(
    cond: Condition,
    df: pd.DataFrame,
    cache: dict[str, pd.Series],
    indicators_computed: dict[str, pd.Series],
    summaries: list[str],
) -> pd.Series:
    """Evaluate a single Condition into a boolean Series."""
    left_series = _resolve_series(cond.left, df, cache, indicators_computed)
    right_series = _resolve_series(cond.right, df, cache, indicators_computed)
    result = _apply_operator(left_series, cond.operator, right_series, cond.right_upper, df)

    # Build human-readable summary
    left_label = (
        cond.left.alias or cond.left.indicator_key
        if isinstance(cond.left, IndicatorReference)
        else str(cond.left)
    )
    right_label = (
        cond.right.alias or cond.right.indicator_key
        if isinstance(cond.right, IndicatorReference)
        else str(cond.right)
    )
    summary = f"{left_label} {cond.operator} {right_label}"
    if cond.operator == "between" and cond.right_upper is not None:
        summary += f" .. {cond.right_upper}"
    summaries.append(summary)

    # Fill NaN with False (missing indicator data = condition not met)
    return result.fillna(False).astype(bool)


def _eval_condition_group(
    group: ConditionGroup,
    df: pd.DataFrame,
    cache: dict[str, pd.Series],
    indicators_computed: dict[str, pd.Series],
    summaries: list[str],
) -> pd.Series:
    """Evaluate a ConditionGroup into a single boolean Series.

    Conditions within a group are combined using the group's logic
    ("and" = &, "or" = |).
    """
    if not group.conditions:
        # Empty group -- vacuously True
        return pd.Series(True, index=df.index)

    results: list[pd.Series] = []
    for cond in group.conditions:
        results.append(_eval_condition(cond, df, cache, indicators_computed, summaries))

    if group.logic == "and":
        combined = results[0]
        for s in results[1:]:
            combined = combined & s
        return combined
    else:  # "or"
        combined = results[0]
        for s in results[1:]:
            combined = combined | s
        return combined


def _eval_condition_groups(
    groups: list[ConditionGroup],
    df: pd.DataFrame,
    cache: dict[str, pd.Series],
    indicators_computed: dict[str, pd.Series],
    summaries: list[str],
) -> pd.Series:
    """Evaluate a list of ConditionGroups combined with OR logic.

    Multiple groups act as independent rule-sets: if *any* group fires,
    the overall signal is True (OR across groups).
    """
    if not groups:
        return pd.Series(False, index=df.index)

    overall = pd.Series(False, index=df.index)
    for group in groups:
        overall = overall | _eval_condition_group(group, df, cache, indicators_computed, summaries)
    return overall


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compile_strategy(spec: StrategySpec, df: pd.DataFrame) -> CompiledStrategy:
    """Compile a StrategySpec into boolean signal Series.

    The compiler:
    1. Iterates all conditions in entry/exit/filters
    2. For each IndicatorReference, calls compute_indicator(df, key, params)
    3. For each Condition, evaluates the operator via the dispatch table
    4. Combines conditions within a group using logic ("and" = &, "or" = |)
    5. Combines groups (entry groups are OR'd together)
    6. Returns CompiledStrategy with all signal Series

    Parameters
    ----------
    spec : StrategySpec
        A validated strategy specification.
    df : pd.DataFrame
        OHLCV DataFrame with columns: date, open, high, low, close, volume.

    Returns
    -------
    CompiledStrategy
    """
    cache: dict[str, pd.Series] = {}
    indicators_computed: dict[str, pd.Series] = {}
    summaries: list[str] = []

    # -- Entry signals -----------------------------------------------------
    long_entry = _eval_condition_groups(
        spec.entry.long_conditions, df, cache, indicators_computed, summaries,
    )
    short_entry = _eval_condition_groups(
        spec.entry.short_conditions, df, cache, indicators_computed, summaries,
    )

    # -- Exit signals ------------------------------------------------------
    long_exit = _eval_condition_groups(
        spec.exit.long_exit_conditions, df, cache, indicators_computed, summaries,
    )
    short_exit = _eval_condition_groups(
        spec.exit.short_exit_conditions, df, cache, indicators_computed, summaries,
    )

    # -- Global filters ----------------------------------------------------
    if spec.filters:
        filter_mask = _eval_condition_groups(
            spec.filters, df, cache, indicators_computed, summaries,
        )
    else:
        filter_mask = pd.Series(True, index=df.index)

    # -- Mask by direction -------------------------------------------------
    if spec.direction == "long_only":
        short_entry = pd.Series(False, index=df.index)
    elif spec.direction == "short_only":
        long_entry = pd.Series(False, index=df.index)

    # Apply filter mask to entries
    long_entry = long_entry & filter_mask
    short_entry = short_entry & filter_mask

    return CompiledStrategy(
        spec=spec,
        long_entry_signals=long_entry.astype(bool),
        short_entry_signals=short_entry.astype(bool),
        long_exit_signals=long_exit.astype(bool),
        short_exit_signals=short_exit.astype(bool),
        filter_mask=filter_mask.astype(bool),
        indicators_computed=indicators_computed,
        compiled_conditions_summary=summaries,
    )
