"""
Tests for escalation management API endpoints, including role enforcement
and tenant scoping.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Customer, Escalation


def _make_escalation(customer_id, escalation_id="esc_test_1"):
    return Escalation(
        escalation_id=escalation_id,
        record_id=uuid.uuid4(),
        customer_id=customer_id,
        agent_id="test-agent",
        tool_name="issue_refund",
        params={"amount_usd": 500},
        reason="Amount exceeds threshold",
        status="pending",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )


@pytest.mark.asyncio
async def test_list_escalations_requires_auth(client):
    """Test that listing escalations without a token is rejected."""
    response = await client.get("/api/v1/escalations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_viewer_can_list_but_not_resolve(client, db_session, test_customer, viewer_headers):
    """Test that a viewer can read escalations but not resolve them."""
    escalation = _make_escalation(test_customer.customer_id)
    db_session.add(escalation)
    await db_session.commit()

    list_response = await client.get("/api/v1/escalations", headers=viewer_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    resolve_response = await client.post(
        f"/api/v1/escalations/{escalation.escalation_id}/resolve",
        json={"resolution": "approved"},
        headers=viewer_headers,
    )
    assert resolve_response.status_code == 403


@pytest.mark.asyncio
async def test_operator_can_resolve_and_resolved_by_is_server_derived(
    client, db_session, test_customer, operator_headers, test_operator_user
):
    """Test that an operator can resolve, and resolved_by can't be spoofed by the client."""
    escalation = _make_escalation(test_customer.customer_id)
    db_session.add(escalation)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/escalations/{escalation.escalation_id}/resolve",
        json={"resolution": "approved", "resolved_by": "someone-else@attacker.example"},
        headers=operator_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["resolved_by"] == test_operator_user.email


@pytest.mark.asyncio
async def test_admin_can_also_resolve_escalations(
    client, db_session, test_customer, admin_headers, test_admin_user
):
    """require_role("operator") is a floor, not an exact match - admin (a higher
    role in the hierarchy) must pass it too."""
    escalation = _make_escalation(test_customer.customer_id)
    db_session.add(escalation)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/escalations/{escalation.escalation_id}/resolve",
        json={"resolution": "denied"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["resolved_by"] == test_admin_user.email


@pytest.mark.asyncio
async def test_escalations_scoped_to_own_customer(
    client, db_session, test_customer, viewer_headers
):
    """Test that escalations from another customer are never returned or resolvable."""
    other_customer = Customer(
        customer_id="other-customer",
        name="Other Customer",
        api_key_hash="other_api_key_123_hash",
        is_active=True,
    )
    db_session.add(other_customer)
    await db_session.commit()

    other_escalation = _make_escalation(other_customer.customer_id, escalation_id="esc_other_1")
    db_session.add(other_escalation)
    await db_session.commit()

    list_response = await client.get("/api/v1/escalations", headers=viewer_headers)
    assert list_response.status_code == 200
    assert list_response.json() == []

    get_response = await client.get(
        f"/api/v1/escalations/{other_escalation.escalation_id}", headers=viewer_headers
    )
    assert get_response.status_code == 404
