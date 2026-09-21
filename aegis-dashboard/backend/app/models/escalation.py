"""
Escalation Model - Tracks escalation requests and resolutions.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class Escalation(Base):
    """
    Escalation model - tracks tool calls requiring human approval.
    """

    __tablename__ = "escalations"

    # Primary key
    escalation_id = Column(String(255), primary_key=True)

    # Link to audit record
    record_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Context
    customer_id = Column(String(255), nullable=True, index=True)
    agent_id = Column(String(255), nullable=False, index=True)

    # Tool call details
    tool_name = Column(String(255), nullable=False)
    params = Column(JSON, nullable=False)
    reason = Column(Text, nullable=False)

    # Status
    status = Column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, approved, denied, expired
    resolved_by = Column(String(255), nullable=True)
    resolution_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_customer_status", "customer_id", "status"),
        Index("idx_agent_status", "agent_id", "status"),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "escalation_id": self.escalation_id,
            "record_id": str(self.record_id),
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "params": self.params,
            "reason": self.reason,
            "status": self.status,
            "resolved_by": self.resolved_by,
            "resolution_timestamp": (
                self.resolution_timestamp.isoformat() if self.resolution_timestamp else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
