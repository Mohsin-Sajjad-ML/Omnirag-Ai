import io
import sys
import time
import json
import docx
import requests

BASE_URL = "http://127.0.0.1:8000"
ts = int(time.time())

print("=================================================================")
print("  OMNIRAG AI: PROMPT 11 END-TO-END VERIFICATION PASS")
print("=================================================================")

# -------------------------------------------------------------------
# 1. AUTHENTICATION FLOWS
# -------------------------------------------------------------------
print("\n[SECTION 1: AUTHENTICATION FLOWS]")

# 1.1 Register user 1 (Password only) & login
u1 = f"p11_user1_{ts}"
r1 = requests.post(f"{BASE_URL}/auth/register", json={"username": u1, "password": "Password123!"})
assert r1.status_code == 200, f"Registration failed: {r1.text}"
print(f"✓ 1.1 Registered user '{u1}' (password only)")

r1_login = requests.post(f"{BASE_URL}/auth/login/password", json={"username": u1, "password": "Password123!"})
assert r1_login.status_code == 200 and r1_login.json()["username"] == u1
print("✓ 1.1 Confirmed password login succeeds")

# 1.2 Register user 2 with face registration & confirm face login
u2 = f"p11_user2_{ts}"
r2 = requests.post(f"{BASE_URL}/auth/register", json={"username": u2, "password": "Password123!"})
assert r2.status_code == 200

# Generate distinct 128D face descriptor
face_vector_u2 = [0.08 * ((i % 7) - 3) for i in range(128)]
r2_face_reg = requests.post(f"{BASE_URL}/auth/register-face", json={"username": u2, "face_descriptor": face_vector_u2})
assert r2_face_reg.status_code == 200
print(f"✓ 1.2 Registered user '{u2}' with 128D biometric face descriptor")

r2_face_login = requests.post(f"{BASE_URL}/auth/login/face", json={"face_descriptor": face_vector_u2})
assert r2_face_login.status_code == 200
assert r2_face_login.json()["username"] == u2
print("✓ 1.2 Confirmed face login succeeds and matches user 2")

# 1.3 Attempt face login with unknown face / no face match
unknown_face = [0.85 for _ in range(128)]
r_unknown = requests.post(f"{BASE_URL}/auth/login/face", json={"face_descriptor": unknown_face})
assert r_unknown.status_code == 401
assert "Face not recognized" in r_unknown.json()["detail"]
print("✓ 1.3 Confirmed unknown face vector is rejected with 401 'Face not recognized'")

# 1.4 Attempt password login with wrong password
r_wrong_pwd = requests.post(f"{BASE_URL}/auth/login/password", json={"username": u1, "password": "IncorrectPassword!"})
assert r_wrong_pwd.status_code == 401
assert r_wrong_pwd.json()["detail"] == "Invalid username or password"
print("✓ 1.4 Confirmed wrong password returns generic 401 'Invalid username or password'")

# 1.5 Add/Update Face requires correct password
r_update_wrong = requests.post(
    f"{BASE_URL}/auth/add-face",
    json={"username": u1, "password": "WrongPassword!", "face_descriptor": face_vector_u2}
)
assert r_update_wrong.status_code == 401
assert r_update_wrong.json()["detail"] == "Invalid password"
print("✓ 1.5 Confirmed Add/Update Face with wrong password rejected (401 'Invalid password')")

r_update_correct = requests.post(
    f"{BASE_URL}/auth/add-face",
    json={"username": u1, "password": "Password123!", "face_descriptor": face_vector_u2}
)
assert r_update_correct.status_code == 200
print("✓ 1.5 Confirmed Add/Update Face with correct password succeeds")

# -------------------------------------------------------------------
# 2. DOCUMENT INGESTION & PIPELINE FLOWS
# -------------------------------------------------------------------
print("\n[SECTION 2: DOCUMENT INGESTION FLOWS]")

# 2.1 Upload all 4 supported types (PDF, DOCX, TXT, CSV)
txt_content = (
    "Aerospace Systems Document: Jet Engine Dynamics.\n"
    "The maximum cruise thrust of the Turbofan-900 is 42000 Newtons.\n"
    "The bypass ratio is 10 to 1, delivering optimal fuel efficiency during high altitude transit."
)
r_up_txt = requests.post(
    f"{BASE_URL}/documents/upload",
    data={"username": u1},
    files={"file": ("turbofan_specs.txt", io.BytesIO(txt_content.encode("utf-8")), "text/plain")}
).json()
assert r_up_txt["status"] == "indexed"
assert r_up_txt["chunk_count"] >= 1
assert r_up_txt["summary"] and len(r_up_txt["summary"]) > 0
doc_txt_id = r_up_txt["id"]
print(f"✓ 2.1 TXT uploaded: id={doc_txt_id}, chunk_count={r_up_txt['chunk_count']}, summary generated")

csv_content = (
    "PartID,PartName,Material,TensileStrengthMPa\n"
    "P-01,Turbine Blade,Titanium Alloy,950\n"
    "P-02,Compressor Disk,Nickel Superalloy,1150\n"
    "P-03,Exhaust Nozzle,Inconel 718,1240\n"
)
r_up_csv = requests.post(
    f"{BASE_URL}/documents/upload",
    data={"username": u1},
    files={"file": ("materials.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
).json()
assert r_up_csv["status"] == "indexed"
assert r_up_csv["chunk_count"] >= 1
assert r_up_csv["summary"] and len(r_up_csv["summary"]) > 0
doc_csv_id = r_up_csv["id"]
print(f"✓ 2.1 CSV uploaded: id={doc_csv_id}, chunk_count={r_up_csv['chunk_count']}, summary generated")

doc_obj = docx.Document()
doc_obj.add_heading("Avionics Architecture Standard", 0)
doc_obj.add_paragraph("The primary flight control computers communicate via MIL-STD-1553B data bus.")
doc_obj.add_paragraph("Dual redundant optical sensors monitor hydraulic pressure at 50 millisecond intervals.")
docx_io = io.BytesIO()
doc_obj.save(docx_io)
docx_io.seek(0)
r_up_docx = requests.post(
    f"{BASE_URL}/documents/upload",
    data={"username": u1},
    files={"file": ("avionics.docx", docx_io, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
).json()
assert r_up_docx["status"] == "indexed"
assert r_up_docx["chunk_count"] >= 1
assert r_up_docx["summary"] and len(r_up_docx["summary"]) > 0
doc_docx_id = r_up_docx["id"]
print(f"✓ 2.1 DOCX uploaded: id={doc_docx_id}, chunk_count={r_up_docx['chunk_count']}, summary generated")

MINIMAL_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 300 144]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 76>>stream\n"
    b"BT /F1 14 Tf 20 100 Td (Hydraulic reservoir capacity is strictly 18.5 liters per system) Tj ET\n"
    b"endstream\n"
    b"endobj\n"
    b"xref\n"
    b"0 6\n"
    b"0000000000 65535 f \n"
    b"0000000010 00000 n \n"
    b"0000000060 00000 n \n"
    b"0000000117 00000 n \n"
    b"0000000224 00000 n \n"
    b"0000000293 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n"
    b"418\n"
    b"%%EOF\n"
)
r_up_pdf = requests.post(
    f"{BASE_URL}/documents/upload",
    data={"username": u1},
    files={"file": ("hydraulics.pdf", io.BytesIO(MINIMAL_PDF_BYTES), "application/pdf")}
).json()
assert r_up_pdf["status"] == "indexed"
assert r_up_pdf["chunk_count"] >= 1
assert r_up_pdf["summary"] and len(r_up_pdf["summary"]) > 0
doc_pdf_id = r_up_pdf["id"]
print(f"✓ 2.1 PDF uploaded: id={doc_pdf_id}, chunk_count={r_up_pdf['chunk_count']}, summary generated")

# 2.2 Unsupported file types (.exe, .zip)
r_bad_exe = requests.post(
    f"{BASE_URL}/documents/upload",
    data={"username": u1},
    files={"file": ("script.exe", io.BytesIO(b"MZtest"), "application/x-msdownload")}
)
assert r_bad_exe.status_code == 400
assert "Unsupported file type" in r_bad_exe.json()["detail"]
print("✓ 2.2 Unsupported file type (.exe) rejected with 400 Bad Request")

# 2.3 File over 50MB rejected
class Mock51MBStream(io.RawIOBase):
    def __init__(self, limit):
        self.limit = limit
        self.read_so_far = 0
    def readinto(self, b):
        rem = self.limit - self.read_so_far
        if rem <= 0: return 0
        n = min(len(b), rem)
        b[:n] = b"X" * n
        self.read_so_far += n
        return n

r_oversize = requests.post(
    f"{BASE_URL}/documents/upload",
    data={"username": u1},
    files={"file": ("huge.txt", Mock51MBStream(51 * 1024 * 1024), "text/plain")}
)
assert r_oversize.status_code == 400
assert "50MB limit" in r_oversize.json()["detail"]
print("✓ 2.3 File exceeding 50MB rejected with 400 Bad Request")

# 2.4 Corrupted/empty files fail gracefully with status="failed" and error_message
r_empty = requests.post(
    f"{BASE_URL}/documents/upload",
    data={"username": u1},
    files={"file": ("empty.txt", io.BytesIO(b"   "), "text/plain")}
).json()
assert r_empty["status"] == "failed"
assert r_empty["chunk_count"] == 0
assert "empty" in r_empty["error_message"].lower()
print(f"✓ 2.4 Empty file handled gracefully: status='{r_empty['status']}', error='{r_empty['error_message']}'")

r_corrupt = requests.post(
    f"{BASE_URL}/documents/upload",
    data={"username": u1},
    files={"file": ("broken.pdf", io.BytesIO(b"%PDF-1.4 garbage header only"), "application/pdf")}
).json()
assert r_corrupt["status"] == "failed"
assert r_corrupt["chunk_count"] == 0
assert r_corrupt["error_message"] is not None
print(f"✓ 2.4 Corrupted file handled gracefully: status='{r_corrupt['status']}', error populated")

# -------------------------------------------------------------------
# 3. CHAT, GROUNDED RAG, CITATIONS & SESSIONS
# -------------------------------------------------------------------
print("\n[SECTION 3: CHAT, GROUNDED RAG & CITATIONS]")

# 3.1 Session 1 creation & answerable query
s1 = requests.post(f"{BASE_URL}/chat/sessions", json={"username": u1}).json()
s1_id = s1["session_id"]
print(f"✓ 3.1 Created Chat Session 1 (id={s1_id})")

q_grounded = "What is the maximum cruise thrust of the Turbofan-900?"
ans1 = requests.post(
    f"{BASE_URL}/chat/sessions/{s1_id}/message",
    json={"username": u1, "query": q_grounded}
).json()
assert not ans1["is_fallback"], f"Expected grounded answer, got fallback: {ans1}"
assert "42000" in ans1["answer"] or "42,000" in ans1["answer"]
assert len(ans1["citations"]) >= 1
assert any("turbofan_specs.txt" in c["filename"] for c in ans1["citations"])
print(f"✓ 3.1 Answerable question grounded: '{ans1['answer']}' with citation {ans1['citations'][0]['filename']}")

# 3.2 Unrelated query triggers fallback
q_unrelated = "What is the average rainfall in the Amazon rainforest in 2020?"
ans_fallback = requests.post(
    f"{BASE_URL}/chat/sessions/{s1_id}/message",
    json={"username": u1, "query": q_unrelated}
).json()
assert ans_fallback["is_fallback"] is True
assert len(ans_fallback["citations"]) == 0
print(f"✓ 3.2 Unrelated question cleanly triggered fallback: is_fallback=True, citations={ans_fallback['citations']}")

# 3.3 Create Session 2 & verify message history isolation
s2 = requests.post(f"{BASE_URL}/chat/sessions", json={"username": u1}).json()
s2_id = s2["session_id"]

q_s2 = "What material is used for the Compressor Disk?"
ans_s2 = requests.post(
    f"{BASE_URL}/chat/sessions/{s2_id}/message",
    json={"username": u1, "query": q_s2}
).json()
assert not ans_s2["is_fallback"]
assert "Nickel" in ans_s2["answer"]

# Verify message counts
msgs_s1 = requests.get(f"{BASE_URL}/chat/sessions/{s1_id}/messages").json()
msgs_s2 = requests.get(f"{BASE_URL}/chat/sessions/{s2_id}/messages").json()
assert len(msgs_s1) == 4, f"Expected 4 messages in S1, got {len(msgs_s1)}"
assert len(msgs_s2) == 2, f"Expected 2 messages in S2, got {len(msgs_s2)}"
print(f"✓ 3.3 Session history strictly isolated: Session 1 has {len(msgs_s1)} msgs, Session 2 has {len(msgs_s2)} msgs")

# 3.4 Document selector scope filtering
# When scoped strictly to doc_txt_id (turbofan), asking about compressor disk (which is in csv) should fall back
ans_scope_mismatch = requests.post(
    f"{BASE_URL}/chat/sessions/{s2_id}/message",
    json={"username": u1, "query": "What material is used for the Compressor Disk?", "document_ids": [doc_txt_id]}
).json()
assert ans_scope_mismatch["is_fallback"] is True
print("✓ 3.4 Scoped query to wrong document resulted in fallback as expected")

# When scoped strictly to doc_csv_id (materials.csv), it succeeds with ONLY materials.csv in citations
ans_scope_match = requests.post(
    f"{BASE_URL}/chat/sessions/{s2_id}/message",
    json={"username": u1, "query": "What material is used for the Compressor Disk?", "document_ids": [doc_csv_id]}
).json()
assert not ans_scope_match["is_fallback"]
assert len(ans_scope_match["citations"]) == 1
assert ans_scope_match["citations"][0]["filename"] == "materials.csv"
print("✓ 3.4 Scoped query to target document returned strictly scoped citation: 'materials.csv'")

# 3.5 Session deletion & cascade
r_del = requests.delete(f"{BASE_URL}/chat/sessions/{s1_id}?username={u1}")
assert r_del.status_code == 200
active_sessions = requests.get(f"{BASE_URL}/chat/sessions/{u1}").json()
assert all(s["id"] != s1_id for s in active_sessions)
assert requests.get(f"{BASE_URL}/chat/sessions/{s1_id}/messages").status_code == 404
print(f"✓ 3.5 Deleted Session 1: verified removed from sessions list and messages returned 404")

# -------------------------------------------------------------------
# 4. PERSONALIZATION & MULTI-TENANT ISOLATION
# -------------------------------------------------------------------
print("\n[SECTION 4: PERSONALIZATION & MULTI-TENANT ISOLATION]")

# User 1 has remaining session s2 and 4 uploaded documents
u1_sessions = requests.get(f"{BASE_URL}/chat/sessions/{u1}").json()
u1_docs = requests.get(f"{BASE_URL}/documents/{u1}").json()
assert len(u1_sessions) >= 1
assert len(u1_docs) >= 4
print(f"✓ 4.1 Returning User 1 '{u1}' auto-loads {len(u1_sessions)} session(s) and {len(u1_docs)} document(s)")

# User 2 has 0 sessions and 0 documents
u2_sessions = requests.get(f"{BASE_URL}/chat/sessions/{u2}").json()
u2_docs = requests.get(f"{BASE_URL}/documents/{u2}").json()
assert len(u2_sessions) == 0
assert len(u2_docs) == 0
print(f"✓ 4.2 Switched to User 2 '{u2}': verified 0 sessions, 0 documents (zero data bleed from User 1)")

print("\n=================================================================")
print("  ALL END-TO-END REGRESSION PASSES COMPLETED SUCCESSFULLY!")
print("=================================================================")
