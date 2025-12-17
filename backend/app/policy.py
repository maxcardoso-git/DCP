"""
Policy evaluation module.

Provides both the legacy heuristic evaluation and the new DSL-based engine.
"""
import logging
from typing import Optional

from .policy.engine import PolicyEngine
from .policy.loader import get_policy_engine

logger = logging.getLogger("dcp.policy")

# Global policy engine instance
_engine: Optional[PolicyEngine] = None


def get_engine() -> PolicyEngine:
    """Get or create the policy engine singleton."""
    global _engine
    if _engine is None:
        _engine = get_policy_engine()
    return _engine


def evaluate_policy(
    risk_score: Optional[float],
    confidence_score: Optional[float],
    estimated_cost: Optional[float],
    compliance_flags: Optional[list[str]],
    impact_level: Optional[str] = None,
    use_engine: bool = True,
    **extra_context,
) -> dict:
    """
    Evaluate policy for a decision.

    Args:
        risk_score: Risk score (0.0 to 1.0)
        confidence_score: Confidence score (0.0 to 1.0)
        estimated_cost: Estimated cost of the decision
        compliance_flags: List of compliance flags (e.g., ["aml", "pep"])
        impact_level: Impact level (low, medium, high, critical)
        use_engine: Use DSL engine (True) or legacy heuristic (False)
        **extra_context: Additional context variables for policy evaluation

    Returns:
        Dictionary with 'result' and 'reason' keys
    """
    if use_engine:
        try:
            engine = get_engine()
            context = {
                "risk_score": risk_score,
                "confidence_score": confidence_score,
                "estimated_cost": estimated_cost,
                "compliance_flags": compliance_flags if compliance_flags else None,
                "impact_level": impact_level,
                **extra_context,
            }
            result = engine.evaluate(context)
            return {"result": result.result, "reason": result.reason}
        except Exception as e:
            logger.warning(f"Engine evaluation failed, falling back to heuristic: {e}")
            # Fall back to heuristic

    # Legacy heuristic policy
    return _evaluate_heuristic(risk_score, confidence_score, estimated_cost, compliance_flags)


def _evaluate_heuristic(
    risk_score: Optional[float],
    confidence_score: Optional[float],
    estimated_cost: Optional[float],
    compliance_flags: Optional[list[str]],
) -> dict:
    """
    Legacy heuristic policy evaluation.

    Rules:
    - force_escalation if risk >= 0.8 or compliance flag present
    - auto_approve if risk <= 0.2 and confidence >= 0.8 and cost <= 500
    - require_human otherwise
    """
    if compliance_flags and len(compliance_flags) > 0:
        return {"result": "force_escalation", "reason": "Compliance flag"}
    if risk_score is not None and risk_score >= 0.8:
        return {"result": "force_escalation", "reason": "High risk"}
    if (
        risk_score is not None
        and risk_score <= 0.2
        and confidence_score is not None
        and confidence_score >= 0.8
        and (estimated_cost is None or estimated_cost <= 500)
    ):
        return {"result": "auto_approve", "reason": "Low risk + high confidence"}
    return {"result": "require_human", "reason": "Default"}


def evaluate_with_full_result(
    risk_score: Optional[float],
    confidence_score: Optional[float],
    estimated_cost: Optional[float],
    compliance_flags: Optional[list[str]],
    impact_level: Optional[str] = None,
    **extra_context,
) -> dict:
    """
    Evaluate policy and return full result including evaluated rules.

    Returns:
        Dictionary with result, reason, matched_rule_id, and evaluated_rules
    """
    try:
        engine = get_engine()
        context = {
            "risk_score": risk_score,
            "confidence_score": confidence_score,
            "estimated_cost": estimated_cost,
            "compliance_flags": compliance_flags if compliance_flags else None,
            "impact_level": impact_level,
            **extra_context,
        }
        result = engine.evaluate(context)
        return result.to_dict()
    except Exception as e:
        logger.warning(f"Engine evaluation failed: {e}")
        heuristic_result = _evaluate_heuristic(
            risk_score, confidence_score, estimated_cost, compliance_flags
        )
        return {
            **heuristic_result,
            "matched_rule_id": "heuristic",
            "evaluated_rules": [{"id": "heuristic", "matched": True}],
        }
