"""
Observability module for DCP.

Provides metrics, structured logging, and request tracing.
"""
from .metrics import (
    decision_created_total,
    decision_action_total,
    request_duration_seconds,
    policy_evaluation_seconds,
    pending_decisions_gauge,
    get_metrics,
)
from .logging import setup_logging, get_logger
from .middleware import RequestTracingMiddleware, MetricsMiddleware

__all__ = [
    "decision_created_total",
    "decision_action_total",
    "request_duration_seconds",
    "policy_evaluation_seconds",
    "pending_decisions_gauge",
    "get_metrics",
    "setup_logging",
    "get_logger",
    "RequestTracingMiddleware",
    "MetricsMiddleware",
]
