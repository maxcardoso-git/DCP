"""
Input validation utilities for DCP.

Provides validation functions for common input types.
"""
import re
from typing import Optional
from uuid import UUID

# UUID regex pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Dangerous characters that could be used for injection
DANGEROUS_CHARS = re.compile(r"[<>\"';\\\x00-\x1f]")

# Maximum lengths
MAX_STRING_LENGTH = 1000
MAX_COMMENT_LENGTH = 5000
MAX_FLOW_ID_LENGTH = 255
MAX_NODE_ID_LENGTH = 255


def validate_uuid(value: str) -> bool:
    """
    Validate that a string is a valid UUID.

    Args:
        value: String to validate

    Returns:
        True if valid UUID, False otherwise
    """
    if not value:
        return False

    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def sanitize_string(
    value: Optional[str],
    max_length: int = MAX_STRING_LENGTH,
    allow_newlines: bool = False,
) -> Optional[str]:
    """
    Sanitize a string input.

    Removes dangerous characters and enforces length limits.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        allow_newlines: Whether to allow newline characters

    Returns:
        Sanitized string or None
    """
    if value is None:
        return None

    # Convert to string if not already
    value = str(value)

    # Truncate to max length
    value = value[:max_length]

    # Remove dangerous characters
    value = DANGEROUS_CHARS.sub("", value)

    # Handle newlines
    if not allow_newlines:
        value = value.replace("\n", " ").replace("\r", " ")

    # Strip whitespace
    value = value.strip()

    return value if value else None


def validate_score(value: Optional[float], field_name: str = "score") -> Optional[float]:
    """
    Validate a score value (0.0 to 1.0).

    Args:
        value: Score value to validate
        field_name: Name of the field for error messages

    Returns:
        Validated score or None

    Raises:
        ValueError: If score is out of range
    """
    if value is None:
        return None

    try:
        score = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a number")

    if score < 0.0 or score > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")

    return score


def validate_cost(value: Optional[float], field_name: str = "cost") -> Optional[float]:
    """
    Validate a cost value (non-negative).

    Args:
        value: Cost value to validate
        field_name: Name of the field for error messages

    Returns:
        Validated cost or None

    Raises:
        ValueError: If cost is negative
    """
    if value is None:
        return None

    try:
        cost = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a number")

    if cost < 0:
        raise ValueError(f"{field_name} cannot be negative")

    return cost


def validate_flow_id(value: str) -> str:
    """
    Validate and sanitize a flow ID.

    Args:
        value: Flow ID to validate

    Returns:
        Validated flow ID

    Raises:
        ValueError: If flow ID is invalid
    """
    if not value:
        raise ValueError("flow_id is required")

    sanitized = sanitize_string(value, max_length=MAX_FLOW_ID_LENGTH)

    if not sanitized:
        raise ValueError("flow_id is invalid")

    # Check for valid characters (alphanumeric, dash, underscore)
    if not re.match(r"^[\w\-\.]+$", sanitized):
        raise ValueError("flow_id contains invalid characters")

    return sanitized


def validate_node_id(value: str) -> str:
    """
    Validate and sanitize a node ID.

    Args:
        value: Node ID to validate

    Returns:
        Validated node ID

    Raises:
        ValueError: If node ID is invalid
    """
    if not value:
        raise ValueError("node_id is required")

    sanitized = sanitize_string(value, max_length=MAX_NODE_ID_LENGTH)

    if not sanitized:
        raise ValueError("node_id is invalid")

    # Check for valid characters (alphanumeric, dash, underscore)
    if not re.match(r"^[\w\-\.]+$", sanitized):
        raise ValueError("node_id contains invalid characters")

    return sanitized


def validate_compliance_flags(flags: Optional[list[str]]) -> Optional[list[str]]:
    """
    Validate compliance flags list.

    Args:
        flags: List of compliance flags

    Returns:
        Validated flags list or None

    Raises:
        ValueError: If flags are invalid
    """
    if flags is None:
        return None

    if not isinstance(flags, list):
        raise ValueError("compliance_flags must be a list")

    if len(flags) > 50:
        raise ValueError("Too many compliance flags (max 50)")

    validated = []
    for flag in flags:
        sanitized = sanitize_string(str(flag), max_length=100)
        if sanitized:
            validated.append(sanitized)

    return validated if validated else None
