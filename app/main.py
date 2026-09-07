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
     uvicorn app.main:app --reload

5. Interactive API documentation will be available at:
     - Swagger UI: http://127.0.0.1:8000/docs
     - ReDoc:      http://127.0.0.1:8000/redoc
================================================================================
"""

from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (.env) from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
import app.models
from app.auth import router as auth_router
from app.documents import router as documents_router
from app.chat import router as chat_router

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

# Initialize FastAPI application instance
app = FastAPI(
    title="OmniRAG AI Backend API",
    description="Backend service supporting authentication, biometric face recognition, and document ingestion.",
    version="1.0.0"
)


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
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
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


@app.get("/", summary="Root Health Check")
def root():
    """
    Backend overview and documentation links.
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
