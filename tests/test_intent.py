"""Focused verification for three-way session message intent handling."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database.connection import Base, get_db
from backend.database.models import Document
import backend.chat.service as chat_module
from backend.prompts.rag_prompts import ABOUT_BOT_MESSAGE
from backend.chat.llm_service import build_rag_prompt


engine = create_engine(
    "sqlite:///:memory:",
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


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


client = TestClient(app)


def register_and_create_session(username: str) -> int:
    assert client.post(
        "/auth/register",
        json={"username": username, "password": "password123"},
    ).status_code == 200
    response = client.post("/chat/sessions", json={"username": username})
    assert response.status_code == 201
    return response.json()["session_id"]


def add_indexed_document(username: str) -> None:
    db = TestingSessionLocal()
    try:
        db.add(Document(
            username=username,
            original_filename="tasks.txt",
            file_type="txt",
            status="indexed",
            chunk_count=1,
        ))
        db.commit()
    finally:
        db.close()


def test_document_agnostic_intent_and_retrieval_paths(monkeypatch):
    """Verify only obvious meta messages bypass retrieval; content decides the rest."""
    intents = {
        "hi how are you": "GREETING",
        "can you speak Roman Urdu?": "ABOUT_BOT",
        "how many days notice is required?": "CHECK_DOCUMENTS",
        "what unrelated fact is mentioned?": "CHECK_DOCUMENTS",
    }
    search_calls = []
    monkeypatch.setattr(chat_module, "classify_intent", lambda message: intents[message])
    monkeypatch.setattr(
        chat_module,
        "search_chunks",
        lambda **kwargs: search_calls.append(kwargs) or (
            [{"document_id": 1, "filename": "policy.txt", "file_type": "txt", "chunk_index": 0,
              "distance": 0.2, "text": "Employees must give 30 days notice before resignation."}]
            if "days notice" in kwargs["query"] else
            [{"document_id": 1, "filename": "policy.txt", "file_type": "txt", "chunk_index": 0,
              "distance": 0.95, "text": "Employees must give 30 days notice before resignation."}]
        ),
    )
    monkeypatch.setattr(
        chat_module,
        "generate_answer",
        lambda **kwargs: "The required notice period is 30 days.",
    )

    greeting_session = register_and_create_session("intent_greeting")
    greeting = client.post(
        f"/chat/sessions/{greeting_session}/message",
        json={"username": "intent_greeting", "query": "hi how are you"},
    ).json()
    assert "Hello" in greeting["answer"]

    about_bot_session = register_and_create_session("intent_about_bot")
    about_bot = client.post(
        f"/chat/sessions/{about_bot_session}/message",
        json={"username": "intent_about_bot", "query": "can you speak Roman Urdu?"},
    ).json()
    assert about_bot["answer"] == ABOUT_BOT_MESSAGE
    assert "Roman Urdu" in about_bot["answer"]

    zero_docs_session = register_and_create_session("intent_zero_docs")
    zero_docs = client.post(
        f"/chat/sessions/{zero_docs_session}/message",
        json={"username": "intent_zero_docs", "query": "how many days notice is required?"},
    ).json()
    assert "upload a document first" in zero_docs["answer"].lower()

    username = "intent_indexed"
    answerable_session = register_and_create_session(username)
    add_indexed_document(username)
    answerable = client.post(
        f"/chat/sessions/{answerable_session}/message",
        json={"username": username, "query": "how many days notice is required?"},
    ).json()
    assert answerable["is_fallback"] is False
    assert "30 days" in answerable["answer"]
    assert answerable["citations"]

    fallback = client.post(
        f"/chat/sessions/{answerable_session}/message",
        json={"username": username, "query": "what unrelated fact is mentioned?"},
    ).json()
    assert fallback["is_fallback"] is True
    assert fallback["citations"] == []
    assert len(search_calls) == 2

    prompt = build_rag_prompt(
        "how many days notice is required?",
        [{"document_id": 1, "filename": "policy.txt", "chunk_index": 0, "text": "30 days notice."}],
    )
    assert "NOT_FOUND_IN_DOCUMENT" in prompt
