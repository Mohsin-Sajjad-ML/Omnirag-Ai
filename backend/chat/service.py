"""
service.py - Core business logic and orchestration for Chat domain.
"""
from langfuse import observe

import json
import logging
import re
import sys
from typing import List, Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.database.models import Document, ChatSession, ChatMessage
from backend.chat.schemas import (
    ChatQueryRequest,
    ChatQueryResponse,
    SessionMessageRequest,
    SessionMessageResponse,
    TranscribeResponse,
)
from backend.documents.rag_service import (
    search_chunks as _base_search_chunks,
    term_present_in_document,
    get_document_snippets_for_term,
)
from backend.chat.llm_service import (
    ABOUT_BOT_MESSAGE,
    classify_intent as _base_classify_intent,
    classify_language,
    generate_answer as _base_generate_answer,
    format_response,
    extract_query_subject as _base_extract_query_subject,
)
from backend.chat.voice_service import correct_transcription
from backend.prompts import get_prompt, WHISPER_INITIAL_PROMPT

# Import decomposed session management functions
from backend.chat.session_service import (
    create_chat_session,
    update_chat_session,
    list_user_sessions,
    get_session_messages,
    delete_chat_session,
    pin_chat_session,
    duplicate_chat_session,
    generate_chat_context_summary,
    export_chat_session,
)

# Import decomposed web search & hybrid synthesis functions
from backend.chat.web_search_service import (
    _get_active_groq_client,
    _is_conversational_meta_instruction,
    _call_groq_general,
    _derive_search_query,
    _perform_web_search,
    _call_groq_web_search,
    _generate_hybrid_rag_web_answer,
)

logger = logging.getLogger(__name__)


# Exported functions that tests may monkeypatch on backend.chat.service
search_chunks = _base_search_chunks
generate_answer = _base_generate_answer
extract_query_subject = _base_extract_query_subject
classify_intent = _base_classify_intent


def _get_search_chunks():
    chat_mod = sys.modules.get("backend.chat")
    if chat_mod and hasattr(chat_mod, "search_chunks") and getattr(chat_mod, "search_chunks") is not _base_search_chunks:
        return getattr(chat_mod, "search_chunks")
    mod = sys.modules.get("backend.chat.service") or chat_mod
    if mod and hasattr(mod, "search_chunks"):
        return getattr(mod, "search_chunks")
    return search_chunks


def _get_generate_answer():
    chat_mod = sys.modules.get("backend.chat")
    if chat_mod and hasattr(chat_mod, "generate_answer") and getattr(chat_mod, "generate_answer") is not _base_generate_answer:
        return getattr(chat_mod, "generate_answer")
    mod = sys.modules.get("backend.chat.service") or chat_mod
    if mod and hasattr(mod, "generate_answer"):
        return getattr(mod, "generate_answer")
    return generate_answer


def _get_extract_query_subject():
    mod = sys.modules.get("backend.chat.service") or sys.modules.get("backend.chat")
    if mod and hasattr(mod, "extract_query_subject"):
        return getattr(mod, "extract_query_subject")
    return extract_query_subject


def _get_classify_intent():
    mod = sys.modules.get("backend.chat.service") or sys.modules.get("backend.chat")
    if mod and hasattr(mod, "classify_intent"):
        return getattr(mod, "classify_intent")
    return classify_intent



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
        "kon", "what", "which", "who", "show", "list", "name", "salary", "role",
        "csv", "document", "file", "all", "is", "are",
    }
    candidate_terms = {t for t in query_terms if t not in ignored_terms}

    chunks: List[dict] = []
    for doc in documents:
        if (doc.file_type or "").lower() != "csv":
            continue
        text = doc.extracted_text or ""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            continue

        header = lines[0]
        data_rows = lines[1:]
        matched_rows: List[str] = []

        if requested_ids:
            for row in data_rows:
                row_tokens = re.findall(r"\b\w+\b", row)
                if any(req_id in row_tokens for req_id in requested_ids):
                    matched_rows.append(row)

        if not matched_rows and candidate_terms:
            for row in data_rows:
                row_lower = row.lower()
                if any(term in row_lower for term in candidate_terms):
                    matched_rows.append(row)

        summary_parts = []
        if count_requested:
            summary_parts.append(f"TOTAL_EMPLOYEE_ROWS: {len(data_rows)}")
        if matched_rows:
            summary_parts.append(f"MATCHED_ROWS:\n{header}\n" + "\n".join(matched_rows[:10]))

        if summary_parts:
            chunks.append({
                "id": f"csv_fact_{doc.id}",
                "text": "\n\n".join(summary_parts),
                "document_id": doc.id,
                "filename": doc.original_filename,
                "file_type": "csv",
                "chunk_index": 0,
                "distance": 0.05,
            })

    return chunks


def _csv_direct_answer(documents: List[Document], query: str) -> Optional[str]:
    """Provide a reliable, concise direct answer for common table queries."""
    query_lower = query.lower()
    is_count_query = bool(re.search(
        r"\b(total|count|how many|number of|kitny|kitni)\b.*\b(employees?|staff|workers?|log|people)\b",
        query_lower,
    ))
    has_id_phrase = bool(re.search(r"(?:emp(?:loyee)?\s*id|ids?)\b", query_lower))
    requested_ids = re.findall(r"\b\d+\b", query_lower) if has_id_phrase else []

    target_doc = None
    for doc in documents:
        if (doc.file_type or "").lower() == "csv":
            target_doc = doc
            break

    if not target_doc:
        return None

    text = target_doc.extracted_text or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None

    header = [col.strip().lower() for col in lines[0].split(",")]
    rows = [line.split(",") for line in lines[1:]]

    if is_count_query:
        total = len(rows)
        return (
            f"Based on `{target_doc.original_filename}`, the total number of employees is {total}."
        )

    if requested_ids and "id" in header:
        id_index = header.index("id")
        matches = []
        for row in rows:
            if len(row) > id_index and row[id_index].strip() in requested_ids:
                row_dict = {
                    header[i]: row[i].strip()
                    for i in range(min(len(header), len(row)))
                }
                matches.append(row_dict)

        if matches:
            details = []
            for item in matches:
                name = item.get("name") or item.get("employee_name") or "Unknown"
                emp_id = item.get("id") or "N/A"
                role = item.get("role") or item.get("designation") or item.get("department")
                salary = item.get("salary")
                extra = []
                if role:
                    extra.append(f"Role: {role}")
                if salary:
                    extra.append(f"Salary: {salary}")
                extra_str = f" ({', '.join(extra)})" if extra else ""
                details.append(f"- Employee ID {emp_id}: **{name}**{extra_str}")

            return (
                f"From `{target_doc.original_filename}`:\n"
                + "\n".join(details)
            )

    return None


def _fast_message_intent(message: str) -> Optional[str]:
    """Lightweight regex-based intent classification for fast path."""
    clean = message.strip()
    clean_lower = clean.lower()
    words = re.findall(r"[a-z0-9']+", clean_lower)
    if not words:
        return None

    if len(words) <= 3 and any(
        w in ["hi", "hello", "hey", "salam", "assalam", "aao", "kese", "halo"]
        for w in words
    ):
        return "GREETING"

    if re.search(
        r"\b(who are you|what are you|what is this bot|about you|introduce yourself|tum kon ho|aap kon hain)\b",
        clean_lower,
    ):
        return "ABOUT_BOT"

    return None


def _subject_extraction_input(prior_messages: List[ChatMessage], current_query: str) -> str:
    """Builds a context-aware prompt for subject extraction across conversational turns."""
    if not prior_messages:
        return current_query

    dialogue = []
    for msg in prior_messages[-4:]:
        role = "User" if msg.role == "user" else "Assistant"
        clean = (msg.content or "").strip().replace("\n", " ")
        if clean:
            dialogue.append(f"{role}: {clean[:150]}")

    transcript = "\n".join(dialogue)
    return (
        f"CONVERSATION CONTEXT:\n{transcript}\n\n"
        f"CURRENT USER QUERY:\n{current_query}"
    )


@observe(name="mode-selected")
def record_mode_selected(mode: str, reason: str, details: Optional[dict] = None) -> dict:
    """Logs which path was chosen based on combination logic and why."""
    return {"mode": mode, "reason": reason, "details": details or {}}


@observe(name="chat-completed")
def record_chat_completed(source: str, citation_count: int, message_id: Optional[int] = None) -> dict:
    """Confirms the response was formatted and returned, capturing source and citations."""
    return {"source": source, "citation_count": citation_count, "message_id": message_id}


async def transcribe_audio(audio: UploadFile) -> TranscribeResponse:
    """Transcribe audio only; returns final transcript and detected_final_language."""
    if not audio.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An audio file is required.")

    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The audio file is empty.")

        groq_client = _get_active_groq_client()

        whisper_params = {
            "file": (audio.filename, audio_bytes),
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",
            "prompt": get_prompt("whisper-initial-prompt", fallback=WHISPER_INITIAL_PROMPT),
        }

        transcription = groq_client.audio.transcriptions.create(
            file=whisper_params["file"],
            model=whisper_params["model"],
            response_format=whisper_params["response_format"],
            prompt=whisper_params["prompt"],
        )

        if isinstance(transcription, dict):
            transcript = (transcription.get("text") or "").strip()
            detected_lang_raw = transcription.get("language") or transcription.get("detected_language")
        else:
            transcript = (getattr(transcription, "text", None) or "").strip()
            detected_lang_raw = getattr(transcription, "language", None)
            if detected_lang_raw is None:
                detected_lang_raw = getattr(transcription, "detected_language", None)
            if detected_lang_raw is None and hasattr(transcription, "model_extra") and transcription.model_extra:
                detected_lang_raw = transcription.model_extra.get("language") or transcription.model_extra.get("detected_language")

        detected_lang = str(detected_lang_raw or "en").strip().lower()

        if not transcript:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No speech was detected in the recording.")

        final_transcript, detected_final_language = correct_transcription(
            transcript=transcript,
            detected_language=detected_lang,
            groq_client=groq_client,
        )

        logger.info(
            "Transcribe finished: raw_lang=%s, final_lang=%s, raw='%s' -> final='%s'",
            detected_lang_raw,
            detected_final_language,
            transcript,
            final_transcript,
        )

        return TranscribeResponse(
            transcript=final_transcript,
            text=final_transcript,
            detected_final_language=detected_final_language,
        )
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("Audio transcription failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to transcribe the audio recording: {err}",
        ) from err


def query_knowledge_base(
    payload: ChatQueryRequest,
    clerk_user_id: str,
) -> ChatQueryResponse:
    """
    RAG query service function.
    """
    search_fn = _get_search_chunks()
    retrieved_chunks = search_fn(
        clerk_user_id=clerk_user_id,
        query=payload.query,
        document_ids=payload.document_ids,
        top_k=3,
    )

    if not retrieved_chunks:
        logger.info(
            "No chunks found for user '%s' query '%s'. Short-circuiting without LLM call.",
            clerk_user_id,
            payload.query,
        )
        formatted = format_response(
            raw_answer="NOT_FOUND_IN_DOCUMENT",
            chunks_used=[],
        )
        return ChatQueryResponse(**formatted)

    try:
        generate_fn = _get_generate_answer()
        raw_answer = generate_fn(query=payload.query, retrieved_chunks=retrieved_chunks)
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
    return ChatQueryResponse(**formatted)


def post_session_message(
    session_id: int,
    payload: SessionMessageRequest,
    clerk_user_id: str,
    db: Session,
) -> SessionMessageResponse:
    """
    Sends a query into a session and generates an assistant response.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    if session.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to post in this session."
        )

    existing_count = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
    if existing_count == 0 or session.title == "New Chat":
        clean_text = payload.query.strip().split("\n")[0].strip()
        if len(clean_text) > 40:
            truncated = clean_text[:37].rsplit(" ", 1)[0] if " " in clean_text[:37] else clean_text[:37]
            session.title = f"{truncated}..."
        else:
            session.title = clean_text if clean_text else "New Chat"
        db.add(session)

    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=payload.query,
        citations=None,
        is_fallback=False,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    return _generate_assistant_message_for_query(
        session_id=session_id,
        user_msg_id=user_msg.id,
        query=payload.query,
        clerk_user_id=clerk_user_id,
        db=db,
        document_ids=payload.document_ids,
        rag_enabled=payload.rag_enabled,
        web_search_enabled=payload.web_search_enabled,
    )


def _generate_assistant_message_for_query(
    session_id: int,
    user_msg_id: int,
    query: str,
    clerk_user_id: str,
    db: Session,
    document_ids: Optional[List[int]] = None,
    rag_enabled: bool = True,
    web_search_enabled: bool = False,
) -> SessionMessageResponse:
    # Load recent conversation history turns for multi-turn conversational awareness
    prior_messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.id != user_msg_id,
        )
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    chat_history = [
        {"role": m.role, "content": m.content}
        for m in prior_messages[-8:]
        if m.role in ("user", "assistant") and m.content
    ]

    is_meta_instruction = bool(chat_history) and _is_conversational_meta_instruction(query)

    indexed_document_count = db.query(Document).filter(
        Document.clerk_user_id == clerk_user_id,
        Document.status == "indexed",
    ).count()

    formatted = None

    # Step 2a: If rag_enabled is true AND user has indexed documents AND NOT a conversational meta-instruction:
    # run retrieval pipeline first
    if rag_enabled and indexed_document_count > 0 and not is_meta_instruction:
        intent = _fast_message_intent(query)
        if intent == "GREETING":
            greeting = "Hello! I’m ready to answer questions about your uploaded documents."
            formatted = {
                "answer": greeting,
                "is_fallback": False,
                "citations": [],
                "low_context": False,
                "is_error": False,
                "source": "rag",
                "response_language": classify_language(greeting),
            }
        elif intent == "ABOUT_BOT":
            formatted = {
                "answer": ABOUT_BOT_MESSAGE,
                "is_fallback": False,
                "citations": [],
                "low_context": False,
                "is_error": False,
                "source": "rag",
                "response_language": classify_language(ABOUT_BOT_MESSAGE),
            }
        else:
            search_fn = _get_search_chunks()
            retrieved_chunks = search_fn(
                clerk_user_id=clerk_user_id,
                query=query,
                document_ids=document_ids,
                top_k=3,
            )

            csv_query_documents = db.query(Document).filter(
                Document.clerk_user_id == clerk_user_id,
                Document.status == "indexed",
                Document.file_type == "csv",
            )
            if document_ids:
                csv_query_documents = csv_query_documents.filter(Document.id.in_(document_ids))
            exact_csv_context = _csv_context_for_query(csv_query_documents.all(), query)
            direct_csv_answer = _csv_direct_answer(csv_query_documents.all(), query)
            if direct_csv_answer and exact_csv_context:
                exact_csv_context[0]["direct_answer"] = direct_csv_answer
            retrieved_chunks = (exact_csv_context + retrieved_chunks)[:3]

            top_distance = retrieved_chunks[0].get("distance") if retrieved_chunks else None
            if top_distance is not None and top_distance > 0.85:
                retrieved_chunks = []

            if retrieved_chunks:
                record_mode_selected(
                    mode="rag",
                    reason="Indexed documents found with relevant semantic context",
                    details={"retrieved_chunks": len(retrieved_chunks)},
                )
                generate_fn = _get_generate_answer()
                try:
                    raw_answer = generate_fn(query=query, retrieved_chunks=retrieved_chunks)
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

                grounded_marker = (
                    not raw_answer
                    or raw_answer.strip() == "NOT_FOUND_IN_DOCUMENT"
                    or raw_answer.strip(' ."\'`') == "NOT_FOUND_IN_DOCUMENT"
                )

                if not grounded_marker:
                    # Answer grounded in documents found with citations
                    formatted = format_response(raw_answer=raw_answer, chunks_used=retrieved_chunks, source="rag")
                    formatted["source"] = "rag"
                else:
                    # Chunks exist but answer wasn't directly in them: check subject presence
                    extract_fn = _get_extract_query_subject()
                    subject = extract_fn(
                        _subject_extraction_input(
                            db.query(ChatMessage)
                            .filter(
                                ChatMessage.session_id == session_id,
                                ChatMessage.id != user_msg_id,
                            )
                            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                            .all(),
                            query,
                        )
                    )
                    effective_subject = subject or query.strip()
                    doc_matches = get_document_snippets_for_term(
                        term=effective_subject,
                        clerk_user_id=clerk_user_id,
                        document_ids=document_ids,
                        db=db,
                    )
                    subject_is_present = bool(doc_matches) or term_present_in_document(
                        term=effective_subject,
                        clerk_user_id=clerk_user_id,
                        document_ids=document_ids,
                        db=db,
                    )

                    if web_search_enabled:
                        if subject_is_present:
                            record_mode_selected(
                                mode="rag_and_web",
                                reason="Subject found in document; synthesized with live web search results and document context",
                                details={"subject": effective_subject, "documents": len(doc_matches)},
                            )
                            hybrid_answer = _generate_hybrid_rag_web_answer(
                                query=query,
                                subject=effective_subject,
                                doc_matches=doc_matches,
                                chat_history=chat_history,
                            )
                            formatted = format_response(
                                raw_answer=hybrid_answer,
                                chunks_used=retrieved_chunks,
                                source="rag_and_web",
                            )
                            formatted["source"] = "rag_and_web"
                            formatted["is_fallback"] = False
                        else:
                            # Subject not in document, but web search is enabled: answer directly via web search!
                            record_mode_selected(
                                mode="web_search",
                                reason="Subject not found in document; answered via live web search",
                                details={"web_search_enabled": True},
                            )
                            answer_text = _call_groq_web_search(query, history=chat_history)
                            formatted = {
                                "answer": answer_text,
                                "is_fallback": False,
                                "citations": [],
                                "low_context": False,
                                "is_error": False,
                                "source": "web_search",
                                "response_language": classify_language(answer_text),
                            }
                    elif subject_is_present:
                        try:
                            raw_answer = generate_fn(
                                query=query,
                                retrieved_chunks=retrieved_chunks,
                                mode="general_knowledge_assist",
                                term=effective_subject,
                            )
                        except Exception as err:
                            logger.error("General-knowledge assistance error: %s", err)
                            raise HTTPException(
                                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=str(err),
                            )
                        formatted = format_response(
                            raw_answer=raw_answer,
                            chunks_used=retrieved_chunks,
                            source="rag",
                        )
                        formatted["source"] = "rag"
                    else:
                        # Existing "not found in document" fallback within RAG path (only when web_search is off)
                        formatted = format_response(raw_answer=raw_answer, chunks_used=retrieved_chunks, source="rag")
                        formatted["source"] = "rag"

    # Step 2b: If rag_enabled is false, OR no documents are indexed, OR retrieval found nothing relevant,
    # OR the user query is a conversational formatting/shortening instruction:
    # Fall through to general answering (must ALWAYS produce a substantive answer, never decline):
    if formatted is None:
        if web_search_enabled:
            record_mode_selected(
                mode="web_search",
                reason="RAG off, no documents indexed, or no relevant chunks found; falling back to real-time web search",
                details={"web_search_enabled": True},
            )
            answer_text = _call_groq_web_search(query, history=chat_history)
            formatted = {
                "answer": answer_text,
                "is_fallback": False,
                "citations": [],
                "low_context": False,
                "is_error": False,
                "source": "web_search",
                "response_language": classify_language(answer_text),
            }
        else:
            record_mode_selected(
                mode="llm_api",
                reason="RAG off, no documents indexed, or no relevant chunks found; falling back to general LLM answering",
                details={"web_search_enabled": False},
            )
            answer_text = _call_groq_general(query, history=chat_history)
            formatted = {
                "answer": answer_text,
                "is_fallback": False,
                "citations": [],
                "low_context": False,
                "is_error": False,
                "source": "llm_api",
                "response_language": classify_language(answer_text),
            }

    citations_json = json.dumps(formatted["citations"]) if formatted.get("citations") else None
    response_lang = formatted.get("response_language") or classify_language(formatted["answer"])
    final_source = formatted.get("source") or ("rag" if formatted.get("citations") else "llm_api")

    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=formatted["answer"],
        citations=citations_json,
        is_fallback=formatted.get("is_fallback", False),
        source=final_source,
        response_language=response_lang,
    )
    db.add(assistant_msg)
    db.commit()

    record_chat_completed(
        source=final_source,
        citation_count=len(formatted.get("citations", [])),
        message_id=assistant_msg.id,
    )

    return SessionMessageResponse(
        answer=formatted["answer"],
        is_fallback=formatted.get("is_fallback", False),
        citations=formatted.get("citations", []),
        low_context=formatted.get("low_context", False),
        is_error=formatted.get("is_error", False),
        source=final_source,
        response_language=response_lang,
    )


def edit_message_and_regenerate(
    session_id: int,
    message_id: int,
    query: str,
    clerk_user_id: str,
    db: Session,
    document_ids: Optional[List[int]] = None,
    rag_enabled: bool = True,
    web_search_enabled: bool = False,
) -> SessionMessageResponse:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )
    if session.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit messages in this session."
        )

    target_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.id == message_id, ChatMessage.session_id == session_id)
        .first()
    )
    if not target_msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found."
        )
    if target_msg.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only user messages can be edited."
        )

    # Truncate all subsequent messages in this session
    db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.id > target_msg.id,
    ).delete(synchronize_session=False)

    target_msg.content = query.strip()
    db.commit()
    db.refresh(target_msg)

    return _generate_assistant_message_for_query(
        session_id=session_id,
        user_msg_id=target_msg.id,
        query=target_msg.content,
        clerk_user_id=clerk_user_id,
        db=db,
        document_ids=document_ids,
        rag_enabled=rag_enabled,
        web_search_enabled=web_search_enabled,
    )


def regenerate_assistant_message(
    session_id: int,
    clerk_user_id: str,
    db: Session,
) -> SessionMessageResponse:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )
    if session.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to regenerate messages in this session."
        )

    last_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .first()
    )
    if not last_msg or last_msg.role != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only regenerate the last assistant message."
        )

    # Find the preceding user message
    preceding_user_msg = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.role == "user",
            ChatMessage.id < last_msg.id,
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .first()
    )
    if not preceding_user_msg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No preceding user message found to regenerate response for."
        )

    # Preserve mode previously used on the assistant message
    last_src = getattr(last_msg, "source", None)
    if last_src == "web_search":
        reg_rag = False
        reg_web = True
    elif last_src == "llm_api":
        reg_rag = False
        reg_web = False
    else:
        reg_rag = True
        reg_web = False

    # Delete the last assistant message
    db.delete(last_msg)
    db.commit()

    return _generate_assistant_message_for_query(
        session_id=session_id,
        user_msg_id=preceding_user_msg.id,
        query=preceding_user_msg.content,
        clerk_user_id=clerk_user_id,
        db=db,
        rag_enabled=reg_rag,
        web_search_enabled=reg_web,
    )


__all__ = [
    "_csv_context_for_query",
    "_csv_direct_answer",
    "_fast_message_intent",
    "_subject_extraction_input",
    "_get_active_groq_client",
    "_is_conversational_meta_instruction",
    "_call_groq_general",
    "_derive_search_query",
    "_perform_web_search",
    "_call_groq_web_search",
    "_generate_hybrid_rag_web_answer",
    "transcribe_audio",
    "query_knowledge_base",
    "create_chat_session",
    "list_user_sessions",
    "get_session_messages",
    "update_chat_session",
    "delete_chat_session",
    "post_session_message",
    "pin_chat_session",
    "duplicate_chat_session",
    "export_chat_session",
    "generate_chat_context_summary",
    "edit_message_and_regenerate",
    "regenerate_assistant_message",
]
