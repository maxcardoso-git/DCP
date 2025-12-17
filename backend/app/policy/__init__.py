"""
Policy Engine module for DCP.

Provides JSON-based DSL evaluation for decision policies.
"""
from .engine import PolicyEngine, PolicyResult
from .loader import load_policy_from_file, load_policy_from_dict
from .exceptions import PolicyEvaluationError, PolicyLoadError

__all__ = [
    "PolicyEngine",
    "PolicyResult",
    "load_policy_from_file",
    "load_policy_from_dict",
    "PolicyEvaluationError",
    "PolicyLoadError",
]
