"""
Policy Model - Stores customer policies with version history.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class Policy(Base):
    """
    Policy model - stores YAML policies with version history.
    """

    __tablename__ = "policies"

    # Primary key
    policy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identifiers
    customer_id = Column(String(255), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)

    # Policy content
    policy_yaml = Column(Text, nullable=False)
    policy_hash = Column(String(64), nullable=False)  # SHA-256 hash of YAML

    # Version tracking
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)

    # Metadata
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_customer_agent", "customer_id", "agent_id"),
        Index("idx_customer_agent_active", "customer_id", "agent_id", "is_active"),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "policy_id": str(self.policy_id),
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "policy_yaml": self.policy_yaml,
            "policy_hash": self.policy_hash,
            "version": self.version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "description": self.description,
        }


class Customer(Base):
    """Customer model."""

    __tablename__ = "customers"

    customer_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    # HMAC-SHA256 of the raw API key (see services/auth.hash_api_key) - the
    # raw key is never stored, only ever shown once at creation time.
    api_key_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    is_active = Column(Boolean, nullable=False, default=True)

    def to_dict(self):
        """Convert to dictionary (excluding sensitive fields)."""
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }
