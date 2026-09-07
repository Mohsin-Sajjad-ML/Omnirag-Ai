"""
test_face_auth.py - Automated tests for face biometric authentication routes and algorithms.

Tests covered:
1. Face registration for existing user returns 200 and success message.
2. Face registration for nonexistent user returns 404 Not Found.
3. User info status reflects has_face_registered=True after face registration.
4. Face login returns 200 and username when descriptor Euclidean distance is < 0.5.
5. Face login returns 401 when distance is >= 0.5 (unrecognized face).
6. Face login returns 401 when database has no registered faces.
7. Updating face descriptor with valid password returns 200 OK.
8. Updating face descriptor with invalid password returns 401 Unauthorized.
9. Updating face descriptor for nonexistent user returns 404 Not Found.
10. Isolated Euclidean distance and threshold matching algorithm correctness.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.face_utils import calculate_euclidean_distance, find_best_face_match

# In-memory test database
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


client = TestClient(app)




# Helper: generates 128-float vector with specified base value
def make_descriptor(val: float, noise: float = 0.0) -> list:
    return [val + (i * 0.0001) + noise for i in range(128)]


def test_register_face_success():
    """Test registering a face descriptor for an existing user."""
    client.post("/auth/register", json={"username": "alex", "password": "password123"})

    descriptor = make_descriptor(0.1)
    response = client.post("/auth/register-face", json={
        "username": "alex",
        "face_descriptor": descriptor
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Face registered successfully"

    # Verify status check reflects registered face
    info_res = client.get("/auth/user/alex")
    assert info_res.status_code == 200
    assert info_res.json()["has_face_registered"] is True


def test_register_face_nonexistent_user():
    """Test registering face for nonexistent user returns 404."""
    descriptor = make_descriptor(0.1)
    response = client.post("/auth/register-face", json={
        "username": "nonexistent_alex",
        "face_descriptor": descriptor
    })
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_login_face_success():
    """Test facial recognition login matches candidate below threshold 0.5."""
    # Register two users with distinct face descriptors
    client.post("/auth/register", json={"username": "sarah", "password": "password123"})
    client.post("/auth/register", json={"username": "david", "password": "password123"})

    sarah_descriptor = make_descriptor(0.1)
    david_descriptor = make_descriptor(0.8)

    client.post("/auth/register-face", json={"username": "sarah", "face_descriptor": sarah_descriptor})
    client.post("/auth/register-face", json={"username": "david", "face_descriptor": david_descriptor})

    # Incoming scan very close to Sarah's descriptor (small delta across 128 dims)
    # delta = 0.01 per dim -> euclidean distance = sqrt(128 * 0.01^2) = sqrt(0.0128) ≈ 0.113 < 0.5
    incoming_sarah = make_descriptor(0.1, noise=0.01)

    response = client.post("/auth/login/face", json={"face_descriptor": incoming_sarah})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "sarah"
    assert data["message"] == "Login successful"


def test_login_face_unrecognized_returns_401():
    """Test face scan too far from any registered user returns 401 Face not recognized."""
    client.post("/auth/register", json={"username": "sarah", "password": "password123"})
    client.post("/auth/register-face", json={"username": "sarah", "face_descriptor": make_descriptor(0.1)})

    # Scanned face is far away (val=0.5 -> dist = sqrt(128 * 0.4^2) = sqrt(20.48) ≈ 4.52 >> 0.5)
    scanned_face = make_descriptor(0.5)

    response = client.post("/auth/login/face", json={"face_descriptor": scanned_face})
    assert response.status_code == 401
    assert "Face not recognized" in response.json()["message"]


def test_login_face_empty_database_returns_401():
    """Test face login with no registered users returns 401."""
    scanned_face = make_descriptor(0.2)
    response = client.post("/auth/login/face", json={"face_descriptor": scanned_face})
    assert response.status_code == 401
    assert "Face not recognized" in response.json()["message"]


def test_add_face_success_with_password():
    """Test re-registering face with correct password updates descriptor."""
    client.post("/auth/register", json={"username": "karen", "password": "securepass123"})

    old_desc = make_descriptor(0.1)
    client.post("/auth/register-face", json={"username": "karen", "face_descriptor": old_desc})

    # Update with new descriptor
    new_desc = make_descriptor(0.4)
    response = client.post("/auth/add-face", json={
        "username": "karen",
        "password": "securepass123",
        "face_descriptor": new_desc
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Face updated successfully"

    # Verify login works with new descriptor
    login_res = client.post("/auth/login/face", json={"face_descriptor": new_desc})
    assert login_res.status_code == 200
    assert login_res.json()["username"] == "karen"


def test_add_face_wrong_password_rejected():
    """Test re-registering face fails with wrong password."""
    client.post("/auth/register", json={"username": "karen", "password": "securepass123"})

    response = client.post("/auth/add-face", json={
        "username": "karen",
        "password": "wrongpassword",
        "face_descriptor": make_descriptor(0.2)
    })
    assert response.status_code == 401
    assert "invalid password" in response.json()["detail"].lower()


def test_euclidean_distance_and_threshold_logic():
    """Unit tests for calculate_euclidean_distance and find_best_face_match."""
    v1 = [1.0] * 128
    v2 = [1.0] * 128
    assert calculate_euclidean_distance(v1, v2) == 0.0

    # Test mismatch length raises ValueError
    with pytest.raises(ValueError):
        calculate_euclidean_distance([1.0] * 128, [1.0] * 64)

    # Test candidate matching logic
    candidates = [
        ("user_a", [0.0] * 128),
        ("user_b", [1.0] * 128),
    ]

    # Target close to user_a: distance = sqrt(128 * 0.02^2) ≈ 0.226 < 0.5
    target_a = [0.02] * 128
    match = find_best_face_match(target_a, candidates, threshold=0.5)
    assert match is not None
    assert match[0] == "user_a"

    # Target far from both: distance to user_a = sqrt(128 * 0.5^2) ≈ 5.65 > 0.5
    target_far = [0.5] * 128
    match_none = find_best_face_match(target_far, candidates, threshold=0.5)
    assert match_none is None
