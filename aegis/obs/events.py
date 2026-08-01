"""
Observability Events

Policy-aware observability events for monitoring agent behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class ObservabilityEvent:
    """Base observability event."""

    event_type: str = ""
    timestamp: str = ""
    agent_id: str = ""
    customer_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ToolEvaluatedEvent(ObservabilityEvent):
    """Emitted for every tool call evaluation."""

    event_type: str = "tool_evaluated"
    tool_name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""  # allow, deny, escalate
    matched_rule: str = ""
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class EscalationCreatedEvent(ObservabilityEvent):
    """Emitted when escalation is created."""

    event_type: str = "escalation_created"
    escalation_id: str = ""
    tool_name: str = ""
    reason: str = ""
    expires_at: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class EscalationResolvedEvent(ObservabilityEvent):
    """Emitted when escalation is resolved."""

    event_type: str = "escalation_resolved"
    escalation_id: str = ""
    resolved_by: str = ""
    resolution: str = ""  # approved, denied
    duration_ms: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class PolicyLoadedEvent(ObservabilityEvent):
    """Emitted when policy is loaded or reloaded."""

    event_type: str = "policy_loaded"
    policy_version: str = ""
    rule_count: int = 0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class SessionSummaryEvent(ObservabilityEvent):
    """Emitted when session ends or times out."""

    event_type: str = "session_summary"
    session_id: str = ""
    total_calls: int = 0
    allows: int = 0
    denies: int = 0
    escalations: int = 0
    tools_used: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


def create_tool_evaluated_event(
    agent_id: str,
    customer_id: Optional[str],
    tool_name: str,
    params: dict[str, Any],
    outcome: str,
    matched_rule: str,
    latency_ms: float,
) -> ToolEvaluatedEvent:
    """Factory function for tool evaluated events."""
    return ToolEvaluatedEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent_id=agent_id,
        customer_id=customer_id,
        tool_name=tool_name,
        params=params,
        outcome=outcome,
        matched_rule=matched_rule,
        latency_ms=latency_ms,
    )
