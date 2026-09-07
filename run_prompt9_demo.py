import io
import requests

BASE_URL = "http://127.0.0.1:8000"
username = "p9_verify_user"

print("--- 1. Register User ---")
reg_res = requests.post(f"{BASE_URL}/auth/register", json={"username": username, "password": "password123"})
print(f"Register status: {reg_res.status_code}")

print("\n--- 2. Create Session 1 ---")
sess1_res = requests.post(f"{BASE_URL}/chat/sessions", json={"username": username})
assert sess1_res.status_code == 201, sess1_res.text
sess1_data = sess1_res.json()
sess1_id = sess1_data["session_id"]
print(f"Created Session 1: ID={sess1_id}, title={sess1_data['title']}")

print("\n--- 3. Upload Document Mid-Chat ---")
sample_text = (
    "Project Apollo mission guidelines:\n"
    "The launch commander is Neil Armstrong.\n"
    "The lunar module callsign is Eagle.\n"
    "Landing target coordinates are Sea of Tranquility."
)
files = {"file": ("apollo_mission.txt", io.BytesIO(sample_text.encode("utf-8")), "text/plain")}
data = {"username": username}
up_res = requests.post(f"{BASE_URL}/documents/upload", data=data, files=files)
assert up_res.status_code == 200, up_res.text
print(f"Upload status: {up_res.json()['status']}, chunks: {up_res.json()['chunk_count']}")

print("\n--- 4. Ask Question in Session 1 (Answerable) ---")
q1_res = requests.post(
    f"{BASE_URL}/chat/sessions/{sess1_id}/message",
    json={"username": username, "query": "Who is the launch commander and what is the lunar module callsign?"}
)
assert q1_res.status_code == 200, q1_res.text
q1_data = q1_res.json()
print("Answer:", q1_data["answer"])
print("is_fallback:", q1_data["is_fallback"])
print("citations:", q1_data["citations"])
assert not q1_data["is_fallback"]
assert "Neil Armstrong" in q1_data["answer"] or "Eagle" in q1_data["answer"]
assert len(q1_data["citations"]) >= 1

print("\n--- 5. Verify Session 1 Title Auto-Generated ---")
sessions_list = requests.get(f"{BASE_URL}/chat/sessions/{username}").json()
print("Sessions list:", sessions_list)
assert len(sessions_list) == 1
assert sessions_list[0]["id"] == sess1_id
assert sessions_list[0]["title"] != "New Chat"
print("Auto-generated title:", sessions_list[0]["title"])

print("\n--- 6. Create Session 2 ---")
sess2_res = requests.post(f"{BASE_URL}/chat/sessions", json={"username": username})
assert sess2_res.status_code == 201
sess2_id = sess2_res.json()["session_id"]
print(f"Created Session 2: ID={sess2_id}")

print("\n--- 7. Ask Unrelated Question in Session 2 ---")
q2_res = requests.post(
    f"{BASE_URL}/chat/sessions/{sess2_id}/message",
    json={"username": username, "query": "What is the capital of Mars?"}
)
assert q2_res.status_code == 200
q2_data = q2_res.json()
print("Answer 2:", q2_data["answer"])
print("is_fallback:", q2_data["is_fallback"])
print("citations:", q2_data["citations"])
assert q2_data["is_fallback"] is True
assert q2_data["citations"] == []

print("\n--- 8. Switch Back to Session 1 & Reload Messages ---")
reload_res = requests.get(f"{BASE_URL}/chat/sessions/{sess1_id}/messages")
assert reload_res.status_code == 200
reloaded_msgs = reload_res.json()
print(f"Reloaded {len(reloaded_msgs)} messages in Session 1:")
for m in reloaded_msgs:
    print(f"  [{m['role'].upper()}]: {m['content'][:50]}... (citations: {len(m.get('citations') or [])})")
assert len(reloaded_msgs) == 2
assert reloaded_msgs[0]["role"] == "user"
assert reloaded_msgs[1]["role"] == "assistant"
assert len(reloaded_msgs[1]["citations"]) >= 1

print("\n--- 9. Delete Session 2 ---")
del_res = requests.delete(f"{BASE_URL}/chat/sessions/{sess2_id}", json={"username": username})
assert del_res.status_code == 200
print("Delete response:", del_res.json())

final_sessions = requests.get(f"{BASE_URL}/chat/sessions/{username}").json()
print(f"Remaining sessions count: {len(final_sessions)} (IDs: {[s['id'] for s in final_sessions]})")
assert len(final_sessions) == 1
assert final_sessions[0]["id"] == sess1_id

print("\n>>> ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY! <<<")
