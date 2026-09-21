"""
test_rag_websearch_combination.py - Tests for RAG + Web Search Combination Logic:
1. rag_enabled=True with indexed doc & match -> source: "rag" with citations.
2. rag_enabled=False, web_search_enabled=False -> general Groq answering, source: "llm_api", no decline.
3. rag_enabled=False, web_search_enabled=True -> web search answering, source: "web_search".
4. rag_enabled=True with no indexed docs -> falls through to source: "llm_api" or "web_search".
5. Message history GET /chat/sessions/{id}/messages preserves source field.
"""

import pytest
from unittest.mock import patch
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


current_test_user = {"user_id": "user_combo_tester", "claims": {"sub": "user_combo_tester"}}


def override_clerk_user():
    return current_test_user


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_clerk_user] = override_clerk_user

    # Seed test user
    db = TestingSessionLocal()
    user = User(
        clerk_user_id="user_combo_tester"
    )
    db.add(user)
    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_clerk_user, None)


client = TestClient(app)


def test_rag_disabled_web_disabled_returns_llm_api():
    """When RAG is false and web search is false, uses general Groq and returns source: llm_api."""
    # Create session
    create_res = client.post("/chat/sessions", json={"title": "Test General Knowledge"})
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    with patch("backend.chat.service._call_groq_general") as mock_groq_general:
        mock_groq_general.return_value = "The capital of France is Paris."

        msg_res = client.post(
            f"/chat/sessions/{session_id}/message",
            json={
                "query": "What is the capital of France?",
                "rag_enabled": False,
                "web_search_enabled": False,
            },
        )
        assert msg_res.status_code == 200
        data = msg_res.json()
        assert data["source"] == "llm_api"
        assert "Paris" in data["answer"]
        assert data["citations"] == []
        mock_groq_general.assert_called_once()

    # Check persistence in session messages
    history_res = client.get(f"/chat/sessions/{session_id}/messages")
    assert history_res.status_code == 200
    messages = history_res.json()
    assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0]["source"] == "llm_api"


def test_rag_disabled_web_enabled_returns_web_search():
    """When RAG is false and web search is true, uses Groq web search and returns source: web_search."""
    create_res = client.post("/chat/sessions", json={})
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    with patch("backend.chat.service._call_groq_web_search") as mock_groq_web:
        mock_groq_web.return_value = "Latest news: SpaceX launched Starship Flight 5 today."

        msg_res = client.post(
            f"/chat/sessions/{session_id}/message",
            json={
                "query": "What happened with SpaceX today?",
                "rag_enabled": False,
                "web_search_enabled": True,
            },
        )
        assert msg_res.status_code == 200
        data = msg_res.json()
        assert data["source"] == "web_search"
        assert "SpaceX" in data["answer"]
        mock_groq_web.assert_called_once()

    # Check persistence
    history_res = client.get(f"/chat/sessions/{session_id}/messages")
    assert history_res.status_code == 200
    assistant_msgs = [m for m in history_res.json() if m["role"] == "assistant"]
    assert assistant_msgs[0]["source"] == "web_search"


def test_rag_enabled_no_docs_falls_through():
    """When RAG is true but user has 0 indexed docs, falls through to general or web search."""
    create_res = client.post("/chat/sessions", json={})
    session_id = create_res.json()["id"]

    with patch("backend.chat.service._call_groq_general") as mock_groq_general:
        mock_groq_general.return_value = "Quantum computing uses qubits."

        msg_res = client.post(
            f"/chat/sessions/{session_id}/message",
            json={
                "query": "Explain quantum computing",
                "rag_enabled": True,
                "web_search_enabled": False,
            },
        )
        assert msg_res.status_code == 200
        data = msg_res.json()
        # Because 0 documents are indexed for this user, it fell through to general Groq
        assert data["source"] == "llm_api"
        assert "Quantum" in data["answer"]
        mock_groq_general.assert_called_once()


def test_rag_enabled_with_chunks_returns_rag():
    """When RAG is enabled and chunks are found, returns answer with citations and source: rag."""
    # Seed an indexed document for user
    from backend.database.models import Document
    db = TestingSessionLocal()
    doc = Document(
        clerk_user_id="user_combo_tester",
        original_filename="python_guide.txt",
        file_type="txt",
        status="indexed",
    )
    db.add(doc)
    db.commit()
    db.close()

    create_res = client.post("/chat/sessions", json={})
    session_id = create_res.json()["id"]

    mock_chunk = {
        "text": "Python was created by Guido van Rossum in 1991.",
        "metadata": {
            "source": "python_guide.txt",
            "file_type": "txt",
            "chunk_index": 0,
        },
        "distance": 0.12,
    }

    with patch("backend.chat.search_chunks", return_value=[mock_chunk]), \
         patch("backend.chat.generate_answer", return_value="Python was created by Guido van Rossum."):

        msg_res = client.post(
            f"/chat/sessions/{session_id}/message",
            json={
                "query": "Who created Python?",
                "rag_enabled": True,
                "web_search_enabled": False,
            },
        )
        assert msg_res.status_code == 200
        data = msg_res.json()
        assert data["source"] == "rag"
        assert "Guido van Rossum" in data["answer"]
        assert len(data["citations"]) > 0

    # Check persistence
    history_res = client.get(f"/chat/sessions/{session_id}/messages")
    assert history_res.status_code == 200
    assistant_msgs = [m for m in history_res.json() if m["role"] == "assistant"]
    assert assistant_msgs[0]["source"] == "rag"


def test_rag_and_web_enabled_term_in_doc_returns_hybrid():
    """
    When both RAG and Web Search are enabled and the term is present in the document,
    synthesizes a hybrid response with source 'rag_and_web', web answer, document skill/project context,
    and citations, never declining.
    """
    from backend.database.models import Document
    db = TestingSessionLocal()
    doc = Document(
        clerk_user_id="user_combo_tester",
        original_filename="Mohsin_Sajjad_Resume.pdf",
        file_type="pdf",
        status="indexed",
        extracted_text=(
            "Mohsin Sajjad\n"
            "Technical Skills\nLanguages: Python, C++\n"
            "Projects\nT20 Cricket Match Outcome Predictor | Python, XGBoost\n"
            "Developed real-time prediction model using Python and XGBoost."
        ),
    )
    db.add(doc)
    db.commit()
    db.close()

    create_res = client.post("/chat/sessions", json={})
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    mock_chunk = {
        "text": "Technical Skills\nLanguages: Python, C++",
        "metadata": {
            "source": "Mohsin_Sajjad_Resume.pdf",
            "file_type": "pdf",
            "chunk_index": 0,
        },
        "filename": "Mohsin_Sajjad_Resume.pdf",
        "file_type": "pdf",
        "distance": 0.35,
    }

    synthetic_hybrid = (
        "**Python** was found in your uploaded document (*Mohsin_Sajjad_Resume.pdf*).\n\n"
        "### What is Python?\n"
        "Python is a high-level, interpreted programming language widely used in AI and software engineering.\n\n"
        "### Python in Your Resume\n"
        "In **Mohsin_Sajjad_Resume.pdf**, Python is featured under **Technical Skills (Languages)** and was utilized "
        "in your project **T20 Cricket Match Outcome Predictor**."
    )

    with patch("backend.chat.service._get_search_chunks", return_value=lambda *args, **kw: [mock_chunk]), \
         patch("backend.chat.service._get_generate_answer", return_value=lambda *args, **kw: "NOT_FOUND_IN_DOCUMENT"), \
         patch("backend.chat.service._get_extract_query_subject", return_value=lambda *args, **kw: "python"), \
         patch("backend.chat.service._generate_hybrid_rag_web_answer", return_value=synthetic_hybrid):

        msg_res = client.post(
            f"/chat/sessions/{session_id}/message",
            json={
                "query": "what is python",
                "rag_enabled": True,
                "web_search_enabled": True,
            },
        )
        assert msg_res.status_code == 200
        data = msg_res.json()
        assert data["source"] == "rag_and_web"
        assert data["is_fallback"] is False
        assert "What is Python" in data["answer"]
        assert "Mohsin_Sajjad_Resume.pdf" in data["answer"]
        assert "T20 Cricket Match Outcome Predictor" in data["answer"]
        assert len(data["citations"]) > 0


def test_rag_and_web_enabled_term_not_in_doc_returns_web_search():
    """
    When both RAG and Web Search are enabled but the queried term is NOT in the user's document,
    does NOT decline or show fallback; instead answers via live web search (source: web_search).
    """
    from backend.database.models import Document
    db = TestingSessionLocal()
    doc = Document(
        clerk_user_id="user_combo_tester",
        original_filename="sample_policy.txt",
        file_type="txt",
        status="indexed",
        extracted_text="Office hours are from 9 AM to 5 PM Monday to Friday.",
    )
    db.add(doc)
    db.commit()
    db.close()

    create_res = client.post("/chat/sessions", json={})
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    mock_chunk = {
        "text": "Office hours are from 9 AM to 5 PM Monday to Friday.",
        "metadata": {"source": "sample_policy.txt", "file_type": "txt", "chunk_index": 0},
        "filename": "sample_policy.txt",
        "file_type": "txt",
        "distance": 0.70,
    }

    with patch("backend.chat.service._get_search_chunks", return_value=lambda *args, **kw: [mock_chunk]), \
         patch("backend.chat.service._get_generate_answer", return_value=lambda *args, **kw: "NOT_FOUND_IN_DOCUMENT"), \
         patch("backend.chat.service._get_extract_query_subject", return_value=lambda *args, **kw: "quantum computing"), \
         patch("backend.chat.service._call_groq_web_search", return_value="Quantum computing uses superposition."):

        msg_res = client.post(
            f"/chat/sessions/{session_id}/message",
            json={
                "query": "explain quantum computing",
                "rag_enabled": True,
                "web_search_enabled": True,
            },
        )
        assert msg_res.status_code == 200
        data = msg_res.json()
        assert data["source"] == "web_search"
        assert data["is_fallback"] is False
        assert "Quantum computing" in data["answer"]

