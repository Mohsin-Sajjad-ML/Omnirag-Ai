"""
llm.py - Groq LLM integration and grounded answer generation for OmniRAG AI.

This module handles:
1. Environment configuration loading (GROQ_API_KEY from .env).
2. Grounded prompt construction incorporating retrieved vector chunks.
3. Chat completions invocation via Groq Cloud API.
4. Hallucination prevention and deterministic 'NOT_FOUND_IN_DOCUMENT' fallback.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from groq import Groq, GroqError, AuthenticationError, RateLimitError, APIConnectionError, NotFoundError

logger = logging.getLogger(__name__)

# Ensure .env is loaded from the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Primary model as requested; fallback models on Groq's free tier if the primary is unavailable
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
FALLBACK_GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
# Use a small currently supported fallback for the per-message classifier. The
# configured answer model may be unavailable on a user's Groq tier.
INTENT_CLASSIFIER_MODEL = "qwen/qwen3.8-27b"
MAX_CONTEXT_CHARS_PER_CHUNK = 5000

# Session-message responses are deliberately separate from grounded-answer
# fallback handling because greetings and capability questions need canned replies.
NO_DOCUMENTS_MESSAGE = (
    "Please upload a document first, then I can answer questions about its contents."
)
ABOUT_BOT_MESSAGE = (
    "I'm OmniRAG AI — I answer questions based on documents you upload (PDF, DOCX, TXT, CSV), "
    "and I can reply in the language or style you ask for, including Roman Urdu. "
    "Just ask me about your uploaded documents!"
)


# ===============================================================================
# LIGHTWEIGHT MESSAGE INTENT CLASSIFICATION
# ===============================================================================

def classify_intent(message: str) -> str:
    """Identify only messages that are clearly social or about the assistant."""
    classification_prompt = (
        "Classify the message into exactly one label: GREETING or ABOUT_BOT.\n"
        "GREETING means pure social/conversational text with no informational intent.\n"
        "ABOUT_BOT means a meta-question about this assistant's capabilities, supported languages, or how it works.\n"
        "Anything that is not clearly GREETING or ABOUT_BOT must be classified as CHECK_DOCUMENTS. "
        "Do not guess whether an informational question is answerable; retrieval checks the actual documents.\n"
        "Examples:\n"
        "hi how are you -> GREETING\n"
        "thanks -> GREETING\n"
        "can you speak Roman Urdu? -> ABOUT_BOT\n"
        "what can you do? -> ABOUT_BOT\n"
        "do you support other languages? -> ABOUT_BOT\n"
        "Return ONLY one label word: GREETING, ABOUT_BOT, or CHECK_DOCUMENTS.\n\n"
        f"Message: {message}"
    )

    try:
        response = get_groq_client().chat.completions.create(
            model=INTENT_CLASSIFIER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a fast message-intent classifier. Follow the label rules exactly.",
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

    # Retrieval is the source of truth for every other message. This avoids
    # guessing from phrasing and works for any uploaded document topic.
    return "CHECK_DOCUMENTS"

# ==============================================================================
# PROMPT ENGINEERING & HALLUCINATION PREVENTION (VIVA EXPLANATION)
# ==============================================================================
# Why doesn't OmniRAG hallucinate?
#
# 1. Closed-World Grounding:
#    The system prompt strictly instructs the model to rely SOLELY on the provided
#    context. It explicitly forbids drawing from outside general knowledge or
#    speculating on unmentioned facts.
#
# 2. Deterministic Negative Marker:
#    When the context does not contain sufficient factual evidence to answer the
#    user's query, the model is instructed to emit an exact machine-parseable marker:
#    "NOT_FOUND_IN_DOCUMENT".
#    This eliminates polite conversational fluff (e.g., "I'm sorry, as an AI...")
#    and allows downstream services (Prompt 7 fallback handling) to cleanly detect
#    retrieval/knowledge gaps.
#
# 3. Low Sampling Variance (Temperature = 0.0):
#    Setting temperature to 0.0 produces greedy, deterministic decoding, heavily
#    penalizing speculative or creative hallucinations.
# ==============================================================================

SYSTEM_PROMPT = (
    "You are an accurate, strictly grounded AI assistant for OmniRAG AI.\n"
    "Your task is to answer the user's question based ONLY and EXCLUSIVELY on the provided document context.\n\n"
    "CRITICAL RULES:\n"
    "1. Answer the question using ONLY the information in the provided context.\n"
    "2. If the answer is not contained in the context, respond exactly with: NOT_FOUND_IN_DOCUMENT\n"
    "3. Do not assume, extrapolate, speculate, or bring in any outside knowledge.\n"
    "4. If the answer cannot be directly determined from the context, do NOT provide partial answers, "
    "apologies, or explanations. Respond with ONLY the exact string: NOT_FOUND_IN_DOCUMENT\n"
    "5. If the answer IS contained in the context, be concise, factual, and direct."
)


def get_groq_client() -> Groq:
    """
    Initializes and returns a Groq API client instance.

    Lazy initialization ensures the FastAPI server starts without crashing even
    if the GROQ_API_KEY environment variable is not yet set in .env.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError(
            "Groq API key is not configured. Please add GROQ_API_KEY to your .env file."
        )
    return Groq(api_key=api_key.strip())


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
        f"If the user asks in Roman Urdu, reply in Roman Urdu. If they ask in English, reply in English. "
        f"Match their language naturally. "
        f"Answer the question using ONLY the information in the provided context. "
        f"If the answer is not contained in the context, respond exactly with: NOT_FOUND_IN_DOCUMENT"
    )
    return prompt


def generate_answer(query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Generates an answer to the user's query grounded strictly in retrieved chunks
    using the Groq API.

    Parameters:
    - query (str): User question.
    - retrieved_chunks (list[dict]): Chunks returned by search_chunks().

    Returns:
    - str: Raw text response from the model (or 'NOT_FOUND_IN_DOCUMENT' if unanswerable).

    Raises:
    - RuntimeError: If the API key is missing, invalid, rate-limited, or network fails.
    """
    client = get_groq_client()

    if not retrieved_chunks:
        return "NOT_FOUND_IN_DOCUMENT"

    for chunk in retrieved_chunks:
        direct_answer = chunk.get("direct_answer")
        if direct_answer:
            return direct_answer

    user_prompt = build_rag_prompt(query, retrieved_chunks)

    # Candidate models to try: user-specified / default first, then fallback models
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
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,  # Greedy deterministic decoding to prevent hallucination
                max_tokens=1024,
            )

            raw_answer = response.choices[0].message.content or ""
            clean_answer = raw_answer.strip()

            # Ensure exact marker string match even if model wrapped in quotes or punctuation
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

    # If all models failed with NotFoundError or other error
    raise RuntimeError(
        f"Groq API failed across all attempted models ({', '.join(models_to_try)}): {last_error}"
    )


# ==============================================================================
# RESPONSE FORMATTING & SOURCE CITATIONS (PROMPT 7)
# ==============================================================================

FALLBACK_MESSAGE = (
    "I couldn't find an answer to that in your uploaded document(s). "
    "Try rephrasing your question, or check that you've uploaded the right file."
)


def format_response(raw_answer: str, chunks_used: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Refines raw LLM output into a polished, user-facing response structure with
    proper source citations and friendly fallback messaging.

    Parameters:
    - raw_answer (str): The raw text emitted by generate_answer().
    - chunks_used (list[dict]): The vector chunks retrieved from ChromaDB.

    Returns:
    - dict: {
        "answer": str,
        "is_fallback": bool,
        "citations": list[dict],
        "low_context": bool
      }

    ============================================================================
    CITATION GROUPING LOGIC (VIVA EXPLANATION):
    ============================================================================
    Why group chunks by filename rather than listing each chunk individually?
    1. Clarity & Deduplication:
       If a single document contributed 3 distinct chunks (e.g., chunk 0, 1, and 3),
       repeating the same filename three separate times clutters the UI and
       overwhelms the user with repetitive source cards.
    2. Hierarchical Document Provenance:
       Grouping mirrors established research citation standards (Document -> Sections/Chunks),
       providing a clean document-level reference along with an array of specific
       chunk indexes (`chunk_references: [0, 1, 3]`).
    3. Multi-Document Synthesis:
       When a synthesized answer draws information across multiple distinct files
       (e.g., 'financial_report.pdf' and 'audit_notes.docx'), document-level grouping
       produces a clean bibliography of distinct sources consulted.

    ============================================================================
    CONFIDENCE SIGNAL (low_context):
    ============================================================================
    If fewer than 2 chunks were retrieved for a non-fallback answer, 'low_context'
    is flagged as True. This alerts the client/UI that the answer was synthesized
    from sparse material and may be less exhaustive.
    For fallback responses, citations is an empty list and low_context is False.
    ============================================================================
    """
    clean_answer = (raw_answer or "").strip()
    is_marker = (
        clean_answer == "NOT_FOUND_IN_DOCUMENT"
        or clean_answer.strip('."\'`') == "NOT_FOUND_IN_DOCUMENT"
    )

    # 1. Fallback condition: unanswerable query or no context chunks available
    if is_marker or not chunks_used:
        return {
            "answer": FALLBACK_MESSAGE,
            "is_fallback": True,
            "citations": [],
            "low_context": False,
        }

    # 2. Build grouped citation list by filename
    grouped_citations: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks_used:
        filename = chunk.get("filename") or "Unknown Document"

        # Determine file extension/type
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

    # Sort chunk indexes numerically for clean, predictable presentation
    for citation in grouped_citations.values():
        citation["chunk_references"].sort()

    citations = list(grouped_citations.values())

    # 3. Confidence signal: low_context is true if fewer than 2 chunks retrieved
    low_context = len(chunks_used) < 2

    return {
        "answer": clean_answer,
        "is_fallback": False,
        "citations": citations,
        "low_context": low_context,
    }


# ==============================================================================
# AUTO-SUMMARY GENERATION (PROMPT 8)
# ==============================================================================

def generate_summary(document_text: str, file_type: str) -> Optional[str]:
    """
    Generates an automated 2-4 sentence summary of a document using Groq LLM.

    Prompt 8 Specifications & Architecture Decisions:
    ============================================================================
    1. Truncation Tradeoff (~8,000 characters):
       - If the extracted text is very long, it is truncated to the first 8,000
         characters (~1,500-2,000 words).
       - WHY THIS IS A REASONABLE TRADEOFF: A concise summary does not need the entire
         multi-hundred page content of a large document. The first 8,000 characters
         consistently encompass the title, abstract, executive summary, table of
         contents, introductory thesis, and primary framework. Truncation guarantees
         blazing-fast response times (<1s on Groq LPUs), protects free-tier token
         budgets, and prevents hitting strict rate limits on heavy uploads.

    2. CSV vs. Prose Prompt Specialization:
       - Prose documents (.pdf, .docx, .txt) follow standard narrative structure.
         The prompt instructs the model to highlight the main topic and key points.
       - CSV documents (.csv) represent structured tabular data rather than prose.
         Applying a prose prompt to CSV rows often causes LLMs to fabricate a story
         or generate incoherent narrative summaries. Instead, the CSV prompt explicitly
         instructs the model to describe what the data appears to contain: identifying
         columns, records, and the domain or analytical purpose of the dataset.

    3. Fault Tolerance & Non-blocking Design:
       - Wrapped completely in try/except blocks. If Groq API key is missing,
         rate-limited, or fails, the error is logged and None is returned.
       - Never raises exceptions that would block or fail document upload/indexing.
    ============================================================================
    """
    if not document_text or not document_text.strip():
        logger.info("generate_summary: document_text is empty; skipping summary generation.")
        return None

    try:
        # Step 1: Enforce 8,000 character truncation (Prompt 8 tradeoff)
        MAX_SUMMARY_CHARS = 8000
        truncated_text = document_text[:MAX_SUMMARY_CHARS].strip()

        # Step 2: Differentiate prompt based on file format (CSV vs Prose)
        is_csv = (file_type or "").lower().strip(".") == "csv"

        if is_csv:
            # CSV / Tabular prompt specialization:
            # Focus on schema, columns, entities, and what the dataset is about.
            system_prompt = (
                "You are an expert data analyst assistant for OmniRAG AI.\n"
                "Your task is to analyze the provided CSV dataset excerpt and summarize what the data contains.\n"
                "In 2-4 concise sentences, explain what columns/fields are present and what this dataset appears to be about.\n"
                "Do not invent fictitious narratives. Focus on the schema, entities, and analytical purpose."
            )
            user_prompt = (
                f"Analyze this CSV dataset excerpt and summarize what it contains in 2-4 concise sentences, "
                f"highlighting its main topic and key points:\n\n"
                f"```csv\n{truncated_text}\n```"
            )
        else:
            # Prose prompt (PDF, DOCX, TXT):
            # Focus on document thesis, main topic, and core findings.
            system_prompt = (
                "You are an accurate, helpful AI summarizer for OmniRAG AI.\n"
                "Summarize the provided document text in 2-4 concise sentences, highlighting its main topic and key points.\n"
                "Be direct, informative, and factual."
            )
            user_prompt = (
                f"Summarize this document in 2-4 concise sentences, highlighting its main topic and key points:\n\n"
                f"\"\"\"\n{truncated_text}\n\"\"\""
            )

        client = get_groq_client()

        models_to_try = [DEFAULT_GROQ_MODEL] + [
            m for m in FALLBACK_GROQ_MODELS if m != DEFAULT_GROQ_MODEL
        ]

        last_error = None
        for model in models_to_try:
            try:
                logger.info("Generating document auto-summary with model '%s'...", model)
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=250,
                )

                summary_text = (response.choices[0].message.content or "").strip()
                if summary_text:
                    logger.info("Auto-summary generated successfully (%d chars).", len(summary_text))
                    return summary_text

            except NotFoundError as err:
                logger.warning("Groq model '%s' not found for summary: %s. Trying fallback...", model, err)
                last_error = err
                continue
            except Exception as err:
                logger.warning("Groq model '%s' error during summary: %s. Trying fallback...", model, err)
                last_error = err
                continue

        logger.error("All Groq models failed to generate summary. Last error: %s", last_error)
        return None

    except Exception as exc:
        # Critical rule: Summary failure must NEVER fail the core upload/indexing flow
        logger.error("generate_summary encountered an error: %s", exc)
        return None

