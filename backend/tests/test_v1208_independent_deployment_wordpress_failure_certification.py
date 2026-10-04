import os
from pathlib import Path
import socket
import tempfile
from unittest.mock import patch

os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
os.environ.setdefault("SC_RL_IDENTITY_COOKIE_SECURE","false")

from fastapi.testclient import TestClient

from app.services.independent_deployment_certification import (
    certification_manifest,
    certification_report,
    REQUIRED_INDEPENDENT_ROUTES,
)

def test_certification_manifest_defines_wordpress_failure_boundary():
    m=certification_manifest()
    assert m["milestone"]=="12.0.8"
    assert m["runtime_authority"]=="python-fastapi-backend"
    assert m["wordpress_required"] is False
    assert m["certification_target"]=="wordpress-unreachable-or-absent"
    assert m["database_migration"] is None
    assert m["wordpress_adapter_policy"]["adapter_optional"] is True
    assert m["wordpress_adapter_policy"]["backend_does_not_call_wordpress_for_independent_operations"] is True
    assert m["wordpress_adapter_policy"]["adapter_failure_behavior"]=="fail-closed-no-wordpress-research-fallback"
    assert m["certification_method"]["wordpress_dns_blackout_probe"] is True
    assert m["governance"]["certification_does_not_modify_research_state"] is True
    assert m["next_boundary"]=="neural-research-intelligence-foundation"

def test_certification_report_is_read_only_and_fingerprinted():
    report=certification_report(set(REQUIRED_INDEPENDENT_ROUTES))
    assert report["milestone"]=="12.0.8"
    assert report["certified"] is True
    assert report["wordpress_required"] is False
    assert report["runtime_authority"]=="python-fastapi-backend"
    assert report["failed_count"]==0
    assert len(report["certificate_fingerprint"])==64
    assert report["governance"]["read_only_certification"] is True
    assert report["governance"]["research_state_modified"] is False
    assert report["governance"]["legacy_wordpress_state_modified"] is False
    assert report["next_boundary"]=="neural-research-intelligence-foundation"

def test_wordpress_dns_blackout_does_not_break_independent_runtime(tmp_path):
    from app.services import identity_session_access as identity_service
    from app.services.identity_session_access import IdentitySessionStore
    from app.services import persistent_research_session_conversation as session_service
    from app.services.persistent_research_session_conversation import PersistentResearchSessionStore
    from app.services import wordpress_state_migration as migration_service
    from app.services.wordpress_state_migration import WordPressStateMigrationStore

    identity_service._STORE=IdentitySessionStore(sqlite_path=tmp_path/"identity.sqlite3")
    session_service._STORE=PersistentResearchSessionStore(sqlite_path=tmp_path/"sessions.sqlite3")
    migration_service._STORE=WordPressStateMigrationStore(sqlite_path=tmp_path/"migration.sqlite3")

    from app.main import app
    client=TestClient(app)

    real_getaddrinfo=socket.getaddrinfo
    blocked=[]

    def guard(host,*args,**kwargs):
        text=str(host or "").lower()
        if "sustainablecatalyst.com" in text or "wordpress" in text:
            blocked.append(text)
            raise OSError("v12.0.8 simulated WordPress DNS blackout")
        return real_getaddrinfo(host,*args,**kwargs)

    with patch("socket.getaddrinfo",side_effect=guard):
        health=client.get("/health")
        assert health.status_code==200
        assert health.json()["version"]=="12.0.8"
        assert health.json()["wordpress_required"] is False
        assert health.json()["independent_deployment_certification"] is True

        web=client.get("/research-librarian/")
        assert web.status_code==200

        manifest=client.get(
            "/v1/research-librarian/manifest",
            headers={"X-SC-RL-Key":"test-key"},
        )
        assert manifest.status_code==200
        assert manifest.json()["data"]["wordpress_required"] is False

        auth_manifest=client.get("/v1/research-librarian/auth/manifest")
        assert auth_manifest.status_code==200

        migration_manifest=client.get("/v1/research-librarian/wordpress-migration/manifest")
        assert migration_manifest.status_code==200
        assert migration_manifest.json()["data"]["wordpress_required"] is False

        retrieve=client.post(
            "/v1/research-librarian/retrieve",
            headers={"X-SC-RL-Key":"test-key"},
            json={
                "query":"wordpress blackout certification",
                "limit":3,
                "include_semantic":False,
            },
        )
        assert retrieve.status_code==200

        created=client.post(
            "/v1/research-librarian/sessions",
            headers={"X-SC-RL-Key":"test-key"},
            json={"title":"v12.0.8 blackout certification","metadata":{"certification":True}},
        )
        assert created.status_code==200
        session_id=created.json()["data"]["session_id"]

        turn=client.post(
            f"/v1/research-librarian/sessions/{session_id}/turns",
            headers={"X-SC-RL-Key":"test-key"},
            json={"role":"research-note","content":"WordPress unavailable; backend session remained writable."},
        )
        assert turn.status_code==200

        summary=client.get(
            f"/v1/research-librarian/sessions/{session_id}/summary",
            headers={"X-SC-RL-Key":"test-key"},
        )
        assert summary.status_code==200

        report=client.get(
            "/v1/research-librarian/independence/report",
            headers={"X-SC-RL-Key":"test-key"},
        )
        assert report.status_code==200
        data=report.json()["data"]
        assert data["certified"] is True
        assert data["failed_count"]==0
        assert data["wordpress_required"] is False

    assert blocked==[]

def test_independence_routes_are_registered_and_report_is_protected():
    from app.main import app
    client=TestClient(app)
    paths={getattr(r,"path","") for r in app.routes}
    assert "/v1/research-librarian/independence/manifest" in paths
    assert "/v1/research-librarian/independence/report" in paths
    assert client.get("/v1/research-librarian/independence/manifest").status_code==200
    assert client.get("/v1/research-librarian/independence/report").status_code==401
    ok=client.get(
        "/v1/research-librarian/independence/report",
        headers={"X-SC-RL-Key":"test-key"},
    )
    assert ok.status_code==200
    assert ok.json()["data"]["certified"] is True

def test_current_api_boundary_advances_to_neural_foundation():
    from app.services.independent_research_librarian_api import api_manifest,capabilities
    m=api_manifest()
    c=capabilities()
    assert m["scope"]["wordpress_state_migration"] is True
    assert m["scope"]["independent_deployment_certification"] is True
    assert m["next_boundary"]=="neural-research-intelligence-foundation"
    assert c["milestone"]=="12.0.8"
    assert c["independent_deployment_certification"] is True
    assert c["wordpress_failure_certification"] is True
