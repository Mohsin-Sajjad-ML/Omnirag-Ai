"""Regression tests for the controlled general-knowledge term-presence gate."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import chat as chat_module
from backend.documents import rag_service as rag_module
from backend.database.connection import Base, get_db
from backend.main import app
from backend.database.models import Document


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


@pytest.fixture
def gate_client(monkeypatch):
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(rag_module, "SessionLocal", TestingSessionLocal)

    def extract_subject(context):
        current_query = context.rsplit("CURRENT USER QUERY:\n", 1)[-1].lower()
        if "deep learning" in current_query:
            return "deep learning"
        if "machine learning" in current_query:
            return "machine learning"
        if "more detail" in current_query and "machine learning" in context.lower():
            return "machine learning"
        if "fastapi" in current_query:
            return "fastapi"
        return "quantum teleportation"

    def retrieve_chunks(username, query, document_ids=None, top_k=3):
        lowered = query.lower()
        if "machine learning" in lowered or "deep learning" in lowered:
            return [{
                "id": "mention",
                "text": "The report mentions machine learning once.",
                "document_id": 1,
                "filename": "mentions.txt",
                "file_type": "txt",
                "chunk_index": 0,
                "distance": 0.1,
            }]
        if "fastapi" in lowered:
            return [{
                "id": "definition",
                "text": "FastAPI is a modern Python web framework for building APIs.",
                "document_id": 2,
                "filename": "definitions.txt",
                "file_type": "txt",
                "chunk_index": 0,
                "distance": 0.1,
            }]
        return []

    def generate(query, retrieved_chunks, mode="document", term=None):
        if mode == "general_knowledge_assist":
            return (
                "General knowledge: machine learning enables systems to learn from data. "
                "Deep learning is a related concept."
            )
        if "fastapi" in query.lower():
            return "FastAPI is a Python web framework for building APIs."
        return "NOT_FOUND_IN_DOCUMENT"

    monkeypatch.setattr(chat_module, "extract_query_subject", extract_subject)
    monkeypatch.setattr(chat_module, "search_chunks", retrieve_chunks)
    monkeypatch.setattr(chat_module, "generate_answer", generate)

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)


def test_term_presence_gate_and_followups(gate_client):
    username = "term_gate_user"
    register = gate_client.post(
        "/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert register.status_code == 200

    db = TestingSessionLocal()
    db.add_all([
        Document(
            id=1,
            username=username,
            original_filename="mentions.txt",
            file_type="txt",
            status="indexed",
            extracted_text="The report mentions machine learning once.",
            chunk_count=1,
        ),
        Document(
            id=2,
            username=username,
            original_filename="definitions.txt",
            file_type="txt",
            status="indexed",
            extracted_text="FastAPI is a modern Python web framework for building APIs.",
            chunk_count=1,
        ),
    ])
    db.commit()
    db.close()

    session = gate_client.post("/chat/sessions", json={"username": username}).json()
    session_id = session["session_id"]

    def ask(query, document_ids):
        response = gate_client.post(
            f"/chat/sessions/{session_id}/message",
            json={
                "username": username,
                "query": query,
                "document_ids": document_ids,
            },
        )
        assert response.status_code == 200, response.text
        return response.json()

    machine = ask("What is machine learning?", [1])
    assert machine["source"] == "general_knowledge"
    assert machine["is_fallback"] is False
    assert machine["citations"] == []

    more_detail = ask("Give me more detail", [1])
    assert more_detail["source"] == "general_knowledge"
    assert more_detail["is_fallback"] is False

    deep = ask("What is deep learning?", [1])
    assert deep["source"] == "document"
    assert deep["is_fallback"] is True
    assert deep["citations"] == []

    documented = ask("What is FastAPI?", [2])
    assert documented["source"] == "document"
    assert documented["is_fallback"] is False
    assert documented["citations"]

    absent = ask("What is quantum teleportation?", [1])
    assert absent["source"] == "document"
    assert absent["is_fallback"] is True
    assert absent["citations"] == []