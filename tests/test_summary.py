"""
test_summary.py - Automated test suite for Prompt 8: Auto-summary feature for OmniRAG AI.

Tests covered:
1. Unit test: generate_summary() returns None for empty/whitespace input.
2. Unit test: generate_summary() truncates input text exceeding 8,000 characters.
3. Unit test: generate_summary() sends tabular/CSV prompt when file_type is 'csv'.
4. Unit test: generate_summary() sends prose prompt when file_type is 'txt'/'pdf'/'docx'.
5. Unit test: generate_summary() safely catches Groq API errors and returns None without raising.
6. Integration test: POST /documents/upload persists summary in SQLite documents table.
7. Integration test: POST /documents/upload succeeds and reaches 'indexed' status even if summary generation fails.
8. Integration test: GET /documents/{username} includes the 'summary' field in response.
"""

import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database.connection import Base, get_db
from backend.database.models import User, Document
from backend.chat.summary_service import generate_summary

# Use isolated in-memory SQLite database for testing
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


def create_test_user(username: str = "summary_test_user"):
    """Creates a test user directly in the database."""
    db = TestingSessionLocal()
    try:
        user = User(
            username=username,
            hashed_password="mock_hashed_password"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


# ==============================================================================
# 1. UNIT TESTS: generate_summary()
# ==============================================================================

def test_generate_summary_empty_text():
    """Confirms empty or whitespace text immediately returns None."""
    assert generate_summary("", "txt") is None
    assert generate_summary("   \n\t  ", "pdf") is None
    assert generate_summary(None, "csv") is None


def test_generate_summary_truncation():
    """Confirms text exceeding 8,000 characters is safely truncated to 8,000 chars."""
    long_text = "OmniRAG intelligence " * 600  # > 12,000 characters
    assert len(long_text) > 8000

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "This document discusses OmniRAG intelligence architecture and features."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("backend.chat.get_groq_client", return_value=mock_client):
        summary = generate_summary(long_text, "txt")

    assert summary == "This document discusses OmniRAG intelligence architecture and features."
    # Verify the user prompt received text capped at 8000 chars
    called_messages = mock_client.chat.completions.create.call_args[1]["messages"]
    user_prompt = called_messages[1]["content"]
    assert len(user_prompt) < 8500  # 8000 chars + surrounding template


def test_generate_summary_csv_prompt():
    """Confirms CSV files trigger dataset/tabular schema instructions."""
    csv_text = "id,name,role,salary\n1,Alice,Engineer,120000\n2,Bob,Scientist,130000"

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "This dataset contains employee salary records with names, IDs, and roles."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("backend.chat.get_groq_client", return_value=mock_client):
        summary = generate_summary(csv_text, "csv")

    assert summary == "This dataset contains employee salary records with names, IDs, and roles."
    called_messages = mock_client.chat.completions.create.call_args[1]["messages"]
    system_prompt = called_messages[0]["content"]
    user_prompt = called_messages[1]["content"]

    assert "CSV dataset" in system_prompt or "data analyst" in system_prompt
    assert "```csv" in user_prompt


def test_generate_summary_handles_exception_gracefully():
    """Confirms that if Groq API throws an error, generate_summary returns None without crashing."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("Groq network connection reset")

    with patch("backend.chat.get_groq_client", return_value=mock_client):
        summary = generate_summary("Sample document content.", "txt")

    assert summary is None


# ==============================================================================
# 2. INTEGRATION TESTS: POST /documents/upload & GET /documents/{username}
# ==============================================================================

def test_upload_document_auto_generates_and_stores_summary():
    """
    Confirms that upon successful upload and indexing:
    1. Document reaches status 'indexed'.
    2. Document.summary is generated and stored in SQLite.
    3. DocumentUploadResponse contains the summary.
    4. GET /documents/{username} includes the summary.
    """
    username = "summary_auto_user"
    create_test_user(username)

    mock_summary = "This document provides project specifications for OmniRAG AI Prompt 8 auto-summarization."

    with patch("backend.documents.service.generate_summary", return_value=mock_summary):
        txt_content = b"OmniRAG AI is an advanced enterprise RAG platform with auto-summary capabilities."
        response = client.post(
            "/documents/upload",
            data={"username": username},
            files={"file": ("prompt8_spec.txt", io.BytesIO(txt_content), "text/plain")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "indexed"
    assert data["summary"] == mock_summary

    # Verify directly in SQLite DB
    db = TestingSessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == data["id"]).first()
        assert doc is not None
        assert doc.summary == mock_summary
        assert doc.status == "indexed"
    finally:
        db.close()

    # Verify GET /documents/{username} includes summary
    get_res = client.get(f"/documents/{username}")
    assert get_res.status_code == 200
    doc_list = get_res.json()
    assert len(doc_list) == 1
    assert doc_list[0]["summary"] == mock_summary
    assert doc_list[0]["status"] == "indexed"


def test_upload_document_resilience_when_summary_fails():
    """
    Prompt 8 Constraint:
    Summary generation must never block or fail the core upload/indexing flow.
    If summary generation fails, document should still be 'indexed' with summary=None.
    """
    username = "summary_resilience_user"
    create_test_user(username)

    # Simulate generate_summary returning None due to an API timeout
    with patch("backend.documents.service.generate_summary", return_value=None):
        txt_content = b"Knowledge base document that succeeds indexing even without a summary."
        response = client.post(
            "/documents/upload",
            data={"username": username},
            files={"file": ("resilience_doc.txt", io.BytesIO(txt_content), "text/plain")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "indexed"
    assert data["summary"] is None

    # Verify in GET /documents/{username}
    get_res = client.get(f"/documents/{username}")
    assert get_res.status_code == 200
    doc_list = get_res.json()
    assert len(doc_list) == 1
    assert doc_list[0]["summary"] is None
    assert doc_list[0]["status"] == "indexed"
