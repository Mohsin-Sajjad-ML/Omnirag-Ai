"""
llm_service.py - Groq LLM integration and grounded answer generation for OmniRAG AI.
"""
import langfuse


import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from groq import Groq, GroqError, AuthenticationError, RateLimitError, APIConnectionError, NotFoundError

from backend.config import settings, get_langfuse_client
import logging

logger = logging.getLogger(__name__)
from backend.prompts import (
    get_prompt,
    get_prompt_object,
    SYSTEM_PROMPT,
    GENERAL_KNOWLEDGE_SYSTEM_PROMPT,
    NO_DOCUMENTS_MESSAGE,
    ABOUT_BOT_MESSAGE,
    FALLBACK_MESSAGE,
    INTENT_CLASSIFIER_SYSTEM_PROMPT,
    INTENT_CLASSIFIER_USER_TEMPLATE,
    SUBJECT_EXTRACTOR_SYSTEM_PROMPT,
    SUBJECT_EXTRACTOR_USER_TEMPLATE,
)

# Primary model verified on active Groq tier; fallback models on Groq's tier if primary is unavailable
DEFAULT_GROQ_MODEL = settings.GROQ_MODEL
FALLBACK_GROQ_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
INTENT_CLASSIFIER_MODEL = "qwen/qwen3.8-27b"
SUBJECT_EXTRACTOR_MODEL = INTENT_CLASSIFIER_MODEL
MAX_CONTEXT_CHARS_PER_CHUNK = 5000


def get_groq_client() -> Groq:
    """
    Initializes and returns a Groq API client instance.
    """
    api_key = settings.GROQ_API_KEY
    if not api_key or not api_key.strip():
        raise RuntimeError(
            "Groq API key is not configured. Please add GROQ_API_KEY to your .env file."
        )
    return Groq(api_key=api_key.strip())


import sys


def _get_active_groq_client():
    mod_llm = sys.modules.get("backend.llm")
    if mod_llm and hasattr(mod_llm, "get_groq_client"):
        return getattr(mod_llm, "get_groq_client")()
    mod_chat = sys.modules.get("backend.chat")
    if mod_chat and hasattr(mod_chat, "get_groq_client"):
        return getattr(mod_chat, "get_groq_client")()
    return get_groq_client()


@langfuse.observe(as_type="generation")
def classify_intent(message: str) -> str:
    """Identify only messages that are clearly social or about the assistant."""
    try:
        sys_text = get_prompt("intent-classifier-system-prompt", fallback=INTENT_CLASSIFIER_SYSTEM_PROMPT)
        sys_obj = get_prompt_object("intent-classifier-system-prompt")
        user_tpl_text = get_prompt("intent-classifier-user-template", fallback=INTENT_CLASSIFIER_USER_TEMPLATE)
        
        if sys_obj:
            try:
                get_langfuse_client().update_current_generation(prompt=sys_obj)
            except Exception:
                pass
            
        classification_prompt = user_tpl_text.replace("{{message}}", "{message}").format(message=message)

        response = _get_active_groq_client().chat.completions.create(
            model=INTENT_CLASSIFIER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": sys_text,
                },
                {"role": "user", "content": classification_prompt},
            ],
            temperature=0.0,
            max_tokens=10,
        )
        label = (response.choices[0].message.content or "").strip().upper()
        if label == "GREETING":
            return "GREETING"
        if label == "ABOUT_BOT":
            return "ABOUT_BOT"
    except Exception as err:
        logger.warning("Intent classification failed; checking documents by default: %s", err)

    return "CHECK_DOCUMENTS"


@langfuse.observe(as_type="generation")
def extract_query_subject(query: str) -> str:
    """Extract the current question's core subject using a cheap Groq call."""
    try:
        sys_text = get_prompt("subject-extractor-system-prompt", fallback=SUBJECT_EXTRACTOR_SYSTEM_PROMPT)
        sys_obj = get_prompt_object("subject-extractor-system-prompt")
        user_tpl_text = get_prompt("subject-extractor-user-template", fallback=SUBJECT_EXTRACTOR_USER_TEMPLATE)
        
        if sys_obj:
            try:
                get_langfuse_client().update_current_generation(prompt=sys_obj)
            except Exception:
                pass
            
        extraction_prompt = user_tpl_text.replace("{{query}}", "{query}").format(query=query)

        response = _get_active_groq_client().chat.completions.create(
            model=SUBJECT_EXTRACTOR_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": sys_text,
                },
                {"role": "user", "content": extraction_prompt},
            ],
            temperature=0.0,
            max_tokens=16,
        )
        subject = (response.choices[0].message.content or "").strip()
        return subject.strip("`\"'.,!?;:")
    except Exception as err:
        logger.warning("Query subject extraction failed; denying general-knowledge assistance: %s", err)
        return ""


def build_rag_prompt(query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Constructs the contextual user prompt combining the user query with formatted
    retrieved chunk contents.
    """
    formatted_chunks = []
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        doc_id = chunk.get("document_id", "unknown")
        filename = chunk.get("filename", "document")
        chunk_idx = chunk.get("chunk_index", idx)
        text = chunk.get("text", "").strip()
        if len(text) > MAX_CONTEXT_CHARS_PER_CHUNK:
            text = text[:MAX_CONTEXT_CHARS_PER_CHUNK].rsplit(" ", 1)[0] + "..."
        formatted_chunks.append(
            f"[Source: {filename} | Doc ID: {doc_id} | Chunk: {chunk_idx}]\n{text}"
        )

    context_str = "\n\n".join(formatted_chunks)

    prompt = (
        f"CONTEXT INFORMATION:\n"
        f"---------------------\n"
        f"{context_str}\n"
        f"---------------------\n\n"
        f"USER QUESTION: {query}\n\n"
        f"Format your answer clearly for a chat interface. Use short paragraphs or bullet points where listing multiple items "
        f"(such as skills, dates, or categories). Add a blank line between distinct sections or list items. "
        f"Use markdown bold (**text**) for labels like field names, and bullet points (- item) for lists of more than 2 items. "
        f"Keep the tone professional and easy to scan, not a single dense block of text. "
        f"Respond in the same language and script the user used to ask the question. "
        f"If the user asks in Roman Urdu, you MUST reply strictly in Roman Urdu (Urdu written in Latin/English letters, e.g. 'Aapki policy ke mutabiq...'). "
        f"Never output Hindi or Devanagari script. Never output Icelandic, Welsh, or any other hallucinated language. "
        f"If they ask in English, reply in English. "
        f"Match their language naturally. "
        f"Answer the question using ONLY the information in the provided context. "
        f"If the answer is not contained in the context, respond exactly with: NOT_FOUND_IN_DOCUMENT"
    )
    return prompt


@langfuse.observe(as_type="generation", name="rag-answer")
def generate_answer(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    mode: str = "document",
    term: Optional[str] = None,
) -> str:
    """
    Generates an answer to the user's query grounded strictly in retrieved chunks
    using the Groq API.
    """
    client = _get_active_groq_client()
    prompt_obj = None
    if mode == "general_knowledge_assist":
        system_prompt = get_prompt("general-knowledge-system-prompt", fallback=GENERAL_KNOWLEDGE_SYSTEM_PROMPT)
        prompt_obj = get_prompt_object("general-knowledge-system-prompt")
        user_prompt = (
            f"The user's uploaded document mentions '{term or query}', but the retrieved context does not explain it in detail. "
            f"Answer the user's question using your own general knowledge, providing a clear definition and a simple example. "
            f"Clearly present this as general knowledge that supplements what is in the document, not as something quoted from the document itself. "
            f"Respond in the same language and script the user used to ask the question. "
            f"If the user asks in Roman Urdu (Urdu written in Latin/English letters), you MUST reply in Roman Urdu. "
            f"If they ask in English, reply in English. "
            f"Never output Hindi or Devanagari script unless the user explicitly wrote in Devanagari script. "
            f"Never output Icelandic or other hallucinated languages. "
            f"Match their language naturally.\n\nUSER QUESTION: {query}"
        )
    else:
        if not retrieved_chunks:
            return "NOT_FOUND_IN_DOCUMENT"
        system_prompt = get_prompt("rag-main-system-prompt", fallback=SYSTEM_PROMPT)
        prompt_obj = get_prompt_object("rag-main-system-prompt")
        user_prompt = build_rag_prompt(query, retrieved_chunks)

    if prompt_obj:
        try:
            get_langfuse_client().update_current_generation(prompt=prompt_obj)
        except Exception:
            pass

    if mode == "general_knowledge_assist":
        retrieved_chunks = retrieved_chunks or [{}]

    if not retrieved_chunks:
        return "NOT_FOUND_IN_DOCUMENT"

    for chunk in retrieved_chunks:
        if mode == "general_knowledge_assist":
            break
        direct_answer = chunk.get("direct_answer")
        if direct_answer:
            return direct_answer

    models_to_try = [DEFAULT_GROQ_MODEL] + [
        m for m in FALLBACK_GROQ_MODELS if m != DEFAULT_GROQ_MODEL
    ]

    last_error: Optional[Exception] = None

    for model in models_to_try:
        try:
            logger.info("Calling Groq chat completions with model '%s'...", model)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=1024,
            )

            try:
                usage = None
                if hasattr(response, "usage") and response.usage:
                    usage = {
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                        "total": response.usage.total_tokens,
                    }
                get_langfuse_client().update_current_generation(
                    model=model,
                    prompt=prompt_obj,
                    usage_details=usage,
                )
            except Exception as upd_err:
                logger.debug("Failed updating generation in Langfuse: %s", upd_err)

            raw_answer = response.choices[0].message.content or ""
            clean_answer = raw_answer.strip()

            if clean_answer.strip('."\'`') == "NOT_FOUND_IN_DOCUMENT":
                return "NOT_FOUND_IN_DOCUMENT"

            return clean_answer

        except NotFoundError as err:
            logger.warning("Model '%s' not found on current Groq tier: %s. Trying next model...", model, err)
            last_error = err
            continue
        except AuthenticationError as err:
            logger.error("Groq authentication failed: %s", err)
            raise RuntimeError(
                f"Groq API authentication failed. Please verify your GROQ_API_KEY in .env: {err}"
            ) from err
        except RateLimitError as err:
            logger.error("Groq rate limit reached: %s", err)
            raise RuntimeError(
                f"Groq API rate limit exceeded. Please wait a moment and try again: {err}"
            ) from err
        except APIConnectionError as err:
            logger.error("Groq connection error: %s", err)
            raise RuntimeError(
                f"Failed to connect to Groq API. Please check your internet connection: {err}"
            ) from err
        except GroqError as err:
            logger.error("Groq API error: %s", err)
            raise RuntimeError(f"Groq API error: {err}") from err
        except Exception as err:
            logger.error("Unexpected error during Groq LLM call: %s", err)
            raise RuntimeError(f"Failed to generate LLM response: {err}") from err

    raise RuntimeError(
        f"Groq API failed across all attempted models ({', '.join(models_to_try)}): {last_error}"
    )


ROMAN_URDU_WORDS = {
    "kya", "kiya", "kyun", "kyu", "kaise", "kaisay", "kahan", "kidhar", "kab", "kon", "kaun",
    "konsa", "kounsa", "kiske", "kisko", "kis", "kitna", "kitne", "kitni", "kitny",
    "yeh", "ye", "woh", "wo", "yahan", "wahan", "idhar", "udhar",
    "mai", "main", "mera", "meri", "mere", "mery", "meray", "mujhe", "mujhy", "humein", "hume",
    "humara", "hamara", "hamari", "hamare", "hum", "ham",
    "tum", "tu", "aap", "ap", "apka", "apki", "apke", "apko", "aapka", "aapki", "aapke", "aapko",
    "tera", "teri", "tere", "tery", "teray", "tumhara", "tumhari", "tumhare", "tumhe", "tumhein",
    "iska", "iski", "iske", "uska", "uski", "uske", "unka", "unki", "unke", "unhon", "inka", "inki", "inke", "inhon",
    "apna", "apni", "apne", "apny", "apnay", "mein", "men", "me",
    "hai", "hain", "hoon", "hun", "ho", "tha", "thi", "thay", "the", "hoga", "hogi", "hoge", "honge", "hongi",
    "karta", "karti", "karte", "karty", "kare", "karo", "karna", "karen", "kre", "kren", "kr", "kar", "kro", "krna",
    "gaya", "gayi", "gaye", "gye", "raha", "rahi", "rahe", "rahy", "sakta", "sakti", "sakte", "sakty",
    "chahiye", "chahta", "chahti", "chahte",
    "batao", "bataen", "bataiye", "bataien", "btao", "bolo", "bolen", "kehta", "kehti", "dekho", "dekh", "dekhna",
    "suno", "sun", "sunen",
    "aur", "lekin", "magar", "nahi", "nahin", "nhi", "na", "mat", "bhi", "toh", "to", "sirf", "bohot", "bahut",
    "zyada", "ziada", "kam", "acha", "achi", "ache", "achy", "achha", "theek", "thik", "shamil", "mutabiq",
    "tareekh", "naam", "shukriya", "shukria", "salaam", "salam", "assalam", "walaikum", "khuda", "hafiz", "allah", "bhai",
    "haan", "han", "bilkul", "dobara", "poochein", "poocho", "sawal", "jawab", "ke", "ki", "ka", "ky", "ko", "se", "per", "pe", "par", "ne",
    "haal", "hal", "baat", "bat", "kuch", "koi", "ab", "jab", "tab", "sab", "sub", "log", "wala", "wali", "wale", "waly", "walay",
}

ENGLISH_WORDS = {
    "the", "is", "are", "was", "were", "this", "that", "these", "those",
    "there", "their", "they", "them", "what", "where", "when", "which",
    "who", "whom", "whose", "why", "how", "with", "from", "about", "above",
    "below", "under", "between", "into", "through", "during", "before",
    "after", "have", "has", "had", "having", "do", "does", "did", "doing",
    "would", "should", "could", "will", "shall", "can", "may", "might", "must",
    "you", "your", "yours", "yourself", "yourselves", "we", "our", "ours",
    "ourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "and", "but", "if", "or", "because", "as", "until",
    "while", "of", "at", "by", "for", "document", "documents", "summary",
    "information", "according", "following", "please", "cannot", "found",
    "based", "query", "answer", "file", "text", "hello", "hi", "thanks", "thank",
    "revenue", "total", "count", "show", "give", "tell", "explain", "all",
}


def classify_language(text: str) -> str:
    """
    Lightweight, deterministic language classification determining if text is
    English ('en') or Roman Urdu ('roman-ur').
    """
    if not text or not text.strip():
        return "en"

    if re.search(r"[\u0600-\u06FF\u0900-\u097F]", text):
        return "roman-ur"

    tokens = re.findall(r"[a-z']+", text.lower())
    if not tokens:
        return "en"

    roman_exclusive = ROMAN_URDU_WORDS - ENGLISH_WORDS
    exclusive_roman_count = sum(1 for t in tokens if t in roman_exclusive)
    roman_urdu_count = sum(1 for t in tokens if t in ROMAN_URDU_WORDS)
    english_count = sum(1 for t in tokens if t in ENGLISH_WORDS)

    if exclusive_roman_count > 0 and roman_urdu_count > english_count:
        return "roman-ur"
    if exclusive_roman_count >= 2 and (exclusive_roman_count / len(tokens)) >= 0.2:
        return "roman-ur"

    return "en"


def format_response(
    raw_answer: str,
    chunks_used: List[Dict[str, Any]],
    source: str = "document",
) -> Dict[str, Any]:
    """
    Refines raw LLM output into a polished, user-facing response structure with
    proper source citations, friendly fallback messaging, and response_language.
    """
    clean_answer = (raw_answer or "").strip()
    is_marker = (
        clean_answer == "NOT_FOUND_IN_DOCUMENT"
        or clean_answer.strip('."\'`') == "NOT_FOUND_IN_DOCUMENT"
    )

    if source in ("general_knowledge", "rag_and_web", "web_search") and not is_marker:
        grouped_citations: Dict[str, Dict[str, Any]] = {}
        for chunk in (chunks_used or []):
            filename = chunk.get("filename") or "Unknown Document"
            file_type = chunk.get("file_type")
            if not file_type:
                file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

            doc_id = chunk.get("document_id")
            chunk_idx = chunk.get("chunk_index")

            if filename not in grouped_citations:
                grouped_citations[filename] = {
                    "filename": filename,
                    "file_type": file_type,
                    "document_id": doc_id,
                    "chunk_references": [],
                }

            if chunk_idx is not None and chunk_idx not in grouped_citations[filename]["chunk_references"]:
                grouped_citations[filename]["chunk_references"].append(chunk_idx)

        for citation in grouped_citations.values():
            citation["chunk_references"].sort()

        return {
            "answer": clean_answer,
            "is_fallback": False,
            "citations": list(grouped_citations.values()),
            "low_context": False,
            "source": source,
            "response_language": classify_language(clean_answer),
        }

    if is_marker or not chunks_used:
        return {
            "answer": FALLBACK_MESSAGE,
            "is_fallback": True,
            "citations": [],
            "low_context": False,
            "source": source,
            "response_language": "en",
        }

    grouped_citations: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks_used:
        filename = chunk.get("filename") or "Unknown Document"
        file_type = chunk.get("file_type")
        if not file_type:
            file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

        doc_id = chunk.get("document_id")
        chunk_idx = chunk.get("chunk_index")

        if filename not in grouped_citations:
            grouped_citations[filename] = {
                "filename": filename,
                "file_type": file_type,
                "document_id": doc_id,
                "chunk_references": [],
            }

        if chunk_idx is not None and chunk_idx not in grouped_citations[filename]["chunk_references"]:
            grouped_citations[filename]["chunk_references"].append(chunk_idx)

    for citation in grouped_citations.values():
        citation["chunk_references"].sort()

    citations = list(grouped_citations.values())
    low_context = len(chunks_used) < 2
    response_lang = classify_language(clean_answer)

    return {
        "answer": clean_answer,
        "is_fallback": False,
        "citations": citations,
        "low_context": low_context,
        "source": source,
        "response_language": response_lang,
    }


__all__ = [
    "DEFAULT_GROQ_MODEL",
    "FALLBACK_GROQ_MODELS",
    "INTENT_CLASSIFIER_MODEL",
    "SUBJECT_EXTRACTOR_MODEL",
    "MAX_CONTEXT_CHARS_PER_CHUNK",
    "get_groq_client",
    "classify_intent",
    "extract_query_subject",
    "build_rag_prompt",
    "generate_answer",
    "ROMAN_URDU_WORDS",
    "ENGLISH_WORDS",
    "classify_language",
    "format_response",
    "SYSTEM_PROMPT",
    "GENERAL_KNOWLEDGE_SYSTEM_PROMPT",
    "NO_DOCUMENTS_MESSAGE",
    "ABOUT_BOT_MESSAGE",
    "FALLBACK_MESSAGE",
    "INTENT_CLASSIFIER_SYSTEM_PROMPT",
    "INTENT_CLASSIFIER_USER_TEMPLATE",
    "SUBJECT_EXTRACTOR_SYSTEM_PROMPT",
    "SUBJECT_EXTRACTOR_USER_TEMPLATE",
]
