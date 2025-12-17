"""
Operators for the Policy DSL evaluation.

Supports comparison, logical, and collection operators.
"""
import re
from typing import Any, Callable

from .exceptions import InvalidOperatorError


def _safe_compare(a: Any, b: Any, op: Callable[[Any, Any], bool]) -> bool:
    """Safely compare two values, handling None cases."""
    if a is None or b is None:
        return False
    try:
        return op(float(a), float(b))
    except (ValueError, TypeError):
        return False


def op_gt(a: Any, b: Any) -> bool:
    """Greater than operator."""
    return _safe_compare(a, b, lambda x, y: x > y)


def op_gte(a: Any, b: Any) -> bool:
    """Greater than or equal operator."""
    return _safe_compare(a, b, lambda x, y: x >= y)


def op_lt(a: Any, b: Any) -> bool:
    """Less than operator."""
    return _safe_compare(a, b, lambda x, y: x < y)


def op_lte(a: Any, b: Any) -> bool:
    """Less than or equal operator."""
    return _safe_compare(a, b, lambda x, y: x <= y)


def op_eq(a: Any, b: Any) -> bool:
    """Equality operator."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    # Try numeric comparison first
    try:
        return float(a) == float(b)
    except (ValueError, TypeError):
        return str(a) == str(b)


def op_neq(a: Any, b: Any) -> bool:
    """Not equal operator."""
    return not op_eq(a, b)


def op_includes(collection: Any, value: Any) -> bool:
    """Check if collection contains value."""
    if collection is None:
        return False
    if isinstance(collection, (list, tuple, set)):
        return value in collection
    if isinstance(collection, str):
        return str(value) in collection
    return False


def op_missing(value: Any, _: Any = None) -> bool:
    """Check if value is None or empty."""
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict, str)) and len(value) == 0:
        return True
    return False


def op_exists(value: Any, _: Any = None) -> bool:
    """Check if value exists (not None and not empty)."""
    return not op_missing(value)


def op_in(value: Any, collection: Any) -> bool:
    """Check if value is in collection (reverse of includes)."""
    return op_includes(collection, value)


def op_matches(value: Any, pattern: Any) -> bool:
    """Check if value matches regex pattern."""
    if value is None or pattern is None:
        return False
    try:
        return bool(re.match(str(pattern), str(value)))
    except re.error:
        return False


# Operator registry
OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "gt": op_gt,
    "gte": op_gte,
    "lt": op_lt,
    "lte": op_lte,
    "eq": op_eq,
    "neq": op_neq,
    "includes": op_includes,
    "missing": op_missing,
    "exists": op_exists,
    "in": op_in,
    "matches": op_matches,
}


def get_operator(name: str) -> Callable[[Any, Any], bool]:
    """Get operator function by name."""
    if name not in OPERATORS:
        raise InvalidOperatorError(name)
    return OPERATORS[name]


def is_operator(name: str) -> bool:
    """Check if name is a valid operator."""
    return name in OPERATORS or name in ("all", "any")
