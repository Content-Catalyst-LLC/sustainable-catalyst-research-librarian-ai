import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient

from app.contracts.independent_research_librarian_api import *
from app.services.independent_research_librarian_api import (
    IndependentAPIContractSnapshotStore,
    api_manifest,
    envelope,
    capabilities,
)

def test_manifest_is_versioned_and_wordpress_independent():
    m=api_manifest()
    assert m["api_version"]=="v1"
    assert m["base_path"]=="/v1/research-librarian"
    assert m["runtime_authority"]=="python-fastapi-backend"
    assert m["wordpress_required"] is False
    assert m["response_envelope"]==INDEPENDENT_API_ENVELOPE_SCHEMA
    assert m["stability"]["breaking_changes_require_new_api_version"] is True
    assert m["scope"]["persistent_conversations"] is True
    assert m["scope"]["identity_sessions"] is True

def test_envelope_is_stable():
    e=envelope({"x":1},resource="test")
    assert e["schema"]==INDEPENDENT_API_ENVELOPE_SCHEMA
    assert e["api_version"]=="v1"
    assert e["ok"] is True
    assert e["resource"]=="test"
    assert e["data"]["x"]==1

def test_contract_snapshot(tmp_path):
    s=IndependentAPIContractSnapshotStore(tmp_path/"api.sqlite3")
    snap=s.freeze(IndependentAPIContractSnapshotRequest(actor_ref="architect"))
    assert snap["schema"]==INDEPENDENT_API_SNAPSHOT_SCHEMA
    assert len(snap["snapshot_hash"])==64
    assert snap["governance"]["wordpress-not-required"] is True
    assert snap["governance"]["snapshot-does-not-authorize-access"] is True

def test_routes_auth_and_manifest():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
      "/v1/research-librarian/manifest",
      "/v1/research-librarian/capabilities",
      "/v1/research-librarian/status",
      "/v1/research-librarian/retrieve",
      "/v1/research-librarian/projects",
      "/v1/research-librarian/projects/{project_id}",
      "/v1/research-librarian/projects/{project_id}/investigations",
      "/v1/research-librarian/scientist-environments/{scientist_environment_id}",
      "/v1/research-librarian/scientist-environments/{scientist_environment_id}/dossier",
      "/v1/research-librarian/runtime-authority",
      "/v1/research-librarian/contract-snapshots/freeze",
    }
    assert not(required-paths)
    client=TestClient(app)
    assert client.get("/v1/research-librarian/manifest").status_code in {401,503}
    ok=client.get("/v1/research-librarian/manifest",headers={"X-SC-RL-Key":"test-key"})
    assert ok.status_code==200
    body=ok.json()
    assert body["schema"]==INDEPENDENT_API_ENVELOPE_SCHEMA
    assert body["data"]["wordpress_required"] is False
    assert body["data"]["authentication"]["scheme"]=="backend-key-or-identity-session-v1"

def test_capabilities_boundary():
    c=capabilities()
    assert c["milestone"]=="12.0.5"
    assert c["direct_backend_access"] is True
    assert c["wordpress_required"] is False
    assert c["persistent_conversations"] is True
    assert c["identity_sessions"] is True
    assert c["breaking_changes_require_new_api_version"] is True
