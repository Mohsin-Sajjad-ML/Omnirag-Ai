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
        "session_id": "mock_sess_trace_test",
        "claims": {"sub": test_user_id}
    }

app.dependency_overrides[get_current_clerk_user] = mock_get_current_user
client = TestClient(app)

print("=" * 70)
print("  OMNIRAG AI: LANGFUSE RENAMED TRACES & PIPELINE VERIFICATION")
print("=" * 70)

# 1. Document Upload Trace (document-ingest)
print("\n--- 1. Testing Document Upload Flow (document-ingest) ---")
doc_content = (
    "OmniRAG Remote Work Security Protocol:\n"
    "All engineers connecting to internal production clusters must utilize zero-trust wireguard VPN.\n"
    "Multi-factor authentication (MFA) hardware security keys are mandatory for cloud console access.\n"
    "Data exports exceeding 50MB require dual managerial approval in the security ticketing system."
)
files = {
    "file": ("remote_work_security_protocol.txt", doc_content.encode("utf-8"), "text/plain")
}
upload_resp = client.post("/documents/upload", files=files)
print("Upload status:", upload_resp.status_code)
assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
uploaded_doc_id = upload_resp.json().get("id")
print(f"Uploaded Document ID: {uploaded_doc_id}")

# 2. Chat Session Creation
sess_resp = client.post("/chat/sessions", json={})
assert sess_resp.status_code == 201
session_id = sess_resp.json().get("session_id") or sess_resp.json().get("id")
print(f"Created Test Chat Session ID: {session_id}")

# 3. Chat Request with RAG Enabled
print("\n--- 2. Testing Chat Message with RAG Enabled (chat-request -> embedding -> retrieval -> mode-selected -> rag-answer -> chat-completed) ---")
rag_msg_resp = client.post(
    f"/chat/sessions/{session_id}/message",
    json={
        "query": "What hardware keys are mandatory for cloud console access according to the protocol?",
        "rag_enabled": True,
        "web_search_enabled": False,
        "document_ids": [uploaded_doc_id] if uploaded_doc_id else None,
    }
)
print("RAG Chat message status:", rag_msg_resp.status_code)
assert rag_msg_resp.status_code == 200
rag_data = rag_msg_resp.json()
print("RAG Answer:", rag_data.get("answer"))
print("RAG Source:", rag_data.get("source"))

# 4. Chat Request with Fallback (RAG and Web Search disabled -> general-answer)
print("\n--- 3. Testing Chat Message Fallback (embedding & retrieval skipped) ---")
fallback_msg_resp = client.post(
    f"/chat/sessions/{session_id}/message",
    json={
        "query": "What is Python?",
        "rag_enabled": False,
        "web_search_enabled": False,
    }
)
print("Fallback Chat message status:", fallback_msg_resp.status_code)
assert fallback_msg_resp.status_code == 200
fallback_data = fallback_msg_resp.json()
print("Fallback Answer preview:", (fallback_data.get("answer") or "")[:80] + "...")
print("Fallback Source:", fallback_data.get("source"))

# 5. Flush traces to Langfuse
print("\n--- 4. Flushing Langfuse Traces ---")
lf_client = get_langfuse_client()
lf_client.flush()
print("Flushed! Waiting 10s for cloud ingestion...")
time.sleep(10)

# 6. Retrieve recent traces
print("\n--- 5. Inspecting Traces in Langfuse Cloud ---")
recent_traces = lf_client.api.trace.list(limit=60)

traces_by_id = {}
for t_meta in recent_traces.data:
    traces_by_id[t_meta.id] = lf_client.api.trace.get(t_meta.id)

print(f"Retrieved {len(traces_by_id)} recent traces from Langfuse.")

# Group traces by name
traces_by_name = {}
for t_id, detail in traces_by_id.items():
    if detail.name not in traces_by_name:
        traces_by_name[detail.name] = []
    traces_by_name[detail.name].append(detail)

for name, trace_list in traces_by_name.items():
    print(f"\nTrace Category: '{name}' ({len(trace_list)} trace(s)):")
    for t in trace_list[:2]:  # show up to 2 latest
        obs_names = [f"{o.name} ({o.type})" for o in t.observations]
        print(f"  ID: {t.id} | Nodes: {obs_names}")

# Verifications
print("\n--- 6. Running Trace Structure Assertions ---")

# Check Document Ingest
assert "document-ingest" in traces_by_name, "document-ingest trace not found in Langfuse!"
latest_doc_trace = traces_by_name["document-ingest"][0]
doc_obs = {o.name: o for o in latest_doc_trace.observations}
print(f"✓ Latest 'document-ingest' trace found with {len(latest_doc_trace.observations)} nodes:")
for o in latest_doc_trace.observations:
    model_str = f" [model: {getattr(o, 'model', None)}]" if getattr(o, 'model', None) else ""
    print(f"    - [{o.type}] {o.name}{model_str}")

assert "extract-text" in doc_obs, "Missing 'extract-text' span in document-ingest trace"
assert "chunking" in doc_obs, "Missing 'chunking' span in document-ingest trace"
assert "index-write" in doc_obs, "Missing 'index-write' span in document-ingest trace"
assert "generate-summary" in doc_obs, "Missing 'generate-summary' generation span in document-ingest trace"
assert doc_obs["generate-summary"].type == "GENERATION", "'generate-summary' must be of type GENERATION"
print("✓ Document upload trace fully verified with correct hyphenated spans!")

# Check Chat Request
assert "chat-request" in traces_by_name, "chat-request trace not found in Langfuse!"
chat_traces = traces_by_name["chat-request"]
print(f"✓ Found {len(chat_traces)} 'chat-request' traces.")

# Distinguish RAG trace from Fallback trace
rag_chat_trace = None
fallback_chat_trace = None

for t in chat_traces:
    names = [o.name for o in t.observations]
    if "rag-answer" in names and rag_chat_trace is None:
        rag_chat_trace = t
    elif "general-answer" in names and fallback_chat_trace is None:
        fallback_chat_trace = t

assert rag_chat_trace is not None, "Could not find a chat-request trace containing 'rag-answer'"
rag_obs = {o.name: o for o in rag_chat_trace.observations}
print(f"\n✓ RAG chat-request trace ({rag_chat_trace.id}):")
for o in rag_chat_trace.observations:
    model_str = f" [model: {getattr(o, 'model', None)}]" if getattr(o, 'model', None) else ""
    print(f"    - [{o.type}] {o.name}{model_str}")

assert "embedding" in rag_obs, "Missing 'embedding' span in RAG chat trace"
assert "retrieval" in rag_obs, "Missing 'retrieval' span in RAG chat trace"
assert "mode-selected" in rag_obs, "Missing 'mode-selected' span in RAG chat trace"
assert "rag-answer" in rag_obs, "Missing 'rag-answer' generation span in RAG chat trace"
assert rag_obs["rag-answer"].type == "GENERATION", "'rag-answer' must be of type GENERATION"
assert "chat-completed" in rag_obs, "Missing 'chat-completed' span in RAG chat trace"
print("✓ RAG chat trace hierarchy and span names confirmed!")

assert fallback_chat_trace is not None, "Could not find a chat-request trace containing 'general-answer'"
fb_names = [o.name for o in fallback_chat_trace.observations]
print(f"\n✓ Fallback chat-request trace ({fallback_chat_trace.id}):")
for o in fallback_chat_trace.observations:
    model_str = f" [model: {getattr(o, 'model', None)}]" if getattr(o, 'model', None) else ""
    print(f"    - [{o.type}] {o.name}{model_str}")

assert "embedding" not in fb_names, "'embedding' must be skipped when RAG is disabled"
assert "retrieval" not in fb_names, "'retrieval' must be skipped when RAG is disabled"
assert "mode-selected" in fb_names, "Missing 'mode-selected' span in Fallback chat trace"
assert "general-answer" in fb_names, "Missing 'general-answer' span in Fallback chat trace"
assert "chat-completed" in fb_names, "Missing 'chat-completed' span in Fallback chat trace"
print("✓ Fallback chat trace confirms conditional absence of 'embedding' and 'retrieval'!")

print("\n" + "=" * 70)
print("  ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
print("=" * 70)
