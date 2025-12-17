"""
Custom exceptions for the Policy Engine.
"""


class PolicyError(Exception):
    """Base exception for policy-related errors."""

    pass


class PolicyLoadError(PolicyError):
    """Raised when a policy file cannot be loaded or parsed."""

    pass


class PolicyEvaluationError(PolicyError):
    """Raised when policy evaluation fails."""

    pass


class InvalidOperatorError(PolicyEvaluationError):
    """Raised when an unknown operator is used in a policy rule."""

    def __init__(self, operator: str):
        self.operator = operator
        super().__init__(f"Unknown operator: {operator}")


class InvalidConditionError(PolicyEvaluationError):
    """Raised when a condition is malformed."""

    def __init__(self, condition: dict, reason: str):
        self.condition = condition
        self.reason = reason
        super().__init__(f"Invalid condition {condition}: {reason}")
