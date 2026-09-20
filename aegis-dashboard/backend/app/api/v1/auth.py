"""
Authentication API endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ...database import get_db
from ...models.user import User
from ...services.auth import (
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    get_password_hash,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)

router = APIRouter()
settings = get_settings()


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """User registration schema."""

    email: EmailStr
    password: str
    full_name: str
    customer_id: str


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    """Refresh request schema."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Refresh response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    """Logout request schema."""

    refresh_token: str | None = None


class UserResponse(BaseModel):
    """User response schema."""

    user_id: str
    email: str
    full_name: str | None
    customer_id: str
    role: str
    is_active: bool
    is_verified: bool


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.

    Creates a new user account and returns an access token.
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        customer_id=data.customer_id,
        role="viewer",  # Default role
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate access + refresh tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = await create_refresh_token(user, db)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user.to_dict(),
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login with email and password.

    Returns an access token on successful authentication.
    """
    # Find user
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Generate access + refresh tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = await create_refresh_token(user, db)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user.to_dict(),
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    return UserResponse(**current_user.to_dict())


@router.post("/auth/refresh", response_model=RefreshResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Exchange a refresh token for a new access/refresh pair.

    The presented refresh token is revoked as part of this call (rotation) -
    it cannot be used again.
    """
    new_access_token, new_refresh_token = await rotate_refresh_token(data.refresh_token, db)
    return RefreshResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/auth/logout")
async def logout(
    data: LogoutRequest | None = Body(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Logout endpoint.

    Revokes the presented refresh token, if any, so it can't be used to
    mint further access tokens. The access token itself remains valid
    until it expires (JWTs are stateless).
    """
    if data and data.refresh_token:
        await revoke_refresh_token(data.refresh_token, db)
    return {"message": "Logged out successfully"}
