"""
router.py - Thin HTTP route handlers for Chat domain.
"""

from typing import List
from fastapi import APIRouter, Query, Depends, File, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langfuse import observe

from backend.database.connection import get_db
from backend.auth.dependencies import ClerkUser
from backend.chat.schemas import (
    ChatQueryRequest,
    ChatQueryResponse,
    CreateSessionRequest,
    SessionResponse,
    SessionResponse,
    SessionItemResponse,
    MessageItemResponse,
    UpdateSessionRequest,
    PinSessionRequest,
    SessionMessageRequest,
    SessionMessageResponse,
    MessageResponse,
    TranscribeResponse,
)
from backend.chat import service

router = APIRouter(prefix="/chat", tags=["Chat"], dependencies=[ClerkUser])


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    summary="Transcribe an uploaded audio recording",
    description="Converts a browser-recorded audio file to text with Groq Whisper and normalizes language.",
)
@observe()
async def transcribe_audio(audio: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribe audio only; returns final transcript and detected_final_language."""
    return await service.transcribe_audio(audio=audio)


@router.post(
    "/query",
    response_model=ChatQueryResponse,
    summary="Query Knowledge Base and Generate Grounded Answer",
    description=(
        "Retrieves semantically relevant document chunks from ChromaDB for the user's "
        "query, calls the Groq LLM with strict grounding instructions, and formats "
        "the response with grouped document citations, fallback detection, and a "
        "context-completeness confidence indicator."
    ),
)
@observe()
def query_knowledge_base(
    payload: ChatQueryRequest,
    clerk_user: dict = ClerkUser,
) -> ChatQueryResponse:
    """
    RAG query endpoint.
    """
    return service.query_knowledge_base(
        payload=payload,
        clerk_user_id=clerk_user["user_id"],
    )


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
    description="Creates a new empty chat session for the specified user and returns its session details.",
)
@observe()
def create_chat_session(
    payload: CreateSessionRequest,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> SessionResponse:
    """
    Creates a new conversation session record in SQLite.
    """
    return service.create_chat_session(
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


@router.get(
    "/sessions",
    response_model=List[SessionItemResponse],
    summary="List all chat sessions for the current user",
    description="Returns a list of chat sessions belonging to the authenticated user, sorted most recent first.",
)
@router.get(
    "/sessions/{user_identifier}",
    response_model=List[SessionItemResponse],
    include_in_schema=False,
)
@observe()
def list_user_sessions(
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> List[SessionItemResponse]:
    """
    Retrieves all chat sessions for the authenticated user, ordered by creation date descending.
    """
    return service.list_user_sessions(
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[MessageItemResponse],
    summary="Get all messages in a session",
    description="Returns all user and assistant messages for a session in chronological order.",
)
@observe()
def get_session_messages(
    session_id: int,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> List[MessageItemResponse]:
    """
    Fetches the full message transcript for a session.
    """
    return service.get_session_messages(
        session_id=session_id,
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


@router.patch(
    "/sessions/{session_id}",
    response_model=SessionItemResponse,
    summary="Update chat session",
    description="Updates the title of a chat session.",
)
@observe()
def update_chat_session(
    session_id: int,
    payload: UpdateSessionRequest,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> SessionItemResponse:
    """
    Updates the session title.
    """
    return service.update_chat_session(
        session_id=session_id,
        clerk_user_id=clerk_user["user_id"],
        title=payload.title,
        db=db,
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
    summary="Delete chat session and its messages",
    description="Deletes a chat session and cascades deletion to all contained messages after verifying ownership via Clerk authentication.",
)
@observe()
def delete_chat_session(
    session_id: int,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Deletes the session and all associated messages.
    """
    return service.delete_chat_session(
        session_id=session_id,
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


@router.post(
    "/sessions/{session_id}/message",
    response_model=SessionMessageResponse,
    summary="Send a message in a session and generate persistent answer",
    description=(
        "Persists user message, performs RAG retrieval and LLM generation, "
        "persists assistant response with citations and fallback flag, and returns the response."
    ),
)
@observe(name="chat-request")
def post_session_message(
    session_id: int,
    payload: SessionMessageRequest,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> SessionMessageResponse:
    """
    Sends a query into a session and generates an assistant response.
    """
    try:
        from backend.config import get_langfuse_client
        get_langfuse_client().update_current_span(
            input={
                "session_id": session_id,
                "query": payload.query,
                "rag_enabled": payload.rag_enabled,
                "web_search_enabled": payload.web_search_enabled,
                "document_ids": payload.document_ids,
            }
        )
    except Exception:
        pass

    return service.post_session_message(
        session_id=session_id,
        payload=payload,
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )




@router.patch(
    "/sessions/{session_id}/pin",
    response_model=SessionItemResponse,
    summary="Pin chat session",
)
@observe()
def pin_chat_session(
    session_id: int,
    payload: PinSessionRequest,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> SessionItemResponse:
    return service.pin_chat_session(
        session_id=session_id,
        clerk_user_id=clerk_user["user_id"],
        pinned=payload.pinned,
        db=db,
    )


@router.get(
    "/sessions/{session_id}/export",
    summary="Export chat session",
)
@observe()
def export_chat_session(
    session_id: int,
    format: str = Query("txt", pattern="^(txt|pdf)$"),
    mode: str = Query("full", pattern="^(full|context|summary)$"),
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
):
    return service.export_chat_session(
        session_id=session_id,
        clerk_user_id=clerk_user["user_id"],
        format=format,
        mode=mode,
        db=db,
    )


@router.post(
    "/sessions/{session_id}/duplicate",
    response_model=SessionResponse,
    summary="Duplicate chat session",
)
@observe()
def duplicate_chat_session(
    session_id: int,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> SessionResponse:
    return service.duplicate_chat_session(
        session_id=session_id,
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


@router.post(
    "/sessions/{session_id}/messages/{message_id}/edit",
    response_model=SessionMessageResponse,
    summary="Edit user message and regenerate",
)
@observe()
def edit_message_and_regenerate(
    session_id: int,
    message_id: int,
    payload: SessionMessageRequest,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> SessionMessageResponse:
    return service.edit_message_and_regenerate(
        session_id=session_id,
        message_id=message_id,
        query=payload.query,
        clerk_user_id=clerk_user["user_id"],
        db=db,
        document_ids=payload.document_ids,
        rag_enabled=payload.rag_enabled,
        web_search_enabled=payload.web_search_enabled,
    )


@router.post(
    "/sessions/{session_id}/regenerate",
    response_model=SessionMessageResponse,
    summary="Regenerate last assistant message",
)
@observe()
def regenerate_assistant_message(
    session_id: int,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> SessionMessageResponse:
    return service.regenerate_assistant_message(
        session_id=session_id,
        clerk_user_id=clerk_user["user_id"],
        db=db,
    )


__all__ = [
    "router",
    "transcribe_audio",
    "query_knowledge_base",
    "create_chat_session",
    "list_user_sessions",
    "get_session_messages",
    "update_chat_session",
    "delete_chat_session",
    "post_session_message",
    "pin_chat_session",
    "export_chat_session",
    "duplicate_chat_session",
    "edit_message_and_regenerate",
    "regenerate_assistant_message",
]
