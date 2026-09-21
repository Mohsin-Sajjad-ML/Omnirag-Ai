"""
service.py - Core business logic and orchestration for Documents domain.
"""
from langfuse import observe


import os
import tempfile
import logging
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.models import Document
from backend.documents.schemas import (
    DocumentUploadResponse,
    DocumentMetadataResponse,
    MessageResponse,
    DocumentChunkResponse,
)
from backend.documents.parsing_service import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    extract_document_text,
)
from backend.documents.rag_service import (
    chunk_text,
    chunk_csv_text,
    embed_and_store,
    delete_document_chunks,
    get_user_collection,
)
from backend.chat.summary_service import generate_summary

logger = logging.getLogger(__name__)


@observe(name="chunking")
def _chunk_document(parsed_text: str, file_type: str) -> list:
    """Splits parsed document text into semantic chunks."""
    if file_type == "csv":
        return chunk_csv_text(parsed_text, rows_per_chunk=20)
    return chunk_text(parsed_text, chunk_size=500, overlap=50)


@observe(name="index-write")
def _index_write(
    clerk_user_id: str,
    doc_id: int,
    filename: str,
    file_type: str,
    chunks: list,
) -> int:
    """Embeds and persists document chunks in ChromaDB."""
    if not chunks:
        return 0
    return embed_and_store(
        clerk_user_id=clerk_user_id,
        document_id=doc_id,
        filename=filename,
        file_type=file_type,
        chunks=chunks,
    )


async def upload_document(
    file: UploadFile,
    clerk_user_id: str,
    db: Session,
) -> DocumentUploadResponse:
    """
    Uploads, parses, indexes, and summarizes a document for the authenticated user.
    """
    original_filename = file.filename or "unknown"
    extension = original_filename.split(".")[-1].lower() if "." in original_filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Please upload PDF, DOCX, TXT, or CSV."
        )

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}")
    temp_file_path = temp_file.name
    total_size = 0

    try:
        try:
            while chunk := await file.read(64 * 1024):  # 64KB chunks
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File size exceeds the 50MB limit."
                    )
                temp_file.write(chunk)
        finally:
            temp_file.close()

        parsed_text: Optional[str] = None
        doc_status = "parsed"
        error_msg: Optional[str] = None

        try:
            parsed_text = extract_document_text(temp_file_path, extension)
        except Exception as exc:
            logger.warning("Document parsing failed for '%s': %s", original_filename, exc)
            doc_status = "failed"
            error_msg = str(exc)

        new_doc = Document(
            clerk_user_id=clerk_user_id,
            original_filename=original_filename,
            file_type=extension,
            extracted_text=parsed_text,
            status=doc_status,
            chunk_count=0,
            error_message=error_msg,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        if doc_status == "parsed" and parsed_text:
            try:
                chunks = _chunk_document(parsed_text, new_doc.file_type)
                stored_chunks = _index_write(
                    clerk_user_id=clerk_user_id,
                    doc_id=new_doc.id,
                    filename=new_doc.original_filename,
                    file_type=new_doc.file_type,
                    chunks=chunks,
                )

                if stored_chunks == 0:
                    new_doc.status = "failed"
                    new_doc.chunk_count = 0
                    new_doc.error_message = "Document parsed but produced zero text chunks."
                    db.commit()
                    db.refresh(new_doc)

                    return DocumentUploadResponse(
                        id=new_doc.id,
                        filename=new_doc.original_filename,
                        status="failed",
                        chunk_count=0,
                        message="Document parsed but produced zero indexable text chunks.",
                        error_message="Document parsed but produced zero text chunks.",
                    )

                new_doc.status = "indexed"
                new_doc.chunk_count = stored_chunks
                new_doc.error_message = None
                db.commit()
                db.refresh(new_doc)

                try:
                    doc_summary = generate_summary(parsed_text, extension)
                    if doc_summary:
                        new_doc.summary = doc_summary
                        db.commit()
                        db.refresh(new_doc)
                except Exception as sum_err:
                    logger.error("Auto-summary generation failed for document %d: %s", new_doc.id, sum_err)

                return DocumentUploadResponse(
                    id=new_doc.id,
                    filename=new_doc.original_filename,
                    status="indexed",
                    chunk_count=new_doc.chunk_count,
                    summary=new_doc.summary,
                    message=f"Document uploaded and indexed successfully ({new_doc.chunk_count} chunks)",
                    error_message=None,
                )

            except Exception as index_exc:
                logger.error("Embedding and vector storage failed for doc %d: %s", new_doc.id, index_exc)
                new_doc.status = "failed"
                new_doc.chunk_count = 0
                new_doc.error_message = f"Vector indexing failed: {index_exc}"
                db.commit()
                db.refresh(new_doc)

                return DocumentUploadResponse(
                    id=new_doc.id,
                    filename=new_doc.original_filename,
                    status="failed",
                    chunk_count=0,
                    message=f"Document parsing succeeded, but vector indexing failed: {index_exc}",
                    error_message=f"Vector indexing failed: {index_exc}",
                )
        else:
            return DocumentUploadResponse(
                id=new_doc.id,
                filename=new_doc.original_filename,
                status="failed",
                chunk_count=0,
                message=f"Document parsing failed: {error_msg}",
                error_message=error_msg,
            )

    finally:
        if os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError as cleanup_err:
                logger.warning("Failed to clean up temp file '%s': %s", temp_file_path, cleanup_err)


def get_document_chunk(
    document_id: int,
    chunk_index: int,
    clerk_user_id: str,
    db: Session,
) -> dict:
    """
    Return one read-only source chunk after verifying its document owner.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if doc.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this document chunk.",
        )

    try:
        collection = get_user_collection(clerk_user_id)
        stored = collection.get(where={"document_id": int(document_id)}, include=["documents", "metadatas"])
        documents = stored.get("documents", [])
        metadatas = stored.get("metadatas", [])
        for index, metadata in enumerate(metadatas):
            if metadata and int(metadata.get("chunk_index", -1)) == chunk_index:
                return {
                    "document_id": document_id,
                    "filename": metadata.get("filename", doc.original_filename),
                    "chunk_index": chunk_index,
                    "chunk_text": documents[index] if index < len(documents) else "",
                }
    except Exception as err:
        logger.exception("Failed to retrieve chunk %d for document %d: %s", chunk_index, document_id, err)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document chunk not found.")


def get_user_documents(
    clerk_user_id: str,
    db: Session,
) -> List[Document]:
    """
    Retrieves all document metadata (excluding full text content) for a given user.
    """
    return (
        db.query(Document)
        .filter(Document.clerk_user_id == clerk_user_id)
        .order_by(Document.upload_timestamp.desc())
        .all()
    )


def delete_document(
    document_id: int,
    clerk_user_id: str,
    db: Session,
) -> MessageResponse:
    """
    Deletes an uploaded document and purges its vector chunks.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    if doc.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this document."
        )

    delete_document_chunks(clerk_user_id=clerk_user_id, document_id=document_id)

    db.delete(doc)
    db.commit()

    return MessageResponse(message="Document deleted successfully")


__all__ = [
    "upload_document",
    "get_document_chunk",
    "get_user_documents",
    "delete_document",
]
