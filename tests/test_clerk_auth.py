"""Focused tests for Clerk session verification and protected route behavior."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.auth import dependencies as clerk_auth
from backend.main import app


client = TestClient(app)


def test_missing_clerk_token_is_rejected():
    response = client.get("/documents/")
    assert response.status_code == 401


def test_invalid_clerk_token_is_rejected():
    response = client.get(
        "/documents/",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_verified_clerk_payload_returns_user_identity(monkeypatch):
    payload = {"sub": "user_test123", "sid": "sess_test123"}
    signed_in_state = SimpleNamespace(status=clerk_auth.AuthStatus.SIGNED_IN, payload=payload)

    class FakeClerk:
        def __init__(self, **kwargs):
            pass

        def authenticate_request(self, request, options):
            return signed_in_state

    monkeypatch.setattr(clerk_auth, "Clerk", FakeClerk)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_mock")

    result = clerk_auth.get_current_clerk_user(
        SimpleNamespace(headers={"Authorization": "Bearer token"})
    )

    assert result["user_id"] == "user_test123"
    assert result["session_id"] == "sess_test123"


def test_failed_sdk_verification_returns_401(monkeypatch):
    class FakeClerk:
        def __init__(self, **kwargs):
            pass

        def authenticate_request(self, request, options):
            raise RuntimeError("invalid token")

    monkeypatch.setattr(clerk_auth, "Clerk", FakeClerk)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_mock")

    with pytest.raises(HTTPException) as error:
        clerk_auth.get_current_clerk_user(SimpleNamespace(headers={}))

    assert error.value.status_code == 401
