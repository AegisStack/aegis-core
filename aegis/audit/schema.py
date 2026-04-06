"""
Audit Record Schema

Structured, immutable audit records for every policy evaluation.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class AuditRecord:
    """
    Immutable audit record for a tool call evaluation.

    Written before execution for deny/escalate outcomes,
    after execution for allow outcomes.
    """

    # Core identification
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Context
    customer_id: Optional[str] = None
    agent_id: str = ""
    session_id: Optional[str] = None

    # Policy evaluation
    policy_version: str = ""
    tool_name: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    outcome: str = ""  # "allow", "deny", "escalate"
    matched_rule: str = ""
    reason: str = ""

    # Escalation fields (if applicable)
    escalation_id: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None  # "approved", "denied"
    resolution_timestamp: Optional[str] = None

    # Execution result (if allowed and executed)
    execution_result: Optional[Any] = None
    execution_error: Optional[str] = None

    # Performance
    latency_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), default=str)


def create_audit_record(
    agent_id: str,
    customer_id: Optional[str],
    session_id: Optional[str],
    policy_version: str,
    tool_name: str,
    params: Dict[str, Any],
    outcome: str,
    matched_rule: str,
    reason: str,
    escalation_id: Optional[str] = None,
    execution_result: Optional[Any] = None,
    execution_error: Optional[str] = None,
    latency_ms: Optional[float] = None,
) -> AuditRecord:
    """
    Factory function to create audit records with validation.

    Args:
        agent_id: Agent identifier
        customer_id: Customer identifier
        session_id: Session identifier
        policy_version: Version hash of policy evaluated
        tool_name: Name of tool called
        params: Parameters passed to tool
        outcome: "allow", "deny", or "escalate"
        matched_rule: Rule that matched
        reason: Human-readable explanation
        escalation_id: Escalation ID if escalated
        execution_result: Result if executed
        execution_error: Error if execution failed
        latency_ms: Evaluation latency in milliseconds

    Returns:
        AuditRecord instance
    """
    if outcome not in ("allow", "deny", "escalate"):
        raise ValueError(f"Invalid outcome: {outcome}")

    return AuditRecord(
        agent_id=agent_id,
        customer_id=customer_id,
        session_id=session_id,
        policy_version=policy_version,
        tool_name=tool_name,
        params=params,
        outcome=outcome,
        matched_rule=matched_rule,
        reason=reason,
        escalation_id=escalation_id,
        execution_result=execution_result,
        execution_error=execution_error,
        latency_ms=latency_ms,
    )
