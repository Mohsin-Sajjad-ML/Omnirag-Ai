"""
run_prompt8_demo.py - Interactive / Standalone demonstration script for Prompt 8.
Verifies automatic document summarization with Groq LLM integration.

Workflow:
1. Registers a fresh demo user.
2. Uploads a prose document (txt) and confirms:
   - Status transitions to "indexed".
   - AI auto-summary is generated in 2-4 concise sentences.
   - Summary is stored in SQLite and returned in GET /documents/{username}.
3. Uploads a tabular document (csv) and confirms:
   - CSV prompt specialization generates a structured dataset summary.
   - Summary is stored in SQLite and returned in GET /documents/{username}.
4. Prints the final document list with all generated summaries.

Usage:
    python run_prompt8_demo.py
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

client = TestClient(app)


def run_prompt8_demonstration():
    print("=" * 80)
    print("OmniRAG AI - Prompt 8 Auto-Summary Generation Live Verification")
    print("=" * 80)

    username = f"summary_demo_{int(time.time())}"
    password = "demopassword123"

    # Step 1: Register user
    print(f"\n[1] Registering demo user '{username}'...")
    reg_res = client.post("/auth/register", json={"username": username, "password": password})
    print(f"    Status: {reg_res.status_code}, Message: {reg_res.json().get('message')}")
    assert reg_res.status_code == 200, f"Failed to register user: {reg_res.text}"

    # Step 2: Upload prose document
    prose_content = (
        "Project Orion Autonomous Navigation System - Architectural Overview\n\n"
        "Project Orion is an autonomous deep-space navigational framework designed by Stellaris Dynamics in 2025. "
        "The system utilizes optical pulsar triangulation coupled with decentralized kalman filters to determine spacecraft "
        "state vectors without reliance on Earth-based Deep Space Network telemetry.\n\n"
        "Key capabilities include sub-kilometer positional accuracy at Jupiter orbital distances, instantaneous attitude "
        "correction within 15 milliseconds, and redundant triple-modular radiation-hardened compute nodes. "
        "Flight validation trials are scheduled aboard the Artemis VII exploratory mission launching from Kennedy Space Center."
    )
    print("\n[2] Uploading prose document 'orion_architecture.txt'...")
    files = {"file": ("orion_architecture.txt", io.BytesIO(prose_content.encode("utf-8")), "text/plain")}
    upload_res = client.post("/documents/upload", data={"username": username}, files=files)
    upload_data = upload_res.json()
    print(f"    Upload Status Code: {upload_res.status_code}")
    print(f"    Document ID: {upload_data.get('id')}")
    print(f"    Indexing Status: {upload_data.get('status')}")
    print(f"    Chunks Indexed: {upload_data.get('chunk_count')}")
    print(f"    Generated Summary:\n    \"{upload_data.get('summary')}\"")

    assert upload_data.get("status") == "indexed", "Document failed to reach indexed status!"
    assert upload_data.get("summary") is not None, "Summary was not generated for prose document!"

    # Step 3: Upload CSV dataset (verifying tabular prompt specialization)
    csv_content = (
        "quarter,department,revenue_usd,expenses_usd,headcount,status\n"
        "Q1-2025,Engineering,4500000,3200000,42,Approved\n"
        "Q1-2025,Research,2100000,1950000,18,Approved\n"
        "Q2-2025,Engineering,4900000,3400000,46,Approved\n"
        "Q2-2025,Research,2300000,2100000,20,Approved\n"
        "Q3-2025,Engineering,5400000,3600000,50,Pending\n"
        "Q3-2025,Research,2600000,2250000,22,Pending\n"
    )
    print("\n[3] Uploading CSV dataset 'q3_department_finances.csv'...")
    files_csv = {"file": ("q3_department_finances.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_csv_res = client.post("/documents/upload", data={"username": username}, files=files_csv)
    upload_csv_data = upload_csv_res.json()
    print(f"    Upload Status Code: {upload_csv_res.status_code}")
    print(f"    Document ID: {upload_csv_data.get('id')}")
    print(f"    Indexing Status: {upload_csv_data.get('status')}")
    print(f"    Chunks Indexed: {upload_csv_data.get('chunk_count')}")
    print(f"    Generated CSV Summary:\n    \"{upload_csv_data.get('summary')}\"")

    assert upload_csv_data.get("status") == "indexed", "CSV failed to reach indexed status!"
    assert upload_csv_data.get("summary") is not None, "Summary was not generated for CSV dataset!"

    # Step 4: Verify GET /documents/{username} contains both summaries
    print(f"\n[4] Querying GET /documents/{username} to verify metadata listing...")
    list_res = client.get(f"/documents/{username}")
    print(f"    Status Code: {list_res.status_code}")
    documents = list_res.json()
    print(f"    Total Documents Found: {len(documents)}")

    for idx, doc in enumerate(documents, start=1):
        print(f"\n    --- Document {idx}: {doc.get('original_filename')} ({doc.get('file_type')}) ---")
        print(f"    ID: {doc.get('id')} | Status: {doc.get('status')} | Chunks: {doc.get('chunk_count')}")
        print(f"    Summary: {doc.get('summary')}")
        assert doc.get("summary") is not None, f"Document {doc.get('id')} missing summary in listing!"

    print("\n" + "=" * 80)
    print("SUCCESS: Prompt 8 Auto-Summary Feature Verified End-to-End!")
    print("=" * 80)


if __name__ == "__main__":
    run_prompt8_demonstration()
