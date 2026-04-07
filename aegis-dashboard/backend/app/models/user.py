"""
User Model for authentication and authorization.
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from ..database import Base


class User(Base):
    """User model for dashboard authentication."""

    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    # Associated customer for multi-tenancy
    customer_id = Column(String(255), ForeignKey("customers.customer_id"), nullable=False)

    # Role-based access control
    role = Column(String(50), nullable=False, default="viewer")  # admin, operator, viewer

    # Account status
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        """Convert to dictionary (excluding sensitive fields)."""
        return {
            "user_id": str(self.user_id),
            "email": self.email,
            "full_name": self.full_name,
            "customer_id": self.customer_id,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
