r"""
================================================================================
HOW TO RUN THIS SERVER:
================================================================================
1. Create a Python virtual environment:
     python -m venv venv

2. Activate the virtual environment:
     - Windows (PowerShell): .\venv\Scripts\Activate.ps1
     - Windows (CMD):        .\venv\Scripts\activate.bat
     - Linux/macOS:          source venv/bin/activate

3. Install all dependencies from requirements.txt:
     pip install -r requirements.txt

4. Run the FastAPI development server:
     uvicorn backend.main:app --reload

5. Interactive API documentation will be available at:
     - Swagger UI: http://127.0.0.1:8000/docs
     - ReDoc:      http://127.0.0.1:8000/redoc
================================================================================
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure Windows stdout/stderr safely handles non-ASCII/Urdu characters
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

# Load environment variables (.env) from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.database.connection import engine, Base
import backend.database.models
from backend.auth import router as auth_router
from backend.documents import router as documents_router
from backend.chat import router as chat_router

# Create database tables automatically when the app initializes
Base.metadata.create_all(bind=engine)

# Backward-compatibility migration: ensure chunk_count and summary exist in SQLite documents table (Prompt 8)
from sqlalchemy import text
with engine.connect() as _migration_conn:
    try:
        _migration_conn.execute(text("ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0"))
        _migration_conn.commit()
    except Exception:
        # Column already exists
        pass
    try:
        _migration_conn.execute(text("ALTER TABLE documents ADD COLUMN summary TEXT DEFAULT NULL"))
        _migration_conn.commit()
    except Exception:
        # Column already exists
        pass
    try:
        _migration_conn.execute(text("ALTER TABLE chat_messages ADD COLUMN response_language VARCHAR(20) DEFAULT 'en'"))
        _migration_conn.commit()
    except Exception:
        # Column already exists
        pass
    try:
        _migration_conn.execute(text("ALTER TABLE chat_messages ADD COLUMN source VARCHAR(30) DEFAULT 'rag'"))
        _migration_conn.commit()
    except Exception:
        # Column already exists
        pass
    try:
        _migration_conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN pinned BOOLEAN DEFAULT 0"))
        _migration_conn.commit()
    except Exception:
        # Column already exists
        pass

    # Migrate legacy User.face_descriptor to FaceDescriptor table
    try:
        _old_face_rows = _migration_conn.execute(
            text("SELECT clerk_user_id, face_descriptor, created_at FROM users WHERE face_descriptor IS NOT NULL AND face_descriptor != ''")
        ).fetchall()
        for _row in _old_face_rows:
            _c_id, _f_desc, _c_at = _row
            _has_face = _migration_conn.execute(
                text("SELECT id FROM face_descriptors WHERE clerk_user_id = :cid"),
                {"cid": _c_id}
            ).first()
            if not _has_face:
                _migration_conn.execute(
                    text("INSERT INTO face_descriptors (clerk_user_id, descriptor, label, created_at) VALUES (:cid, :desc, :label, :cat)"),
                    {"cid": _c_id, "desc": _f_desc, "label": "Primary Face", "cat": _c_at}
                )
        _migration_conn.execute(text("UPDATE users SET face_descriptor = NULL"))
        _migration_conn.commit()
    except Exception:
        pass

# Initialize FastAPI application instance
app = FastAPI(
    title="OmniRAG AI Backend API",
    description="Backend service supporting authentication, biometric face recognition, and document ingestion.",
    version="1.0.0"
)

@app.on_event("shutdown")
def shutdown_event():
    from backend.config import get_langfuse_client
    try:
        get_langfuse_client().flush()
    except Exception:
        pass



@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """
    Ensure both 'detail' and 'message' fields are returned in HTTP error responses
    to support diverse API client conventions.
    """
    detail = exc.detail
    if isinstance(detail, str):
        content = {"detail": detail, "message": detail}
    elif isinstance(detail, dict):
        content = dict(detail)
        if "message" not in content and "detail" in content:
            content["message"] = str(content["detail"])
        elif "detail" not in content and "message" in content:
            content["detail"] = str(content["message"])
    else:
        content = {"detail": detail}

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


# Configure CORS Middleware to allow requests from frontend dev servers
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register APIRouters
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/api", summary="Backend API Overview")
@app.get("/api/health", summary="API Health Check")
def api_overview():
    """
    Backend overview, health status, and documentation links.
    """
    return {
        "service": "OmniRAG AI Backend API",
        "version": app.version,
        "status": "online",
        "description": "Document-grounded chat, authentication, and document management service.",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json",
        },
        "endpoint_groups": {
            "authentication": "/auth/*",
            "documents": "/documents/*",
            "chat_and_sessions": "/chat/*",
        },
        "message": "API is running. Open /docs to view and test all endpoints.",
    }


# Frontend static files and SPA client-side fallback
FRONTEND_DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

STATIC_ASSET_EXTENSIONS = {
    ".js", ".css", ".map", ".json", ".png", ".jpg", ".jpeg",
    ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".webp", ".wasm"
}


class SinglePageApplication(StaticFiles):
    """
    Serves built frontend static files from /frontend/dist and falls back to index.html
    for any non-API client-side route so React Router can handle navigation smoothly.
    Ensures API routes and documentation endpoints return standard 404 responses instead of HTML.
    """

    def __init__(self, directory: Path | str, index: str = "index.html", html: bool = True):
        super().__init__(directory=str(directory), html=html, check_dir=False)
        self.index = index

    async def get_response(self, path: str, scope):
        # Only GET and HEAD requests can serve web pages / static files
        if scope.get("method") not in ("GET", "HEAD"):
            return JSONResponse(
                status_code=404,
                content={"detail": "Not Found", "message": "Not Found"},
            )

        raw_path = scope.get("path", "")
        # Prevent unmatched API routes or Swagger/Redoc endpoints from falling back to index.html.
        # Note: /chat and /chat/ are frontend client-side routes, whereas /chat/sessions,
        # /chat/query, and /chat/transcribe are API endpoints.
        is_api_path = (
            raw_path.startswith(("/auth/", "/documents/", "/api/"))
            or (raw_path.startswith("/chat/") and raw_path.rstrip("/") != "/chat")
            or raw_path in ("/auth", "/documents", "/docs", "/redoc", "/openapi.json")
        )
        if is_api_path:
            return JSONResponse(
                status_code=404,
                content={"detail": "Not Found", "message": "Not Found"},
            )

        # Do not fall back to index.html for static assets (e.g. /assets/xyz.js or missing images)
        file_ext = Path(path).suffix.lower()
        is_static_asset = file_ext in STATIC_ASSET_EXTENSIONS or raw_path.startswith(("/assets/", "/models/"))

        try:
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                if is_static_asset:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": f"Static asset '{path}' not found.", "message": f"Static asset '{path}' not found."},
                    )
                index_response = await super().get_response(self.index, scope)
                if index_response.status_code == 404:
                    return JSONResponse(
                        status_code=404,
                        content={
                            "detail": "Frontend static build not found. Please run 'npm run build' inside /frontend.",
                            "message": "Frontend static build not found. Please run 'npm run build' inside /frontend.",
                        },
                    )
                return index_response
            return response
        except StarletteHTTPException as ex:
            if ex.status_code == 404:
                if is_static_asset:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": f"Static asset '{path}' not found.", "message": f"Static asset '{path}' not found."},
                    )
                try:
                    index_response = await super().get_response(self.index, scope)
                    if index_response.status_code == 404:
                        return JSONResponse(
                            status_code=404,
                            content={
                                "detail": "Frontend static build not found. Please run 'npm run build' inside /frontend.",
                                "message": "Frontend static build not found. Please run 'npm run build' inside /frontend.",
                            },
                        )
                    return index_response
                except StarletteHTTPException:
                    return JSONResponse(
                        status_code=404,
                        content={
                            "detail": "Frontend static build not found. Please run 'npm run build' inside /frontend.",
                            "message": "Frontend static build not found. Please run 'npm run build' inside /frontend.",
                        },
                    )
            raise


# Mount frontend SPA static file handler at root URL
app.mount("/", SinglePageApplication(directory=FRONTEND_DIST_DIR, html=True), name="frontend-spa")
