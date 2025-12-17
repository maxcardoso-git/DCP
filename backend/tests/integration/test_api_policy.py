"""
Integration tests for the policy evaluation endpoint.
"""
import pytest
from uuid import uuid4


class TestPolicyEvaluate:
    """Tests for POST /policy/evaluate endpoint."""

    @pytest.mark.integration
    async def test_evaluate_force_escalation_high_risk(self, client, auth_headers):
        """Should return force_escalation for high risk."""
        payload = {
            "execution_id": str(uuid4()),
            "flow_id": "test",
            "node_id": "test",
            "risk_score": 0.9,
            "confidence_score": 0.8,
            "estimated_cost": 100,
            "recommendation": {"summary": "test"},
        }

        response = await client.post(
            "/api/v2/dcp/policy/evaluate",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "force_escalation"
        assert "High risk" in data["reason"]

    @pytest.mark.integration
    async def test_evaluate_force_escalation_compliance(self, client, auth_headers):
        """Should return force_escalation for compliance flags."""
        payload = {
            "execution_id": str(uuid4()),
            "flow_id": "test",
            "node_id": "test",
            "risk_score": 0.1,
            "confidence_score": 0.9,
            "estimated_cost": 100,
            "compliance_flags": ["aml"],
            "recommendation": {"summary": "test"},
        }

        response = await client.post(
            "/api/v2/dcp/policy/evaluate",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "force_escalation"
        assert "Compliance" in data["reason"]

    @pytest.mark.integration
    async def test_evaluate_auto_approve(self, client, auth_headers):
        """Should return auto_approve for low risk, high confidence, low cost."""
        payload = {
            "execution_id": str(uuid4()),
            "flow_id": "test",
            "node_id": "test",
            "risk_score": 0.1,
            "confidence_score": 0.9,
            "estimated_cost": 100,
            "recommendation": {"summary": "test"},
        }

        response = await client.post(
            "/api/v2/dcp/policy/evaluate",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "auto_approve"

    @pytest.mark.integration
    async def test_evaluate_require_human(self, client, auth_headers):
        """Should return require_human for medium risk."""
        payload = {
            "execution_id": str(uuid4()),
            "flow_id": "test",
            "node_id": "test",
            "risk_score": 0.5,
            "confidence_score": 0.7,
            "estimated_cost": 1000,
            "recommendation": {"summary": "test"},
        }

        response = await client.post(
            "/api/v2/dcp/policy/evaluate",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "require_human"

    @pytest.mark.integration
    async def test_evaluate_without_auth(self, client):
        """Should return 401 without authorization."""
        payload = {
            "execution_id": str(uuid4()),
            "flow_id": "test",
            "node_id": "test",
            "recommendation": {"summary": "test"},
        }

        response = await client.post(
            "/api/v2/dcp/policy/evaluate",
            json=payload,
        )

        assert response.status_code == 401

    @pytest.mark.integration
    async def test_evaluate_missing_fields(self, client, auth_headers):
        """Should return 422 for missing required fields."""
        payload = {"risk_score": 0.5}

        response = await client.post(
            "/api/v2/dcp/policy/evaluate",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 422
