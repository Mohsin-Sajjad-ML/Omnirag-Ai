"""
schemas.py - Pydantic request validation and response models for Documents domain.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class DocumentMetadataResponse(BaseModel):
    """
    Response model representing document metadata stored in SQLite.
    Excludes the full extracted text to keep API responses lightweight.
    """
    id: int
    original_filename: str
    file_type: str
    status: str
    chunk_count: Optional[int] = 0
    summary: Optional[str] = None
    upload_timestamp: datetime
    error_message: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    """
    Response model returned after an uploaded file has been processed.
    """
    id: int
    filename: str
    status: str
    chunk_count: int
    summary: Optional[str] = None
    message: str
    error_message: Optional[str] = None


class MessageResponse(BaseModel):
    """
    Standard message response model.
    """
    message: str


class DocumentChunkResponse(BaseModel):
    """
    Response model for single document chunk preview.
    """
    document_id: int
    filename: str
    chunk_index: int
    chunk_text: str


__all__ = [
    "DocumentMetadataResponse",
    "DocumentUploadResponse",
    "MessageResponse",
    "DocumentChunkResponse",
]
