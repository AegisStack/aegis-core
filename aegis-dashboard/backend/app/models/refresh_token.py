"""
Refresh Token Model - Tracks issued refresh tokens for rotation and revocation.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class RefreshToken(Base):
    """
    Refresh token model.

    Stores only a hash of the token, never the raw value, so a database dump
    doesn't expose usable tokens. Rotated (revoked_at set) on every use.
    """

    __tablename__ = "refresh_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
