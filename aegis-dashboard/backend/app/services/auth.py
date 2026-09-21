"""
Authentication service with JWT token generation and validation.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..models.refresh_token import RefreshToken
from ..models.user import User

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT bearer scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def hash_api_key(raw_key: str) -> str:
    """
    Hash an SDK ingestion API key for storage/comparison.

    Uses HMAC-SHA256 keyed with a dedicated pepper (not the JWT
    secret_key) rather than a plain hash, so a database dump alone isn't
    enough to forge a key even if the hashing scheme is known.
    """
    return hmac.new(settings.api_key_pepper.encode(), raw_key.encode(), hashlib.sha256).hexdigest()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user (convenience wrapper)."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_user_from_token(token: str, db: AsyncSession) -> User | None:
    """
    Resolve a user from a JWT access token without raising.

    Used by the WebSocket endpoint, which needs to choose its own close code
    (4001/4003) rather than let an HTTPException propagate.
    """
    try:
        payload = decode_access_token(token)
    except HTTPException:
        return None

    email = payload.get("sub")
    if email is None:
        return None

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    return user


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_refresh_token(user: User, db: AsyncSession) -> str:
    """Issue a new refresh token for a user, persisting only its hash."""
    raw_token = secrets.token_urlsafe(32)

    refresh_token = RefreshToken(
        user_id=user.user_id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_token)
    await db.commit()

    return raw_token


async def rotate_refresh_token(raw_token: str, db: AsyncSession) -> tuple[str, str]:
    """
    Validate a refresh token, revoke it, and issue a new access/refresh pair.

    Raises:
        HTTPException: If the token is unknown, revoked, or expired.
    """
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token))
    )
    stored = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_result = await db.execute(select(User).where(User.user_id == stored.user_id))
    user = user_result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    stored.revoked_at = datetime.now(timezone.utc)

    new_access_token = create_access_token(data={"sub": user.email})
    new_refresh_token = await create_refresh_token(user, db)

    return new_access_token, new_refresh_token


async def revoke_refresh_token(raw_token: str, db: AsyncSession) -> None:
    """Revoke a refresh token (e.g. on logout). No-op if already revoked/unknown."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token))
    )
    stored = result.scalar_one_or_none()

    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        await db.commit()


def require_role(required_role: str):
    """
    Dependency to require a specific role.

    Args:
        required_role: Required role (admin, operator, viewer)

    Returns:
        Dependency function
    """

    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        role_hierarchy = {"viewer": 0, "operator": 1, "admin": 2}

        user_level = role_hierarchy.get(current_user.role, -1)
        required_level = role_hierarchy.get(required_role, 999)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )

        return current_user

    return role_checker
