"""
Authentication API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta

from ...database import get_db
from ...models.user import User
from ...services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_active_user,
)
from ...config import get_settings

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
    token_type: str = "bearer"
    user: dict


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

    # Generate access token
    access_token = create_access_token(data={"sub": user.email})

    return TokenResponse(
        access_token=access_token,
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

    # Generate access token
    access_token = create_access_token(data={"sub": user.email})

    return TokenResponse(
        access_token=access_token,
        user=user.to_dict(),
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    return UserResponse(**current_user.to_dict())


@router.post("/auth/logout")
async def logout():
    """
    Logout endpoint.

    Since JWT is stateless, this is mainly for client-side token removal.
    In production, you might want to implement token blacklisting.
    """
    return {"message": "Logged out successfully"}
