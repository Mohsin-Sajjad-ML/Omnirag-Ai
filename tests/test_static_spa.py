"""
Tests for single-port static file serving and SPA fallback in FastAPI backend.
Verifies that:
1. Frontend static files (dist/) are served properly.
2. Root URL ('/') and client-side SPA routes (/chat, /login/face, /sign-in, etc.) fall back to index.html.
3. Existing API routes (/auth/*, /documents/*, /chat/*, /api, /docs, /openapi.json) are not shadowed or broken.
4. Non-existent API routes and missing static assets return 404 JSON instead of HTML.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_serves_index_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert '<div id="root"></div>' in response.text


def test_spa_client_routes_fallback_to_index_html():
    client_routes = [
        "/chat",
        "/chat/",
        "/login/face",
        "/login/password",
        "/sign-in",
        "/sign-up",
        "/register",
        "/register-face",
        "/account/add-face",
    ]
    for route in client_routes:
        response = client.get(route)
        assert response.status_code == 200, f"Route {route} failed with {response.status_code}"
        assert "text/html" in response.headers.get("content-type", ""), f"Route {route} did not return HTML"
        assert '<div id="root"></div>' in response.text, f"Route {route} missing root div"


def test_static_assets_served_correctly():
    import re

    root_res = client.get("/")
    assert root_res.status_code == 200

    # JavaScript bundle dynamically extracted from index.html
    js_match = re.search(r'src="(/assets/[^"]+\.js)"', root_res.text)
    assert js_match is not None, "Could not find JS bundle script tag in index.html"
    js_path = js_match.group(1)
    js_response = client.get(js_path)
    assert js_response.status_code == 200
    assert any(t in js_response.headers.get("content-type", "") for t in ("javascript", "application/x-javascript", "text/javascript"))

    # CSS bundle dynamically extracted from index.html
    css_match = re.search(r'href="(/assets/[^"]+\.css)"', root_res.text)
    assert css_match is not None, "Could not find CSS bundle link tag in index.html"
    css_path = css_match.group(1)
    css_response = client.get(css_path)
    assert css_response.status_code == 200
    assert "text/css" in css_response.headers.get("content-type", "")

    # Face models
    model_response = client.get("/models/tiny_face_detector_model-weights_manifest.json")
    assert model_response.status_code == 200
    assert "application/json" in model_response.headers.get("content-type", "")

    # HEAD request for face models (used by faceService.verifyModelFilesExist)
    head_response = client.head("/models/face_landmark_68_model-weights_manifest.json")
    assert head_response.status_code == 200


def test_missing_static_assets_return_404_not_html():
    missing_assets = [
        "/assets/nonexistent_bundle.js",
        "/assets/missing_style.css",
        "/models/missing_model.json",
        "/models/missing_shard",
    ]
    for asset in missing_assets:
        response = client.get(asset)
        assert response.status_code == 404, f"Asset {asset} did not return 404"
        assert "text/html" not in response.headers.get("content-type", ""), f"Asset {asset} returned HTML fallback"


def test_api_routes_not_shadowed():
    # /api and /api/health
    r_api = client.get("/api")
    assert r_api.status_code == 200
    assert r_api.json().get("service") == "OmniRAG AI Backend API"

    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.json().get("status") == "online"

    # /docs and /openapi.json
    r_docs = client.get("/docs")
    assert r_docs.status_code == 200
    assert "swagger" in r_docs.text.lower() or "openapi" in r_docs.text.lower()

    r_openapi = client.get("/openapi.json")
    assert r_openapi.status_code == 200
    assert "openapi" in r_openapi.json()


def test_unmatched_api_routes_return_404_json_not_html():
    unmatched_api_paths = [
        "/auth/does-not-exist",
        "/documents/does-not-exist/subpath",
        "/chat/sessions/invalid_action/random",
        "/api/not-a-real-endpoint",
    ]
    for path in unmatched_api_paths:
        response = client.get(path)
        assert response.status_code == 404, f"Path {path} returned {response.status_code}"
        assert "text/html" not in response.headers.get("content-type", ""), f"API path {path} returned HTML fallback"
        assert response.json().get("detail") == "Not Found" or "not found" in response.text.lower()


def test_api_endpoints_protected_or_functional():
    # Documents requires Clerk token
    r_doc = client.get("/documents/")
    assert r_doc.status_code == 401

    # Chat sessions requires Clerk token
    r_sessions = client.get("/chat/sessions")
    assert r_sessions.status_code == 401

    # Face login with empty descriptor returns 422
    r_login = client.post("/auth/login/face", json={})
    assert r_login.status_code == 422
