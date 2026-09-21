"""
Chat domain package.
"""

from backend.prompts import (
    CORRECTION_SYSTEM_PROMPT,
    WHISPER_INITIAL_PROMPT,
    ABOUT_BOT_MESSAGE,
    NO_DOCUMENTS_MESSAGE,
)
from backend.chat.voice_service import (
    correct_transcription,
    transliterate_urdu_transcript,
)
from backend.chat.llm_service import (
    classify_intent,
    classify_language,
    generate_answer,
    format_response,
    get_groq_client,
    INTENT_CLASSIFIER_MODEL,
    extract_query_subject,
)
from backend.documents.rag_service import (
    search_chunks,
    term_present_in_document,
    get_document_snippets_for_term,
)
from backend.chat.service import (
    _csv_context_for_query,
    _csv_direct_answer,
    _fast_message_intent,
    _subject_extraction_input,
)
from backend.chat.router import (
    router,
    transcribe_audio,
    query_knowledge_base,
    create_chat_session,
    list_user_sessions,
    get_session_messages,
    delete_chat_session,
    post_session_message,
)

__all__ = [
    "CORRECTION_SYSTEM_PROMPT",
    "WHISPER_INITIAL_PROMPT",
    "ABOUT_BOT_MESSAGE",
    "NO_DOCUMENTS_MESSAGE",
    "correct_transcription",
    "transliterate_urdu_transcript",
    "classify_intent",
    "classify_language",
    "generate_answer",
    "format_response",
    "get_groq_client",
    "INTENT_CLASSIFIER_MODEL",
    "extract_query_subject",
    "search_chunks",
    "term_present_in_document",
    "get_document_snippets_for_term",
    "_csv_context_for_query",
    "_csv_direct_answer",
    "_fast_message_intent",
    "_subject_extraction_input",
    "router",
    "transcribe_audio",
    "query_knowledge_base",
    "create_chat_session",
    "list_user_sessions",
    "get_session_messages",
    "delete_chat_session",
    "post_session_message",
]
