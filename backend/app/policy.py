from typing import Optional


def evaluate_policy(
    risk_score: Optional[float],
    confidence_score: Optional[float],
    estimated_cost: Optional[float],
    compliance_flags: Optional[list[str]],
) -> dict:
    """
    Simple heuristic policy:
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
