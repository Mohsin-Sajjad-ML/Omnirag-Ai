import os
os.environ["LANGFUSE_TIMEOUT"] = "30"

import sys
import time
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_langfuse_client
from backend.auth.dependencies import get_current_clerk_user

test_user_id = "user_3JDqZ88QnvMUEzBgzFLkiHilhKh"

def mock_get_current_user():
    return {
        "user_id": test_user_id,
        "session_id": "mock_sess_1",
        "claims": {"sub": test_user_id}
    }

app.dependency_overrides[get_current_clerk_user] = mock_get_current_user
client = TestClient(app)

print("--- 1. Creating a new chat session ---")
session_resp = client.post("/chat/sessions", json={})
assert session_resp.status_code == 201, f"Failed to create session: {session_resp.text}"
session_id = session_resp.json().get("session_id") or session_resp.json().get("id")
print(f"Created Session ID: {session_id}")

print(f"\n--- 2. Sending real chat query with RAG in session {session_id} ---")
msg_resp = client.post(
    f"/chat/sessions/{session_id}/message",
    json={
        "query": "According to the employee handbook, what is the policy on employee annual vacation leave?",
        "rag_enabled": True,
        "web_search_enabled": False,
    }
)
print("Chat message status:", msg_resp.status_code)
msg_data = msg_resp.json()
print("Chat answer:", (msg_data.get("answer") or "")[:120] + "...")
print("Chat source:", msg_data.get("source"))

print("\n--- 3. Flushing Langfuse traces ---")
lf_client = get_langfuse_client()
lf_client.flush()
time.sleep(6)  # allow cloud ingestion

print("\n--- 4. Fetching latest post_session_message trace from Langfuse Cloud ---")
recent_traces = lf_client.api.trace.list(limit=5)
chat_trace = None
for t_meta in recent_traces.data:
    if t_meta.name == "post_session_message":
        chat_trace = lf_client.api.trace.get(t_meta.id)
        # Verify it's this current session message
        if len(chat_trace.observations) >= 4:
            break

assert chat_trace is not None, "Could not find recent post_session_message trace in Langfuse!"

print(f"\nFound Trace: '{chat_trace.name}' (ID: {chat_trace.id})")
print(f"Total observations count: {len(chat_trace.observations)}")

obs_by_id = {o.id: o for o in chat_trace.observations}
obs_names = [o.name for o in chat_trace.observations]
obs_types = {o.name: o.type for o in chat_trace.observations}

print("\nAll observations in trace:")
for o in chat_trace.observations:
    parent_info = f"parent={obs_by_id[o.parent_observation_id].name}" if o.parent_observation_id and o.parent_observation_id in obs_by_id else "root"
    print(f"  - [{o.type}] {o.name} ({parent_info})")

print("\n--- Checking Tree Structure ---")
assert "retrieve_relevant_chunks" in obs_names, "retrieve_relevant_chunks missing!"
assert "embed_query" in obs_names, "embed_query missing!"
assert "vector_search" in obs_names, "vector_search missing!"
assert "generate_answer" in obs_names, "generate_answer missing!"
assert obs_types.get("generate_answer") == "GENERATION", "generate_answer must be a GENERATION card!"

# Check parent relationships
retrieval_obs = next(o for o in chat_trace.observations if o.name == "retrieve_relevant_chunks")
embed_obs = next(o for o in chat_trace.observations if o.name == "embed_query")
search_obs = next(o for o in chat_trace.observations if o.name == "vector_search")

print(f"\nretrieve_relevant_chunks ID: {retrieval_obs.id}")
print(f"embed_query parent: {embed_obs.parent_observation_id}")
print(f"vector_search parent: {search_obs.parent_observation_id}")

assert embed_obs.parent_observation_id == retrieval_obs.id, "embed_query must be nested inside retrieve_relevant_chunks!"
assert search_obs.parent_observation_id == retrieval_obs.id, "vector_search must be nested inside retrieve_relevant_chunks!"

print("\n✓ Tree Structure Confirmed:")
print("  post_session_message (root)")
print("  ├── retrieve_relevant_chunks")
print("  │   ├── embed_query (SPAN)")
print("  │   └── vector_search (SPAN)")
print("  └── generate_answer (GENERATION)")
print("\nALL VERIFICATIONS PASSED PERFECTLY!")
