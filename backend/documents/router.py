"""
router.py - Thin HTTP route handlers for Documents domain.
"""

from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session
from langfuse import observe

from backend.database.connection import get_db
from backend.auth.dependencies import ClerkUser
from backend.documents.schemas import (
    DocumentMetadataResponse,
    DocumentUploadResponse,
    MessageResponse,
)
from backend.documents import service

router = APIRouter(prefix="/documents", tags=["Documents"], dependencies=[ClerkUser])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and parse a document (PDF, DOCX, TXT, CSV)",
)
@observe(name="document-ingest")
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload (max 50MB)"),
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Uploads and processes a document for the authenticated user.
    """
    return await service.upload_document(
        file=file,
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


@router.get(
    "/{document_id}/chunk/{chunk_index}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve a document chunk for citation preview",
)
@observe()
def get_document_chunk(
    document_id: int,
    chunk_index: int,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
):
    """
    Return one read-only source chunk after verifying its document owner.
    """
    return service.get_document_chunk(
        document_id=document_id,
        chunk_index=chunk_index,
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


@router.get(
    "",
    response_model=List[DocumentMetadataResponse],
    status_code=status.HTTP_200_OK,
    summary="List all uploaded documents metadata for a user",
)
@router.get(
    "/",
    response_model=List[DocumentMetadataResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/{user_identifier}",
    response_model=List[DocumentMetadataResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@observe()
def get_user_documents(
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> List[DocumentMetadataResponse]:
    """
    Retrieves all document metadata for the authenticated user.
    """
    return service.get_user_documents(
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a document by ID with ownership verification",
)
@observe()
def delete_document(
    document_id: int,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Deletes an uploaded document and removes associated vector embeddings.
    """
    return service.delete_document(
        document_id=document_id,
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


__all__ = [
    "router",
    "upload_document",
    "get_document_chunk",
    "get_user_documents",
    "delete_document",
]
