"""
Tests for audit query API endpoints.
"""

import pytest
from datetime import datetime, timezone
import uuid
from app.models import AuditRecord


@pytest.mark.asyncio
async def test_query_audit_records(client, db_session, test_customer):
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
        params={"customer_id": test_customer.customer_id, "limit": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_query_audit_records_with_filters(client, db_session, test_customer):
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
        params={"customer_id": test_customer.customer_id, "outcome": "deny"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(r["outcome"] == "deny" for r in data)


@pytest.mark.asyncio
async def test_get_audit_record_by_id(client, db_session, test_customer):
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

    response = await client.get(f"/api/v1/audit/{record_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["record_id"] == str(record_id)
    assert data["tool_name"] == "test_tool"


@pytest.mark.asyncio
async def test_get_audit_record_not_found(client):
    """Test retrieving non-existent audit record."""
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/audit/{fake_id}")
    assert response.status_code == 404
