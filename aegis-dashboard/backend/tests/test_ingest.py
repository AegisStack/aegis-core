"""
Tests for ingestion API endpoints.
"""

import pytest
from datetime import datetime, timezone
import uuid


@pytest.mark.asyncio
async def test_ingest_audit_records_success(client, test_customer):
    """Test successful audit record ingestion."""
    records = [
        {
            "record_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "customer_id": test_customer.customer_id,
            "agent_id": "test-agent",
            "session_id": "sess_123",
            "policy_version": "policy-v1@sha256:abc123",
            "tool_name": "test_tool",
            "params": {"key": "value"},
            "outcome": "allow",
            "matched_rule": "test_tool.allow[0]",
            "reason": "Test reason",
            "latency_ms": 2.5,
        }
    ]

    response = await client.post(
        "/api/v1/ingest/audit",
        json=records,
        headers={"X-API-Key": test_customer.api_key},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["records_received"] == 1
    assert data["customer_id"] == test_customer.customer_id


@pytest.mark.asyncio
async def test_ingest_audit_records_invalid_api_key(client):
    """Test ingestion with invalid API key."""
    records = [
        {
            "record_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "customer_id": "test-customer",
            "agent_id": "test-agent",
            "policy_version": "policy-v1",
            "tool_name": "test_tool",
            "params": {},
            "outcome": "allow",
            "matched_rule": "rule",
            "reason": "reason",
        }
    ]

    response = await client.post(
        "/api/v1/ingest/audit",
        json=records,
        headers={"X-API-Key": "invalid_key"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_audit_records_customer_mismatch(client, test_customer):
    """Test ingestion with mismatched customer_id."""
    records = [
        {
            "record_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "customer_id": "different-customer",  # Mismatch
            "agent_id": "test-agent",
            "policy_version": "policy-v1",
            "tool_name": "test_tool",
            "params": {},
            "outcome": "allow",
            "matched_rule": "rule",
            "reason": "reason",
        }
    ]

    response = await client.post(
        "/api/v1/ingest/audit",
        json=records,
        headers={"X-API-Key": test_customer.api_key},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ingest_batch_records(client, test_customer):
    """Test batch ingestion of multiple records."""
    records = [
        {
            "record_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "customer_id": test_customer.customer_id,
            "agent_id": f"agent-{i}",
            "policy_version": "policy-v1",
            "tool_name": f"tool_{i}",
            "params": {"index": i},
            "outcome": "allow",
            "matched_rule": "rule",
            "reason": f"Test {i}",
        }
        for i in range(10)
    ]

    response = await client.post(
        "/api/v1/ingest/audit",
        json=records,
        headers={"X-API-Key": test_customer.api_key},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["records_received"] == 10
