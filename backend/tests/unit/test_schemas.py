"""
Unit tests for Pydantic schemas validation.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from app.schemas import (
    DecisionCreate,
    DecisionActionIn,
    DecisionModifyIn,
    DecisionRecommendationIn,
    DecisionPolicySnapshotIn,
    DecisionOut,
)


class TestDecisionCreate:
    """Tests for DecisionCreate schema validation."""

    @pytest.mark.unit
    def test_valid_decision_create(self):
        """Valid decision create payload should pass validation."""
        data = DecisionCreate(
            execution_id=uuid4(),
            flow_id="test-flow",
            node_id="test-node",
            language="en",
            risk_score=0.5,
            confidence_score=0.7,
            estimated_cost=100.0,
            recommendation=DecisionRecommendationIn(
                summary="Test summary",
                detailed_explanation={"reason": "test"},
            ),
        )
        assert data.flow_id == "test-flow"
        assert data.language == "en"

    @pytest.mark.unit
    def test_decision_create_with_minimal_data(self):
        """Decision create with only required fields should pass."""
        data = DecisionCreate(
            execution_id=uuid4(),
            flow_id="flow",
            node_id="node",
            recommendation=DecisionRecommendationIn(),
        )
        assert data.language == "en"  # default
        assert data.risk_score is None
        assert data.confidence_score is None

    @pytest.mark.unit
    def test_decision_create_with_compliance_flags(self):
        """Decision create with compliance flags should pass."""
        data = DecisionCreate(
            execution_id=uuid4(),
            flow_id="flow",
            node_id="node",
            compliance_flags=["aml", "pep"],
            recommendation=DecisionRecommendationIn(),
        )
        assert data.compliance_flags == ["aml", "pep"]

    @pytest.mark.unit
    def test_decision_create_with_policy_snapshot(self):
        """Decision create with policy snapshot should pass."""
        data = DecisionCreate(
            execution_id=uuid4(),
            flow_id="flow",
            node_id="node",
            recommendation=DecisionRecommendationIn(),
            policy_snapshot=DecisionPolicySnapshotIn(
                policy_version="v2.0.0",
                evaluated_rules=[{"id": "rule1", "outcome": "require_human"}],
                result="require_human",
            ),
        )
        assert data.policy_snapshot.policy_version == "v2.0.0"

    @pytest.mark.unit
    def test_decision_create_missing_execution_id(self):
        """Decision create without execution_id should fail."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionCreate(
                flow_id="flow",
                node_id="node",
                recommendation=DecisionRecommendationIn(),
            )
        assert "execution_id" in str(exc_info.value)

    @pytest.mark.unit
    def test_decision_create_missing_flow_id(self):
        """Decision create without flow_id should fail."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionCreate(
                execution_id=uuid4(),
                node_id="node",
                recommendation=DecisionRecommendationIn(),
            )
        assert "flow_id" in str(exc_info.value)

    @pytest.mark.unit
    def test_decision_create_missing_recommendation(self):
        """Decision create without recommendation should fail."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionCreate(
                execution_id=uuid4(),
                flow_id="flow",
                node_id="node",
            )
        assert "recommendation" in str(exc_info.value)

    @pytest.mark.unit
    def test_decision_create_invalid_uuid(self):
        """Decision create with invalid UUID should fail."""
        with pytest.raises(ValidationError):
            DecisionCreate(
                execution_id="not-a-uuid",
                flow_id="flow",
                node_id="node",
                recommendation=DecisionRecommendationIn(),
            )


class TestDecisionActionIn:
    """Tests for DecisionActionIn schema validation."""

    @pytest.mark.unit
    def test_valid_action_with_comment(self):
        """Valid action with comment should pass."""
        data = DecisionActionIn(
            actor_id="user-123",
            actor_type="human",
            comment="Approved after review",
        )
        assert data.actor_id == "user-123"
        assert data.comment == "Approved after review"

    @pytest.mark.unit
    def test_action_with_defaults(self):
        """Action with default values should pass."""
        data = DecisionActionIn()
        assert data.actor_type == "human"
        assert data.actor_id is None
        assert data.comment is None

    @pytest.mark.unit
    def test_action_with_system_actor(self):
        """Action with system actor type should pass."""
        data = DecisionActionIn(
            actor_type="system",
            actor_id="auto-approver",
        )
        assert data.actor_type == "system"


class TestDecisionModifyIn:
    """Tests for DecisionModifyIn schema validation."""

    @pytest.mark.unit
    def test_valid_modify_action(self):
        """Valid modify action should pass."""
        data = DecisionModifyIn(
            actor_id="user-123",
            comment="Modified the amount",
            modifications={"amount": 500, "reason": "Corrected value"},
        )
        assert data.modifications == {"amount": 500, "reason": "Corrected value"}

    @pytest.mark.unit
    def test_modify_missing_modifications(self):
        """Modify action without modifications should fail."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionModifyIn(
                actor_id="user-123",
                comment="Modified",
            )
        assert "modifications" in str(exc_info.value)

    @pytest.mark.unit
    def test_modify_empty_modifications(self):
        """Modify action with empty modifications dict should pass."""
        data = DecisionModifyIn(
            modifications={},
        )
        assert data.modifications == {}


class TestDecisionRecommendationIn:
    """Tests for DecisionRecommendationIn schema validation."""

    @pytest.mark.unit
    def test_full_recommendation(self):
        """Full recommendation with all fields should pass."""
        data = DecisionRecommendationIn(
            summary="Approve this transaction",
            detailed_explanation={"reasons": ["low risk", "verified customer"]},
            model_used="gpt-4",
            prompt_version="v2.1",
        )
        assert data.summary == "Approve this transaction"
        assert data.model_used == "gpt-4"

    @pytest.mark.unit
    def test_empty_recommendation(self):
        """Empty recommendation should pass (all fields optional)."""
        data = DecisionRecommendationIn()
        assert data.summary is None
        assert data.detailed_explanation is None


class TestDecisionPolicySnapshotIn:
    """Tests for DecisionPolicySnapshotIn schema validation."""

    @pytest.mark.unit
    def test_full_policy_snapshot(self):
        """Full policy snapshot should pass."""
        data = DecisionPolicySnapshotIn(
            policy_version="v2.0.0",
            evaluated_rules=[
                {"id": "rule-1", "outcome": "pass"},
                {"id": "rule-2", "outcome": "fail"},
            ],
            result="require_human",
        )
        assert data.policy_version == "v2.0.0"
        assert len(data.evaluated_rules) == 2

    @pytest.mark.unit
    def test_policy_snapshot_with_dict_rules(self):
        """Policy snapshot with dict evaluated_rules should pass."""
        data = DecisionPolicySnapshotIn(
            policy_version="v1.0.0",
            evaluated_rules={"id": "single-rule", "outcome": "pass"},
            result="auto_approve",
        )
        assert data.evaluated_rules == {"id": "single-rule", "outcome": "pass"}

    @pytest.mark.unit
    def test_empty_policy_snapshot(self):
        """Empty policy snapshot should pass."""
        data = DecisionPolicySnapshotIn()
        assert data.policy_version is None
        assert data.result is None
