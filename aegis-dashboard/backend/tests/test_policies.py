"""
Tests for policy management API endpoints.
"""

import pytest
from app.models import Policy


@pytest.mark.asyncio
async def test_create_policy(client, test_customer):
    """Test creating a new policy."""
    policy_data = {
        "customer_id": test_customer.customer_id,
        "agent_id": "test-agent",
        "policy_yaml": """
version: 1
rules:
  - tool: test_tool
    allow: always
""",
        "description": "Test policy",
        "created_by": "test@example.com",
    }

    response = await client.post("/api/v1/policies", json=policy_data)

    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == test_customer.customer_id
    assert data["agent_id"] == "test-agent"
    assert data["version"] == 1
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_policy_invalid_yaml(client, test_customer):
    """Test creating policy with invalid YAML."""
    policy_data = {
        "customer_id": test_customer.customer_id,
        "agent_id": "test-agent",
        "policy_yaml": "not: valid: yaml: structure:",
        "description": "Invalid",
    }

    response = await client.post("/api/v1/policies", json=policy_data)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_policy_missing_version(client, test_customer):
    """Test creating policy without version field."""
    policy_data = {
        "customer_id": test_customer.customer_id,
        "agent_id": "test-agent",
        "policy_yaml": "rules: []",
    }

    response = await client.post("/api/v1/policies", json=policy_data)

    assert response.status_code == 400
    assert "version" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_policies(client, db_session, test_customer):
    """Test listing policies for a customer."""
    # Create test policies
    for i in range(3):
        policy = Policy(
            customer_id=test_customer.customer_id,
            agent_id=f"agent-{i}",
            policy_yaml=f"version: 1\nrules: []",
            policy_hash=f"hash{i}",
            version=1,
            is_active=True,
        )
        db_session.add(policy)

    await db_session.commit()

    response = await client.get(
        "/api/v1/policies",
        params={"customer_id": test_customer.customer_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_activate_policy_rollback(client, db_session, test_customer):
    """Test activating an old policy version (rollback)."""
    # Create policy versions
    policy_v1 = Policy(
        customer_id=test_customer.customer_id,
        agent_id="test-agent",
        policy_yaml="version: 1\nrules: []",
        policy_hash="hash1",
        version=1,
        is_active=False,
    )
    policy_v2 = Policy(
        customer_id=test_customer.customer_id,
        agent_id="test-agent",
        policy_yaml="version: 1\nrules:\n  - tool: test\n    allow: always",
        policy_hash="hash2",
        version=2,
        is_active=True,
    )
    db_session.add_all([policy_v1, policy_v2])
    await db_session.commit()
    await db_session.refresh(policy_v1)

    # Rollback to v1
    response = await client.post(f"/api/v1/policies/{policy_v1.policy_id}/activate")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 1
    assert data["is_active"] is True
