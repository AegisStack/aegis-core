"""
Escalation Manager - Human-in-the-loop for high-risk tool calls.

Handles escalation webhooks, blocking, timeout, and resolution.
"""

import uuid
import time
import requests
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone, timedelta

from ..exceptions import AegisEscalationTimeout


class EscalationRequest:
    """Represents an escalation waiting for human resolution."""

    def __init__(
        self,
        escalation_id: str,
        record_id: str,
        customer_id: Optional[str],
        agent_id: str,
        tool_name: str,
        params: Dict[str, Any],
        reason: str,
        timeout_minutes: int,
    ):
        self.escalation_id = escalation_id
        self.record_id = record_id
        self.customer_id = customer_id
        self.agent_id = agent_id
        self.tool_name = tool_name
        self.params = params
        self.reason = reason
        self.timeout_minutes = timeout_minutes
        self.created_at = datetime.now(timezone.utc)
        self.expires_at = self.created_at + timedelta(minutes=timeout_minutes)
        self.resolved = False
        self.resolution: Optional[str] = None
        self.resolved_by: Optional[str] = None
        self.resolution_timestamp: Optional[datetime] = None


class EscalationManager:
    """
    Manages escalations for tool calls requiring human approval.

    Sends webhook notifications and handles resolution flow.
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        timeout_minutes: int = 30,
        on_escalate: str = "block",
        resolve_callback: Optional[Callable[[str], Dict[str, str]]] = None,
    ):
        """
        Initialize escalation manager.

        Args:
            webhook_url: URL to POST escalation notifications
            timeout_minutes: Default timeout for escalations
            on_escalate: 'block' (wait for resolution) or 'notify_and_proceed' (continue)
            resolve_callback: Optional callback to check for resolutions
        """
        self.webhook_url = webhook_url
        self.timeout_minutes = timeout_minutes
        self.on_escalate = on_escalate
        self.resolve_callback = resolve_callback

        # Track active escalations
        self._escalations: Dict[str, EscalationRequest] = {}
        self._lock = threading.Lock()

    def escalate(
        self,
        record_id: str,
        customer_id: Optional[str],
        agent_id: str,
        tool_name: str,
        params: Dict[str, Any],
        reason: str,
    ) -> EscalationRequest:
        """
        Create and send an escalation request.

        Args:
            record_id: Audit record ID
            customer_id: Customer identifier
            agent_id: Agent identifier
            tool_name: Tool being called
            params: Tool parameters
            reason: Why it's being escalated

        Returns:
            EscalationRequest object

        Raises:
            AegisEscalationTimeout: If blocking and timeout expires
        """
        escalation_id = f"esc_{uuid.uuid4().hex[:12]}"

        escalation = EscalationRequest(
            escalation_id=escalation_id,
            record_id=record_id,
            customer_id=customer_id,
            agent_id=agent_id,
            tool_name=tool_name,
            params=params,
            reason=reason,
            timeout_minutes=self.timeout_minutes,
        )

        with self._lock:
            self._escalations[escalation_id] = escalation

        # Send webhook notification
        if self.webhook_url:
            self._send_webhook(escalation)

        # If blocking, wait for resolution
        if self.on_escalate == "block":
            return self._wait_for_resolution(escalation)

        # Otherwise return immediately
        return escalation

    def _send_webhook(self, escalation: EscalationRequest) -> None:
        """Send escalation webhook notification."""
        payload = {
            "type": "escalation_request",
            "escalation_id": escalation.escalation_id,
            "record_id": escalation.record_id,
            "customer_id": escalation.customer_id,
            "agent_id": escalation.agent_id,
            "tool_name": escalation.tool_name,
            "params": escalation.params,
            "reason": escalation.reason,
            "resolve_url": f"https://api.aegis.dev/v1/escalations/{escalation.escalation_id}/resolve",
            "expires_at": escalation.expires_at.isoformat(),
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # Log error but don't fail the escalation
            print(f"Error sending escalation webhook: {e}")

    def _wait_for_resolution(self, escalation: EscalationRequest) -> EscalationRequest:
        """
        Block and wait for human resolution.

        Args:
            escalation: EscalationRequest to wait for

        Returns:
            Resolved EscalationRequest

        Raises:
            AegisEscalationTimeout: If timeout expires
        """
        poll_interval = 2  # seconds
        start_time = time.time()
        timeout_seconds = self.timeout_minutes * 60

        while time.time() - start_time < timeout_seconds:
            # Check if resolved
            with self._lock:
                if escalation.resolved:
                    return escalation

            # Use callback if provided
            if self.resolve_callback:
                try:
                    resolution_data = self.resolve_callback(escalation.escalation_id)
                    if resolution_data:
                        self.resolve(
                            escalation.escalation_id,
                            resolution=resolution_data.get("resolution", "approved"),
                            resolved_by=resolution_data.get("resolved_by", "unknown"),
                        )
                        return escalation
                except Exception as e:
                    print(f"Error in resolve_callback: {e}")

            # Wait before next check
            time.sleep(poll_interval)

        # Timeout expired
        raise AegisEscalationTimeout(escalation.escalation_id, self.timeout_minutes)

    def resolve(
        self,
        escalation_id: str,
        resolution: str,
        resolved_by: str,
    ) -> None:
        """
        Resolve an escalation (called by external resolution API).

        Args:
            escalation_id: Escalation to resolve
            resolution: 'approved' or 'denied'
            resolved_by: Email/ID of resolver

        Raises:
            ValueError: If escalation not found or already resolved
        """
        with self._lock:
            if escalation_id not in self._escalations:
                raise ValueError(f"Escalation {escalation_id} not found")

            escalation = self._escalations[escalation_id]

            if escalation.resolved:
                raise ValueError(f"Escalation {escalation_id} already resolved")

            if resolution not in ("approved", "denied"):
                raise ValueError(f"Invalid resolution: {resolution}")

            escalation.resolved = True
            escalation.resolution = resolution
            escalation.resolved_by = resolved_by
            escalation.resolution_timestamp = datetime.now(timezone.utc)

    def get_escalation(self, escalation_id: str) -> Optional[EscalationRequest]:
        """Get an escalation by ID."""
        with self._lock:
            return self._escalations.get(escalation_id)

    def list_pending(self) -> list[EscalationRequest]:
        """List all pending (unresolved) escalations."""
        with self._lock:
            return [e for e in self._escalations.values() if not e.resolved]

    def cleanup_expired(self) -> None:
        """Remove expired escalations from tracking."""
        now = datetime.now(timezone.utc)
        with self._lock:
            expired = [
                eid
                for eid, e in self._escalations.items()
                if e.expires_at < now
            ]
            for eid in expired:
                del self._escalations[eid]
