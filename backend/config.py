"""
config.py - Centralized environment variables and settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded from the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Settings:
    # Auth configuration
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "").strip()
    CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "").strip()

    # Database configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db").strip()

    # LLM (Groq) configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

    # Langfuse configuration
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").strip()

settings = Settings()

def get_langfuse_client():
    from langfuse import get_client
    return get_client()

def get_dynamic_prompt(name: str, fallback_text: str):
    """
    Fetches a prompt from Langfuse Prompt Management with TTL caching and fallback.
    Returns (compiled_text, prompt_object)
    """
    from backend.prompts import get_prompt_with_object
    return get_prompt_with_object(name, fallback_text)
