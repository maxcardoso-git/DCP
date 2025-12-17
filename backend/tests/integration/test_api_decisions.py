"""
Integration tests for the decision API endpoints.
"""
import pytest
from uuid import uuid4


class TestCreateDecisionGate:
    """Tests for POST /decision-gates endpoint."""

    @pytest.mark.integration
    async def test_create_decision_gate_success(self, client, auth_headers, decision_factory):
        """Should create a new decision gate successfully."""
        payload = decision_factory.create_payload()

        response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["flow_id"] == payload["flow_id"]
        assert data["node_id"] == payload["node_id"]
        assert data["status"] == "pending_human_review"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.integration
    async def test_create_decision_gate_idempotent(self, client, auth_headers, decision_factory):
        """Creating same decision gate twice should return existing one."""
        execution_id = str(uuid4())
        payload = decision_factory.create_payload(execution_id=execution_id, node_id="same-node")

        # First creation
        response1 = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )
        assert response1.status_code == 201
        decision_id1 = response1.json()["id"]

        # Second creation with same execution_id and node_id
        response2 = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )
        assert response2.status_code == 201
        decision_id2 = response2.json()["id"]

        # Should return the same decision
        assert decision_id1 == decision_id2

    @pytest.mark.integration
    async def test_create_decision_gate_without_policy_snapshot(self, client, auth_headers):
        """Should apply heuristic policy when no snapshot provided."""
        payload = {
            "execution_id": str(uuid4()),
            "flow_id": "test-flow",
            "node_id": "test-node",
            "risk_score": 0.1,
            "confidence_score": 0.9,
            "estimated_cost": 100,
            "recommendation": {
                "summary": "Test",
            },
        }

        response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["policy_snapshot"] is not None
        assert data["policy_snapshot"]["policy_version"] == "heuristic-v1"

    @pytest.mark.integration
    async def test_create_decision_gate_missing_required_fields(self, client, auth_headers):
        """Should return 422 for missing required fields."""
        payload = {"flow_id": "test"}  # Missing required fields

        response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.integration
    async def test_create_decision_gate_without_auth(self, client):
        """Should return 401 without authorization header."""
        payload = {
            "execution_id": str(uuid4()),
            "flow_id": "test-flow",
            "node_id": "test-node",
            "recommendation": {"summary": "Test"},
        }

        response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
        )

        assert response.status_code == 401

    @pytest.mark.integration
    async def test_create_decision_gate_invalid_token(self, client, invalid_auth_headers, decision_factory):
        """Should return 403 with invalid token."""
        payload = decision_factory.create_payload()

        response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=invalid_auth_headers,
        )

        assert response.status_code == 403


class TestListDecisions:
    """Tests for GET /decisions endpoint."""

    @pytest.mark.integration
    async def test_list_decisions_empty(self, client, auth_headers):
        """Should return empty list when no decisions exist."""
        response = await client.get(
            "/api/v2/dcp/decisions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.integration
    async def test_list_decisions_with_filter(self, client, auth_headers, decision_factory):
        """Should filter decisions by status."""
        # Create a decision
        payload = decision_factory.create_payload()
        await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )

        # List with pending_human_review filter (default)
        response = await client.get(
            "/api/v2/dcp/decisions?status=pending_human_review",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["status"] == "pending_human_review"

    @pytest.mark.integration
    async def test_list_decisions_pagination(self, client, auth_headers, decision_factory):
        """Should respect limit and offset parameters."""
        # Create multiple decisions
        for i in range(5):
            payload = decision_factory.create_payload(node_id=f"node-{i}")
            await client.post(
                "/api/v2/dcp/decision-gates",
                json=payload,
                headers=auth_headers,
            )

        # Test pagination
        response = await client.get(
            "/api/v2/dcp/decisions?limit=2&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5

    @pytest.mark.integration
    async def test_list_decisions_without_auth(self, client):
        """Should return 401 without authorization."""
        response = await client.get("/api/v2/dcp/decisions")
        assert response.status_code == 401


class TestApproveDecision:
    """Tests for POST /decisions/{id}/approve endpoint."""

    @pytest.mark.integration
    async def test_approve_decision_success(self, client, auth_headers, decision_factory):
        """Should approve a pending decision."""
        # Create a decision
        payload = decision_factory.create_payload()
        create_response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )
        decision_id = create_response.json()["id"]

        # Approve it
        response = await client.post(
            f"/api/v2/dcp/decisions/{decision_id}/approve",
            json={"actor_id": "user-1", "comment": "Looks good"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert len(data["actions"]) == 1
        assert data["actions"][0]["action_type"] == "approve"
        assert data["actions"][0]["comment"] == "Looks good"

    @pytest.mark.integration
    async def test_approve_nonexistent_decision(self, client, auth_headers):
        """Should return 404 for nonexistent decision."""
        fake_id = str(uuid4())

        response = await client.post(
            f"/api/v2/dcp/decisions/{fake_id}/approve",
            json={"comment": "Test"},
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestRejectDecision:
    """Tests for POST /decisions/{id}/reject endpoint."""

    @pytest.mark.integration
    async def test_reject_decision_success(self, client, auth_headers, decision_factory):
        """Should reject a pending decision."""
        # Create a decision
        payload = decision_factory.create_payload()
        create_response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )
        decision_id = create_response.json()["id"]

        # Reject it
        response = await client.post(
            f"/api/v2/dcp/decisions/{decision_id}/reject",
            json={"actor_id": "user-1", "comment": "Too risky"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["actions"][0]["action_type"] == "reject"

    @pytest.mark.integration
    async def test_reject_nonexistent_decision(self, client, auth_headers):
        """Should return 404 for nonexistent decision."""
        fake_id = str(uuid4())

        response = await client.post(
            f"/api/v2/dcp/decisions/{fake_id}/reject",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestEscalateDecision:
    """Tests for POST /decisions/{id}/escalate endpoint."""

    @pytest.mark.integration
    async def test_escalate_decision_success(self, client, auth_headers, decision_factory):
        """Should escalate a pending decision."""
        # Create a decision
        payload = decision_factory.create_payload()
        create_response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )
        decision_id = create_response.json()["id"]

        # Escalate it
        response = await client.post(
            f"/api/v2/dcp/decisions/{decision_id}/escalate",
            json={"actor_id": "user-1", "comment": "Need manager approval"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "escalated"
        assert data["actions"][0]["action_type"] == "escalate"


class TestModifyDecision:
    """Tests for POST /decisions/{id}/modify endpoint."""

    @pytest.mark.integration
    async def test_modify_decision_success(self, client, auth_headers, decision_factory):
        """Should modify a pending decision."""
        # Create a decision
        payload = decision_factory.create_payload()
        create_response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )
        decision_id = create_response.json()["id"]

        # Modify it
        response = await client.post(
            f"/api/v2/dcp/decisions/{decision_id}/modify",
            json={
                "actor_id": "user-1",
                "comment": "Adjusted amount",
                "modifications": {"amount": 500, "note": "corrected"},
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "modified"
        assert data["actions"][0]["action_type"] == "modify"
        assert data["actions"][0]["payload"]["amount"] == 500

    @pytest.mark.integration
    async def test_modify_missing_modifications(self, client, auth_headers, decision_factory):
        """Should return 422 when modifications field is missing."""
        # Create a decision
        payload = decision_factory.create_payload()
        create_response = await client.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
            headers=auth_headers,
        )
        decision_id = create_response.json()["id"]

        # Try to modify without modifications
        response = await client.post(
            f"/api/v2/dcp/decisions/{decision_id}/modify",
            json={"comment": "Test"},
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestAuthenticationNoToken:
    """Tests for API when no bearer token is configured."""

    @pytest.mark.integration
    async def test_create_decision_without_token_config(self, client_no_auth, decision_factory):
        """Should allow requests when bearer_token is not configured."""
        payload = decision_factory.create_payload()

        response = await client_no_auth.post(
            "/api/v2/dcp/decision-gates",
            json=payload,
        )

        assert response.status_code == 201

    @pytest.mark.integration
    async def test_list_decisions_without_token_config(self, client_no_auth):
        """Should allow requests when bearer_token is not configured."""
        response = await client_no_auth.get("/api/v2/dcp/decisions")
        assert response.status_code == 200
