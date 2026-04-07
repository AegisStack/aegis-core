"""
Audit Record Model - TimescaleDB hypertable for time-series data.
"""

from sqlalchemy import Column, String, Text, Float, Integer, JSON, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from ..database import Base


class AuditRecord(Base):
    """
    Audit record model - stores every tool call evaluation.

    This table is converted to a TimescaleDB hypertable partitioned by timestamp
    for efficient time-series queries.
    """

    __tablename__ = "audit_records"

    # Primary key
    record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Timestamp - partition key for TimescaleDB
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Context
    customer_id = Column(String(255), nullable=True, index=True)
    agent_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)

    # Policy evaluation
    policy_version = Column(String(255), nullable=False)
    tool_name = Column(String(255), nullable=False, index=True)
    params = Column(JSON, nullable=False)
    outcome = Column(String(50), nullable=False, index=True)  # allow, deny, escalate
    matched_rule = Column(String(500), nullable=False)
    reason = Column(Text, nullable=False)

    # Escalation fields
    escalation_id = Column(String(255), nullable=True, index=True)
    resolved_by = Column(String(255), nullable=True)
    resolution = Column(String(50), nullable=True)  # approved, denied
    resolution_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Execution result
    execution_result = Column(JSON, nullable=True)
    execution_error = Column(Text, nullable=True)

    # Performance
    latency_ms = Column(Float, nullable=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_customer_timestamp", "customer_id", "timestamp"),
        Index("idx_agent_timestamp", "agent_id", "timestamp"),
        Index("idx_customer_agent_timestamp", "customer_id", "agent_id", "timestamp"),
        Index("idx_customer_outcome", "customer_id", "outcome"),
        Index("idx_customer_tool", "customer_id", "tool_name"),
    )

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "record_id": str(self.record_id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "policy_version": self.policy_version,
            "tool_name": self.tool_name,
            "params": self.params,
            "outcome": self.outcome,
            "matched_rule": self.matched_rule,
            "reason": self.reason,
            "escalation_id": self.escalation_id,
            "resolved_by": self.resolved_by,
            "resolution": self.resolution,
            "resolution_timestamp": (
                self.resolution_timestamp.isoformat() if self.resolution_timestamp else None
            ),
            "execution_result": self.execution_result,
            "execution_error": self.execution_error,
            "latency_ms": self.latency_ms,
        }
