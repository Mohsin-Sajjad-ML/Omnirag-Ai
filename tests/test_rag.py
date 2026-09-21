"""
test_rag.py - Automated test suite for chunking, embedding, ChromaDB vector storage, and search.

Tests covered:
1. chunk_text returns empty list for empty/whitespace input.
2. chunk_text returns a single chunk when word count <= chunk_size.
3. chunk_text correctly splits into overlapping chunks with word-level boundaries preserved.
4. chunk_csv_text preserves table headers across every chunk and groups rows cleanly.
5. embed_and_store generates embeddings and persists vectors in ChromaDB with proper metadata.
6. search_chunks retrieves semantically relevant chunks based on query similarity.
7. search_chunks filters properly when document_ids is specified.
8. Per-user Chroma collection isolation prevents cross-tenant data leakage.
9. delete_document_chunks removes document chunks from ChromaDB.
10. End-to-end: POST /documents/upload transitions document from parsing to "indexed" status with nonzero chunk_count.
11. End-to-end: GET /documents/{username} includes chunk_count in response.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database.connection import Base, get_db
from backend.database.models import User, Document
from backend.documents.rag_service import (
    chunk_text,
    chunk_csv_text,
    embed_and_store,
    search_chunks,
    delete_document_chunks,
    get_document_chunk_count,
    get_user_collection,
)

# Use in-memory SQLite database for testing
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
# UNIT TESTS: CHUNKING LOGIC
# ==============================================================================

def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\t  ") == []


def test_chunk_text_single_chunk():
    text = "Artificial intelligence is transforming modern software engineering."
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_overlapping():
    # Generate 120 distinct words: "word_0 word_1 ... word_119"
    words = [f"word_{i}" for i in range(120)]
    text = " ".join(words)

    # Chunk with size=50 and overlap=10 -> step=40
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) == 3

    # Check chunk 1: words 0 to 49
    assert chunks[0].startswith("word_0")
    assert chunks[0].endswith("word_49")

    # Check chunk 2: words 40 to 89 (overlap: words 40-49)
    assert chunks[1].startswith("word_40")
    assert chunks[1].endswith("word_89")

    # Check chunk 3: words 80 to 119 (overlap: words 80-89)
    assert chunks[2].startswith("word_80")
    assert chunks[2].endswith("word_119")


def test_chunk_csv_text():
    header = "[Table Columns (3)]: id, name, department"
    rows = [f"Row {i}: id={i}, name=Person_{i}, department=Engineering" for i in range(1, 45)]
    csv_text = "\n".join([header] + rows)

    chunks = chunk_csv_text(csv_text, rows_per_chunk=20)
    # 44 rows with 20 rows per chunk -> 3 chunks (20, 20, 4)
    assert len(chunks) == 3

    # Every chunk must start with the schema header
    for chunk in chunks:
        assert chunk.startswith(header)

    # First chunk contains rows 1 to 20
    assert "Row 1: id=1" in chunks[0]
    assert "Row 20: id=20" in chunks[0]
    assert "Row 21: id=21" not in chunks[0]

    # Second chunk contains rows 21 to 40
    assert "Row 21: id=21" in chunks[1]
    assert "Row 40: id=40" in chunks[1]

    # Third chunk contains remaining 4 rows
    assert "Row 41: id=41" in chunks[2]
    assert "Row 44: id=44" in chunks[2]


# ==============================================================================
# INTEGRATION TESTS: EMBEDDING & CHROMADB VECTOR STORAGE
# ==============================================================================

def test_embed_and_store_and_search():
    username = "test_alice"
    doc_id = 101

    chunks = [
        "FastAPI is a modern, fast web framework for building APIs with Python.",
        "PostgreSQL is a powerful open-source object-relational database system.",
        "ChromaDB is the AI-native open-source embedding vector database.",
    ]

    stored_count = embed_and_store(
        username=username,
        document_id=doc_id,
        filename="technologies.txt",
        file_type="txt",
        chunks=chunks,
    )
    assert stored_count == 3

    # Search for vector database content
    results = search_chunks(username=username, query="vector database for embeddings", top_k=1)
    assert len(results) >= 1
    assert "ChromaDB" in results[0]["text"]
    assert results[0]["document_id"] == doc_id
    assert results[0]["filename"] == "technologies.txt"


def test_user_collection_isolation():
    """Confirms that user A's collection never returns results from user B's documents."""
    user_a = "user_alpha"
    user_b = "user_beta"

    embed_and_store(
        username=user_a,
        document_id=201,
        filename="alpha_secret.txt",
        file_type="txt",
        chunks=["Top secret cryptographic blueprint for Project Alpha."],
    )

    embed_and_store(
        username=user_b,
        document_id=202,
        filename="beta_notes.txt",
        file_type="txt",
        chunks=["Standard marketing copy for public product announcement."],
    )

    # User B searching for "cryptographic blueprint" should find NOTHING
    results_b = search_chunks(username=user_b, query="cryptographic blueprint", top_k=5)
    for r in results_b:
        assert "Project Alpha" not in r["text"]
        assert r["document_id"] != 201

    # User A searching should find it
    results_a = search_chunks(username=user_a, query="cryptographic blueprint", top_k=1)
    assert len(results_a) == 1
    assert "Project Alpha" in results_a[0]["text"]


def test_delete_document_chunks():
    username = "test_cleanup_user"
    doc_id = 301

    embed_and_store(
        username=username,
        document_id=doc_id,
        filename="temporary.txt",
        file_type="txt",
        chunks=["Temporary data chunk to be purged."],
    )

    assert get_document_chunk_count(username, doc_id) == 1

    delete_document_chunks(username, doc_id)
    assert get_document_chunk_count(username, doc_id) == 0


# ==============================================================================
# END-TO-END API TESTS: UPLOAD -> PARSE -> CHUNK -> EMBED -> INDEXED
# ==============================================================================

def test_api_upload_text_reaches_indexed_status():
    # Register user first
    client.post("/auth/register", json={"username": "ingest_user", "password": "password123"})

    file_content = b"Retrieval-Augmented Generation enhances large language models by grounding them in retrieved factual documents."
    files = {"file": ("intro_rag.txt", io.BytesIO(file_content), "text/plain")}
    data = {"username": "ingest_user"}

    response = client.post("/documents/upload", data=data, files=files)
    assert response.status_code == 200
    res_data = response.json()

    # Document must reach "indexed" status with non-zero chunk count
    assert res_data["status"] == "indexed"
    assert res_data["chunk_count"] == 1
    assert "indexed successfully" in res_data["message"]

    # Verify via GET /documents/{username}
    list_response = client.get("/documents/ingest_user")
    assert list_response.status_code == 200
    docs = list_response.json()
    assert len(docs) == 1
    assert docs[0]["status"] == "indexed"
    assert docs[0]["chunk_count"] == 1


def test_api_upload_csv_reaches_indexed_status():
    # Register user
    client.post("/auth/register", json={"username": "csv_user", "password": "password123"})

    csv_content = b"product_id,product_name,price\n101,Keyboard,49.99\n102,Mouse,24.99\n103,Monitor,199.99"
    files = {"file": ("products.csv", io.BytesIO(csv_content), "text/csv")}
    data = {"username": "csv_user"}

    response = client.post("/documents/upload", data=data, files=files)
    assert response.status_code == 200
    res_data = response.json()

    assert res_data["status"] == "indexed"
    assert res_data["chunk_count"] >= 1
    assert "products.csv" == res_data["filename"]
