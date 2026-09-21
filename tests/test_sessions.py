"""
test_sessions.py - Automated test suite for Prompt 9: Chat sessions, persistence, and messaging pipeline.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database.connection import Base, get_db

# In-memory SQLite database for test isolation
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
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


def test_session_lifecycle():
    username = "session_user_1"
    reg = client.post("/auth/register", json={"username": username, "password": "password123"})
    assert reg.status_code == 200

    # 1. Create session
    create_res = client.post("/chat/sessions", json={"username": username})
    assert create_res.status_code == 201
    session_data = create_res.json()
    assert "session_id" in session_data
    session_id = session_data["session_id"]
    assert session_data["title"] == "New Chat"

    # 2. List sessions
    list_res = client.get(f"/chat/sessions/{username}")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    assert sessions[0]["title"] == "New Chat"

    # 3. Empty messages
    msgs_res = client.get(f"/chat/sessions/{session_id}/messages")
    assert msgs_res.status_code == 200
    assert msgs_res.json() == []

    # 4. Attempt unauthorized delete (wrong username)
    bad_del = client.request(
        "DELETE",
        f"/chat/sessions/{session_id}",
        json={"username": "wrong_user"}
    )
    assert bad_del.status_code == 403

    # 5. Authorized delete
    del_res = client.request(
        "DELETE",
        f"/chat/sessions/{session_id}",
        json={"username": username}
    )
    assert del_res.status_code == 200

    # Verify session is gone
    after_list = client.get(f"/chat/sessions/{username}")
    assert after_list.status_code == 200
    assert len(after_list.json()) == 0


def test_session_message_and_title_generation():
    username = "session_rag_user"
    client.post("/auth/register", json={"username": username, "password": "password123"})

    doc_text = "OmniRAG project version is 9.0. Secret encryption key is AlphaOmega."
    files = {"file": ("project_info.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")}
    up_res = client.post("/documents/upload", data={"username": username}, files=files)
    assert up_res.status_code == 200
    assert up_res.json()["status"] == "indexed"

    # Create session
    sess_res = client.post("/chat/sessions", json={"username": username})
    session_id = sess_res.json()["session_id"]

    # Send message
    msg_res = client.post(
        f"/chat/sessions/{session_id}/message",
        json={
            "username": username,
            "query": "What is the secret encryption key?",
        }
    )
    assert msg_res.status_code == 200
    resp_data = msg_res.json()
    assert "AlphaOmega" in resp_data["answer"]
    assert resp_data["is_fallback"] is False
    assert len(resp_data["citations"]) >= 1

    # Check session title auto-generation
    sess_list = client.get(f"/chat/sessions/{username}").json()
    assert len(sess_list) == 1
    assert "encryption key" in sess_list[0]["title"].lower()

    # Check message transcript persistence
    msgs = client.get(f"/chat/sessions/{session_id}/messages").json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "What is the secret encryption key?"
    assert msgs[1]["role"] == "assistant"
    assert "AlphaOmega" in msgs[1]["content"]
    assert len(msgs[1]["citations"]) >= 1
