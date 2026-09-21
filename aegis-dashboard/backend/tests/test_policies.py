"""
Tests for policy management API endpoints.
"""

import pytest

from app.models import Customer, Policy


@pytest.mark.asyncio
async def test_create_policy(client, test_customer, admin_headers):
    """Test creating a new policy."""
    policy_data = {
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

    response = await client.post("/api/v1/policies", json=policy_data, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == test_customer.customer_id
    assert data["agent_id"] == "test-agent"
    assert data["version"] == 1
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_policy_requires_admin(client, test_customer, viewer_headers):
    """Test that a viewer cannot create policies."""
    policy_data = {
        "agent_id": "test-agent",
        "policy_yaml": "version: 1\nrules: []",
    }

    response = await client.post("/api/v1/policies", json=policy_data, headers=viewer_headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_policy_requires_admin_not_just_operator(
    client, test_customer, operator_headers
):
    """require_role("admin") is an exact floor at the top of the hierarchy -
    operator (one level below) must still be rejected."""
    policy_data = {
        "agent_id": "test-agent",
        "policy_yaml": "version: 1\nrules: []",
    }

    response = await client.post("/api/v1/policies", json=policy_data, headers=operator_headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_policy_invalid_yaml(client, test_customer, admin_headers):
    """Test creating policy with invalid YAML."""
    policy_data = {
        "agent_id": "test-agent",
        "policy_yaml": "not: valid: yaml: structure:",
        "description": "Invalid",
    }

    response = await client.post("/api/v1/policies", json=policy_data, headers=admin_headers)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_policy_missing_version(client, test_customer, admin_headers):
    """Test creating policy without version field."""
    policy_data = {
        "agent_id": "test-agent",
        "policy_yaml": "rules: []",
    }

    response = await client.post("/api/v1/policies", json=policy_data, headers=admin_headers)

    assert response.status_code == 400
    assert "version" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_policies(client, db_session, test_customer, viewer_headers):
    """Test listing policies for a customer."""
    # Create test policies
    for i in range(3):
        policy = Policy(
            customer_id=test_customer.customer_id,
            agent_id=f"agent-{i}",
            policy_yaml="version: 1\nrules: []",
            policy_hash=f"hash{i}",
            version=1,
            is_active=True,
        )
        db_session.add(policy)

    await db_session.commit()

    response = await client.get("/api/v1/policies", headers=viewer_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_policies_scoped_to_own_customer(
    client, db_session, test_customer, viewer_headers
):
    """Test that policies from another customer are never returned."""
    other_customer = Customer(
        customer_id="other-customer",
        name="Other Customer",
        api_key_hash="other_api_key_123_hash",
        is_active=True,
    )
    db_session.add(other_customer)
    await db_session.commit()

    own_policy = Policy(
        customer_id=test_customer.customer_id,
        agent_id="own-agent",
        policy_yaml="version: 1\nrules: []",
        policy_hash="own-hash",
        version=1,
        is_active=True,
    )
    other_policy = Policy(
        customer_id=other_customer.customer_id,
        agent_id="other-agent",
        policy_yaml="version: 1\nrules: []",
        policy_hash="other-hash",
        version=1,
        is_active=True,
    )
    db_session.add_all([own_policy, other_policy])
    await db_session.commit()
    await db_session.refresh(other_policy)

    response = await client.get("/api/v1/policies", headers=viewer_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["agent_id"] == "own-agent"

    response = await client.get(
        f"/api/v1/policies/{other_policy.policy_id}", headers=viewer_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_activate_policy_rollback(client, db_session, test_customer, admin_headers):
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
    response = await client.post(
        f"/api/v1/policies/{policy_v1.policy_id}/activate", headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 1
    assert data["is_active"] is True
