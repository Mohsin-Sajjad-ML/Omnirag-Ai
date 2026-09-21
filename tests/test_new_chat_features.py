"""
test_new_chat_features.py - End-to-end tests for newly added session features:
1. Pin: PATCH /chat/sessions/{id}/pin + pinned ordering/flag.
2. Export: GET /chat/sessions/{id}/export?format=txt|pdf (timestamps in txt, formatted PDF).
3. Duplicate: POST /chat/sessions/{id}/duplicate (copies session and messages).
4. Message edit: POST /chat/sessions/{id}/messages/{message_id}/edit (truncates subsequent messages, re-runs RAG pipeline).
5. Message regenerate: POST /chat/sessions/{id}/regenerate (regenerates last assistant message).
6. Clerk ownership validation on all new endpoints.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database.connection import Base, get_db
from backend.auth.dependencies import get_current_clerk_user
from backend.database.models import User, ChatSession, ChatMessage

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


current_test_user = {"user_id": "user_alpha_123", "claims": {"sub": "user_alpha_123"}}


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


def test_pin_session_and_ownership():
    global current_test_user
    current_test_user = {"user_id": "user_alpha_123", "claims": {"sub": "user_alpha_123"}}

    # Create session
    create_res = client.post("/chat/sessions", json={"username": "user_alpha"})
    assert create_res.status_code == 201
    sess_id = create_res.json()["id"]
    assert create_res.json()["pinned"] is False

    # Pin session
    pin_res = client.patch(f"/chat/sessions/{sess_id}/pin", json={"pinned": True})
    assert pin_res.status_code == 200
    assert pin_res.json()["pinned"] is True

    # List sessions confirms pinned
    list_res = client.get("/chat/sessions")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert len(sessions) == 1
    assert sessions[0]["pinned"] is True

    # Another user cannot pin/unpin this session (ownership check)
    current_test_user = {"user_id": "user_beta_456", "claims": {"sub": "user_beta_456"}}
    forbidden_res = client.patch(f"/chat/sessions/{sess_id}/pin", json={"pinned": False})
    assert forbidden_res.status_code == 403

    # Reset user back and unpin
    current_test_user = {"user_id": "user_alpha_123", "claims": {"sub": "user_alpha_123"}}
    unpin_res = client.patch(f"/chat/sessions/{sess_id}/pin", json={"pinned": False})
    assert unpin_res.status_code == 200
    assert unpin_res.json()["pinned"] is False


def test_duplicate_session():
    global current_test_user
    current_test_user = {"user_id": "user_alpha_123", "claims": {"sub": "user_alpha_123"}}

    # Create session and add message
    create_res = client.post("/chat/sessions", json={"username": "user_alpha"})
    sess_id = create_res.json()["id"]

    post_msg = client.post(f"/chat/sessions/{sess_id}/message", json={"query": "Hello!"})
    assert post_msg.status_code == 200

    # Duplicate session
    dup_res = client.post(f"/chat/sessions/{sess_id}/duplicate")
    assert dup_res.status_code == 200
    dup_data = dup_res.json()
    new_sess_id = dup_data["id"]
    assert new_sess_id != sess_id
    assert "(Copy)" in dup_data["title"]

    # Verify messages were duplicated
    orig_msgs = client.get(f"/chat/sessions/{sess_id}/messages").json()
    dup_msgs = client.get(f"/chat/sessions/{new_sess_id}/messages").json()
    assert len(orig_msgs) == 2
    assert len(dup_msgs) == 2
    assert dup_msgs[0]["content"] == orig_msgs[0]["content"]
    assert dup_msgs[1]["content"] == orig_msgs[1]["content"]
    assert dup_msgs[0]["id"] != orig_msgs[0]["id"]

    # Another user cannot duplicate user_alpha's session
    current_test_user = {"user_id": "user_beta_456", "claims": {"sub": "user_beta_456"}}
    bad_dup = client.post(f"/chat/sessions/{sess_id}/duplicate")
    assert bad_dup.status_code == 403


def test_export_session_txt_and_pdf():
    global current_test_user
    current_test_user = {"user_id": "user_alpha_123", "claims": {"sub": "user_alpha_123"}}

    # Create session with messages
    create_res = client.post("/chat/sessions", json={"username": "user_alpha"})
    sess_id = create_res.json()["id"]

    client.post(f"/chat/sessions/{sess_id}/message", json={"query": "What is OmniRAG?"})

    # Export TXT
    txt_res = client.get(f"/chat/sessions/{sess_id}/export?format=txt")
    assert txt_res.status_code == 200
    assert "text/plain" in txt_res.headers["content-type"]
    txt_text = txt_res.text
    assert "OmniRAG AI - Chat Session Transcript" in txt_text
    assert "What is OmniRAG?" in txt_text
    assert "UTC" in txt_text  # Timestamp present

    # Export PDF
    pdf_res = client.get(f"/chat/sessions/{sess_id}/export?format=pdf")
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers["content-type"]
    assert pdf_res.content.startswith(b"%PDF")

    # Export Compressed Context TXT
    ctx_txt_res = client.get(f"/chat/sessions/{sess_id}/export?format=txt&mode=context")
    assert ctx_txt_res.status_code == 200
    assert "text/plain" in ctx_txt_res.headers["content-type"]
    assert "_context.txt" in ctx_txt_res.headers.get("content-disposition", "")
    ctx_txt = ctx_txt_res.text
    assert "Compressed Chat Context" in ctx_txt
    assert "Conversation Goal & Topic" in ctx_txt or "Goal" in ctx_txt

    # Export Compressed Context PDF
    ctx_pdf_res = client.get(f"/chat/sessions/{sess_id}/export?format=pdf&mode=context")
    assert ctx_pdf_res.status_code == 200
    assert "application/pdf" in ctx_pdf_res.headers["content-type"]
    assert "_context.pdf" in ctx_pdf_res.headers.get("content-disposition", "")
    assert ctx_pdf_res.content.startswith(b"%PDF")

    # Another user cannot export
    current_test_user = {"user_id": "user_beta_456", "claims": {"sub": "user_beta_456"}}
    forbidden_export = client.get(f"/chat/sessions/{sess_id}/export?format=txt")
    assert forbidden_export.status_code == 403


def test_message_edit_and_regenerate():
    global current_test_user
    current_test_user = {"user_id": "user_alpha_123", "claims": {"sub": "user_alpha_123"}}

    # Create session
    create_res = client.post("/chat/sessions", json={"username": "user_alpha"})
    sess_id = create_res.json()["id"]

    # Send 2 queries (total 4 messages: user1, asst1, user2, asst2)
    client.post(f"/chat/sessions/{sess_id}/message", json={"query": "First greeting"})
    client.post(f"/chat/sessions/{sess_id}/message", json={"query": "Second question"})

    msgs_before = client.get(f"/chat/sessions/{sess_id}/messages").json()
    assert len(msgs_before) == 4
    first_user_msg_id = msgs_before[0]["id"]

    # Edit the first user message
    edit_res = client.post(
        f"/chat/sessions/{sess_id}/messages/{first_user_msg_id}/edit",
        json={"query": "Edited first question"}
    )
    assert edit_res.status_code == 200

    # Check that subsequent messages were truncated (now total 2 messages: edited user1, new asst1)
    msgs_after = client.get(f"/chat/sessions/{sess_id}/messages").json()
    assert len(msgs_after) == 2
    assert msgs_after[0]["id"] == first_user_msg_id
    assert msgs_after[0]["content"] == "Edited first question"
    assert msgs_after[1]["role"] == "assistant"

    # Regenerate assistant message
    regen_res = client.post(f"/chat/sessions/{sess_id}/regenerate")
    assert regen_res.status_code == 200
    msgs_after_regen = client.get(f"/chat/sessions/{sess_id}/messages").json()
    assert len(msgs_after_regen) == 2
    assert msgs_after_regen[0]["content"] == "Edited first question"
    assert msgs_after_regen[1]["role"] == "assistant"

    # Unauthorized check
    current_test_user = {"user_id": "user_beta_456", "claims": {"sub": "user_beta_456"}}
    bad_edit = client.post(
        f"/chat/sessions/{sess_id}/messages/{first_user_msg_id}/edit",
        json={"query": "Hacked query"}
    )
    assert bad_edit.status_code == 403

    bad_regen = client.post(f"/chat/sessions/{sess_id}/regenerate")
    assert bad_regen.status_code == 403
