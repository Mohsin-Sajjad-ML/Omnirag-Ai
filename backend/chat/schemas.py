"""
schemas.py - Pydantic request validation and response models for Chat domain.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    """
    Source citation grouped by document file, indicating format and matching chunk indexes.
    """
    filename: str
    file_type: str = "txt"
    chunk_references: List[int] = []
    document_id: Optional[int] = None


class ChatQueryRequest(BaseModel):
    """
    Schema for POST /chat/query request body.
    """
    query: str = Field(..., min_length=1, description="Question or query string")
    document_ids: Optional[List[int]] = Field(
        default=None,
        description="Optional list of document IDs to filter the retrieval scope"
    )


class ChatQueryResponse(BaseModel):
    """
    Schema for POST /chat/query response body.
    """
    answer: str
    is_fallback: bool = False
    citations: List[Citation] = []
    low_context: bool = False
    source: str = "document"
    response_language: str = "en"


class CreateSessionRequest(BaseModel):
    """
    Schema for POST /chat/sessions request body.
    """
    pass


class UpdateSessionRequest(BaseModel):
    """
    Schema for PATCH /chat/sessions/{session_id} body.
    """
    title: str = Field(..., min_length=1, max_length=60, description="New session title")


class PinSessionRequest(BaseModel):
    """
    Schema for PATCH /chat/sessions/{session_id}/pin body.
    """
    pinned: bool


class SessionResponse(BaseModel):
    """
    Schema for session creation response.
    """
    session_id: int
    id: int
    title: str
    pinned: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionItemResponse(BaseModel):
    """
    Schema for session list item in GET /chat/sessions.
    """
    id: int
    session_id: int
    title: str
    pinned: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageItemResponse(BaseModel):
    """
    Schema for message item returned in GET /chat/sessions/{session_id}/messages.
    """
    id: int
    session_id: int
    role: str
    content: str
    citations: Optional[List[Citation]] = None
    is_fallback: bool = False
    source: str = "rag"
    response_language: Optional[str] = "en"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeleteSessionRequest(BaseModel):
    """
    Schema for DELETE /chat/sessions/{session_id} body.
    """
    pass


class SessionMessageRequest(BaseModel):
    """
    Schema for POST /chat/sessions/{session_id}/message.
    """
    query: str = Field(..., min_length=1, description="User prompt or question")
    document_ids: Optional[List[int]] = Field(
        default=None,
        description="Optional list of document IDs to restrict retrieval scope"
    )
    rag_enabled: bool = Field(
        default=True,
        description="Enable RAG retrieval from indexed documents (defaults to true)"
    )
    web_search_enabled: bool = Field(
        default=False,
        description="Enable real-time web search via groq/compound (defaults to false)"
    )


class SessionMessageResponse(BaseModel):
    """
    Schema for POST /chat/sessions/{session_id}/message response.
    """
    answer: str
    is_fallback: bool = False
    citations: List[Citation] = []
    low_context: bool = False
    is_error: bool = False
    source: str = "rag"
    response_language: str = "en"


class TranscribeResponse(BaseModel):
    """
    Schema for POST /chat/transcribe response body.
    """
    transcript: str
    text: Optional[str] = None
    detected_final_language: str = "en"


class MessageResponse(BaseModel):
    """
    Standard message response model.
    """
    message: str


__all__ = [
    "Citation",
    "ChatQueryRequest",
    "ChatQueryResponse",
    "CreateSessionRequest",
    "UpdateSessionRequest",
    "PinSessionRequest",
    "SessionResponse",
    "SessionItemResponse",
    "MessageItemResponse",
    "DeleteSessionRequest",
    "SessionMessageRequest",
    "SessionMessageResponse",
    "TranscribeResponse",
    "MessageResponse",
]
