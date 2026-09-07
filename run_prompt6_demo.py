"""
run_prompt6_demo.py - Interactive / Standalone demonstration script for RAG Query & Formatted Output.

Updated for Prompt 7:
1. Registering a test user.
2. Uploading a document and confirming it reaches "indexed" status in ChromaDB.
3. Submitting an answerable question to POST /chat/query:
   - Verifies is_fallback is False
   - Verifies citations contains grouped source metadata
   - Verifies low_context signal
4. Submitting an unrelated question to POST /chat/query:
   - Verifies is_fallback is True
   - Verifies friendly fallback message is returned (not raw marker)
   - Verifies citations is empty

Usage:
    python run_prompt6_demo.py
"""

import io
import json
import sys
import time

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient

from app.main import app
from app.llm import FALLBACK_MESSAGE

client = TestClient(app)


def run_demonstration():
    print("=" * 80)
    print("OmniRAG AI - Prompt 7 Response Formatting & Citations Verification")
    print("=" * 80)

    username = f"demo_user_{int(time.time())}"
    password = "demopassword123"

    # Step 1: Register user
    print(f"\n[1] Registering user '{username}'...")
    reg_res = client.post("/auth/register", json={"username": username, "password": password})
    print(f"    Status: {reg_res.status_code}, Response: {reg_res.json()}")

    # Step 2: Upload document
    document_text = (
        "Project Titan Aerospace Specifications:\n"
        "Titan-X is an autonomous high-altitude drone developed by AeroCorp in 2024.\n"
        "It features a wingspan of 35 meters and is powered by dual hydrogen fuel cells.\n"
        "The primary mission commander is Dr. Marcus Vance, operating out of Denver Base Alpha.\n"
        "Titan-X has a maximum ceiling altitude of 65,000 feet."
    )
    print("\n[2] Uploading document 'titan_specs.txt'...")
    files = {"file": ("titan_specs.txt", io.BytesIO(document_text.encode("utf-8")), "text/plain")}
    upload_res = client.post("/documents/upload", data={"username": username}, files=files)
    upload_data = upload_res.json()
    print(f"    Status: {upload_res.status_code}")
    print(f"    Document ID: {upload_data.get('id')}")
    print(f"    Document Status: {upload_data.get('status')}")
    print(f"    Chunks Indexed: {upload_data.get('chunk_count')}")

    assert upload_data.get("status") == "indexed", "Document failed to reach 'indexed' status!"

    # Step 3: Question answerable from the document
    q1 = "Who is the primary mission commander of Titan-X and what is its maximum ceiling altitude?"
    print(f"\n[3] Query 1 (Answerable from document):")
    print(f"    Question: \"{q1}\"")

    q1_res = client.post("/chat/query", json={"username": username, "query": q1})
    q1_data = q1_res.json()
    print(f"    HTTP Status: {q1_res.status_code}")
    print(f"    Answer: {q1_data.get('answer')}")
    print(f"    Is Fallback: {q1_data.get('is_fallback')}")
    print(f"    Citations: {json.dumps(q1_data.get('citations'), indent=2)}")
    print(f"    Low Context: {q1_data.get('low_context')}")

    assert q1_data.get("is_fallback") is False, "Expected is_fallback to be False for answerable question!"
    assert len(q1_data.get("citations", [])) > 0, "Expected non-empty citations list!"
    assert "Dr. Marcus Vance" in q1_data.get("answer", ""), "Expected factual answer!"

    # Step 4: Question completely unrelated to the document
    q2 = "What ingredients are needed to bake a New York cheesecake?"
    print(f"\n[4] Query 2 (Completely unrelated to document):")
    print(f"    Question: \"{q2}\"")

    q2_res = client.post("/chat/query", json={"username": username, "query": q2})
    q2_data = q2_res.json()
    print(f"    HTTP Status: {q2_res.status_code}")
    print(f"    Answer: {q2_data.get('answer')}")
    print(f"    Is Fallback: {q2_data.get('is_fallback')}")
    print(f"    Citations: {json.dumps(q2_data.get('citations'), indent=2)}")
    print(f"    Low Context: {q2_data.get('low_context')}")

    assert q2_data.get("is_fallback") is True, "Expected is_fallback to be True for unrelated question!"
    assert q2_data.get("answer") == FALLBACK_MESSAGE, f"Expected friendly fallback message, got '{q2_data.get('answer')}'"
    assert q2_data.get("citations") == [], "Expected empty citations list when is_fallback is True!"
    assert q2_data.get("low_context") is False, "Expected low_context to be False on fallback!"

    print("\n" + "=" * 80)
    print("SUCCESS: Both answerable and fallback queries formatted cleanly as expected!")
    print("=" * 80)


if __name__ == "__main__":
    run_demonstration()
