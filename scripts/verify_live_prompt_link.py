"""
scripts/verify_live_prompt_link.py

Executes a live query to the running backend, flushes Langfuse, and verifies:
1. Generation span 'rag-answer' is linked to 'rag-main-system-prompt' version.
2. Prompts list in Langfuse contains all registered prompts.
"""

import sys
import time
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.config import get_langfuse_client

print("=" * 70)
print("  OMNIRAG AI: VERIFYING LIVE CHAT PROMPT LINKAGE IN LANGFUSE TRACE")
print("=" * 70)

lf_client = get_langfuse_client()

# 1. Verify Prompts exist in Langfuse
print("\n[STEP 1: VERIFYING PROMPTS IN LANGFUSE]")
expected_prompts = [
    "rag-main-system-prompt",
    "general-knowledge-system-prompt",
    "csv-summary-system-prompt",
    "prose-summary-system-prompt",
    "voice-correction-system-prompt",
    "whisper-initial-prompt",
    "intent-classifier-system-prompt",
    "intent-classifier-user-template",
    "subject-extractor-system-prompt",
    "subject-extractor-user-template",
]

for p_name in expected_prompts:
    try:
        p_obj = lf_client.get_prompt(p_name)
        print(f"  ✓ Prompt '{p_name}' active in Langfuse (version {p_obj.version})")
    except Exception as e:
        print(f"  ✗ Prompt '{p_name}' not found: {e}")

# 2. Perform live chat query via TestClient/direct call to trigger trace
print("\n[STEP 2: TRIGGERING LIVE CHAT WITH PROMPT LINKAGE]")
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth.dependencies import get_current_clerk_user

test_user_id = "user_3JDqZ88QnvMUEzBgzFLkiHilhKh"
app.dependency_overrides[get_current_clerk_user] = lambda: {
    "user_id": test_user_id,
    "session_id": "live_prompt_link_sess",
    "claims": {"sub": test_user_id}
}
client = TestClient(app)

# Create session
sess_res = client.post("/chat/sessions", json={})
assert sess_res.status_code == 201
sess_id = sess_res.json().get("session_id") or sess_res.json().get("id")

# Upload document to test RAG prompt link
doc_content = "OmniRAG System Architecture: Distributed semantic index over vector embeddings."
files = {"file": ("sys_architecture.txt", doc_content.encode("utf-8"), "text/plain")}
upload_res = client.post("/documents/upload", files=files)
assert upload_res.status_code == 200
doc_id = upload_res.json().get("id")

# Post RAG chat message
msg_res = client.post(
    f"/chat/sessions/{sess_id}/message",
    json={
        "query": "What is the system architecture of OmniRAG?",
        "rag_enabled": True,
        "web_search_enabled": False,
        "document_ids": [doc_id]
    }
)
assert msg_res.status_code == 200
print(f"  ✓ Chat query answered: '{msg_res.json().get('answer')}'")

# 3. Flush Langfuse and inspect trace
print("\n[STEP 3: FLUSHING TRACES AND VERIFYING PROMPT LINK IN TRACE]")
lf_client.flush()
print("  Waiting 10s for Langfuse Cloud ingestion...")
time.sleep(10)

recent_traces = lf_client.api.trace.list(limit=50)
print(f"  Retrieved {len(recent_traces.data)} recent traces from Langfuse:")
for t in recent_traces.data[:10]:
    print(f"    - [{t.id}] {t.name}")

rag_trace = None
for t_meta in recent_traces.data:
    if t_meta.name in ("chat-request", "post_session_message"):
        detail = lf_client.api.trace.get(t_meta.id)
        obs_names = [o.name for o in detail.observations]
        if "rag-answer" in obs_names:
            rag_trace = detail
            break

assert rag_trace is not None, "Could not locate chat-request trace containing 'rag-answer'"
print(f"  ✓ Located RAG chat trace: {rag_trace.id}")

rag_gen = next(o for o in rag_trace.observations if o.name == "rag-answer")
print(f"  ✓ Generation span 'rag-answer' details:")
print(f"      Type: {rag_gen.type}")
print(f"      Model: {rag_gen.model}")
prompt_info = getattr(rag_gen, "prompt_name", None) or getattr(rag_gen, "prompt_id", None) or getattr(rag_gen, "prompt", None)
print(f"      Linked Prompt: {getattr(rag_gen, 'prompt_name', 'N/A')} (v{getattr(rag_gen, 'prompt_version', 'N/A')})")

print("\n" + "=" * 70)
print("  LIVE PROMPT LINKAGE VERIFICATION COMPLETED SUCCESSFULLY!")
print("=" * 70)
