"""
Pytest configuration and fixtures for backend tests.
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import Customer, User
from app.services.auth import create_access_token, get_password_hash, hash_api_key

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        # A NullPool opens a brand new (empty) SQLite ":memory:" database on
        # every checkout - StaticPool keeps a single connection alive so the
        # tables created below are visible to the session used by tests.
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session):
    """Create test client with database session override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_customer(db_session):
    """Create a test customer with API key."""
    raw_api_key = "test_api_key_123"
    customer = Customer(
        customer_id="test-customer",
        name="Test Customer",
        api_key_hash=hash_api_key(raw_api_key),
        is_active=True,
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    # Not a mapped column - only the hash is persisted. Stashed here so
    # tests can still send the real key as a header without re-deriving it.
    customer.api_key = raw_api_key
    return customer


async def _make_user(db_session, customer, role, email):
    user = User(
        email=email,
        hashed_password=get_password_hash("testpass123"),
        full_name=f"Test {role.title()}",
        customer_id=customer.customer_id,
        role=role,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def test_admin_user(db_session, test_customer):
    """Create a test admin user for test_customer."""
    return await _make_user(db_session, test_customer, "admin", "admin@test-customer.example")


@pytest.fixture(scope="function")
async def test_operator_user(db_session, test_customer):
    """Create a test operator user for test_customer."""
    return await _make_user(db_session, test_customer, "operator", "operator@test-customer.example")


@pytest.fixture(scope="function")
async def test_viewer_user(db_session, test_customer):
    """Create a test viewer user for test_customer."""
    return await _make_user(db_session, test_customer, "viewer", "viewer@test-customer.example")


@pytest.fixture(scope="function")
def admin_headers(test_admin_user):
    """Authorization header for a logged-in admin of test_customer."""
    token = create_access_token(data={"sub": test_admin_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def operator_headers(test_operator_user):
    """Authorization header for a logged-in operator of test_customer."""
    token = create_access_token(data={"sub": test_operator_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def viewer_headers(test_viewer_user):
    """Authorization header for a logged-in viewer of test_customer."""
    token = create_access_token(data={"sub": test_viewer_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def viewer_token(test_viewer_user):
    """Raw access token (not a header dict) for a viewer of test_customer."""
    return create_access_token(data={"sub": test_viewer_user.email})


@pytest.fixture(scope="function")
def ws_test_client(db_session):
    """
    Sync TestClient sharing the same overridden DB session as `client`.

    Needed only for WebSocket tests: httpx's AsyncClient (used by `client`)
    has no websocket support, so this uses Starlette's TestClient instead,
    which does.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as tc:
        yield tc

    app.dependency_overrides.clear()
