from backend.chat.voice_service import transliterate_urdu_transcript, correct_transcription
from backend.prompts import CORRECTION_SYSTEM_PROMPT, WHISPER_INITIAL_PROMPT
"""
test_voice_fixes.py - Comprehensive verification for OmniRAG AI Voice Features:
1. Fix 1: Whisper transcription normalization & hallucination safety net.
2. Fix 2: Language-aware Text-to-Speech (response_language & speech selection).
3. Fix 3: Voice recording UI cancel/discard button behavior.
"""

import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.auth.dependencies import get_current_clerk_user

from backend.chat.llm_service import (
    classify_language,
    format_response,
    generate_answer,
    ROMAN_URDU_WORDS
)
from backend.main import app
from backend.database.models import ChatMessage, ChatSession, User
from backend.database.connection import SessionLocal


# Setup authenticated test client
@pytest.fixture
def auth_client():
    test_user = {"user_id": "test_voice_user_123", "session_id": "test_sess_123"}
    app.dependency_overrides[get_current_clerk_user] = lambda: test_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_current_clerk_user, None)


# ==============================================================================
# FIX 1: WHISPER TRANSCRIPTION NORMALIZATION TESTS
# ==============================================================================

def test_fix1_correction_system_prompt_content():
    """Verify the correction system prompt matches exact required instructions."""
    assert "The following text is a possibly-incorrect transcription" in CORRECTION_SYSTEM_PROMPT
    assert "Roman Urdu (Urdu written in Latin/English letters, informal style, e.g. 'kya haal hai')" in CORRECTION_SYSTEM_PROMPT
    assert "If the content actually appears to genuinely be English despite being flagged otherwise" in CORRECTION_SYSTEM_PROMPT
    assert "Return ONLY the corrected text in the appropriate language, nothing else — no explanation." in CORRECTION_SYSTEM_PROMPT


def test_fix1_fast_path_english_bypasses_llm():
    """When Whisper detects 'en' or 'english', fast-path returns unchanged with no LLM call."""
    mock_client = MagicMock()

    transcript = "How many employees are in the engineering department?"
    result_text, final_lang = correct_transcription(transcript, detected_language="en", groq_client=mock_client)

    assert result_text == transcript
    assert final_lang == "en"
    mock_client.chat.completions.create.assert_not_called()

    # Case insensitive
    result_text2, final_lang2 = correct_transcription("Hello world", detected_language="ENGLISH", groq_client=mock_client)
    assert result_text2 == "Hello world"
    assert final_lang2 == "en"
    mock_client.chat.completions.create.assert_not_called()


def test_fix1_urdu_detection_normalizes_to_roman_urdu():
    """When Whisper detects Urdu ('ur'), Groq correction normalizes to Roman Urdu."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        SimpleNamespace(message=SimpleNamespace(content="mujhe engineering department ke baray mein batao"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    raw_urdu_script = "مجھے انجینئرنگ ڈیپارٹمنٹ کے بارے میں بتاؤ"
    result_text, final_lang = correct_transcription(raw_urdu_script, detected_language="ur", groq_client=mock_client)

    assert result_text == "mujhe engineering department ke baray mein batao"
    assert final_lang == "roman-ur"
    assert mock_client.chat.completions.create.call_count == 1
    call_args = mock_client.chat.completions.create.call_args[1]
    assert call_args["messages"][0]["content"] == CORRECTION_SYSTEM_PROMPT
    assert call_args["messages"][1]["content"] == raw_urdu_script


def test_fix1_hallucinated_icelandic_to_english():
    """Whisper hallucinating Icelandic ('is') on genuine English speech recovers clean English."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        SimpleNamespace(message=SimpleNamespace(content="What is the total number of employees?"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    icelandic_hallucination = "Hvað er heildarfjöldi starfsmanna?"
    result_text, final_lang = correct_transcription(icelandic_hallucination, detected_language="is", groq_client=mock_client)

    assert result_text == "What is the total number of employees?"
    assert final_lang == "en"
    assert mock_client.chat.completions.create.call_count == 1


def test_fix1_hallucinated_hindi_devanagari_to_roman_urdu():
    """Whisper producing Hindi/Devanagari ('hi') is normalized to Roman Urdu."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        SimpleNamespace(message=SimpleNamespace(content="kya haal hai"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    devanagari_transcript = "क्या हाल है"
    result_text, final_lang = correct_transcription(devanagari_transcript, detected_language="hi", groq_client=mock_client)

    assert result_text == "kya haal hai"
    assert final_lang == "roman-ur"
    assert mock_client.chat.completions.create.call_count == 1


def test_fix1_endpoint_transcribe_verbose_json_and_response_format(auth_client):
    """POST /chat/transcribe requests verbose_json and returns transcript + detected_final_language."""
    fake_audio_bytes = b"RIFFfakeaudio"

    # Mock Groq Whisper transcription call
    with patch("backend.chat.get_groq_client") as mock_get_client:
        mock_groq = MagicMock()
        mock_get_client.return_value = mock_groq

        # 1. English transcription
        mock_whisper_verbose = SimpleNamespace(
            text="How do I upload documents?",
            language="en",
            model_extra={"language": "en"}
        )
        mock_groq.audio.transcriptions.create.return_value = mock_whisper_verbose

        response = auth_client.post(
            "/chat/transcribe",
            files={"audio": ("test_voice.webm", io.BytesIO(fake_audio_bytes), "audio/webm")}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["transcript"] == "How do I upload documents?"
        assert data["detected_final_language"] == "en"

        # Verify verbose_json was requested
        whisper_call_args = mock_groq.audio.transcriptions.create.call_args[1]
        assert whisper_call_args["response_format"] == "verbose_json"
        assert whisper_call_args["model"] == "whisper-large-v3-turbo"

        # 2. Non-English transcription (e.g. Urdu detected)
        mock_whisper_urdu = SimpleNamespace(
            text="کیا حال ہے",
            language="ur",
            model_extra={"language": "ur"}
        )
        mock_groq.audio.transcriptions.create.return_value = mock_whisper_urdu

        mock_correction_response = MagicMock()
        mock_correction_response.choices = [
            SimpleNamespace(message=SimpleNamespace(content="kya haal hai"))
        ]
        mock_groq.chat.completions.create.return_value = mock_correction_response

        response_ur = auth_client.post(
            "/chat/transcribe",
            files={"audio": ("test_urdu.webm", io.BytesIO(fake_audio_bytes), "audio/webm")}
        )
        assert response_ur.status_code == 200
        data_ur = response_ur.json()
        assert data_ur["transcript"] == "kya haal hai"
        assert data_ur["detected_final_language"] == "roman-ur"


def test_fix1_endpoint_transcribe_empty_audio_rejected(auth_client):
    """POST /chat/transcribe rejects empty audio files with 400."""
    response = auth_client.post(
        "/chat/transcribe",
        files={"audio": ("empty.webm", io.BytesIO(b""), "audio/webm")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


# ==============================================================================
# FIX 2: LANGUAGE-AWARE TEXT-TO-SPEECH & PERSISTENCE TESTS
# ==============================================================================

def test_fix2_format_response_language_classification():
    """format_response classifies final answer into response_language ('en' or 'roman-ur')."""
    chunks = [{"filename": "company.txt", "chunk_index": 0, "document_id": 1}]

    # English answer
    en_answer = "The company was founded in 2018 in San Francisco."
    res_en = format_response(raw_answer=en_answer, chunks_used=chunks)
    assert res_en["response_language"] == "en"

    # Roman Urdu answer
    ur_answer = "Is document ke mutabiq total 10 mulazmeen hain."
    res_ur = format_response(raw_answer=ur_answer, chunks_used=chunks)
    assert res_ur["response_language"] == "roman-ur"

    # Fallback answer defaults to English
    res_fallback = format_response(raw_answer="NOT_FOUND_IN_DOCUMENT", chunks_used=chunks)
    assert res_fallback["response_language"] == "en"
    assert res_fallback["is_fallback"] is True


def test_fix2_session_message_stores_and_returns_response_language(auth_client):
    """POST /chat/sessions/{session_id}/message stores response_language and persists across reload."""
    # 1. Create a session
    sess_res = auth_client.post("/chat/sessions", json={})
    assert sess_res.status_code == 201
    session_id = sess_res.json()["session_id"]

    # 2. Send greeting message (bypasses RAG, handled locally)
    msg_res = auth_client.post(
        f"/chat/sessions/{session_id}/message",
        json={"query": "Hello there!"}
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert "response_language" in data
    assert data["response_language"] == "en"

    # 3. Verify in database record
    db = SessionLocal()
    try:
        saved_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id, ChatMessage.role == "assistant")
            .first()
        )
        assert saved_msg is not None
        assert saved_msg.response_language == "en"

        # Manually create a Roman Urdu assistant message to test persistence
        ur_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content="Aapka sawal samajh agya, iska jawab yeh hai.",
            response_language="roman-ur",
        )
        db.add(ur_msg)
        db.commit()
    finally:
        db.close()

    # 4. Reload session messages: GET /chat/sessions/{session_id}/messages
    reload_res = auth_client.get(f"/chat/sessions/{session_id}/messages")
    assert reload_res.status_code == 200
    messages = reload_res.json()
    assert len(messages) >= 2

    # Find the Roman Urdu message and check response_language persisted
    roman_ur_msg = next((m for m in messages if m["content"].startswith("Aapka sawal")), None)
    assert roman_ur_msg is not None
    assert roman_ur_msg["response_language"] == "roman-ur"


# ==============================================================================
# FIX 3: RECORDING UI & SPEECH SYNTHESIS FRONTEND CODE CHECKS
# ==============================================================================

def test_fix3_frontend_recording_cancel_and_speech_logic():
    """Verify frontend ChatLayout.jsx has cancel/discard recording & language-aware speech logic."""
    with open("frontend/src/components/ChatLayout.jsx", "r", encoding="utf-8") as f:
        frontend_code = f.read()

    # Cancel recording implementation checks
    assert "handleCancelRecording" in frontend_code
    assert "isRecordingCancelledRef" in frontend_code
    assert "recordingChunksRef.current = []" in frontend_code
    assert "Cancel and discard recording" in frontend_code

    # Distinct Stop & Send vs Cancel & Discard controls
    assert "Stop and send voice recording" in frontend_code
    assert "Cancel and discard recording" in frontend_code
    assert "Rec" in frontend_code

    # Language-aware speech synthesis checks
    assert "handleReadAloud" in frontend_code
    assert "responseLanguage === 'roman-ur'" in frontend_code
    assert "ur-PK" in frontend_code
    assert "speechSynthesis.getVoices()" in frontend_code
    assert "v.lang.toLowerCase().startsWith('ur')" in frontend_code
    assert "speechSynthesis" in frontend_code
