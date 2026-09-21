"""
test_documents.py - Automated tests for document upload, parsing, listing, and deletion.

Tests covered:
1. TXT file upload and text extraction.
2. CSV file upload and row-by-row structure conversion.
3. DOCX file upload and paragraph extraction.
4. PDF file upload and page text extraction.
5. Nonexistent username rejection (404 Not Found).
6. Unsupported file format rejection (400 Bad Request).
7. Corrupted/unparseable file creates record with status "failed" and returns 200 with error info.
8. Listing document metadata for a user (excludes extracted_text).
9. Listing documents for nonexistent user returns 404.
10. Document deletion by owner succeeds.
11. Document deletion by non-owner rejected (403 Forbidden).
12. Document deletion for nonexistent document returns 404.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import docx

from backend.main import app
from backend.database.connection import Base, get_db
from backend.database.models import User, Document

# In-memory test database with StaticPool
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


def create_test_user(username: str = "testuser"):
    """Helper to create a test user directly in DB."""
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


def test_document_chunk_preview_enforces_ownership(monkeypatch):
    """Citation previews return the exact metadata-selected chunk only to its owner."""
    create_test_user("chunk_owner")
    db = TestingSessionLocal()
    try:
        document = Document(
            username="chunk_owner",
            original_filename="source.txt",
            file_type="txt",
            extracted_text="source text",
            status="indexed",
            chunk_count=2,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        document_id = document.id
    finally:
        db.close()

    class FakeCollection:
        def get(self, **kwargs):
            assert kwargs["where"] == {"document_id": document_id}
            return {
                "documents": ["first chunk", "exact source text"],
                "metadatas": [
                    {"document_id": document_id, "filename": "source.txt", "chunk_index": 0},
                    {"document_id": document_id, "filename": "source.txt", "chunk_index": 1},
                ],
            }

    monkeypatch.setattr("backend.documents.service.get_user_collection", lambda username: FakeCollection())

    response = client.get(f"/documents/{document_id}/chunk/1", params={"username": "chunk_owner"})
    assert response.status_code == 200
    assert response.json() == {
        "document_id": document_id,
        "filename": "source.txt",
        "chunk_index": 1,
        "chunk_text": "exact source text",
    }

    forbidden = client.get(f"/documents/{document_id}/chunk/1", params={"username": "someone_else"})
    assert forbidden.status_code == 403


def generate_test_docx_bytes() -> bytes:
    """Generates a valid DOCX file in memory."""
    doc = docx.Document()
    doc.add_heading("Docx Test Heading", 0)
    doc.add_paragraph("This is a test paragraph inside a docx document.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


# Minimal valid PDF string with text "Hello PDF World"
MINIMAL_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 300 144]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 44>>stream\n"
    b"BT /F1 18 Tf 50 100 Td (Hello PDF World) Tj ET\n"
    b"endstream\n"
    b"endobj\n"
    b"xref\n"
    b"0 6\n"
    b"0000000000 65535 f \n"
    b"0000000010 00000 n \n"
    b"0000000060 00000 n \n"
    b"0000000117 00000 n \n"
    b"0000000224 00000 n \n"
    b"0000000293 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n"
    b"386\n"
    b"%%EOF\n"
)


def test_upload_txt_file_success():
    create_test_user("alice")
    file_content = b"OmniRAG is a powerful AI chatbot platform with biometric security."
    
    response = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["indexed", "parsed"]
    assert data["filename"] == "notes.txt"
    assert "successfully" in data["message"]
    assert data.get("chunk_count", 0) >= 1

    # Verify content in DB
    db = TestingSessionLocal()
    doc = db.query(Document).filter(Document.id == data["id"]).first()
    db.close()
    assert doc is not None
    assert doc.username == "alice"
    assert "OmniRAG is a powerful" in doc.extracted_text


def test_upload_csv_file_success():
    create_test_user("alice")
    csv_content = b"name,role,department\nAlice,Engineer,AI\nBob,Designer,Product"

    response = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("team.csv", io.BytesIO(csv_content), "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["indexed", "parsed"]
    assert data.get("chunk_count", 0) >= 1

    # Verify structured row lines in DB
    db = TestingSessionLocal()
    doc = db.query(Document).filter(Document.id == data["id"]).first()
    db.close()
    assert "[Table Columns (3)]: name, role, department" in doc.extracted_text
    assert "Row 1: name=Alice, role=Engineer, department=AI" in doc.extracted_text
    assert "Row 2: name=Bob, role=Designer, department=Product" in doc.extracted_text


def test_upload_docx_file_success():
    create_test_user("alice")
    docx_bytes = generate_test_docx_bytes()

    response = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("report.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["indexed", "parsed"]
    assert data.get("chunk_count", 0) >= 1

    db = TestingSessionLocal()
    doc = db.query(Document).filter(Document.id == data["id"]).first()
    db.close()
    assert "This is a test paragraph inside a docx document." in doc.extracted_text


def test_upload_pdf_file_success():
    create_test_user("alice")

    response = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("sample.pdf", io.BytesIO(MINIMAL_PDF_BYTES), "application/pdf")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["indexed", "parsed"]
    assert data.get("chunk_count", 0) >= 1

    db = TestingSessionLocal()
    doc = db.query(Document).filter(Document.id == data["id"]).first()
    db.close()
    assert "Hello PDF World" in doc.extracted_text


def test_upload_nonexistent_user():
    response = client.post(
        "/documents/upload",
        data={"username": "nonexistent_user"},
        files={"file": ("test.txt", io.BytesIO(b"Sample"), "text/plain")}
    )
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_upload_unsupported_file_type():
    create_test_user("alice")
    response = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("image.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")}
    )
    assert response.status_code == 400
    assert "Unsupported file type. Please upload PDF, DOCX, TXT, or CSV." in response.json()["detail"]


def test_upload_corrupt_file_handling():
    create_test_user("alice")
    corrupt_docx_bytes = b"Not a real docx archive file at all"

    response = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("corrupt.docx", io.BytesIO(corrupt_docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )

    # Must return 200 with status "failed" and error_message populated rather than crash
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_message"] is not None

    db = TestingSessionLocal()
    doc = db.query(Document).filter(Document.id == data["id"]).first()
    db.close()
    assert doc.status == "failed"
    assert doc.extracted_text is None


def test_get_user_documents():
    create_test_user("alice")
    client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("doc1.txt", io.BytesIO(b"Text 1"), "text/plain")}
    )
    client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("doc2.txt", io.BytesIO(b"Text 2"), "text/plain")}
    )

    response = client.get("/documents/alice")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 2
    for d in docs:
        assert "id" in d
        assert "original_filename" in d
        assert "file_type" in d
        assert "upload_timestamp" in d
        assert "status" in d
        assert "chunk_count" in d
        assert "extracted_text" not in d


def test_get_user_documents_nonexistent_user():
    response = client.get("/documents/nobody")
    assert response.status_code == 404


def test_delete_document_success():
    create_test_user("alice")
    upload_res = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("doc1.txt", io.BytesIO(b"Text 1"), "text/plain")}
    )
    doc_id = upload_res.json()["id"]

    delete_res = client.delete(f"/documents/{doc_id}?username=alice")
    assert delete_res.status_code == 200
    assert delete_res.json()["message"] == "Document deleted successfully"

    db = TestingSessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    db.close()
    assert doc is None


def test_delete_document_unauthorized_user():
    create_test_user("alice")
    create_test_user("bob")
    upload_res = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("doc1.txt", io.BytesIO(b"Text 1"), "text/plain")}
    )
    doc_id = upload_res.json()["id"]

    # Bob tries to delete Alice's document
    delete_res = client.delete(f"/documents/{doc_id}?username=bob")
    assert delete_res.status_code == 403
    assert "permission" in delete_res.json()["detail"]


def test_delete_document_not_found():
    response = client.delete("/documents/99999?username=alice")
    assert response.status_code == 404


def test_upload_file_between_20mb_and_50mb():
    create_test_user("alice")
    # File content 25MB (within new 50MB limit, formerly rejected under 20MB limit)
    content_25mb = (b"Document section header with text content. " + b"A" * 100000 + b"\n") * 250  # ~25MB
    response = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("allowed_25mb.txt", io.BytesIO(content_25mb), "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("indexed", "parsed")
    assert data["filename"] == "allowed_25mb.txt"
    assert data["chunk_count"] > 0


def test_upload_file_exceeding_50mb():
    create_test_user("alice")
    # File content exceeding 50MB limit (50MB + 1024 bytes)
    large_content = b"0" * (50 * 1024 * 1024 + 1024)
    response = client.post(
        "/documents/upload",
        data={"username": "alice"},
        files={"file": ("large.txt", io.BytesIO(large_content), "text/plain")}
    )
    assert response.status_code == 400
    assert "50MB" in response.json()["detail"]
