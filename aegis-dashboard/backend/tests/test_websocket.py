"""
Tests for the /ws/live WebSocket endpoint's authentication.
"""

import pytest
from starlette.websockets import WebSocketDisconnect


def test_websocket_rejects_missing_token(ws_test_client, test_customer):
    """No token query param -> closes 4001.

    The handshake itself succeeds (the server accepts before closing with a
    custom code - see websocket.py), so the disconnect only surfaces once
    the client tries to read from the socket.
    """
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with ws_test_client.websocket_connect(
            f"/ws/live?customer_id={test_customer.customer_id}"
        ) as websocket:
            websocket.receive_text()
    assert exc_info.value.code == 4001


def test_websocket_rejects_invalid_token(ws_test_client, test_customer):
    """Garbage token -> closes 4001."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with ws_test_client.websocket_connect(
            f"/ws/live?customer_id={test_customer.customer_id}&token=not-a-real-token"
        ) as websocket:
            websocket.receive_text()
    assert exc_info.value.code == 4001


def test_websocket_rejects_customer_mismatch(ws_test_client, test_customer, viewer_token):
    """Valid token, but for a different customer_id than requested -> closes 4003."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with ws_test_client.websocket_connect(
            f"/ws/live?customer_id=some-other-customer&token={viewer_token}"
        ) as websocket:
            websocket.receive_text()
    assert exc_info.value.code == 4003


def test_websocket_accepts_valid_token_and_matching_customer(
    ws_test_client, test_customer, viewer_token
):
    """Valid token + matching customer_id -> connects and sends a 'connected' message."""
    with ws_test_client.websocket_connect(
        f"/ws/live?customer_id={test_customer.customer_id}&token={viewer_token}"
    ) as websocket:
        message = websocket.receive_json()
        assert message["type"] == "connected"
        assert message["customer_id"] == test_customer.customer_id
