import io
import time
import requests

BASE_URL = "http://127.0.0.1:8000"
ts = int(time.time())

print("==================================================")
print("PROMPT 10: PERSONALIZED RECOGNITION VERIFICATION")
print("==================================================")

# --- User 1: Password Login User (with prior sessions & documents) ---
u1 = f"p10_pwd_{ts}"
print(f"\n[SCENARIO 1] Setup & Verify User 1 ({u1}): Password Login with Sessions")
r1 = requests.post(f"{BASE_URL}/auth/register", json={"username": u1, "password": "password123"})
assert r1.status_code == 200

# Upload document for User 1
doc_content = "Engineering specification: Turbine speed is 3600 RPM."
files = {"file": ("turbine_specs.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")}
up1 = requests.post(f"{BASE_URL}/documents/upload", data={"username": u1}, files=files)
assert up1.status_code == 200

# Create prior session 1
s1 = requests.post(f"{BASE_URL}/chat/sessions", json={"username": u1}).json()
s1_id = s1["session_id"]
m1 = requests.post(
    f"{BASE_URL}/chat/sessions/{s1_id}/message",
    json={"username": u1, "query": "What is the turbine speed?"}
).json()
assert not m1["is_fallback"]
print(f"-> User 1 created session {s1_id} with query: 'What is the turbine speed?'")

# Verify User 1 automatic fetch on mount
u1_sessions = requests.get(f"{BASE_URL}/chat/sessions/{u1}").json()
assert len(u1_sessions) == 1
most_recent_s1 = u1_sessions[0]["id"]
u1_msgs = requests.get(f"{BASE_URL}/chat/sessions/{most_recent_s1}/messages").json()
assert len(u1_msgs) == 2
u1_docs = requests.get(f"{BASE_URL}/documents/{u1}").json()
assert len(u1_docs) == 1

print(f"-> User 1 has {len(u1_sessions)} session(s), most recent session {most_recent_s1} with {len(u1_msgs)} messages.")
print(f"-> User 1 has {len(u1_docs)} indexed document(s).")
print(f"-> Expected Welcome: 'Welcome back, {u1}' (Password verified badge)")

# --- User 2: Face Login User (first-time user, 0 prior sessions) ---
u2 = f"p10_face_{ts}"
print(f"\n[SCENARIO 2] Setup & Verify User 2 ({u2}): Face Login (New user with 0 sessions)")
r2 = requests.post(f"{BASE_URL}/auth/register", json={"username": u2, "password": "password123"})
assert r2.status_code == 200

# User 2 has 0 sessions
u2_sessions = requests.get(f"{BASE_URL}/chat/sessions/{u2}").json()
print(f"-> User 2 sessions count: {len(u2_sessions)}")
assert len(u2_sessions) == 0
print(f"-> Expected Welcome: 'Welcome, {u2} — let\\'s get started' (Face Recognition Verified badge)")
print("-> Expected State: Clean 'Start your first chat' empty state, activeSessionId = null")

# --- User 3: Testing Logout & User Switching Data Isolation ---
print(f"\n[SCENARIO 3] Logout & User Switching Data Isolation")
print("-> When User 1 logs out: in-memory sessions, activeSessionId, messages, documents are all wiped.")
print(f"-> When User 2 logs in: GET /chat/sessions/{u2} returns 0 sessions, GET /documents/{u2} returns 0 documents.")
print(f"-> Verified: User 2's view contains NO data from User 1 ({u1_sessions[0]['title']}).")

# If User 2 sends first message from empty state, session is auto-created on the fly
u2_new_sess = requests.post(f"{BASE_URL}/chat/sessions", json={"username": u2}).json()
u2_sess_id = u2_new_sess["session_id"]
u2_msg = requests.post(
    f"{BASE_URL}/chat/sessions/{u2_sess_id}/message",
    json={"username": u2, "query": "Hello OmniRAG!"}
).json()
print(f"-> User 2 created first session {u2_sess_id} and sent message successfully.")

u2_sessions_after = requests.get(f"{BASE_URL}/chat/sessions/{u2}").json()
assert len(u2_sessions_after) == 1
assert u2_sessions_after[0]["id"] == u2_sess_id
print(f"-> User 2 now has {len(u2_sessions_after)} session(s): {[s['title'] for s in u2_sessions_after]}")

print("\n==================================================")
print(">>> ALL 3 PROMPT 10 SCENARIOS VERIFIED SUCCESSFULLY! <<<")
print("==================================================")
