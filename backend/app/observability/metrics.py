"""
Prometheus metrics for DCP.

Provides counters, histograms, and gauges for monitoring application behavior.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


# Decision metrics
decision_created_total = Counter(
    "dcp_decision_created_total",
    "Total number of decisions created",
    ["flow_id", "policy_result"],
)

decision_action_total = Counter(
    "dcp_decision_action_total",
    "Total number of decision actions taken",
    ["action_type", "actor_type"],
)

decision_expired_total = Counter(
    "dcp_decision_expired_total",
    "Total number of decisions that expired",
    ["flow_id"],
)

# Request metrics
request_duration_seconds = Histogram(
    "dcp_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

request_total = Counter(
    "dcp_request_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# Policy metrics
policy_evaluation_seconds = Histogram(
    "dcp_policy_evaluation_seconds",
    "Policy evaluation duration in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
)

policy_result_total = Counter(
    "dcp_policy_result_total",
    "Policy evaluation results",
    ["result", "matched_rule"],
)

# Gauge metrics
pending_decisions_gauge = Gauge(
    "dcp_pending_decisions",
    "Current number of pending decisions",
)

active_connections_gauge = Gauge(
    "dcp_active_connections",
    "Current number of active HTTP connections",
)

# Database metrics
db_query_duration_seconds = Histogram(
    "dcp_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# Event metrics
event_published_total = Counter(
    "dcp_event_published_total",
    "Total events published",
    ["event_type", "status"],
)


def get_metrics() -> bytes:
    """
    Generate Prometheus metrics output.

    Returns:
        Prometheus metrics in text format
    """
    return generate_latest()


def get_metrics_content_type() -> str:
    """
    Get the content type for Prometheus metrics.

    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST


# Helper functions for recording metrics
def record_decision_created(flow_id: str, policy_result: str) -> None:
    """Record a decision creation."""
    decision_created_total.labels(flow_id=flow_id, policy_result=policy_result).inc()


def record_decision_action(action_type: str, actor_type: str) -> None:
    """Record a decision action."""
    decision_action_total.labels(action_type=action_type, actor_type=actor_type).inc()


def record_policy_evaluation(duration: float, result: str, matched_rule: str | None) -> None:
    """Record a policy evaluation."""
    policy_evaluation_seconds.observe(duration)
    policy_result_total.labels(result=result, matched_rule=matched_rule or "default").inc()


def record_event_published(event_type: str, success: bool) -> None:
    """Record an event publication."""
    status = "success" if success else "failure"
    event_published_total.labels(event_type=event_type, status=status).inc()
