"""Validate a StrategySpec against the indicator catalog and internal rules.

Checks:
- All indicator_keys in conditions exist in INDICATOR_CATALOG
- Operators are valid for the indicator's output_type
- Required fields are present (the df will have open, high, low, close, volume)
- Parameters are reasonable (positive periods, etc.)
- At least one entry condition exists
- Direction matches conditions (long_only shouldn't have short_conditions, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.strategy_engine.schemas import (
    Condition,
    ConditionGroup,
    IndicatorReference,
    StrategySpec,
    StrategyValidateRequest,
)

# ---------------------------------------------------------------------------
# Import the indicator catalog.
# Fall back to an empty dict so the module can still be imported.
# ---------------------------------------------------------------------------
try:
    from app.indicators.registry import INDICATOR_CATALOG
except ImportError:
    INDICATOR_CATALOG: dict = {}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_OPERATORS = {
    "gt", "lt", "gte", "lte", "eq",
    "crosses_above", "crosses_below",
    "between",
}

# Operators that only make sense for numeric output types
_NUMERIC_ONLY_OPERATORS = {
    "gt", "lt", "gte", "lte",
    "crosses_above", "crosses_below",
    "between",
}

VALID_DIRECTIONS = {"long_only", "short_only", "long_short"}
VALID_SIZING_MODES = {"fixed", "atr_based", "volatility_scaled"}
PRICE_FIELDS = {"close", "open", "high", "low", "volume"}

# Reasonable hard limits for indicator parameters
_MAX_PERIOD = 1000
_MIN_PERIOD = 1
_MAX_MULTIPLIER = 100.0


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of validating a StrategySpec."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_indicator_ref(
    ref: IndicatorReference,
    errors: list[str],
    warnings: list[str],
    location: str,
) -> None:
    """Check that an IndicatorReference points to a valid catalog entry."""
    key = ref.indicator_key

    if not key:
        errors.append(f"{location}: indicator_key is empty.")
        return

    if INDICATOR_CATALOG:
        if key not in INDICATOR_CATALOG:
            errors.append(
                f"{location}: indicator_key '{key}' not found in the catalog."
            )
            return

        meta = INDICATOR_CATALOG[key]
        default_params = meta.get("parameters", meta.get("default_params", {}))

        # Warn about unknown parameter names
        for pname in ref.params:
            if pname not in default_params:
                warnings.append(
                    f"{location}: parameter '{pname}' is not a recognised "
                    f"parameter of indicator '{key}'. Known params: "
                    f"{list(default_params.keys())}."
                )

    # Check parameter value ranges
    for pname, pval in ref.params.items():
        if isinstance(pval, (int, float)):
            if "period" in pname or "length" in pname or "window" in pname:
                if pval < _MIN_PERIOD:
                    errors.append(
                        f"{location}: parameter '{pname}' = {pval} is below "
                        f"minimum period ({_MIN_PERIOD})."
                    )
                if pval > _MAX_PERIOD:
                    warnings.append(
                        f"{location}: parameter '{pname}' = {pval} is unusually "
                        f"large (>{_MAX_PERIOD})."
                    )
            if "multiplier" in pname or "mult" in pname:
                if pval <= 0:
                    errors.append(
                        f"{location}: parameter '{pname}' = {pval} must be positive."
                    )
                if pval > _MAX_MULTIPLIER:
                    warnings.append(
                        f"{location}: parameter '{pname}' = {pval} is unusually "
                        f"large (>{_MAX_MULTIPLIER})."
                    )


def _check_operator_for_output_type(
    operator: str,
    indicator_key: str,
    errors: list[str],
    location: str,
) -> None:
    """Check that the operator is compatible with the indicator's output_type."""
    if not INDICATOR_CATALOG or indicator_key not in INDICATOR_CATALOG:
        return
    meta = INDICATOR_CATALOG[indicator_key]
    supported = meta.get("supported_operators", [])
    if supported and operator not in supported:
        errors.append(
            f"{location}: operator '{operator}' is not supported by indicator "
            f"'{indicator_key}' (output_type={meta.get('output_type', '?')}). "
            f"Supported: {supported}."
        )


def _validate_operand(
    operand,
    errors: list,
    warnings: list,
    location: str,
) -> None:
    """Validate one side of a condition (left or right)."""
    # Coerce dict → IndicatorReference
    if isinstance(operand, dict) and "indicator_key" in operand:
        try:
            operand = IndicatorReference(**operand)
        except Exception:
            errors.append(f"{location}: invalid IndicatorReference dict: {operand}")
            return

    if isinstance(operand, IndicatorReference):
        _validate_indicator_ref(operand, errors, warnings, location)
    elif isinstance(operand, str):
        if operand not in PRICE_FIELDS:
            warnings.append(
                f"{location}: operand string '{operand}' is not a recognised "
                f"price field ({', '.join(sorted(PRICE_FIELDS))}). If this "
                f"was meant to be an indicator, use an IndicatorReference."
            )
    # float / int is always acceptable


def _validate_condition(
    cond: Condition,
    errors: list[str],
    warnings: list[str],
    location: str,
) -> None:
    """Validate a single Condition."""
    # Operator
    if cond.operator not in VALID_OPERATORS:
        errors.append(
            f"{location}: operator '{cond.operator}' is not valid. "
            f"Must be one of {sorted(VALID_OPERATORS)}."
        )

    # Left operand
    _validate_operand(cond.left, errors, warnings, f"{location}.left")

    # Right operand
    _validate_operand(cond.right, errors, warnings, f"{location}.right")

    # Check operator compatibility with indicator output_type
    left_op = cond.left
    if isinstance(left_op, dict) and "indicator_key" in left_op:
        try:
            left_op = IndicatorReference(**left_op)
        except Exception:
            pass
    if isinstance(left_op, IndicatorReference):
        _check_operator_for_output_type(
            cond.operator, left_op.indicator_key, errors, location
        )

    # "between" requires right_upper
    if cond.operator == "between":
        if cond.right_upper is None:
            errors.append(
                f"{location}: operator 'between' requires 'right_upper' to be set."
            )
        elif isinstance(cond.right, (int, float)) and cond.right_upper <= cond.right:
            errors.append(
                f"{location}: 'right_upper' ({cond.right_upper}) must be greater "
                f"than 'right' ({cond.right}) for 'between' operator."
            )


def _validate_condition_group(
    group: ConditionGroup,
    errors: list[str],
    warnings: list[str],
    location: str,
) -> None:
    """Validate a ConditionGroup."""
    if group.logic not in ("and", "or"):
        errors.append(f"{location}: logic must be 'and' or 'or', got '{group.logic}'.")
    for idx, cond in enumerate(group.conditions):
        _validate_condition(cond, errors, warnings, f"{location}.conditions[{idx}]")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_strategy(spec: StrategySpec) -> ValidationResult:
    """Validate a StrategySpec against the indicator catalog and internal rules.

    Checks:
    - All indicator_keys in conditions exist in INDICATOR_CATALOG
    - Operators are valid for the indicator's output_type
    - Required fields are present (open, high, low, close, volume)
    - Parameters are reasonable (positive periods, etc.)
    - At least one entry condition exists
    - Direction matches conditions (long_only shouldn't have short_conditions)

    Returns
    -------
    ValidationResult with valid flag, errors, and warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # -- Direction ----------------------------------------------------------
    if spec.direction not in VALID_DIRECTIONS:
        errors.append(
            f"direction '{spec.direction}' is invalid. "
            f"Must be one of {sorted(VALID_DIRECTIONS)}."
        )

    # -- At least one entry condition ---------------------------------------
    has_long_entry = any(
        len(g.conditions) > 0 for g in spec.entry.long_conditions
    )
    has_short_entry = any(
        len(g.conditions) > 0 for g in spec.entry.short_conditions
    )

    if not has_long_entry and not has_short_entry:
        errors.append("At least one entry condition (long or short) is required.")

    # -- Direction consistency ----------------------------------------------
    if spec.direction == "long_only" and has_short_entry and not has_long_entry:
        errors.append(
            "direction is 'long_only' but only short entry conditions are defined."
        )
    if spec.direction == "short_only" and has_long_entry and not has_short_entry:
        errors.append(
            "direction is 'short_only' but only long entry conditions are defined."
        )

    # Warn about mismatched direction / conditions
    if spec.direction == "long_only" and has_short_entry:
        warnings.append(
            "direction is 'long_only' but short entry conditions are present. "
            "Short conditions will be ignored."
        )
    if spec.direction == "short_only" and has_long_entry:
        warnings.append(
            "direction is 'short_only' but long entry conditions are present. "
            "Long conditions will be ignored."
        )

    # -- Validate all condition groups --------------------------------------
    for idx, g in enumerate(spec.entry.long_conditions):
        _validate_condition_group(g, errors, warnings, f"entry.long_conditions[{idx}]")

    for idx, g in enumerate(spec.entry.short_conditions):
        _validate_condition_group(g, errors, warnings, f"entry.short_conditions[{idx}]")

    for idx, g in enumerate(spec.exit.long_exit_conditions):
        _validate_condition_group(g, errors, warnings, f"exit.long_exit_conditions[{idx}]")

    for idx, g in enumerate(spec.exit.short_exit_conditions):
        _validate_condition_group(g, errors, warnings, f"exit.short_exit_conditions[{idx}]")

    for idx, g in enumerate(spec.filters):
        _validate_condition_group(g, errors, warnings, f"filters[{idx}]")

    # -- Risk parameters ----------------------------------------------------
    risk = spec.risk

    if risk.stop_loss_pct is not None and risk.stop_loss_pct <= 0:
        errors.append("risk.stop_loss_pct must be positive if set.")
    if risk.stop_loss_pct is not None and risk.stop_loss_pct > 100:
        warnings.append("risk.stop_loss_pct > 100% seems unusually large.")

    if risk.take_profit_pct is not None and risk.take_profit_pct <= 0:
        errors.append("risk.take_profit_pct must be positive if set.")
    if risk.take_profit_pct is not None and risk.take_profit_pct > 1000:
        warnings.append("risk.take_profit_pct > 1000% seems unusually large.")

    if risk.trailing_stop_pct is not None and risk.trailing_stop_pct <= 0:
        errors.append("risk.trailing_stop_pct must be positive if set.")

    if risk.trailing_stop_atr_mult is not None and risk.trailing_stop_atr_mult <= 0:
        errors.append("risk.trailing_stop_atr_mult must be positive if set.")

    if risk.max_positions < 1:
        errors.append("risk.max_positions must be >= 1.")

    if risk.sizing_mode not in VALID_SIZING_MODES:
        errors.append(
            f"risk.sizing_mode '{risk.sizing_mode}' is invalid. "
            f"Must be one of {sorted(VALID_SIZING_MODES)}."
        )

    if risk.risk_per_trade_pct <= 0:
        errors.append("risk.risk_per_trade_pct must be positive.")
    if risk.risk_per_trade_pct > 100:
        warnings.append("risk.risk_per_trade_pct > 100% is extremely aggressive.")

    is_valid = len(errors) == 0
    return ValidationResult(valid=is_valid, errors=errors, warnings=warnings)
