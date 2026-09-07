"""
test_auth.py - Automated tests for the authentication API.

Tests covered:
1. User registration success (200 OK)
2. Duplicate username registration rejection (400 Bad Request)
3. Password login success (200 OK)
4. Password login failure with incorrect password (401 Unauthorized)
5. Password login failure with nonexistent username (401 Unauthorized)
6. Fetching user info for registered user (200 OK)
7. Fetching user info for nonexistent user (404 Not Found)
8. Input validation rules (422 Unprocessable Entity)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

# Use an isolated in-memory SQLite database with StaticPool for test runs
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Dependency override providing isolated in-memory database sessions during testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Apply dependency override to FastAPI app
app.dependency_overrides[get_db] = override_get_db

# Create TestClient instance
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Re-creates fresh database tables before each test function execution."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)



def test_register_user_success():
    """Test registering a new user returns HTTP 200 and success message."""
    payload = {
        "username": "john_doe",
        "password": "secretpassword123"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "john_doe"
    assert data["message"] == "User registered successfully"
    # Ensure sensitive password fields are never returned
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_username_fails():
    """Test registering the same username twice returns HTTP 400 Bad Request."""
    payload = {
        "username": "duplicate_user",
        "password": "password123"
    }
    # First registration attempt (succeeds)
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 200

    # Second registration attempt with identical username (fails with 400)
    res2 = client.post("/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"].lower()


def test_login_correct_password_success():
    """Test logging in with correct credentials returns HTTP 200."""
    credentials = {
        "username": "alice_smith",
        "password": "correctpassword123"
    }
    # Register user first
    client.post("/auth/register", json=credentials)

    # Attempt login with correct password
    response = client.post("/auth/login/password", json=credentials)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice_smith"
    assert data["message"] == "Login successful"


def test_login_wrong_password_fails():
    """Test logging in with an incorrect password returns HTTP 401 Unauthorized."""
    # Register user
    client.post("/auth/register", json={
        "username": "bob_builder",
        "password": "realpassword123"
    })

    # Login with wrong password
    response = client.post("/auth/login/password", json={
        "username": "bob_builder",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_nonexistent_user_fails():
    """Test logging in with a non-existent username returns HTTP 401 Unauthorized (generic error)."""
    response = client.post("/auth/login/password", json={
        "username": "ghost_user",
        "password": "any_password"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_get_user_info_success():
    """Test fetching user profile details for existing user."""
    client.post("/auth/register", json={
        "username": "charlie_brown",
        "password": "mypassword123"
    })

    response = client.get("/auth/user/charlie_brown")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "charlie_brown"
    assert data["has_face_registered"] is False
    assert "created_at" in data


def test_get_user_info_not_found():
    """Test fetching user profile details for non-existent user returns HTTP 404 Not Found."""
    response = client.get("/auth/user/unknown_user")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_pydantic_validation_rules():
    """Test Pydantic input validation rules for username pattern and password min length."""
    # Username too short (<3 characters) -> 422 Unprocessable Entity
    res1 = client.post("/auth/register", json={"username": "ab", "password": "validpassword"})
    assert res1.status_code == 422

    # Username invalid characters (contains special symbols) -> 422
    res2 = client.post("/auth/register", json={"username": "user@name!", "password": "validpassword"})
    assert res2.status_code == 422

    # Password too short (<6 characters) -> 422
    res3 = client.post("/auth/register", json={"username": "valid_user", "password": "123"})
    assert res3.status_code == 422
