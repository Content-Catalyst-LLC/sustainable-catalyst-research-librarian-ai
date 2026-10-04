import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")

from fastapi.testclient import TestClient

from app.services.independent_web_app import (
    web_app_manifest,
    web_app_capabilities,
)

def test_web_app_manifest_is_wordpress_independent_and_secret_safe():
    m=web_app_manifest()
    assert m["milestone"]=="12.0.6"
    assert m["entry_path"]=="/research-librarian/"
    assert m["api_base"]=="/v1/research-librarian"
    assert m["runtime_authority"]=="python-fastapi-backend"
    assert m["wordpress_required"] is False
    assert m["canonical_state_location"]=="python-postgres-backend"
    assert m["browser_state_policy"]["canonical_research_state_in_browser"] is False
    assert m["browser_state_policy"]["local_storage_used"] is False
    assert m["browser_state_policy"]["embedded_backend_secret"] is False
    assert m["authentication"]["key_embedded_in_app"] is False
    assert m["authentication"]["production_user_identity"] is True
    assert m["next_boundary"]=="neural-research-intelligence-foundation"

def test_web_app_capabilities_boundary():
    c=web_app_capabilities()
    assert c["milestone"]=="12.0.6"
    assert c["standalone_browser_shell"] is True
    assert c["persistent_backend_sessions"] is True
    assert c["wordpress_required"] is False
    assert c["browser_canonical_state"] is False
    assert c["embedded_secret"] is False
    assert c["identity_sessions"] is True

def test_web_app_routes_and_assets():
    from app.main import app
    client=TestClient(app)
    html=client.get("/research-librarian/")
    assert html.status_code==200
    assert "IDENTITY, SESSION & ACCESS RUNTIME" in html.text
    assert "/v1/research-librarian" in html.text
    assert "WordPress is not an identity authority" in html.text
    manifest=client.get("/research-librarian/app-manifest.json")
    assert manifest.status_code==200
    assert manifest.json()["wordpress_required"] is False
    css=client.get("/research-librarian/assets/app.css")
    js=client.get("/research-librarian/assets/app.js")
    assert css.status_code==200
    assert js.status_code==200
    assert "localStorage" not in js.text
    assert "sessionStorage" not in js.text
    assert "SC_RL_BACKEND_API_KEY" not in js.text
    assert '/auth/login' in js.text
    assert '"/v1/research-librarian"' not in js.text or "/retrieve" in js.text

def test_web_app_shell_uses_independent_api_and_persistent_sessions():
    from app.main import app
    client=TestClient(app)
    js=client.get("/research-librarian/assets/app.js").text
    for required in [
        '"/auth/manifest"',
        '"/projects?limit=100"',
        '"/sessions?limit=100"',
        '"/retrieve"',
        '/turns',
        '/snapshots/freeze',
        '/auth/me',
    ]:
        assert required in js
    assert "localStorage" not in js
    assert "document.cookie" not in js

def test_health_advertises_web_app():
    from app.main import app
    client=TestClient(app)
    health=client.get("/health")
    assert health.status_code==200
    body=health.json()
    assert body["version"]=="12.0.8"
    assert body["independent_web_app"] is True
    assert body["independent_web_app_path"]=="/research-librarian/"
    assert body["wordpress_required"] is False
