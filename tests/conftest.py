"""
Pytest configuration and fixtures for testing.

This file provides:
- Test database setup (separate from development database)
- Reusable test fixtures (database session, test client, test users)
- Database cleanup between tests
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.schemas.user import UserCreate
from app.services.user import UserService

# Test database URL (uses SQLite in-memory for speed, or override with pytest env)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine with SQLite (check_same_thread=False is needed for SQLite)
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set to True for SQL query debugging
)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def test_db():
    """
    Fixture that provides a clean database session for each test.

    Creates all tables before the test, yields a session,
    then drops all tables after the test completes.

    Scope: function - each test gets a fresh database
    """
    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables to ensure clean state
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_db):
    """
    Fixture that provides a FastAPI TestClient with test database.

    Overrides the get_db dependency to use the test database
    instead of the production database.

    Scope: function - each test gets a fresh client
    """
    # Override the get_db dependency
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Create test client
    with TestClient(app) as test_client:
        yield test_client

    # Clean up - remove dependency override
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(test_db):
    """
    Fixture that creates a regular test user in the database.

    Returns the created user object (with hashed_password).
    Useful for tests that need an existing user.
    """
    user_data = UserCreate(
        email="testuser@example.com",
        username="testuser",
        password="Test123!@#",
    )
    user = UserService.create(db=test_db, user_in=user_data)
    return user


@pytest.fixture(scope="function")
def test_superuser(test_db):
    """
    Fixture that creates a superuser test account.

    Returns the created superuser object.
    Useful for testing admin-only endpoints.
    """
    user_data = UserCreate(
        email="admin@example.com",
        username="admin",
        password="Admin123!@#",
    )
    user = UserService.create(db=test_db, user_in=user_data)

    # Manually set superuser status (no public API for this)
    user.is_superuser = True
    test_db.commit()
    test_db.refresh(user)

    return user


@pytest.fixture(scope="function")
def auth_headers(client, test_user):
    """
    Fixture that provides authentication headers for a regular user.

    Logs in the test_user and returns headers with Bearer token.
    Use with client.get("/endpoint", headers=auth_headers)
    """
    response = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={
            "email": test_user.email,
            "password": "Test123!@#",  # Original password before hashing
        },
    )
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture(scope="function")
def superuser_headers(client, test_superuser):
    """
    Fixture that provides authentication headers for a superuser.

    Logs in the test_superuser and returns headers with Bearer token.
    Use for testing admin-only endpoints.
    """
    response = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={
            "email": test_superuser.email,
            "password": "Admin123!@#",  # Original password before hashing
        },
    )
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}
