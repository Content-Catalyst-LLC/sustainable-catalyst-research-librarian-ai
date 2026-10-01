import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient

from app.contracts.runtime_authority_wordpress_decoupling import *
from app.services.runtime_authority_wordpress_decoupling import (
    RuntimeAuthorityCertificationStore,
    runtime_authority_manifest,
    wordpress_adapter_contract,
    dependency_map,
    independence_readiness,
    capabilities,
)

def test_runtime_authority_manifest():
    m=runtime_authority_manifest()
    assert m["runtime_authority"]=="python-fastapi-backend"
    assert m["python_runtime_authoritative"] is True
    assert m["wordpress_required_for_backend_boot"] is False
    assert m["wordpress_required_for_research_api"] is False
    assert "canonical-research-state" in m["wordpress_must_not_own"]

def test_wordpress_is_thin_optional_adapter():
    c=wordpress_adapter_contract()
    assert c["adapter_type"]=="optional-wordpress-interface"
    assert c["backend_is_source_of_runtime_truth"] is True
    assert c["failure_behavior"]["wordpress_unavailable"]=="backend-remains-operational"
    assert c["compatibility"]["independent_web_app_target_supported"] is True

def test_dependency_map_and_readiness():
    d=dependency_map()
    assert d["wordpress_is_runtime_dependency"] is False
    assert "wordpress" in d["optional_interfaces"]
    r=independence_readiness()
    assert r["ready_for_progressive_wordpress_decoupling"] is True
    assert r["blockers"]==[]
    assert r["next_boundary"]=="independent-research-librarian-api-v1"

def test_snapshot_is_durable_and_not_cutover(tmp_path):
    s=RuntimeAuthorityCertificationStore(tmp_path/"authority.sqlite3")
    snap=s.freeze_snapshot(RuntimeAuthoritySnapshotRequest(actor_ref="architect"))
    assert snap["schema"]==RUNTIME_AUTHORITY_SNAPSHOT_SCHEMA
    assert len(snap["snapshot_hash"])==64
    assert snap["governance"]["snapshot-is-architecture-certification-not-cutover"] is True
    assert snap["independence_readiness"]["ready_for_progressive_wordpress_decoupling"] is True

def test_api_routes_and_health_metadata():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
      "/v1/core/runtime-authority/capabilities",
      "/v1/core/runtime-authority/manifest",
      "/v1/core/runtime-authority/wordpress-adapter-contract",
      "/v1/core/runtime-authority/dependency-map",
      "/v1/core/runtime-authority/independence-readiness",
      "/v1/core/runtime-authority/snapshots/freeze",
    }
    assert not(required-paths)
    client=TestClient(app)
    health=client.get("/health")
    assert health.status_code==200
    h=health.json()
    assert h["runtime_authority"]=="python-fastapi-backend"
    assert h["wordpress_required"] is False
    assert client.get("/v1/core/runtime-authority/manifest").status_code in {401,503}
    ok=client.get("/v1/core/runtime-authority/manifest",headers={"X-SC-RL-Key":"test-key"})
    assert ok.status_code==200 and ok.json()["python_runtime_authoritative"] is True

def test_capabilities():
    c=capabilities()
    assert c["milestone"]=="12.0.1"
    assert c["python_runtime_authority"] is True
    assert c["wordpress_optional_interface"] is True
    assert c["wordpress_required_for_backend_runtime"] is False
    assert c["automatic_data_migration"] is False
    assert c["automatic_cutover"] is False
