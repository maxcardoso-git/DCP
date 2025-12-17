"""
Integration tests for CRUD operations.
"""
import pytest
from uuid import uuid4

from app import crud, schemas, models


class TestCreateDecision:
    """Tests for create_decision CRUD operation."""

    @pytest.mark.integration
    async def test_create_decision_success(self, async_session):
        """Should create a new decision in the database."""
        payload = schemas.DecisionCreate(
            execution_id=uuid4(),
            flow_id="test-flow",
            node_id="test-node",
            language="en",
            risk_score=0.5,
            confidence_score=0.7,
            estimated_cost=100.0,
            recommendation=schemas.DecisionRecommendationIn(
                summary="Test summary",
                detailed_explanation={"reason": "test"},
            ),
            policy_snapshot=schemas.DecisionPolicySnapshotIn(
                policy_version="v1.0.0",
                evaluated_rules=[{"id": "rule1"}],
                result="require_human",
            ),
        )

        decision = await crud.create_decision(async_session, payload)

        assert decision.id is not None
        assert decision.flow_id == "test-flow"
        assert decision.status == "pending_human_review"
        assert decision.recommendation is not None
        assert decision.recommendation.summary == "Test summary"
        assert decision.policy_snapshot is not None
        assert decision.policy_snapshot.policy_version == "v1.0.0"

    @pytest.mark.integration
    async def test_create_decision_idempotent(self, async_session):
        """Creating decision with same execution_id and node_id should return existing."""
        execution_id = uuid4()
        payload = schemas.DecisionCreate(
            execution_id=execution_id,
            flow_id="test-flow",
            node_id="same-node",
            recommendation=schemas.DecisionRecommendationIn(summary="First"),
        )

        # Create first
        decision1 = await crud.create_decision(async_session, payload)

        # Create second with same keys
        payload2 = schemas.DecisionCreate(
            execution_id=execution_id,
            flow_id="different-flow",  # Different flow
            node_id="same-node",  # Same node
            recommendation=schemas.DecisionRecommendationIn(summary="Second"),
        )
        decision2 = await crud.create_decision(async_session, payload2)

        # Should return the same decision
        assert decision1.id == decision2.id
        assert decision2.flow_id == "test-flow"  # Original value preserved

    @pytest.mark.integration
    async def test_create_decision_without_optional_fields(self, async_session):
        """Should create decision with only required fields."""
        payload = schemas.DecisionCreate(
            execution_id=uuid4(),
            flow_id="minimal-flow",
            node_id="minimal-node",
            recommendation=schemas.DecisionRecommendationIn(),
        )

        decision = await crud.create_decision(async_session, payload)

        assert decision.id is not None
        assert decision.risk_score is None
        assert decision.confidence_score is None
        assert decision.estimated_cost is None


class TestListDecisions:
    """Tests for list_decisions CRUD operation."""

    @pytest.mark.integration
    async def test_list_decisions_empty(self, async_session):
        """Should return empty list when no decisions exist."""
        items, total = await crud.list_decisions(async_session)

        assert items == []
        assert total == 0

    @pytest.mark.integration
    async def test_list_decisions_with_status_filter(self, async_session):
        """Should filter decisions by status."""
        # Create a decision
        payload = schemas.DecisionCreate(
            execution_id=uuid4(),
            flow_id="test",
            node_id="test",
            recommendation=schemas.DecisionRecommendationIn(),
        )
        await crud.create_decision(async_session, payload)

        # List pending
        items, total = await crud.list_decisions(
            async_session, status="pending_human_review"
        )

        assert total >= 1
        for item in items:
            assert item.status == "pending_human_review"

    @pytest.mark.integration
    async def test_list_decisions_pagination(self, async_session):
        """Should respect limit and offset."""
        # Create multiple decisions
        for i in range(5):
            payload = schemas.DecisionCreate(
                execution_id=uuid4(),
                flow_id="test",
                node_id=f"node-{i}",
                recommendation=schemas.DecisionRecommendationIn(),
            )
            await crud.create_decision(async_session, payload)

        # Test limit
        items, total = await crud.list_decisions(async_session, limit=2)
        assert len(items) == 2
        assert total >= 5

        # Test offset
        items2, _ = await crud.list_decisions(async_session, limit=2, offset=2)
        assert len(items2) == 2
        # Items should be different due to offset
        assert items[0].id != items2[0].id


class TestDecisionActions:
    """Tests for decision action CRUD operations."""

    @pytest.mark.integration
    async def test_approve_decision(self, async_session):
        """Should approve a decision and record the action."""
        # Create a decision
        payload = schemas.DecisionCreate(
            execution_id=uuid4(),
            flow_id="test",
            node_id="test",
            recommendation=schemas.DecisionRecommendationIn(),
        )
        decision = await crud.create_decision(async_session, payload)

        # Approve it
        action = schemas.DecisionActionIn(
            actor_id="user-1",
            actor_type="human",
            comment="Approved",
        )
        updated = await crud.approve_decision(async_session, decision.id, action)

        assert updated.status == "approved"
        assert len(updated.actions) == 1
        assert updated.actions[0].action_type == "approve"
        assert updated.actions[0].actor_id == "user-1"
        assert updated.actions[0].comment == "Approved"

    @pytest.mark.integration
    async def test_reject_decision(self, async_session):
        """Should reject a decision and record the action."""
        # Create a decision
        payload = schemas.DecisionCreate(
            execution_id=uuid4(),
            flow_id="test",
            node_id="test",
            recommendation=schemas.DecisionRecommendationIn(),
        )
        decision = await crud.create_decision(async_session, payload)

        # Reject it
        action = schemas.DecisionActionIn(
            actor_id="user-1",
            comment="Rejected due to risk",
        )
        updated = await crud.reject_decision(async_session, decision.id, action)

        assert updated.status == "rejected"
        assert updated.actions[0].action_type == "reject"

    @pytest.mark.integration
    async def test_escalate_decision(self, async_session):
        """Should escalate a decision and record the action."""
        # Create a decision
        payload = schemas.DecisionCreate(
            execution_id=uuid4(),
            flow_id="test",
            node_id="test",
            recommendation=schemas.DecisionRecommendationIn(),
        )
        decision = await crud.create_decision(async_session, payload)

        # Escalate it
        action = schemas.DecisionActionIn(
            actor_id="user-1",
            comment="Needs manager approval",
        )
        updated = await crud.escalate_decision(async_session, decision.id, action)

        assert updated.status == "escalated"
        assert updated.actions[0].action_type == "escalate"

    @pytest.mark.integration
    async def test_modify_decision(self, async_session):
        """Should modify a decision with payload."""
        # Create a decision
        payload = schemas.DecisionCreate(
            execution_id=uuid4(),
            flow_id="test",
            node_id="test",
            recommendation=schemas.DecisionRecommendationIn(),
        )
        decision = await crud.create_decision(async_session, payload)

        # Modify it
        modify_payload = schemas.DecisionModifyIn(
            actor_id="user-1",
            comment="Adjusted amount",
            modifications={"amount": 500, "reason": "corrected"},
        )
        updated = await crud.modify_decision(async_session, decision.id, modify_payload)

        assert updated.status == "modified"
        assert updated.actions[0].action_type == "modify"
        assert updated.actions[0].payload == {"amount": 500, "reason": "corrected"}

    @pytest.mark.integration
    async def test_action_on_nonexistent_decision(self, async_session):
        """Should raise ValueError for nonexistent decision."""
        fake_id = uuid4()
        action = schemas.DecisionActionIn(comment="Test")

        with pytest.raises(ValueError, match="Decision not found"):
            await crud.approve_decision(async_session, fake_id, action)

    @pytest.mark.integration
    async def test_multiple_actions_on_decision(self, async_session):
        """Should allow multiple actions on the same decision."""
        # Create a decision
        payload = schemas.DecisionCreate(
            execution_id=uuid4(),
            flow_id="test",
            node_id="test",
            recommendation=schemas.DecisionRecommendationIn(),
        )
        decision = await crud.create_decision(async_session, payload)

        # First action: escalate
        action1 = schemas.DecisionActionIn(
            actor_id="user-1",
            comment="Escalating",
        )
        await crud.escalate_decision(async_session, decision.id, action1)

        # Second action: approve (after escalation review)
        action2 = schemas.DecisionActionIn(
            actor_id="manager-1",
            comment="Approved after review",
        )
        updated = await crud.approve_decision(async_session, decision.id, action2)

        assert updated.status == "approved"
        assert len(updated.actions) == 2
        assert updated.actions[0].action_type == "escalate"
        assert updated.actions[1].action_type == "approve"
