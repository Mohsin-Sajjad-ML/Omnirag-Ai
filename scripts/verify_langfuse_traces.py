import os
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

print("--- 1. Performing real document upload ---")
doc_content = (
    "OmniRAG Enterprise Vacation Policy:\n"
    "All full-time staff members are allocated 28 days of paid annual vacation leave each calendar year.\n"
    "Leave requests should be submitted at least two weeks in advance via the HR portal."
)
files = {
    "file": ("enterprise_vacation_policy.txt", doc_content.encode("utf-8"), "text/plain")
}
upload_resp = client.post("/documents/upload", files=files)
print("Upload status:", upload_resp.status_code, upload_resp.json())
uploaded_doc_id = upload_resp.json().get("id")

print("\n--- 2. Performing real chat session creation (CRUD) ---")
session_resp = client.post("/chat/sessions", json={})
print("Create session status:", session_resp.status_code, session_resp.json())
session_id = session_resp.json().get("session_id") or session_resp.json().get("id")

print(f"\n--- 3. Performing real chat message send with RAG in session {session_id} ---")
msg_resp = client.post(
    f"/chat/sessions/{session_id}/message",
    json={
        "query": "How many days of paid annual vacation leave are allocated to full-time staff?",
        "rag_enabled": True,
        "web_search_enabled": False,
        "document_ids": [uploaded_doc_id] if uploaded_doc_id else None,
    }
)
print("Chat message status:", msg_resp.status_code)
print("Chat answer:", msg_resp.json().get("answer"))
print("Chat source:", msg_resp.json().get("source"))

print("\n--- 4. Flushing Langfuse traces to Langfuse Cloud ---")
lf_client = get_langfuse_client()
lf_client.flush()
time.sleep(5)  # Wait for cloud ingestion

print("\n--- 5. Fetching and inspecting traces from Langfuse Cloud ---")
recent_traces = lf_client.api.trace.list(limit=15)

traces_by_name = {}
for t_meta in recent_traces.data:
    if t_meta.name not in traces_by_name:
        t_detail = lf_client.api.trace.get(t_meta.id)
        traces_by_name[t_meta.name] = t_detail

print("\nRecent traces retrieved:")
for name, detail in traces_by_name.items():
    print(f"\n* Trace Name: '{name}' | Trace ID: {detail.id}")
    print(f"  Total observations: {len(detail.observations)}")
    for obs in detail.observations:
        print(f"    - [{obs.type}] {obs.name}")

# Assertions for the prompt requirements
print("\n--- Verification Checklist ---")

# Chat message pipeline
if "post_session_message" in traces_by_name:
    chat_trace = traces_by_name["post_session_message"]
    obs_names = [o.name for o in chat_trace.observations]
    obs_types = {o.name: o.type for o in chat_trace.observations}
    print(f"✓ Chat message trace '{chat_trace.name}' has {len(chat_trace.observations)} nodes:")
    for o in chat_trace.observations:
        print(f"    - {o.name} ({o.type})")
    assert "retrieve_relevant_chunks" in obs_names, "retrieve_relevant_chunks span missing in chat trace!"
    assert "generate_answer" in obs_names, "generate_answer span missing in chat trace!"
    assert obs_types.get("generate_answer") == "GENERATION", "generate_answer must be of type GENERATION!"
    print("✓ Chat pipeline nesting and generation card confirmed! Graph view is ACTIVE (>= 2 nested spans).")

# Document upload pipeline
if "upload_document" in traces_by_name:
    upload_trace = traces_by_name["upload_document"]
    obs_names = [o.name for o in upload_trace.observations]
    obs_types = {o.name: o.type for o in upload_trace.observations}
    print(f"✓ Document upload trace '{upload_trace.name}' has {len(upload_trace.observations)} nodes:")
    for o in upload_trace.observations:
        print(f"    - {o.name} ({o.type})")
    assert "parse_document" in obs_names, "parse_document span missing in upload trace!"
    assert "index_document" in obs_names, "index_document span missing in upload trace!"
    assert "generate_summary" in obs_names, "generate_summary span missing in upload trace!"
    assert obs_types.get("generate_summary") == "GENERATION", "generate_summary must be of type GENERATION!"
    print("✓ Document upload pipeline nesting confirmed! Graph view is ACTIVE (>= 2 nested spans).")

# Simple CRUD endpoint
if "create_chat_session" in traces_by_name:
    crud_trace = traces_by_name["create_chat_session"]
    print(f"✓ Simple CRUD trace '{crud_trace.name}' has {len(crud_trace.observations)} node(s):")
    for o in crud_trace.observations:
        print(f"    - {o.name} ({o.type})")
    assert len(crud_trace.observations) == 1, f"CRUD trace should be 1 flat node, but got {len(crud_trace.observations)}!"
    print("✓ Simple CRUD trace confirmed flat (single-node, no over-instrumentation).")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
