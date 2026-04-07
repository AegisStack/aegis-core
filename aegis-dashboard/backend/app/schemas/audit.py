"""
Pydantic schemas for audit records.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class AuditRecordCreate(BaseModel):
    """Schema for creating audit records (from SDK ingestion)."""

    record_id: UUID
    timestamp: datetime
    customer_id: Optional[str] = None
    agent_id: str
    session_id: Optional[str] = None
    policy_version: str
    tool_name: str
    params: dict[str, Any]
    outcome: str  # allow, deny, escalate
    matched_rule: str
    reason: str
    escalation_id: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None
    resolution_timestamp: Optional[datetime] = None
    execution_result: Optional[Any] = None
    execution_error: Optional[str] = None
    latency_ms: Optional[float] = None


class AuditRecordResponse(BaseModel):
    """Schema for audit record responses."""

    record_id: str
    timestamp: str
    customer_id: Optional[str]
    agent_id: str
    session_id: Optional[str]
    policy_version: str
    tool_name: str
    params: dict[str, Any]
    outcome: str
    matched_rule: str
    reason: str
    escalation_id: Optional[str]
    resolved_by: Optional[str]
    resolution: Optional[str]
    resolution_timestamp: Optional[str]
    execution_result: Optional[Any]
    execution_error: Optional[str]
    latency_ms: Optional[float]

    class Config:
        from_attributes = True


class AuditQueryParams(BaseModel):
    """Query parameters for audit log search."""

    customer_id: Optional[str] = None
    agent_id: Optional[str] = None
    tool_name: Optional[str] = None
    outcome: Optional[str] = None  # allow, deny, escalate
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)
