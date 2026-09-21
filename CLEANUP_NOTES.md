# OmniRAG AI — Project Cleanup & Reorganization Baseline Inventory

**Date:** 2026-09-18  
**Baseline Status:** Captured prior to any file deletion, reorganization, or refactoring.

---

## 1. Baseline Inventory: Pages & Screens

| Page / Screen | Route | Primary Component | Functional Description |
| :--- | :--- | :--- | :--- |
| **Login Choice** | `/` | `pages/LoginChoice.jsx` | Welcome landing screen. Provides options to choose login method: Biometric Face Recognition, Email/Password (Clerk), or Legacy Password. |
| **Face Login** | `/login/face` | `pages/FaceLogin.jsx` | Uses webcam and `face-api.js` (128D embedding vector) to authenticate existing registered faces via `POST /auth/login-face`. |
| **Password Login** | `/login/password` | `pages/PasswordLogin.jsx` | Username/Password login screen for legacy database authentication via `POST /auth/login`. |
| **Register** | `/register` | `pages/Register.jsx` | User account registration form with optional biometric enrollment via `POST /auth/register`. |
| **Clerk Sign In** | `/sign-in/*` | `pages/ClerkSignIn.jsx` | Hosted/embedded Clerk authentication sign-in screen. |
| **Clerk Sign Up** | `/sign-up/*` | `pages/ClerkSignUp.jsx` | Hosted/embedded Clerk authentication registration screen. |
| **Register Face** | `/register-face` | `pages/RegisterFace.jsx` | Onboarding face enrollment screen for newly registered Clerk users via `POST /auth/register-face`. |
| **Manage / Add Face** | `/account/add-face` | `pages/AddFace.jsx` | Profile settings page. Allows users to view registered faces, register additional biometric faces (`POST /auth/faces`), delete faces (`DELETE /auth/faces/{id}`), or delete the entire account (`DELETE /auth/account`). |
| **Main Chat & Workspace** | `/chat` | `pages/ChatPage.jsx` + `components/ChatLayout.jsx` | Core application screen: Multi-session chat, session list/search/pin/rename/delete/duplicate, document drawer (upload, list, delete, scope selection), message history, voice recording with Whisper transcription, RAG retrieval with citations, real-time web search, and hybrid RAG+Web answering. |

---

## 2. Baseline Inventory: Backend API Endpoints & Frontend Callers

### Authentication Domain (`/auth`)
| Endpoint | Method | Backend Handler | Frontend Caller | Feature Description |
| :--- | :--- | :--- | :--- | :--- |
| `/auth/register` | `POST` | `auth.router.register` | `pages/Register.jsx` | User creation with password |
| `/auth/login` | `POST` | `auth.router.login` | `pages/PasswordLogin.jsx` | Legacy username/password authentication |
| `/auth/register-face` | `POST` | `auth.router.register_face` | `pages/RegisterFace.jsx` | Initial face biometric enrollment |
| `/auth/login-face` | `POST` | `auth.router.login_face` | `pages/FaceLogin.jsx` | Biometric face login |
| `/auth/faces` | `POST` | `auth.router.add_face` | `pages/AddFace.jsx` | Add secondary/additional face |
| `/auth/faces` | `GET` | `auth.router.list_faces` | `pages/AddFace.jsx`, `ChatLayout.jsx` | List registered user faces |
| `/auth/faces/{face_id}` | `DELETE` | `auth.router.delete_face` | `pages/AddFace.jsx` | Delete specific face profile |
| `/auth/account` | `DELETE` | `auth.router.delete_account` | `pages/AddFace.jsx` | Full account & biometric purge |

### Documents Domain (`/documents`)
| Endpoint | Method | Backend Handler | Frontend Caller | Feature Description |
| :--- | :--- | :--- | :--- | :--- |
| `/documents/upload` | `POST` | `documents.router.upload_document` | `UploadDocument.jsx`, `ChatLayout.jsx` | Upload & index PDF, DOCX, TXT, CSV into ChromaDB |
| `/documents` / `/{username}` | `GET` | `documents.router.get_user_documents` | `DocumentList.jsx`, `ChatLayout.jsx` | List all user documents with summaries |
| `/documents/{id}` | `DELETE` | `documents.router.delete_document` | `DocumentList.jsx`, `ChatLayout.jsx` | Delete document and remove ChromaDB chunks |
| `/documents/{id}/chunk/{idx}` | `GET` | `documents.router.get_document_chunk` | `ChatLayout.jsx` (Citation cards) | Preview raw text chunk cited in assistant response |

### Chat Domain (`/chat`)
| Endpoint | Method | Backend Handler | Frontend Caller | Feature Description |
| :--- | :--- | :--- | :--- | :--- |
| `/chat/sessions` | `POST` | `chat.router.create_chat_session` | `ChatLayout.jsx` | Create new conversation session |
| `/chat/sessions/{username}` | `GET` | `chat.router.list_user_sessions` | `ChatLayout.jsx` | Fetch user chat sessions list (with pinned status) |
| `/chat/sessions/{id}/messages` | `GET` | `chat.router.get_session_messages` | `ChatLayout.jsx` | Load multi-turn message history with citations |
| `/chat/sessions/{id}/message` | `POST` | `chat.router.post_session_message` | `ChatLayout.jsx` | Send query, execute RAG/Web Search, get assistant reply |
| `/chat/sessions/{id}/pin` | `PATCH` | `chat.router.pin_chat_session` | `ChatLayout.jsx` | Pin / unpin chat session in sidebar |
| `/chat/sessions/{id}/rename` | `PATCH` | `chat.router.rename_chat_session` | `ChatLayout.jsx` | Rename session title inline |
| `/chat/sessions/{id}/duplicate`| `POST` | `chat.router.duplicate_chat_session` | `ChatLayout.jsx` | Duplicate session and all its messages |
| `/chat/sessions/{id}` | `DELETE` | `chat.router.delete_chat_session` | `ChatLayout.jsx` | Delete session and its messages |
| `/chat/sessions/{id}/export` | `GET` | `chat.router.export_chat_session` | `ChatLayout.jsx` | Export chat history as formatted TXT or PDF |
| `/chat/transcribe` | `POST` | `chat.router.transcribe_audio` | `ChatLayout.jsx` (Voice Recorder) | Whisper audio transcription & correction |
| `/chat/query` | `POST` | `chat.router.query_knowledge_base` | `services/api.js` | One-shot document RAG query |

---

## 3. Baseline Inventory: Working End-to-End Features

1. **Biometric Face Login & Registration**:
   - Camera activation, 128D embedding extraction via face-api.js, Euclidean distance verification (< 0.6 threshold).
   - Multi-face profile management (add face, delete face, account deletion).
2. **Clerk Authentication Integration**:
   - Clerk token exchange with FastAPI backend dependency (`ClerkUser`).
3. **Multi-Format Document Ingestion**:
   - PDF, DOCX, TXT parsing and CSV schema summary generation.
   - Vector chunking & ChromaDB embedding using `all-MiniLM-L6-v2`.
   - Document search/filter in retrieval scope dropdown.
4. **Chat Session Management**:
   - Create, list, switch, rename, duplicate, delete with undo toast, pin to top.
   - Export session history to TXT and PDF.
5. **Intelligent Query Execution**:
   - Fast intent routing (Greeting, About Bot, Document Query).
   - Strict closed-world RAG with document citations and chunk previews.
   - Real-time DuckDuckGo web search fallback and direct web search mode.
   - Hybrid RAG + Web Search synthesis (structured definition + resume/document skill/project context with citations).
   - Multi-lingual matching (English & Roman Urdu).
6. **Voice Input & Whisper Transcription**:
   - Audio recording with canvas waveform visualizer.
   - Whisper transcription with domain-specific dictionary correction.
7. **Observability & Granular Tracing**:
   - Langfuse trace pipelines for document ingest (`document-ingest`, `extract-text`, `chunking`, `index-write`) and chat (`chat-request`, `embedding`, `retrieval`, `embed_query`, `vector_search`, `mode-selected`, `generate_answer`, `chat-completed`).

---

## 4. File Usage Analysis (Candidates for Removal)

### A. Confirmed Truly Unused Files (To be removed from project)
- **`frontend/src/pages/ChatPlaceholder.jsx`**:
  - *Analysis*: Verified 0 imports across entire codebase. Was an early prototyping placeholder superseded by `ChatLayout.jsx` and `ChatPage.jsx`.
- **Root-level one-off debugging / scratch scripts**:
  - `add_obs.py` — Temporary observation patcher from past Langfuse task. 0 imports.
  - `fix_router.py` — Temporary fix script from past task. 0 imports.
  - `fix_router2.py` — Temporary fix script from past task. 0 imports.
  - `run_prompt6_demo.py` — Standalone demo script. 0 imports in app.
  - `run_prompt7_demo.py` — Standalone demo script. 0 imports in app.
  - `run_prompt8_demo.py` — Standalone demo script. 0 imports in app.
  - `run_prompt9_demo.py` — Standalone demo script. 0 imports in app.
  - `run_prompt10_verification.py` — Standalone verification script. 0 imports in app.
  - `run_prompt11_verification.py` — Standalone verification script. 0 imports in app.
  - `verify_voice_scenarios.py` — Standalone scratch test. 0 imports in app.
- **`scratch/` directory**:
  - Contains ~136 MB of temporary Edge test browser profiles and obsolete debug files. Completely unused by app and test suites.

### B. Files That MUST BE KEPT
- **`scripts/register_langfuse_prompts.py`** and other `scripts/verify_*.py`: Kept as official maintenance/verification tools.
- **`tests/`**: All test files kept and updated.
- **`backend/` & `frontend/` source files**: All core code kept.
