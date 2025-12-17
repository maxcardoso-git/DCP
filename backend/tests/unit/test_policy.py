"""
Unit tests for the policy evaluation logic.
"""
import pytest
from app.policy import evaluate_policy


class TestEvaluatePolicy:
    """Tests for the evaluate_policy function."""

    # Force Escalation Tests

    @pytest.mark.unit
    def test_force_escalation_high_risk(self):
        """High risk score (>= 0.8) should force escalation."""
        result = evaluate_policy(
            risk_score=0.8,
            confidence_score=0.9,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert result["result"] == "force_escalation"
        assert "High risk" in result["reason"]

    @pytest.mark.unit
    def test_force_escalation_very_high_risk(self):
        """Very high risk score should force escalation."""
        result = evaluate_policy(
            risk_score=0.95,
            confidence_score=0.9,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert result["result"] == "force_escalation"

    @pytest.mark.unit
    def test_force_escalation_compliance_flag(self):
        """Presence of compliance flags should force escalation."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.9,
            estimated_cost=100,
            compliance_flags=["aml"],
        )
        assert result["result"] == "force_escalation"
        assert "Compliance" in result["reason"]

    @pytest.mark.unit
    def test_force_escalation_multiple_compliance_flags(self):
        """Multiple compliance flags should force escalation."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.9,
            estimated_cost=100,
            compliance_flags=["aml", "pep", "sanctions"],
        )
        assert result["result"] == "force_escalation"

    @pytest.mark.unit
    def test_compliance_flag_takes_precedence_over_low_risk(self):
        """Compliance flags should override auto-approve conditions."""
        result = evaluate_policy(
            risk_score=0.1,  # Low risk
            confidence_score=0.9,  # High confidence
            estimated_cost=100,  # Low cost
            compliance_flags=["kyc"],  # But has compliance flag
        )
        assert result["result"] == "force_escalation"

    # Auto Approve Tests

    @pytest.mark.unit
    def test_auto_approve_low_risk_high_confidence_low_cost(self):
        """Low risk + high confidence + low cost should auto approve."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.9,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert result["result"] == "auto_approve"
        assert "Low risk" in result["reason"]

    @pytest.mark.unit
    def test_auto_approve_boundary_risk(self):
        """Risk score exactly at 0.2 should still auto approve."""
        result = evaluate_policy(
            risk_score=0.2,
            confidence_score=0.8,
            estimated_cost=500,
            compliance_flags=None,
        )
        assert result["result"] == "auto_approve"

    @pytest.mark.unit
    def test_auto_approve_boundary_confidence(self):
        """Confidence score exactly at 0.8 should still auto approve."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.8,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert result["result"] == "auto_approve"

    @pytest.mark.unit
    def test_auto_approve_boundary_cost(self):
        """Cost exactly at 500 should still auto approve."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.9,
            estimated_cost=500,
            compliance_flags=None,
        )
        assert result["result"] == "auto_approve"

    @pytest.mark.unit
    def test_auto_approve_null_cost(self):
        """Null cost should allow auto approve if other conditions met."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.9,
            estimated_cost=None,
            compliance_flags=None,
        )
        assert result["result"] == "auto_approve"

    # Require Human Tests

    @pytest.mark.unit
    def test_require_human_medium_risk(self):
        """Medium risk score should require human review."""
        result = evaluate_policy(
            risk_score=0.5,
            confidence_score=0.7,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert result["result"] == "require_human"
        assert "Default" in result["reason"]

    @pytest.mark.unit
    def test_require_human_risk_above_threshold(self):
        """Risk score just above 0.2 should require human review."""
        result = evaluate_policy(
            risk_score=0.21,
            confidence_score=0.9,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert result["result"] == "require_human"

    @pytest.mark.unit
    def test_require_human_confidence_below_threshold(self):
        """Confidence score below 0.8 should require human review."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.79,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert result["result"] == "require_human"

    @pytest.mark.unit
    def test_require_human_cost_above_threshold(self):
        """Cost above 500 should require human review."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.9,
            estimated_cost=501,
            compliance_flags=None,
        )
        assert result["result"] == "require_human"

    @pytest.mark.unit
    def test_require_human_high_cost(self):
        """Very high cost should require human review."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.9,
            estimated_cost=10000,
            compliance_flags=None,
        )
        assert result["result"] == "require_human"

    # Null/None Values Tests

    @pytest.mark.unit
    def test_null_risk_score(self):
        """Null risk score should require human review."""
        result = evaluate_policy(
            risk_score=None,
            confidence_score=0.9,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert result["result"] == "require_human"

    @pytest.mark.unit
    def test_null_confidence_score(self):
        """Null confidence score should require human review."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=None,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert result["result"] == "require_human"

    @pytest.mark.unit
    def test_all_null_values(self):
        """All null values should require human review."""
        result = evaluate_policy(
            risk_score=None,
            confidence_score=None,
            estimated_cost=None,
            compliance_flags=None,
        )
        assert result["result"] == "require_human"

    @pytest.mark.unit
    def test_empty_compliance_flags(self):
        """Empty compliance flags list should not force escalation."""
        result = evaluate_policy(
            risk_score=0.1,
            confidence_score=0.9,
            estimated_cost=100,
            compliance_flags=[],
        )
        assert result["result"] == "auto_approve"

    # Edge Cases

    @pytest.mark.unit
    def test_risk_score_zero(self):
        """Zero risk score with high confidence should auto approve."""
        result = evaluate_policy(
            risk_score=0.0,
            confidence_score=1.0,
            estimated_cost=0,
            compliance_flags=None,
        )
        assert result["result"] == "auto_approve"

    @pytest.mark.unit
    def test_risk_score_one(self):
        """Risk score of 1.0 should force escalation."""
        result = evaluate_policy(
            risk_score=1.0,
            confidence_score=1.0,
            estimated_cost=0,
            compliance_flags=None,
        )
        assert result["result"] == "force_escalation"

    @pytest.mark.unit
    def test_result_contains_required_keys(self):
        """Result should always contain 'result' and 'reason' keys."""
        result = evaluate_policy(
            risk_score=0.5,
            confidence_score=0.5,
            estimated_cost=100,
            compliance_flags=None,
        )
        assert "result" in result
        assert "reason" in result
        assert result["result"] in ["auto_approve", "require_human", "force_escalation"]
