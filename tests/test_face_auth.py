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

from backend.main import app
from backend.database.connection import Base, get_db
from backend.database.models import User
from backend.auth.face_matching import calculate_euclidean_distance, find_best_face_match

from backend.auth.dependencies import get_current_clerk_user

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


current_test_user = {"user_id": "alex", "session_id": "test_session", "claims": {"sub": "alex"}}


def override_clerk_user():
    return current_test_user


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_clerk_user] = override_clerk_user
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_clerk_user, None)


client = TestClient(app)


def create_test_user(user_id: str):
    """Helper to insert user directly into test database."""
    db = TestingSessionLocal()
    try:
        user = User(clerk_user_id=user_id)
        db.add(user)
        db.commit()
    finally:
        db.close()


# Helper: generates 128-float vector with specified base value
def make_descriptor(val: float, noise: float = 0.0) -> list:
    return [val + (i * 0.0001) + noise for i in range(128)]


def test_register_face_success():
    """Test registering a face descriptor derives identity from Clerk session."""
    current_test_user["user_id"] = "alex"
    create_test_user("alex")

    descriptor = make_descriptor(0.1)
    response = client.post("/auth/register-face", json={
        "face_descriptor": descriptor
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Face registered successfully"

    # Verify status check reflects registered face
    info_res = client.get("/auth/user/alex")
    assert info_res.status_code == 200
    assert info_res.json()["has_face_registered"] is True

    # Verify /auth/me also reflects registered face
    me_res = client.get("/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["has_face_registered"] is True


def test_register_face_creates_user_if_missing():
    """Test registering face for a new Clerk user auto-creates User record."""
    current_test_user["user_id"] = "brand_new_clerk_user"

    descriptor = make_descriptor(0.15)
    response = client.post("/auth/register-face", json={
        "face_descriptor": descriptor
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Face registered successfully"

    info_res = client.get("/auth/user/brand_new_clerk_user")
    assert info_res.status_code == 200
    assert info_res.json()["has_face_registered"] is True


def test_register_face_unauthenticated_fails():
    """Test registering face without valid Clerk session returns 401."""
    app.dependency_overrides.pop(get_current_clerk_user, None)
    descriptor = make_descriptor(0.1)
    response = client.post("/auth/register-face", json={
        "face_descriptor": descriptor
    })
    assert response.status_code == 401


def test_login_face_success():
    """Test facial recognition login matches candidate below threshold 0.5."""
    # Register two users with distinct face descriptors
    current_test_user["user_id"] = "sarah"
    sarah_descriptor = make_descriptor(0.1)
    client.post("/auth/register-face", json={"face_descriptor": sarah_descriptor})

    current_test_user["user_id"] = "david"
    david_descriptor = make_descriptor(0.8)
    client.post("/auth/register-face", json={"face_descriptor": david_descriptor})

    # Incoming scan very close to Sarah's descriptor (small delta across 128 dims)
    incoming_sarah = make_descriptor(0.1, noise=0.01)

    response = client.post("/auth/login/face", json={"face_descriptor": incoming_sarah})
    assert response.status_code == 200
    data = response.json()
    assert data["clerk_user_id"] == "sarah"
    assert data["message"] == "Login successful"


def test_login_face_unrecognized_returns_401():
    """Test face scan too far from any registered user returns 401 Face not recognized."""
    current_test_user["user_id"] = "sarah"
    client.post("/auth/register-face", json={"face_descriptor": make_descriptor(0.1)})

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


def test_add_face_success_without_password():
    """Test registering an additional face appends descriptor via Clerk session without password requirement."""
    current_test_user["user_id"] = "karen"

    old_desc = make_descriptor(0.1)
    client.post("/auth/register-face", json={"face_descriptor": old_desc})

    # Add second descriptor
    new_desc = make_descriptor(0.4)
    response = client.post("/auth/add-face", json={
        "face_descriptor": new_desc
    })
    assert response.status_code == 200
    assert response.json()["message"] in ("Face added successfully", "Face updated successfully")

    # Verify login works with both descriptors
    login_res1 = client.post("/auth/login/face", json={"face_descriptor": new_desc})
    assert login_res1.status_code == 200
    assert login_res1.json()["clerk_user_id"] == "karen"

    login_res2 = client.post("/auth/login/face", json={"face_descriptor": old_desc})
    assert login_res2.status_code == 200
    assert login_res2.json()["clerk_user_id"] == "karen"


def test_list_and_delete_faces():
    """Test GET /auth/faces and DELETE /auth/faces/{id}."""
    current_test_user["user_id"] = "multi_user"

    # Register two faces
    face1 = make_descriptor(0.1)
    face2 = make_descriptor(0.3)
    client.post("/auth/register-face", json={"face_descriptor": face1, "label": "Morning Face"})
    client.post("/auth/add-face", json={"face_descriptor": face2, "label": "Evening Face"})

    # List faces
    res = client.get("/auth/faces")
    assert res.status_code == 200
    faces = res.json()
    assert len(faces) == 2
    # Verify no raw descriptors returned
    for f in faces:
        assert "descriptor" not in f
        assert "id" in f
        assert "label" in f
        assert "created_at" in f

    # Delete first face
    face_to_delete_id = faces[0]["id"]
    del_res = client.delete(f"/auth/faces/{face_to_delete_id}")
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Face deleted successfully"

    # Verify list now has 1 face
    res_after = client.get("/auth/faces")
    assert len(res_after.json()) == 1


def test_delete_other_user_face_forbidden():
    """Test cannot delete another user's face."""
    current_test_user["user_id"] = "user_one"
    client.post("/auth/register-face", json={"face_descriptor": make_descriptor(0.1)})
    faces_one = client.get("/auth/faces").json()
    face_id = faces_one[0]["id"]

    # Switch to user_two
    current_test_user["user_id"] = "user_two"
    del_res = client.delete(f"/auth/faces/{face_id}")
    assert del_res.status_code in (403, 404)


def test_account_deletion(monkeypatch):
    """Test DELETE /auth/account purges user data and calls Clerk delete."""
    current_test_user["user_id"] = "delete_me"

    # Register face
    client.post("/auth/register-face", json={"face_descriptor": make_descriptor(0.1)})
    # Create chat session
    client.post("/chat/sessions", json={})

    deleted_clerk_users = []

    class MockClerkUsers:
        def delete(self, *, user_id, **kwargs):
            deleted_clerk_users.append(user_id)
            return {"id": user_id, "deleted": True}

    class MockClerk:
        def __init__(self, bearer_auth=None):
            self.users = MockClerkUsers()

    monkeypatch.setattr("backend.auth.Clerk", MockClerk)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_mock")

    del_res = client.delete("/auth/account")
    assert del_res.status_code == 200
    assert del_res.json()["clerk_user_id"] == "delete_me"
    assert "delete_me" in deleted_clerk_users

    # Verify faces are gone
    faces_res = client.get("/auth/faces")
    assert len(faces_res.json()) == 0


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


def test_login_face_generates_clerk_sign_in_token(monkeypatch):
    """Test face login returns sign_in_token when Clerk API produces a ticket token."""
    current_test_user["user_id"] = "sarah"
    sarah_descriptor = make_descriptor(0.1)
    client.post("/auth/register-face", json={"face_descriptor": sarah_descriptor})

    class DummyTokenRes:
        token = "mock_clerk_ticket_xyz123"

    class DummySignInTokens:
        def create(self, request):
            return DummyTokenRes()

    class DummyClerk:
        def __init__(self, bearer_auth=None):
            self.sign_in_tokens = DummySignInTokens()

    monkeypatch.setattr("backend.auth.Clerk", DummyClerk)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_mock")

    incoming_sarah = make_descriptor(0.1, noise=0.01)
    response = client.post("/auth/login/face", json={"face_descriptor": incoming_sarah})
    assert response.status_code == 200
    data = response.json()
    assert data["clerk_user_id"] == "sarah"
    assert data["sign_in_token"] == "mock_clerk_ticket_xyz123"

