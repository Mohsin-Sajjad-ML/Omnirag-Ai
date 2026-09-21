"""
backend/prompts/__init__.py

Central prompt registry re-exporting all system prompt constants, templates,
and providing the resilient get_prompt helper with in-memory TTL caching and graceful local fallback.
"""

import time
import logging
from typing import Optional, Dict, Any, Tuple

from backend.prompts.rag_prompts import (
    SYSTEM_PROMPT,
    RAG_SYSTEM_PROMPT,
    GENERAL_KNOWLEDGE_SYSTEM_PROMPT,
    CSV_SUMMARY_SYSTEM_PROMPT,
    PROSE_SUMMARY_SYSTEM_PROMPT,
    NO_DOCUMENTS_MESSAGE,
    ABOUT_BOT_MESSAGE,
    FALLBACK_MESSAGE,
)
from backend.prompts.voice_prompts import (
    CORRECTION_SYSTEM_PROMPT,
    WHISPER_INITIAL_PROMPT,
)
from backend.prompts.intent_prompts import (
    INTENT_CLASSIFIER_SYSTEM_PROMPT,
    INTENT_CLASSIFIER_USER_TEMPLATE,
    SUBJECT_EXTRACTOR_SYSTEM_PROMPT,
    SUBJECT_EXTRACTOR_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)

# In-memory TTL prompt cache: {prompt_name: {"compiled_text": str, "prompt_obj": obj, "expires_at": float}}
_PROMPT_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes
FAILURE_COOLDOWN_SECONDS = 30  # Cooldown on network/auth failure before retrying


def get_prompt_with_object(name: str, fallback: str, **kwargs) -> Tuple[str, Optional[Any]]:
    """
    Fetches a prompt from Langfuse Prompt Management with an in-memory TTL cache (5 min)
    and graceful local fallback. Returns a tuple of (compiled_text, prompt_object).

    Guaranteed never to raise an exception or block application functionality.
    """
    now = time.time()
    cached = _PROMPT_CACHE.get(name)

    if cached and now < cached.get("expires_at", 0):
        prompt_obj = cached.get("prompt_obj")
        if prompt_obj:
            try:
                if kwargs:
                    return prompt_obj.compile(**kwargs), prompt_obj
                return cached.get("compiled_text", fallback), prompt_obj
            except Exception as compile_err:
                logger.warning("Error compiling cached Langfuse prompt '%s': %s. Using local fallback.", name, compile_err)
                try:
                    return fallback.format(**kwargs) if kwargs else fallback, prompt_obj
                except Exception:
                    return fallback, prompt_obj
        else:
            # In failure cooldown window; return local fallback directly
            try:
                return fallback.format(**kwargs) if kwargs else fallback, None
            except Exception:
                return fallback, None

    try:
        from backend.config import get_langfuse_client
        client = get_langfuse_client()
        prompt_obj = client.get_prompt(name, label="production")
        if kwargs:
            compiled_text = prompt_obj.compile(**kwargs)
        else:
            compiled_text = prompt_obj.compile()

        _PROMPT_CACHE[name] = {
            "compiled_text": compiled_text,
            "prompt_obj": prompt_obj,
            "expires_at": now + CACHE_TTL_SECONDS,
        }
        return compiled_text, prompt_obj
    except Exception as exc:
        logger.warning(
            "Langfuse prompt fetch failed for '%s' (%s). Using local fallback prompt.",
            name,
            exc,
        )
        _PROMPT_CACHE[name] = {
            "compiled_text": fallback,
            "prompt_obj": None,
            "expires_at": now + FAILURE_COOLDOWN_SECONDS,
        }
        try:
            return fallback.format(**kwargs) if kwargs else fallback, None
        except Exception:
            return fallback, None


def get_prompt(name: str, fallback: str, **kwargs) -> str:
    """
    Fetches the compiled prompt string from Langfuse or returns the fallback constant.
    Guaranteed never to raise or block app execution.
    """
    compiled_text, _ = get_prompt_with_object(name, fallback, **kwargs)
    return compiled_text


def get_prompt_object(name: str) -> Optional[Any]:
    """
    Returns the cached Langfuse prompt object for linking with Langfuse generation cards.
    """
    entry = _PROMPT_CACHE.get(name)
    if entry:
        return entry.get("prompt_obj")
    return None


def clear_prompt_cache() -> None:
    """Clears the in-memory prompt cache."""
    _PROMPT_CACHE.clear()


__all__ = [
    # Helpers
    "get_prompt",
    "get_prompt_with_object",
    "get_prompt_object",
    "clear_prompt_cache",
    # Prompt Constants
    "SYSTEM_PROMPT",
    "RAG_SYSTEM_PROMPT",
    "GENERAL_KNOWLEDGE_SYSTEM_PROMPT",
    "CSV_SUMMARY_SYSTEM_PROMPT",
    "PROSE_SUMMARY_SYSTEM_PROMPT",
    "NO_DOCUMENTS_MESSAGE",
    "ABOUT_BOT_MESSAGE",
    "FALLBACK_MESSAGE",
    "CORRECTION_SYSTEM_PROMPT",
    "WHISPER_INITIAL_PROMPT",
    "INTENT_CLASSIFIER_SYSTEM_PROMPT",
    "INTENT_CLASSIFIER_USER_TEMPLATE",
    "SUBJECT_EXTRACTOR_SYSTEM_PROMPT",
    "SUBJECT_EXTRACTOR_USER_TEMPLATE",
]
