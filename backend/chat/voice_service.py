"""
voice_service.py - Whisper voice transcription normalization and correction routines.
"""
import langfuse


import re
import logging
from typing import Optional, Tuple

from backend.chat.llm_service import (
    get_groq_client,
    classify_language,
    INTENT_CLASSIFIER_MODEL,
)
from backend.config import get_langfuse_client
from backend.prompts import (
    get_prompt,
    get_prompt_object,
    CORRECTION_SYSTEM_PROMPT,
    WHISPER_INITIAL_PROMPT,
)

logger = logging.getLogger(__name__)


@langfuse.observe(as_type="generation")
def correct_transcription(
    transcript: str,
    detected_language: str = "en",
    groq_client=None,
) -> Tuple[str, str]:
    """
    Normalizes Whisper transcriptions based on detected language metadata and script.

    Target languages:
    - English ('en'): Fast-path, pass through unchanged without extra LLM call (unless
      the text contains non-Latin scripts like Urdu or Devanagari).
    - Roman Urdu ('roman-ur') or anything other than 'en': Routed through content-aware
      Groq correction safety net, outputting either Roman Urdu or clean English.

    Returns:
        Tuple[str, str]: (final_transcript, detected_final_language)
    """
    lang_norm = (detected_language or "").strip().lower()
    has_indic_or_arabic_script = bool(re.search(r"[\u0600-\u06FF\u0900-\u097F]", transcript))
    is_detected_english = lang_norm in ("en", "english")
    should_fast_path = is_detected_english and not has_indic_or_arabic_script

    if should_fast_path:
        logger.info("Fast-path taken for language=%s; correction LLM skipped.", lang_norm)
        return transcript, "en"

    logger.info(
        "Non-English detection or non-Latin script present (language=%s, script_flag=%s). Invoking Groq correction...",
        lang_norm,
        has_indic_or_arabic_script,
    )

    try:
        client = groq_client or get_groq_client()
        sys_text = get_prompt("voice-correction-system-prompt", fallback=CORRECTION_SYSTEM_PROMPT)
        prompt_obj = get_prompt_object("voice-correction-system-prompt")
        if prompt_obj:
            try:
                get_langfuse_client().update_current_generation(prompt=prompt_obj)
            except Exception:
                pass

        response = client.chat.completions.create(
            model=INTENT_CLASSIFIER_MODEL,
            messages=[
                {"role": "system", "content": sys_text},
                {"role": "user", "content": transcript},
            ],
            temperature=0.0,
            max_tokens=256,
        )
        corrected = (response.choices[0].message.content or "").strip()
        final_text = corrected or transcript
        final_lang = classify_language(final_text)
        logger.info("Groq correction completed: '%s' -> '%s' (%s)", transcript, final_text, final_lang)
        return final_text, final_lang
    except Exception as err:
        logger.warning("Transcription correction call failed; using raw transcript: %s", err)
        final_lang = classify_language(transcript)
        return transcript, final_lang


@langfuse.observe()
def transliterate_urdu_transcript(
    transcript: str,
    groq_client=None,
    detected_language: Optional[str] = None,
) -> str:
    """
    Backwards-compatible wrapper for transcription normalization.
    """
    if detected_language is not None:
        final_text, _ = correct_transcription(transcript, detected_language, groq_client)
        return final_text

    if re.search(r"[\u0600-\u06FF\u0900-\u097F]", transcript):
        final_text, _ = correct_transcription(transcript, detected_language="ur", groq_client=groq_client)
        return final_text

    return transcript


__all__ = [
    "correct_transcription",
    "transliterate_urdu_transcript",
    "CORRECTION_SYSTEM_PROMPT",
    "WHISPER_INITIAL_PROMPT",
]
