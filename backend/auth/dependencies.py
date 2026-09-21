"""
dependencies.py - Clerk session-token verification dependency for FastAPI routes.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions, AuthStatus

from backend.config import settings


def get_current_clerk_user(request: Request) -> Dict[str, Any]:
    """Verify the Clerk session JWT from Authorization or __session cookie."""
    secret_key = settings.CLERK_SECRET_KEY
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk authentication is not configured on the server.",
        )

    # Support monkeypatching on app.clerk_auth or app.auth.dependencies in tests
    clerk_mod = sys.modules.get("backend.clerk_auth") or sys.modules.get("backend.auth.dependencies")
    clerk_cls = getattr(clerk_mod, "Clerk", Clerk)
    auth_status_cls = getattr(clerk_mod, "AuthStatus", AuthStatus)

    try:
        clerk = clerk_cls(bearer_auth=secret_key)
        request_state = clerk.authenticate_request(
            request,
            AuthenticateRequestOptions(secret_key=secret_key),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to verify Clerk session token.",
        ) from exc

    if getattr(request_state, "status", None) != auth_status_cls.SIGNED_IN or not getattr(request_state, "payload", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing, invalid, or expired Clerk session token.",
        )

    payload = request_state.payload
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk session token does not identify a user.",
        )

    return {"user_id": clerk_user_id, "session_id": payload.get("sid"), "claims": payload}


ClerkUser = Depends(get_current_clerk_user)

__all__ = [
    "Clerk",
    "AuthStatus",
    "AuthenticateRequestOptions",
    "get_current_clerk_user",
    "ClerkUser",
]
