"""
Pydantic schemas for audit records.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditRecordCreate(BaseModel):
    """Schema for creating audit records (from SDK ingestion)."""

    record_id: UUID
    timestamp: datetime
    customer_id: str | None = None
    agent_id: str
    session_id: str | None = None
    policy_version: str
    tool_name: str
    params: dict[str, Any]
    outcome: str  # allow, deny, escalate
    matched_rule: str
    reason: str
    escalation_id: str | None = None
    resolved_by: str | None = None
    resolution: str | None = None
    resolution_timestamp: datetime | None = None
    execution_result: Any | None = None
    execution_error: str | None = None
    latency_ms: float | None = None


class AuditRecordResponse(BaseModel):
    """Schema for audit record responses."""

    record_id: str
    timestamp: str
    customer_id: str | None
    agent_id: str
    session_id: str | None
    policy_version: str
    tool_name: str
    params: dict[str, Any]
    outcome: str
    matched_rule: str
    reason: str
    escalation_id: str | None
    resolved_by: str | None
    resolution: str | None
    resolution_timestamp: str | None
    execution_result: Any | None
    execution_error: str | None
    latency_ms: float | None

    class Config:
        from_attributes = True


class AuditQueryParams(BaseModel):
    """Query parameters for audit log search."""

    customer_id: str | None = None
    agent_id: str | None = None
    tool_name: str | None = None
    outcome: str | None = None  # allow, deny, escalate
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)
