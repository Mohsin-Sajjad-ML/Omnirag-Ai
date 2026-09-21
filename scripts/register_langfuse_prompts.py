"""
scripts/register_langfuse_prompts.py

One-time setup script to push all OmniRAG AI system prompts and templates
from backend/prompts/ into Langfuse Prompt Management with the 'production' label.
"""

import sys
import re
from pathlib import Path

# Add project root to sys.path so we can import backend packages
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.config import get_langfuse_client
from backend.prompts.rag_prompts import (
    SYSTEM_PROMPT,
    GENERAL_KNOWLEDGE_SYSTEM_PROMPT,
    CSV_SUMMARY_SYSTEM_PROMPT,
    PROSE_SUMMARY_SYSTEM_PROMPT,
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


def register_prompts():
    print("=" * 70)
    print("  OMNIRAG AI: REGISTERING PROMPTS IN LANGFUSE PROMPT MANAGEMENT")
    print("=" * 70)

    client = get_langfuse_client()

    prompts_to_register = [
        ("rag-main-system-prompt", SYSTEM_PROMPT),
        ("general-knowledge-system-prompt", GENERAL_KNOWLEDGE_SYSTEM_PROMPT),
        ("csv-summary-system-prompt", CSV_SUMMARY_SYSTEM_PROMPT),
        ("prose-summary-system-prompt", PROSE_SUMMARY_SYSTEM_PROMPT),
        ("voice-correction-system-prompt", CORRECTION_SYSTEM_PROMPT),
        ("whisper-initial-prompt", WHISPER_INITIAL_PROMPT),
        ("intent-classifier-system-prompt", INTENT_CLASSIFIER_SYSTEM_PROMPT),
        ("intent-classifier-user-template", INTENT_CLASSIFIER_USER_TEMPLATE),
        ("subject-extractor-system-prompt", SUBJECT_EXTRACTOR_SYSTEM_PROMPT),
        ("subject-extractor-user-template", SUBJECT_EXTRACTOR_USER_TEMPLATE),
    ]

    success_count = 0
    failure_count = 0

    for name, prompt_text in prompts_to_register:
        try:
            # Convert single-bracket placeholders (e.g. {message}) to mustache double-brackets (e.g. {{message}})
            langfuse_prompt_text = re.sub(r"(?<!\{)\{([a-zA-Z0-9_]+)\}(?!\})", r"{{\1}}", prompt_text)

            res = client.create_prompt(
                name=name,
                prompt=langfuse_prompt_text,
                labels=["production"],
                type="text",
            )
            version_str = f"v{res.version}" if hasattr(res, "version") else "ok"
            print(f"  [SUCCESS] '{name}' registered successfully ({version_str})")
            success_count += 1
        except Exception as exc:
            print(f"  [FAILED]  '{name}' registration error: {exc}")
            failure_count += 1

    print("-" * 70)
    print(f"Registration Summary: {success_count} succeeded, {failure_count} failed out of {len(prompts_to_register)}.")
    print("=" * 70)

    if failure_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    register_prompts()
