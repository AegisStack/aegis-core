"""
Initialize database with test data for local development.
Run this script after starting the database to create test users and customers.
"""

import asyncio
import sys
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, ".")

from app.database import Base
from app.models.policy import Customer
from app.models.user import User
from app.services.auth import get_password_hash


async def init_database():
    """Initialize database with test data."""

    DATABASE_URL = "postgresql+asyncpg://aegis:aegis@localhost:5432/aegis_dashboard"

    print("🔌 Connecting to database...")
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        print("📊 Creating tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("👤 Creating test customer and users...")
        async with async_session() as session:
            # Check if customer already exists
            from sqlalchemy import select
            result = await session.execute(
                select(Customer).where(Customer.customer_id == "test_customer")
            )
            existing_customer = result.scalar_one_or_none()

            if existing_customer:
                print("⚠️  Test customer already exists, skipping creation")
                return

            # Create test customer
            customer = Customer(
                customer_id="test_customer",
                name="Test Company",
                api_key="test_api_key_12345"
            )
            session.add(customer)
            await session.flush()

            # Create admin user
            admin = User(
                email="admin@test.com",
                full_name="Admin User",
                hashed_password=get_password_hash("admin123"),
                customer_id="test_customer",
                role="admin",
                is_active=True,
                is_verified=True
            )
            session.add(admin)

            # Create operator user
            operator = User(
                email="operator@test.com",
                full_name="Operator User",
                hashed_password=get_password_hash("operator123"),
                customer_id="test_customer",
                role="operator",
                is_active=True,
                is_verified=True
            )
            session.add(operator)

            # Create viewer user
            viewer = User(
                email="viewer@test.com",
                full_name="Viewer User",
                hashed_password=get_password_hash("viewer123"),
                customer_id="test_customer",
                role="viewer",
                is_active=True,
                is_verified=True
            )
            session.add(viewer)

            await session.commit()

            print("\n✅ Database initialized successfully!")
            print("\n📝 Test accounts created:")
            print("   • Admin:    admin@test.com / admin123")
            print("   • Operator: operator@test.com / operator123")
            print("   • Viewer:   viewer@test.com / viewer123")
            print("\n🔑 API Key: test_api_key_12345")
            print("\n🌐 Dashboard: http://localhost:3000")
            print("📡 Backend:   http://localhost:8000")
            print("📚 API Docs:  http://localhost:8000/docs")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("🚀 Initializing Aegis Dashboard Database\n")
    asyncio.run(init_database())
