import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")

from fastapi.testclient import TestClient

from app.contracts.thin_wordpress_adapter import (
    ALL_OPERATIONS,
    READ_OPERATIONS,
    WRITE_OPERATIONS,
    THIN_WORDPRESS_ADAPTER_SCHEMA,
)
from app.services.thin_wordpress_adapter import (
    thin_wordpress_adapter_manifest,
    thin_wordpress_adapter_capabilities,
)

def test_thin_wordpress_adapter_manifest_preserves_backend_authority():
    m=thin_wordpress_adapter_manifest()
    assert m["schema"]==THIN_WORDPRESS_ADAPTER_SCHEMA
    assert m["milestone"]=="12.0.6"
    assert m["adapter_type"]=="optional-wordpress-presentation-proxy"
    assert m["backend_authoritative"] is True
    assert m["wordpress_required"] is False
    assert m["wordpress_runtime_authority"] is False
    assert m["wordpress_identity_authority"] is False
    assert m["wordpress_session_authority"] is False
    assert m["wordpress_canonical_research_state"] is False
    assert m["wordpress_canonical_conversation_state"] is False
    assert m["wordpress_canonical_project_state"] is False
    assert m["wordpress_canonical_evidence_state"] is False
    assert m["browser_backend_key_exposure"] is False
    assert m["proxy_policy"]["arbitrary_paths_allowed"] is False
    assert m["proxy_policy"]["arbitrary_hosts_allowed"] is False
    assert m["proxy_policy"]["arbitrary_methods_allowed"] is False
    assert m["proxy_policy"]["fixed_operation_allowlist"] is True
    assert m["proxy_policy"]["backend_failure_behavior"]=="fail-closed-no-wordpress-research-fallback"
    assert m["next_boundary"]=="neural-research-intelligence-foundation"

def test_adapter_operation_catalog_is_fixed_and_bounded():
    assert "retrieve" in READ_OPERATIONS
    assert "project-create" in WRITE_OPERATIONS
    assert "session-create" in WRITE_OPERATIONS
    assert "session-turn-add" in WRITE_OPERATIONS
    assert "session-snapshot-freeze" in WRITE_OPERATIONS
    assert len(ALL_OPERATIONS)==len(set(ALL_OPERATIONS))
    assert len(ALL_OPERATIONS) <= 20

def test_adapter_capabilities():
    c=thin_wordpress_adapter_capabilities()
    assert c["milestone"]=="12.0.6"
    assert c["backend_authoritative"] is True
    assert c["wordpress_required"] is False
    assert c["fixed_operation_allowlist"] is True
    assert c["operation_count"]==len(ALL_OPERATIONS)
    assert c["read_operation_count"]==len(READ_OPERATIONS)
    assert c["write_operation_count"]==len(WRITE_OPERATIONS)
    assert c["next_boundary"]=="neural-research-intelligence-foundation"

def test_backend_routes_and_health_advertise_adapter():
    from app.main import app
    client=TestClient(app)

    manifest=client.get("/v1/research-librarian/wordpress-adapter/manifest")
    assert manifest.status_code==200
    data=manifest.json()["data"]
    assert data["milestone"]=="12.0.6"
    assert data["wordpress_required"] is False

    denied=client.get("/v1/research-librarian/wordpress-adapter/capabilities")
    assert denied.status_code==401

    allowed=client.get(
        "/v1/research-librarian/wordpress-adapter/capabilities",
        headers={"X-SC-RL-Key":"test-key"},
    )
    assert allowed.status_code==200
    assert allowed.json()["data"]["fixed_operation_allowlist"] is True

    health=client.get("/health")
    assert health.status_code==200
    body=health.json()
    assert body["version"]=="12.3.0"
    assert body["thin_wordpress_adapter"] is True
    assert body["thin_wordpress_adapter_contract"]=="2.0"
    assert body["wordpress_required"] is False

def test_independent_api_moves_to_state_migration_boundary():
    from app.services.independent_research_librarian_api import api_manifest, capabilities
    m=api_manifest()
    c=capabilities()
    assert m["scope"]["identity_sessions"] is True
    assert m["scope"]["thin_wordpress_adapter"] is True
    assert m["next_boundary"]=="cross-language-entity-toponym-resolution"
    assert c["milestone"]=="12.3.0"
    assert c["thin_wordpress_adapter"] is True
