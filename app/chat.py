"""
chat.py - Chat, Session History & RAG Query endpoint router for OmniRAG AI.

This module provides:
- POST /chat/query: Legacy RAG query endpoint (Prompt 7).
- POST /chat/sessions: Creates a new empty chat session for a user.
- GET /chat/sessions/{username}: Lists all chat sessions for a user, most recent first.
- GET /chat/sessions/{session_id}/messages: Returns all messages in a session in chronological order.
- DELETE /chat/sessions/{session_id}: Deletes a session and its messages with ownership verification.
- POST /chat/sessions/{session_id}/message: Persists user message, runs RAG retrieval + LLM synthesis,
  persists assistant response with citations and fallback status, and returns the formatted reply.
"""

import json
import logging
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Document, ChatSession, ChatMessage
from app.schemas import (
    ChatQueryRequest,
    ChatQueryResponse,
    Citation,
    CreateSessionRequest,
    SessionResponse,
    SessionItemResponse,
    MessageItemResponse,
    DeleteSessionRequest,
    SessionMessageRequest,
    SessionMessageResponse,
    MessageResponse,
)
from app.rag import search_chunks
from app.llm import (
    ABOUT_BOT_MESSAGE,
    NO_DOCUMENTS_MESSAGE,
    classify_intent,
    generate_answer,
    format_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


def _csv_context_for_query(
    documents: List[Document],
    query: str,
) -> List[dict]:
    """Add compact, exact CSV facts for counts and name-based lookups."""
    query_lower = query.lower()
    count_requested = bool(re.search(
        r"\b(total|count|how many|number|kitny|kitni|employees?|staff|workers?)\b",
        query_lower,
    ))
    query_terms = set(re.findall(r"[a-z][a-z'-]{2,}", query_lower))
    has_id_phrase = bool(re.search(r"(?:emp(?:loyee)?\s*id|ids?)\b", query_lower))
    requested_ids = re.findall(r"\b\d+\b", query_lower) if has_id_phrase else []
    ignored_terms = {
        "mujhy", "mujhe", "btao", "batao", "total", "employees", "employee",
        "kitny", "kitni", "hain", "and", "the", "ka", "ki", "ke", "konsa",
        "knsa", "department", "what", "which", "how", "many", "is", "are",
        "emp", "id", "gender", "zone", "job", "function", "nya", "ka",
    }
    lookup_terms = query_terms - ignored_terms - set(requested_ids)
    context = []

    for document in documents:
        if document.file_type != "csv" or not document.extracted_text:
            continue

        lines = [line.strip() for line in document.extracted_text.splitlines() if line.strip()]
        if not lines:
            continue

        selected_lines = []
        data_lines = lines[1:]
        if requested_ids:
            selected_lines.extend(
                line for line in data_lines
                if any(re.search(rf"\bEmpID\s*=\s*{re.escape(emp_id)}\b", line, re.IGNORECASE)
                       for emp_id in requested_ids)
            )
        if lookup_terms:
            selected_lines.extend(
                line for line in data_lines
                if any(term in line.lower() for term in lookup_terms)
                and line not in selected_lines
            )
        selected_lines = selected_lines[:8]

        facts = [f"CSV FACT: {len(lines) - 1} data rows in {document.original_filename}."] if count_requested else []
        if selected_lines:
            facts.append(lines[0])
            facts.extend(selected_lines)
        if facts:
            context.append({
                "id": f"csv_exact_{document.id}",
                "text": "\n".join(facts),
                "document_id": document.id,
                "filename": document.original_filename,
                "file_type": "csv",
                "chunk_index": 0,
                "distance": 0.0,
            })

    return context


def _csv_direct_answer(documents: List[Document], query: str) -> Optional[str]:
    """Answer exact CSV record lookups from the uploaded file schema."""
    query_lower = query.lower()
    if not re.search(r"\b(?:id|ids|identifier|number|code)\b", query_lower):
        return None

    requested_ids = re.findall(r"\b\d+\b", query_lower)
    field_pattern = (
        r"(?:^|, )([A-Za-z][A-Za-z ]*)=(.*?)(?=, [A-Za-z][A-Za-z ]*=|$)"
    )
    query_words = set(re.findall(r"[a-z][a-z0-9]{3,}", query_lower))
    ignored_words = {
        "what", "which", "where", "when", "tell", "show", "give", "about",
        "from", "that", "this", "these", "those", "have", "with", "and",
        "the", "for", "are", "is", "ka", "ki", "ke", "kya", "hain", "mujhe",
        "btao", "batao", "please", "number", "code", "identifier",
    }
    query_words -= ignored_words
    answers = []
    for document in documents:
        lines = (document.extracted_text or "").splitlines()
        if not lines:
            continue

        header_match = re.search(r"\]:\s*(.*)$", lines[0])
        headers = [part.strip() for part in (header_match.group(1) if header_match else lines[0]).split(",")]
        normalized_headers = {
            re.sub(r"[^a-z0-9]", "", header.lower()): header
            for header in headers
        }
        id_fields = [
            normalized for normalized in normalized_headers
            if "id" in normalized or "number" in normalized
        ]
        if not id_fields:
            id_fields = [normalized for normalized in normalized_headers if "code" in normalized]

        for line in lines[1:]:
            row_data = re.sub(r"^Row\s+\d+:\s*", "", line, flags=re.IGNORECASE)
            fields = {
                re.sub(r"[^a-z0-9]", "", name.lower()): value.strip()
                for name, value in re.findall(field_pattern, row_data)
            }

            if not any(
                fields.get(id_field, "").strip() in requested_ids
                for id_field in id_fields
            ):
                continue

            requested_fields = [
                normalized for normalized in normalized_headers
                if normalized in fields
                and normalized not in id_fields
                and any(word in normalized for word in query_words)
            ]
            if not requested_fields:
                return None

            record_id = next(
                (fields.get(id_field) for id_field in id_fields if fields.get(id_field, "").strip() in requested_ids),
                "unknown",
            )
            values = [
                f"{normalized_headers[field]}: {fields.get(field, 'Not available')}"
                for field in requested_fields
            ]
            answers.append(f"**Record ID {record_id}:** " + "; ".join(values))

    return "\n\n".join(answers) if answers else None


@router.post(
    "/query",
    response_model=ChatQueryResponse,
    summary="Query Knowledge Base and Generate Grounded Answer",
    description=(
        "Retrieves semantically relevant document chunks from ChromaDB for the user's "
        "query, calls the Groq LLM with strict grounding instructions, and formats "
        "the response with grouped document citations, fallback detection, and a "
        "context-completeness confidence indicator."
    )
)
def query_knowledge_base(payload: ChatQueryRequest) -> ChatQueryResponse:
    """
    RAG query endpoint:
    1. Retrieves top-k semantically matching chunks from the user's isolated ChromaDB collection.
    2. Short-circuits early if no matching chunks exist (preventing wasteful LLM calls)
       and returns the friendly fallback response immediately.
    3. Calls Groq LLM (e.g. Llama 3.3 or production fallback) with the strictly grounded prompt.
    4. Passes the raw response to format_response() to group citations by document,
       convert any negative markers into a helpful fallback, and calculate the low_context flag.
    """
    # 1. Retrieve top-k relevant chunks from the user's isolated vector store
    retrieved_chunks = search_chunks(
        username=payload.username,
        query=payload.query,
        document_ids=payload.document_ids,
        top_k=3,
    )

    # 2. Early short-circuit if no chunks found (user has no indexed documents or 0 matches)
    if not retrieved_chunks:
        logger.info(
            "No chunks found for user '%s' query '%s'. Short-circuiting without LLM call.",
            payload.username,
            payload.query,
        )
        formatted = format_response(
            raw_answer="NOT_FOUND_IN_DOCUMENT",
            chunks_used=[],
        )
        return ChatQueryResponse(**formatted)

    # 3. Call LLM to synthesize answer strictly grounded in retrieved chunks
    try:
        raw_answer = generate_answer(query=payload.query, retrieved_chunks=retrieved_chunks)
    except RuntimeError as err:
        logger.error("LLM generation error: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err),
        )
    except Exception as err:
        logger.error("Unexpected error during LLM generation: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while generating answer: {err}",
        )

    # 4. Format user-facing response with grouped citations and fallback handling
    formatted = format_response(raw_answer=raw_answer, chunks_used=retrieved_chunks)
    return ChatQueryResponse(**formatted)


# ==============================================================================
# SESSION HISTORY & PERSISTENT MESSAGING ENDPOINTS (PROMPT 9)
# ==============================================================================

@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
    description="Creates a new empty chat session for the specified user and returns its session details."
)
def create_chat_session(
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
) -> SessionResponse:
    """
    Creates a new conversation session record in SQLite.
    Initializes with default title 'New Chat'.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{payload.username}' does not exist."
        )

    session = ChatSession(
        username=payload.username,
        title="New Chat",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionResponse(
        session_id=session.id,
        id=session.id,
        title=session.title,
        created_at=session.created_at,
    )


@router.get(
    "/sessions/{username}",
    response_model=List[SessionItemResponse],
    summary="List all chat sessions for a user",
    description="Returns a list of chat sessions belonging to the user, sorted most recent first."
)
def list_user_sessions(
    username: str,
    db: Session = Depends(get_db),
) -> List[SessionItemResponse]:
    """
    Retrieves all chat sessions for the specified user, ordered by creation date descending.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' does not exist."
        )

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.username == username)
        .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
        .all()
    )

    return [
        SessionItemResponse(
            id=s.id,
            session_id=s.id,
            title=s.title,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[MessageItemResponse],
    summary="Get all messages in a session",
    description="Returns all user and assistant messages for a session in chronological order."
)
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
) -> List[MessageItemResponse]:
    """
    Fetches the full message transcript for a session.
    Parses JSON citations stored on assistant messages back into structured Citation objects.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )

    results = []
    for msg in messages:
        citations = None
        if msg.citations:
            try:
                raw_citations = json.loads(msg.citations)
                citations = [Citation(**c) for c in raw_citations]
            except Exception as parse_err:
                logger.warning("Could not parse citations for message %s: %s", msg.id, parse_err)
                citations = []
        results.append(
            MessageItemResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                citations=citations,
                is_fallback=msg.is_fallback,
                created_at=msg.created_at,
            )
        )
    return results


@router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
    summary="Delete chat session and its messages",
    description="Deletes a chat session and cascades deletion to all contained messages upon confirming username ownership."
)
def delete_chat_session(
    session_id: int,
    payload: Optional[DeleteSessionRequest] = None,
    username: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Deletes the session and all associated messages. Verifies that the requesting user owns the session.
    Accepts username in either JSON body or query parameter for client flexibility.
    """
    req_username = (payload.username if payload else None) or username
    if not req_username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username is required to confirm session ownership."
        )

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    if session.username != req_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this session."
        )

    db.delete(session)
    db.commit()

    return MessageResponse(message="Session and its messages deleted successfully")


@router.post(
    "/sessions/{session_id}/message",
    response_model=SessionMessageResponse,
    summary="Send a message in a session and generate persistent answer",
    description=(
        "Persists user message, performs RAG retrieval and LLM generation, "
        "persists assistant response with citations and fallback flag, and returns the response."
    )
)
def post_session_message(
    session_id: int,
    payload: SessionMessageRequest,
    db: Session = Depends(get_db),
) -> SessionMessageResponse:
    """
    Sends a query into a session:
    1. Verifies session existence and user ownership.
    2. Auto-generates a short title (~40 chars) from the query if this is the session's first message.
    3. Saves the user's message in 'chat_messages'.
    4. Executes the existing RAG retrieval + LLM synthesis pipeline.
    5. Saves the assistant's response in 'chat_messages' with citations and is_fallback.
    6. Returns { answer, is_fallback, citations, low_context }.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    if session.username != payload.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to post in this session."
        )

    # If this is the session's first message, auto-generate a short title from query text
    existing_count = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
    if existing_count == 0 or session.title == "New Chat":
        clean_text = payload.query.strip().split("\n")[0].strip()
        if len(clean_text) > 40:
            truncated = clean_text[:37].rsplit(" ", 1)[0] if " " in clean_text[:37] else clean_text[:37]
            session.title = f"{truncated}..."
        else:
            session.title = clean_text if clean_text else "New Chat"
        db.add(session)

    # 1. Save user's message to chat_messages first
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=payload.query,
        citations=None,
        is_fallback=False,
    )
    db.add(user_msg)
    db.commit()

    # 2. Only clearly social or capability messages bypass retrieval. Every
    # other message checks the actual documents instead of guessing from wording.
    intent = classify_intent(payload.query)
    indexed_document_count = db.query(Document).filter(
        Document.username == payload.username,
        Document.status == "indexed",
    ).count()

    if intent == "GREETING":
        greeting = (
            "Hello! I’m ready to answer questions about your uploaded documents."
            if indexed_document_count
            else "Hello! Please upload a document first, and I’ll help you with its contents."
        )
        formatted = {
            "answer": greeting,
            "is_fallback": False,
            "citations": [],
            "low_context": False,
            "is_error": False,
        }
    elif intent == "ABOUT_BOT":
        # ABOUT_BOT asks about the assistant itself, so it is handled separately
        # from pure GREETING messages and never needs document retrieval.
        formatted = {
            "answer": ABOUT_BOT_MESSAGE,
            "is_fallback": False,
            "citations": [],
            "low_context": False,
            "is_error": False,
        }
    elif indexed_document_count == 0:
        formatted = {
            "answer": NO_DOCUMENTS_MESSAGE,
            "is_fallback": False,
            "citations": [],
            "low_context": False,
            "is_error": False,
        }
    else:
        # CHECK_DOCUMENTS always retrieves first. Actual context, then the
        # grounded NOT_FOUND_IN_DOCUMENT rule, decides whether an answer exists.
        retrieved_chunks = search_chunks(
            username=payload.username,
            query=payload.query,
            document_ids=payload.document_ids,
            top_k=3,
        )

        csv_query_documents = db.query(Document).filter(
            Document.username == payload.username,
            Document.status == "indexed",
            Document.file_type == "csv",
        )
        if payload.document_ids:
            csv_query_documents = csv_query_documents.filter(Document.id.in_(payload.document_ids))
        exact_csv_context = _csv_context_for_query(csv_query_documents.all(), payload.query)
        direct_csv_answer = _csv_direct_answer(csv_query_documents.all(), payload.query)
        if direct_csv_answer and exact_csv_context:
            exact_csv_context[0]["direct_answer"] = direct_csv_answer
        retrieved_chunks = (exact_csv_context + retrieved_chunks)[:3]

        # Chroma cosine distances are lower for closer matches. This gate only
        # uses the actual retrieval score, never question wording; missing scores
        # are allowed through for compatibility with lightweight test doubles.
        top_distance = retrieved_chunks[0].get("distance") if retrieved_chunks else None
        if top_distance is not None and top_distance > 0.85:
            retrieved_chunks = []

        if not retrieved_chunks:
            logger.info(
                "No chunks found for user '%s' query '%s'. Short-circuiting without LLM call.",
                payload.username,
                payload.query,
            )
            formatted = format_response(
                raw_answer="NOT_FOUND_IN_DOCUMENT",
                chunks_used=[],
            )
        else:
            try:
                raw_answer = generate_answer(query=payload.query, retrieved_chunks=retrieved_chunks)
            except RuntimeError as err:
                logger.error("LLM generation error: %s", err)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(err),
                )
            except Exception as err:
                logger.error("Unexpected error during LLM generation: %s", err)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred while generating answer: {err}",
                )
            formatted = format_response(raw_answer=raw_answer, chunks_used=retrieved_chunks)

    # 3. Save assistant's response to chat_messages
    citations_json = json.dumps(formatted["citations"]) if formatted.get("citations") else None
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=formatted["answer"],
        citations=citations_json,
        is_fallback=formatted["is_fallback"],
    )
    db.add(assistant_msg)
    db.commit()

    # 4. Returns the assistant's message and intent flags for frontend styling.
    return SessionMessageResponse(
        answer=formatted["answer"],
        is_fallback=formatted["is_fallback"],
        citations=formatted["citations"],
        low_context=formatted["low_context"],
        is_error=formatted.get("is_error", False),
    )

