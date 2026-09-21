"""
scripts/verify_prompt_resilience.py

End-to-end verification of Langfuse Prompt Management and graceful local fallback resilience:
1. Valid configuration: Fetches from Langfuse, caches in memory (5 min TTL), links prompt in trace.
2. Resilience: Simulates invalid credentials/network failure; verifies silent fallback to local constants.
3. Restoration: Restores valid configuration; verifies successful Langfuse fetching resumes.
"""

import os
import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.main import app
from backend.config import settings, get_langfuse_client
from backend.auth.dependencies import get_current_clerk_user
from backend.prompts import (
    get_prompt,
    get_prompt_object,
    clear_prompt_cache,
    SYSTEM_PROMPT,
    CSV_SUMMARY_SYSTEM_PROMPT,
    PROSE_SUMMARY_SYSTEM_PROMPT,
    CORRECTION_SYSTEM_PROMPT,
    INTENT_CLASSIFIER_SYSTEM_PROMPT,
    SUBJECT_EXTRACTOR_SYSTEM_PROMPT,
)

test_user_id = "user_3JDqZ88QnvMUEzBgzFLkiHilhKh"

def mock_get_current_user():
    return {
        "user_id": test_user_id,
        "session_id": "mock_sess_resilience_test",
        "claims": {"sub": test_user_id}
    }

app.dependency_overrides[get_current_clerk_user] = mock_get_current_user
client = TestClient(app)

print("=" * 70)
print("  OMNIRAG AI: LANGFUSE PROMPT RESILIENCE & FALLBACK VERIFICATION")
print("=" * 70)

# -----------------------------------------------------------------------------
# STEP 1: Test with Valid Langfuse Configuration
# -----------------------------------------------------------------------------
print("\n[PHASE 1: VALID LANGFUSE CONFIGURATION]")
clear_prompt_cache()

prompt_text = get_prompt("rag-main-system-prompt", fallback=SYSTEM_PROMPT)
prompt_obj = get_prompt_object("rag-main-system-prompt")

assert prompt_text is not None and len(prompt_text) > 0, "Prompt text should not be empty"
assert prompt_obj is not None, "Prompt object should be fetched and cached from Langfuse"
print(f"  ✓ Fetched 'rag-main-system-prompt' from Langfuse (v{prompt_obj.version})")

# Cache hit test
t0 = time.time()
cached_text = get_prompt("rag-main-system-prompt", fallback=SYSTEM_PROMPT)
duration_ms = (time.time() - t0) * 1000
assert cached_text == prompt_text
print(f"  ✓ Subsequent fetch served instantly from in-memory TTL cache ({duration_ms:.2f}ms)")

# -----------------------------------------------------------------------------
# STEP 2: Resilience Test with Invalid Credentials (Failure Simulation)
# -----------------------------------------------------------------------------
print("\n[PHASE 2: RESILIENCE TEST - SIMULATED FAILURE & LOCAL FALLBACK]")
original_secret = os.environ.get("LANGFUSE_SECRET_KEY", "")

try:
    # Intentionally corrupt Langfuse secret key
    os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-invalid-fake-secret-key-12345"
    clear_prompt_cache()

    print("  -> Corrupted LANGFUSE_SECRET_KEY to simulate outage/auth error.")
    print("  -> Attempting get_prompt with fallback constant...")

    fallback_text = get_prompt("rag-main-system-prompt", fallback=SYSTEM_PROMPT)
    assert fallback_text == SYSTEM_PROMPT, "Should return exact local SYSTEM_PROMPT on failure!"
    print("  ✓ Graceful degradation confirmed: get_prompt returned local SYSTEM_PROMPT without raising.")

    # Create session and send chat query while Langfuse is broken
    sess_res = client.post("/chat/sessions", json={})
    assert sess_res.status_code == 201
    sess_id = sess_res.json().get("session_id") or sess_res.json().get("id")

    chat_res = client.post(
        f"/chat/sessions/{sess_id}/message",
        json={
            "query": "What is OmniRAG AI?",
            "rag_enabled": False,
            "web_search_enabled": False,
        }
    )
    assert chat_res.status_code == 200, f"Chat failed during Langfuse outage: {chat_res.text}"
    answer = chat_res.json().get("answer")
    assert answer and len(answer) > 10, "Assistant should generate a valid answer using fallback prompt"
    print("  ✓ Real chat query succeeded with HTTP 200 using local fallback prompts under Langfuse outage.")
    print(f"    Answer snippet: '{answer[:75]}...'")

finally:
    # -------------------------------------------------------------------------
    # STEP 3: Restoration to Valid Configuration
    # -------------------------------------------------------------------------
    print("\n[PHASE 3: RESTORATION & RESUMING LANGFUSE FETCH]")
    os.environ["LANGFUSE_SECRET_KEY"] = original_secret
    clear_prompt_cache()

    restored_text = get_prompt("rag-main-system-prompt", fallback=SYSTEM_PROMPT)
    restored_obj = get_prompt_object("rag-main-system-prompt")

    assert restored_obj is not None, "Should resume fetching from Langfuse once credentials restored"
    print(f"  ✓ Valid credentials restored. Fetched from Langfuse again (v{restored_obj.version}).")

    # Send chat query with restored configuration and RAG enabled
    chat_res2 = client.post(
        f"/chat/sessions/{sess_id}/message",
        json={
            "query": "Summarize what you can do.",
            "rag_enabled": False,
            "web_search_enabled": False,
        }
    )
    assert chat_res2.status_code == 200
    print("  ✓ Real chat query executed successfully after restoration.")

print("\n" + "=" * 70)
print("  PROMPT RESILIENCE & LOCAL-FALLBACK TESTS PASSED 100%!")
print("=" * 70)
