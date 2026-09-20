"""
Tests for audit query API endpoints.
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.models import AuditRecord, Customer


@pytest.mark.asyncio
async def test_query_audit_records(client, db_session, test_customer, viewer_headers):
    """Test querying audit records."""
    # Create test records
    for i in range(5):
        record = AuditRecord(
            record_id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            customer_id=test_customer.customer_id,
            agent_id="test-agent",
            policy_version="policy-v1",
            tool_name=f"tool_{i}",
            params={"index": i},
            outcome="allow",
            matched_rule="rule",
            reason="test",
        )
        db_session.add(record)

    await db_session.commit()

    # Query records
    response = await client.get(
        "/api/v1/audit",
        params={"limit": 10},
        headers=viewer_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_query_audit_records_with_filters(client, db_session, test_customer, viewer_headers):
    """Test querying with outcome filter."""
    # Create records with different outcomes
    for outcome in ["allow", "deny", "escalate"]:
        for i in range(2):
            record = AuditRecord(
                record_id=uuid.uuid4(),
                timestamp=datetime.now(timezone.utc),
                customer_id=test_customer.customer_id,
                agent_id="test-agent",
                policy_version="policy-v1",
                tool_name=f"tool_{i}",
                params={},
                outcome=outcome,
                matched_rule="rule",
                reason="test",
            )
            db_session.add(record)

    await db_session.commit()

    # Query denied records
    response = await client.get(
        "/api/v1/audit",
        params={"outcome": "deny"},
        headers=viewer_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(r["outcome"] == "deny" for r in data)


@pytest.mark.asyncio
async def test_get_audit_record_by_id(client, db_session, test_customer, viewer_headers):
    """Test retrieving single audit record by ID."""
    record_id = uuid.uuid4()
    record = AuditRecord(
        record_id=record_id,
        timestamp=datetime.now(timezone.utc),
        customer_id=test_customer.customer_id,
        agent_id="test-agent",
        policy_version="policy-v1",
        tool_name="test_tool",
        params={"key": "value"},
        outcome="allow",
        matched_rule="rule",
        reason="test",
    )
    db_session.add(record)
    await db_session.commit()

    response = await client.get(f"/api/v1/audit/{record_id}", headers=viewer_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["record_id"] == str(record_id)
    assert data["tool_name"] == "test_tool"


@pytest.mark.asyncio
async def test_get_audit_record_not_found(client, viewer_headers):
    """Test retrieving non-existent audit record."""
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/audit/{fake_id}", headers=viewer_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_query_audit_records_requires_auth(client, test_customer):
    """Test that querying audit records without a token is rejected."""
    response = await client.get("/api/v1/audit")
    assert response.status_code == 401  # HTTPBearer rejects missing credentials


@pytest.mark.asyncio
async def test_query_audit_records_rejects_invalid_token(client, test_customer):
    """Test that an invalid/garbage bearer token is rejected."""
    response = await client.get(
        "/api/v1/audit", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_query_audit_records_scoped_to_own_customer(
    client, db_session, test_customer, viewer_headers
):
    """Test that a user never sees another customer's audit records."""
    other_customer = Customer(
        customer_id="other-customer",
        name="Other Customer",
        api_key="other_api_key_123",
        is_active=True,
    )
    db_session.add(other_customer)
    await db_session.commit()

    own_record = AuditRecord(
        record_id=uuid.uuid4(),
        timestamp=datetime.now(timezone.utc),
        customer_id=test_customer.customer_id,
        agent_id="test-agent",
        policy_version="policy-v1",
        tool_name="own_tool",
        params={},
        outcome="allow",
        matched_rule="rule",
        reason="test",
    )
    other_record = AuditRecord(
        record_id=uuid.uuid4(),
        timestamp=datetime.now(timezone.utc),
        customer_id=other_customer.customer_id,
        agent_id="test-agent",
        policy_version="policy-v1",
        tool_name="other_tool",
        params={},
        outcome="allow",
        matched_rule="rule",
        reason="test",
    )
    db_session.add_all([own_record, other_record])
    await db_session.commit()

    # Even if the caller asks for the other customer's data via a stale
    # query param, only their own tenant's records come back.
    response = await client.get(
        "/api/v1/audit",
        params={"customer_id": other_customer.customer_id},
        headers=viewer_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tool_name"] == "own_tool"

    # And fetching the other customer's record by ID directly 404s.
    response = await client.get(f"/api/v1/audit/{other_record.record_id}", headers=viewer_headers)
    assert response.status_code == 404
