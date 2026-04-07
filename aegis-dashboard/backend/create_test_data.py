"""Quick script to create test data - run inside container"""
import asyncio
from app.database import get_db
from app.models.user import User
from app.models.policy import Customer
from app.services.auth import get_password_hash
from sqlalchemy import select

async def main():
    async for db in get_db():
        # Check if customer exists
        result = await db.execute(select(Customer).where(Customer.customer_id == "test_customer"))
        existing = result.scalar_one_or_none()

        if existing:
            print("✅ Test data already exists!")
            print("\nLogin credentials:")
            print("  admin@test.com / admin123")
            print("  operator@test.com / operator123")
            print("  viewer@test.com / viewer123")
            return

        # Create customer
        customer = Customer(
            customer_id="test_customer",
            name="Test Company",
            api_key="test_api_key_12345"
        )
        db.add(customer)
        await db.flush()

        # Create users
        admin = User(
            email="admin@test.com",
            full_name="Admin User",
            hashed_password=get_password_hash("admin123"),
            customer_id="test_customer",
            role="admin",
            is_active=True,
            is_verified=True
        )
        operator = User(
            email="operator@test.com",
            full_name="Operator User",
            hashed_password=get_password_hash("operator123"),
            customer_id="test_customer",
            role="operator",
            is_active=True,
            is_verified=True
        )
        viewer = User(
            email="viewer@test.com",
            full_name="Viewer User",
            hashed_password=get_password_hash("viewer123"),
            customer_id="test_customer",
            role="viewer",
            is_active=True,
            is_verified=True
        )
        db.add_all([admin, operator, viewer])
        await db.commit()

        print("\n✅ Test data created successfully!")
        print("\nLogin credentials:")
        print("  Admin:    admin@test.com / admin123")
        print("  Operator: operator@test.com / operator123")
        print("  Viewer:   viewer@test.com / viewer123")
        print("\nAPI Key: test_api_key_12345")
        break

if __name__ == "__main__":
    asyncio.run(main())
