"""
Tests for authentication endpoints, including refresh token rotation.
"""

import pytest


@pytest.mark.asyncio
async def test_register_returns_refresh_token(client, test_customer):
    """Test that registration returns both an access and refresh token."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@test-customer.example",
            "password": "password123",
            "full_name": "New User",
            "customer_id": test_customer.customer_id,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]


@pytest.mark.asyncio
async def test_login_returns_refresh_token(client, test_viewer_user):
    """Test that login returns both an access and refresh token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_viewer_user.email, "password": "testpass123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_rotates_token(client, test_viewer_user):
    """Test that /auth/refresh issues a new pair and revokes the old refresh token."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_viewer_user.email, "password": "testpass123"},
    )
    original_refresh_token = login_response.json()["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original_refresh_token}
    )

    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["refresh_token"] != original_refresh_token

    # The original refresh token was revoked by rotation - reusing it fails.
    replay_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original_refresh_token}
    )
    assert replay_response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_unknown_token(client):
    """Test that an unknown refresh token is rejected."""
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-refresh-token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client, test_viewer_user):
    """Test that logout revokes the presented refresh token."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_viewer_user.email, "password": "testpass123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 200

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_refresh_token_still_succeeds(client):
    """Test that logout with no body doesn't error (backward compatible)."""
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
