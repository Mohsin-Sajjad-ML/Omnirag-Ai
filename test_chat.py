"""
test_chat.py - Automated test suite for Prompt 7: Response formatting, source citations & fallback handling.

Tests:
1. Unit test: format_response() returns friendly fallback with empty citations when marker is detected.
2. Unit test: format_response() groups multiple chunk references under the same filename.
3. Unit test: format_response() flags low_context=True when fewer than 2 chunks are used for valid answer.
4. Unit test: format_response() flags low_context=False when 2 or more chunks are used for valid answer.
5. Integration: POST /chat/query with no indexed documents returns fallback format.
6. Integration: POST /chat/query end-to-end:
   - Answerable question returns is_fallback=False, non-empty grouped citations, and appropriate low_context signal.
   - Unrelated question returns is_fallback=True, friendly fallback message, and empty citations.
7. Integration: POST /chat/query with missing GROQ_API_KEY returns clear 500 error without crashing.

================================================================================
CURL REPRODUCTION COMMANDS (PROMPT 7 FORMAT):
================================================================================
# 1. Register user:
# curl -X POST http://127.0.0.1:8000/auth/register \
#   -H "Content-Type: application/json" \
#   -d '{"username": "curl_user", "password": "password123"}'
#
# 2. Upload document:
# curl -X POST http://127.0.0.1:8000/documents/upload \
#   -F "username=curl_user" \
#   -F "file=@sample_doc.txt"
#
# 3. Answerable query:
# curl -X POST http://127.0.0.1:8000/chat/query \
#   -H "Content-Type: application/json" \
#   -d '{"username": "curl_user", "query": "What is the security protocol?"}'
# Response shape:
# {
#   "answer": "The security protocol is Code Omega-7.",
#   "is_fallback": false,
#   "citations": [
#     {
#       "filename": "sample_doc.txt",
#       "file_type": "txt",
#       "chunk_references": [0],
#       "document_id": 1
#     }
#   ],
#   "low_context": true
# }
#
# 4. Unrelated query:
# curl -X POST http://127.0.0.1:8000/chat/query \
#   -H "Content-Type: application/json" \
#   -d '{"username": "curl_user", "query": "What is the speed of light in water?"}'
# Response shape:
# {
#   "answer": "I couldn't find an answer to that in your uploaded document(s). Try rephrasing your question, or check that you've uploaded the right file.",
#   "is_fallback": true,
#   "citations": [],
#   "low_context": false
# }
================================================================================
"""

import io
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.rag import search_chunks
from app.llm import generate_answer, format_response, FALLBACK_MESSAGE

# In-memory SQLite database for isolated tests
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


# ==============================================================================
# 1. UNIT TESTS: FORMAT_RESPONSE & CITATION GROUPING
# ==============================================================================

def test_format_response_fallback_on_marker():
    """Confirms that NOT_FOUND_IN_DOCUMENT produces the friendly fallback and empty citations."""
    sample_chunks = [
        {"document_id": 1, "filename": "specs.pdf", "file_type": "pdf", "chunk_index": 0}
    ]
    res = format_response(raw_answer="NOT_FOUND_IN_DOCUMENT", chunks_used=sample_chunks)
    assert res["is_fallback"] is True
    assert res["answer"] == FALLBACK_MESSAGE
    assert res["citations"] == []
    assert res["low_context"] is False


def test_format_response_fallback_on_empty_chunks():
    """Confirms that empty chunks_used always triggers fallback response."""
    res = format_response(raw_answer="Some answer", chunks_used=[])
    assert res["is_fallback"] is True
    assert res["answer"] == FALLBACK_MESSAGE
    assert res["citations"] == []
    assert res["low_context"] is False


def test_format_response_grouped_citations():
    """
    VIVA TEST: Confirms that multiple chunks from the same document are grouped
    together with sorted chunk_references rather than listed redundantly.
    """
    chunks = [
        {"document_id": 10, "filename": "manual.pdf", "file_type": "pdf", "chunk_index": 3},
        {"document_id": 10, "filename": "manual.pdf", "file_type": "pdf", "chunk_index": 0},
        {"document_id": 10, "filename": "manual.pdf", "file_type": "pdf", "chunk_index": 1},
        {"document_id": 20, "filename": "appendix.docx", "file_type": "docx", "chunk_index": 0},
    ]
    res = format_response(raw_answer="The manual states step 1, 2, and 4.", chunks_used=chunks)

    assert res["is_fallback"] is False
    assert res["answer"] == "The manual states step 1, 2, and 4."
    assert len(res["citations"]) == 2  # Exactly 2 distinct files
    assert res["low_context"] is False  # 4 chunks >= 2

    manual_citation = next(c for c in res["citations"] if c["filename"] == "manual.pdf")
    assert manual_citation["file_type"] == "pdf"
    assert manual_citation["document_id"] == 10
    # Chunks must be deduplicated and sorted
    assert manual_citation["chunk_references"] == [0, 1, 3]

    appendix_citation = next(c for c in res["citations"] if c["filename"] == "appendix.docx")
    assert appendix_citation["file_type"] == "docx"
    assert appendix_citation["document_id"] == 20
    assert appendix_citation["chunk_references"] == [0]


def test_format_response_low_context_flag():
    """Confirms low_context=True when fewer than 2 chunks are used for non-fallback."""
    single_chunk = [
        {"document_id": 1, "filename": "brief.txt", "file_type": "txt", "chunk_index": 0}
    ]
    res = format_response(raw_answer="Brief answer.", chunks_used=single_chunk)
    assert res["is_fallback"] is False
    assert res["low_context"] is True
    assert len(res["citations"]) == 1


# ==============================================================================
# 2. INTEGRATION TESTS: POST /chat/query ENDPOINT (PROMPT 7 SHAPE)
# ==============================================================================

def test_chat_query_no_indexed_documents():
    """Confirms query short-circuits with friendly fallback when user has no indexed chunks."""
    response = client.post(
        "/chat/query",
        json={
            "username": "brand_new_user_with_no_docs",
            "query": "What is the secret recipe?",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_fallback"] is True
    assert data["answer"] == FALLBACK_MESSAGE
    assert data["citations"] == []
    assert data["low_context"] is False


def test_chat_query_end_to_end_answerable_and_unrelated():
    """
    Task 4 & 5 Verification:
    1. Upload document (Prompt 4/5 pipeline) and confirm 'indexed' status.
    2. Query with answerable question:
       -> is_fallback: false
       -> citations: non-empty list of grouped citations
       -> answer: factual synthesized content
       -> low_context: boolean signal
    3. Query with unrelated question:
       -> is_fallback: true
       -> answer: friendly fallback message (not raw marker)
       -> citations: []
       -> low_context: false
    """
    username = "prompt7_tester_user"
    client.post("/auth/register", json={"username": username, "password": "securepassword123"})

    doc_text = (
        "OmniRAG architecture documentation:\n"
        "OmniRAG is powered by a FastAPI backend and ChromaDB vector store.\n"
        "The system administrator is Sarah Connor and the security protocol is Code Omega-7.\n"
        "System deployments occur every Tuesday at 03:00 UTC."
    )

    files = {"file": ("omnirag_specs.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")}
    data = {"username": username}

    # Step 1: Upload document
    upload_res = client.post("/documents/upload", data=data, files=files)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["status"] == "indexed"
    assert upload_data["chunk_count"] >= 1
    doc_id = upload_data["id"]

    # Step 2: Answerable question
    q1_res = client.post(
        "/chat/query",
        json={
            "username": username,
            "query": "Who is the system administrator and what is the security protocol?",
        },
    )
    assert q1_res.status_code == 200
    q1_data = q1_res.json()

    assert q1_data["is_fallback"] is False
    assert "Sarah Connor" in q1_data["answer"]
    assert "Omega-7" in q1_data["answer"]
    assert len(q1_data["citations"]) >= 1

    citation = q1_data["citations"][0]
    assert citation["filename"] == "omnirag_specs.txt"
    assert citation["document_id"] == doc_id
    assert 0 in citation["chunk_references"]
    assert isinstance(q1_data["low_context"], bool)

    # Step 3: Question completely unrelated to document
    q2_res = client.post(
        "/chat/query",
        json={
            "username": username,
            "query": "How many rings does Saturn have?",
        },
    )
    assert q2_res.status_code == 200
    q2_data = q2_res.json()

    assert q2_data["is_fallback"] is True
    assert q2_data["answer"] == FALLBACK_MESSAGE
    assert "NOT_FOUND_IN_DOCUMENT" not in q2_data["answer"]  # Raw marker must NOT be in final answer
    assert q2_data["citations"] == []
    assert q2_data["low_context"] is False


def test_chat_query_missing_api_key(monkeypatch):
    """
    Task 6 (Prompt 6) continuity:
    If GROQ_API_KEY is missing/empty, server returns clear 500 without crashing.
    """
    monkeypatch.setenv("GROQ_API_KEY", "")

    username = "key_test_user_p7"
    client.post("/auth/register", json={"username": username, "password": "password123"})
    files = {"file": ("test.txt", io.BytesIO(b"Some text for test"), "text/plain")}
    client.post("/documents/upload", data={"username": username}, files=files)

    response = client.post(
        "/chat/query",
        json={
            "username": username,
            "query": "What is the content?",
        },
    )
    assert response.status_code == 500
    res_json = response.json()
    error_message = res_json.get("detail", "") or res_json.get("message", "")
    assert "Groq API key is not configured" in error_message
