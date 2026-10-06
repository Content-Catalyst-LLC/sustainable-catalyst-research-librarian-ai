import os
from pathlib import Path
import tempfile

os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
os.environ.setdefault("SC_RL_IDENTITY_COOKIE_SECURE","false")

from fastapi.testclient import TestClient

from app.contracts.identity_session_access import IdentityProvisionRequest
from app.services.identity_session_access import (
    IdentitySessionStore,
    ROLE_PERMISSIONS,
)


def test_identity_store_hashes_passwords_tokens_and_enforces_lockout(tmp_path):
    store=IdentitySessionStore(sqlite_path=tmp_path/"identity.sqlite3")
    identity=store.provision(IdentityProvisionRequest(
        email="owner@example.com",
        display_name="Owner",
        password="correct horse battery staple",
        role="owner",
    ))
    assert identity["role"]=="owner"
    assert identity["email"]=="owner@example.com"
    assert "password" not in identity

    who,token,session=store.authenticate(
        "OWNER@example.com",
        "correct horse battery staple",
        "pytest",
    )
    assert who["identity_id"]==identity["identity_id"]
    assert token
    assert session["state"]=="active"

    access=store.resolve_token(token)
    assert access is not None
    assert access.identity_id==identity["identity_id"]
    assert access.is_admin is True
    assert "research:write" in access.permissions

    rows=store.sessions_for_identity(identity["identity_id"])
    assert len(rows)==1
    assert "token" not in rows[0]
    assert store.revoke(session["auth_session_id"],"pytest") is True
    assert store.resolve_token(token) is None


def test_role_permissions_are_explicit():
    assert "identity:admin" in ROLE_PERMISSIONS["owner"]
    assert "research:write" in ROLE_PERMISSIONS["researcher"]
    assert "research:write" not in ROLE_PERMISSIONS["viewer"]


def test_auth_api_bearer_roundtrip_and_identity_owned_research_sessions():
    from app.services import identity_session_access as auth_service
    auth_service._STORE=IdentitySessionStore(sqlite_path=Path(tempfile.mkdtemp(prefix="sc-rl-v1205-api-"))/"identity-api.sqlite3")

    from app.main import app
    client=TestClient(app)

    provision=client.post(
        "/v1/research-librarian/auth/provision",
        headers={"X-SC-RL-Key":"test-key"},
        json={
            "email":"researcher@example.com",
            "display_name":"Researcher",
            "password":"a secure research password",
            "role":"researcher",
        },
    )
    assert provision.status_code==200
    identity=provision.json()["data"]
    assert identity["identity_ref"].startswith("identity:")

    login=client.post(
        "/v1/research-librarian/auth/login",
        json={
            "email":"researcher@example.com",
            "password":"a secure research password",
            "client_mode":"bearer",
            "client_label":"pytest",
        },
    )
    assert login.status_code==200
    token=login.json()["data"]["bearer_token"]
    headers={"Authorization":f"Bearer {token}"}

    me=client.get("/v1/research-librarian/auth/me",headers=headers)
    assert me.status_code==200
    access=me.json()["data"]
    assert access["auth_mode"]=="identity-session"
    assert access["identity_id"]==identity["identity_id"]
    assert access["can_write"] is True

    created=client.post(
        "/v1/research-librarian/sessions",
        headers=headers,
        json={
            "title":"Identity owned research",
            "client_ref":"spoofed-client-ref",
            "metadata":{"test":True},
        },
    )
    assert created.status_code==200
    research_session=created.json()["data"]
    assert research_session["client_ref"]==identity["identity_ref"]

    sessions=client.get("/v1/research-librarian/sessions?client_ref=spoofed-client-ref",headers=headers)
    assert sessions.status_code==200
    items=sessions.json()["data"]["items"]
    assert any(x["session_id"]==research_session["session_id"] for x in items)
    assert all(x["client_ref"]==identity["identity_ref"] for x in items)

    logout=client.post("/v1/research-librarian/auth/logout",headers=headers,json={})
    assert logout.status_code==200
    assert client.get("/v1/research-librarian/auth/me",headers=headers).status_code==401


def test_viewer_is_read_only():
    from app.services import identity_session_access as auth_service
    auth_service._STORE=IdentitySessionStore(sqlite_path=Path(tempfile.mkdtemp(prefix="sc-rl-v1205-viewer-"))/"viewer.sqlite3")
    store=auth_service._STORE
    identity=store.provision(IdentityProvisionRequest(
        email="viewer@example.com",
        display_name="Viewer",
        password="viewer password long enough",
        role="viewer",
    ))
    _who,token,_session=store.authenticate("viewer@example.com","viewer password long enough","pytest")

    from app.main import app
    client=TestClient(app)
    headers={"Authorization":f"Bearer {token}"}
    assert client.get("/v1/research-librarian/status",headers=headers).status_code==200
    denied=client.post(
        "/v1/research-librarian/retrieve",
        headers=headers,
        json={"query":"test","limit":5},
    )
    assert denied.status_code==403


def test_web_app_uses_identity_cookie_not_backend_key():
    from app.main import app
    client=TestClient(app)
    html=client.get("/research-librarian/")
    js=client.get("/research-librarian/assets/app.js")
    manifest=client.get("/research-librarian/app-manifest.json")
    assert html.status_code==200
    assert js.status_code==200
    assert manifest.status_code==200
    assert "IDENTITY, SESSION & ACCESS RUNTIME" in html.text
    assert "/auth/login" in js.text
    assert "/auth/me" in js.text
    assert "credentials: \"same-origin\"" in js.text
    assert "X-SC-RL-Key" not in js.text
    assert "SC_RL_BACKEND_API_KEY" not in js.text
    assert "localStorage" not in js.text
    assert "sessionStorage" not in js.text
    m=manifest.json()
    assert m["milestone"]=="12.0.6"
    assert m["authentication"]["production_user_identity"] is True
    assert m["authentication"]["backend_api_key_embedded"] is False
    assert m["next_boundary"]=="neural-research-intelligence-foundation"


def test_health_advertises_identity_sessions():
    from app.main import app
    client=TestClient(app)
    body=client.get("/health").json()
    assert body["version"]=="12.3.0"
    assert body["identity_sessions"] is True
    assert body["identity_access_runtime"]=="12.0.5"
    assert body["wordpress_required"] is False
