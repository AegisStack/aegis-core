"""
Tests for escalation flow.
"""

import pytest
from aegis.core.escalation import EscalationManager, EscalationRequest
from aegis import AegisEscalationTimeout


class TestEscalationManager:
    """Test escalation manager."""

    def test_escalation_creation(self):
        manager = EscalationManager(
            webhook_url=None,
            timeout_minutes=30,
            on_escalate="notify_and_proceed"
        )

        escalation = manager.escalate(
            record_id="rec_123",
            customer_id="acme",
            agent_id="billing-agent",
            tool_name="issue_refund",
            params={"amount_usd": 500},
            reason="Amount exceeds auto-approve limit"
        )

        assert escalation.escalation_id.startswith("esc_")
        assert escalation.tool_name == "issue_refund"
        assert escalation.resolved is False

    def test_escalation_resolution(self):
        manager = EscalationManager(
            on_escalate="notify_and_proceed"
        )

        escalation = manager.escalate(
            record_id="rec_123",
            customer_id="acme",
            agent_id="billing-agent",
            tool_name="issue_refund",
            params={"amount_usd": 500},
            reason="Test"
        )

        # Resolve it
        manager.resolve(
            escalation.escalation_id,
            resolution="approved",
            resolved_by="sarah@acme.com"
        )

        resolved = manager.get_escalation(escalation.escalation_id)
        assert resolved.resolved is True
        assert resolved.resolution == "approved"
        assert resolved.resolved_by == "sarah@acme.com"

    def test_escalation_invalid_resolution(self):
        manager = EscalationManager(on_escalate="notify_and_proceed")

        escalation = manager.escalate(
            record_id="rec_123",
            customer_id="acme",
            agent_id="test",
            tool_name="test",
            params={},
            reason="test"
        )

        with pytest.raises(ValueError, match="Invalid resolution"):
            manager.resolve(
                escalation.escalation_id,
                resolution="invalid",
                resolved_by="user"
            )

    def test_list_pending_escalations(self):
        manager = EscalationManager(on_escalate="notify_and_proceed")

        # Create two escalations
        esc1 = manager.escalate(
            record_id="rec_1",
            customer_id="acme",
            agent_id="test",
            tool_name="test",
            params={},
            reason="test1"
        )

        esc2 = manager.escalate(
            record_id="rec_2",
            customer_id="acme",
            agent_id="test",
            tool_name="test",
            params={},
            reason="test2"
        )

        pending = manager.list_pending()
        assert len(pending) == 2

        # Resolve one
        manager.resolve(esc1.escalation_id, "approved", "user")

        pending = manager.list_pending()
        assert len(pending) == 1
        assert pending[0].escalation_id == esc2.escalation_id
