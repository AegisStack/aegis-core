"""
WebSocket endpoint for real-time audit record streaming.
"""

import asyncio

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.auth import get_user_from_token

router = APIRouter()

# Active WebSocket connections per customer
active_connections: dict[str, set[WebSocket]] = {}


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, customer_id: str):
        """Accept WebSocket connection and add to customer group."""
        await websocket.accept()
        if customer_id not in self.active_connections:
            self.active_connections[customer_id] = set()
        self.active_connections[customer_id].add(websocket)

    def disconnect(self, websocket: WebSocket, customer_id: str):
        """Remove WebSocket connection from customer group."""
        if customer_id in self.active_connections:
            self.active_connections[customer_id].discard(websocket)
            if not self.active_connections[customer_id]:
                del self.active_connections[customer_id]

    async def broadcast_to_customer(self, customer_id: str, message: dict):
        """Broadcast message to all connections for a customer."""
        if customer_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[customer_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.add(connection)

            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[customer_id].discard(conn)

    async def broadcast_audit_record(self, customer_id: str, record_dict: dict):
        """Broadcast new audit record to customer's connections."""
        message = {
            "type": "audit_record",
            "data": record_dict,
        }
        await self.broadcast_to_customer(customer_id, message)

    async def broadcast_escalation(self, customer_id: str, escalation_dict: dict):
        """Broadcast escalation event to customer's connections."""
        message = {
            "type": "escalation",
            "data": escalation_dict,
        }
        await self.broadcast_to_customer(customer_id, message)


manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_endpoint(
    websocket: WebSocket,
    customer_id: str = Query(...),
    token: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time audit record streaming.

    Query params:
        customer_id: Customer identifier for filtering
        token: JWT access token (same one used for the HTTP API)

    Closes with 4001 if the token is missing/invalid, 4003 if the token's
    user doesn't belong to the requested customer_id. These codes are
    special-cased by the frontend's reconnect-with-refresh logic.

    Messages sent to client:
        {
            "type": "audit_record" | "escalation" | "heartbeat",
            "data": {...}
        }
    """
    # A custom close code only reaches the browser if the handshake was
    # accepted first - rejecting before accept() surfaces as a generic
    # abnormal closure (1006), which the frontend can't distinguish.
    user = await get_user_from_token(token, db) if token else None
    if user is None:
        await websocket.accept()
        await websocket.close(code=4001)
        return
    if user.customer_id != customer_id:
        await websocket.accept()
        await websocket.close(code=4003)
        return

    await manager.connect(websocket, customer_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "customer_id": customer_id,
                "message": "Connected to Aegis live feed",
            }
        )

        # Keep connection alive with heartbeat
        while True:
            try:
                # Wait for any message from client (or timeout for heartbeat)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Client can send ping to keep alive
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, customer_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, customer_id)


# Expose manager for use in other modules
def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager
