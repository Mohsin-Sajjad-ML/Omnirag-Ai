"""
summary_service.py - Document summary generation using Groq LLM.
"""
import langfuse


import sys
import logging
from typing import Optional
from groq import NotFoundError

from backend.chat.llm_service import (
    get_groq_client,
    DEFAULT_GROQ_MODEL,
    FALLBACK_GROQ_MODELS,
)
from backend.config import get_langfuse_client
from backend.prompts import (
    get_prompt,
    get_prompt_object,
    CSV_SUMMARY_SYSTEM_PROMPT,
    PROSE_SUMMARY_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


def _get_active_groq_client():
    mod_llm = sys.modules.get("backend.llm")
    if mod_llm and hasattr(mod_llm, "get_groq_client"):
        return getattr(mod_llm, "get_groq_client")()
    mod_chat = sys.modules.get("backend.chat")
    if mod_chat and hasattr(mod_chat, "get_groq_client"):
        return getattr(mod_chat, "get_groq_client")()
    return get_groq_client()


@langfuse.observe(as_type="generation", name="generate-summary")
def generate_summary(document_text: str, file_type: str) -> Optional[str]:
    """
    Generates an automated 2-4 sentence summary of a document using Groq LLM.
    """
    if not document_text or not document_text.strip():
        logger.info("generate_summary: document_text is empty; skipping summary generation.")
        return None

    try:
        MAX_SUMMARY_CHARS = 8000
        truncated_text = document_text[:MAX_SUMMARY_CHARS].strip()

        is_csv = (file_type or "").lower().strip(".") == "csv"

        if is_csv:
            system_prompt = get_prompt("csv-summary-system-prompt", fallback=CSV_SUMMARY_SYSTEM_PROMPT)
            prompt_obj = get_prompt_object("csv-summary-system-prompt")
            user_prompt = (
                f"Analyze this CSV dataset excerpt and summarize what it contains in 2-4 concise sentences, "
                f"highlighting its main topic and key points:\n\n"
                f"```csv\n{truncated_text}\n```"
            )
        else:
            system_prompt = get_prompt("prose-summary-system-prompt", fallback=PROSE_SUMMARY_SYSTEM_PROMPT)
            prompt_obj = get_prompt_object("prose-summary-system-prompt")
            user_prompt = (
                f"Summarize this document in 2-4 concise sentences, highlighting its main topic and key points:\n\n"
                f"\"\"\"\n{truncated_text}\n\"\"\""
            )
            
        if prompt_obj:
            try:
                get_langfuse_client().update_current_generation(prompt=prompt_obj)
            except Exception:
                pass

        client = _get_active_groq_client()

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
                    logger.debug("Failed updating summary generation in Langfuse: %s", upd_err)

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
        logger.error("generate_summary encountered an error: %s", exc)
        return None


__all__ = ["generate_summary"]
