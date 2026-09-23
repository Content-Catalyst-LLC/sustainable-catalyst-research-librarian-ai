from __future__ import annotations

import asyncio
from pathlib import Path

from app.collaboration import normalize_room
from app.contracts.research_sync import (
    CORE_RESEARCH_SYNC_SCHEMA,
    CoreProjectSynchronizationPlanRequest,
    CoreProjectSynchronizationRequest,
)
from app.library_context import normalize_library_object, normalize_research_context
from app.platform_v7 import normalize_project
from app.store import KnowledgeStore
import app.services.core_research_sync as sync
import app.services.platform_core_integration as integration


def _store(tmp_path: Path) -> KnowledgeStore:
    s = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    project = normalize_project({"project_id":"project-880","title":"Carbon systems study","objective":"Trace evidence and models.","owner_ref":"owner-1","visibility":"private"})
    s.save_research_project(project)
    s.save_research_context(normalize_research_context({"context_id":"context-880","title":"Current project context","owner_ref":"owner-1","project_id":"project-880","scopes":["current-project"]}))
    s.save_research_room(normalize_room({"room_id":"room-880","title":"Review room","objective":"Review source evidence.","owner_ref":"owner-1","project_id":"project-880"}))
    s.save_library_object(normalize_library_object({"object_id":"source-880","object_type":"source","title":"Systems evidence paper","owner_ref":"owner-1","source_scope":"current-project","relationships":{"project_ids":["project-880"]},"payload":{"doi":"10.8800/source"}}))
    s.save_project_entity({"entity_id":"libref-880","project_id":"project-880","entity_type":"library-object-ref","title":"Systems evidence paper","payload":{"library_object_id":"source-880"}})
    s.save_project_entity({"entity_id":"entity-880","project_id":"project-880","entity_type":"dataset","title":"Study dataset","payload":{"rows":42}})
    return s


def test_plan_maps_project_context_room_source_and_entity(monkeypatch, tmp_path: Path) -> None:
    local = _store(tmp_path)
    monkeypatch.setattr(sync, "store", local)
    plan = sync.build_project_sync_plan(CoreProjectSynchronizationPlanRequest(local_project_id="project-880"))
    assert plan["schema"] == CORE_RESEARCH_SYNC_SCHEMA
    roles = {item["role"] for item in plan["bindings"]}
    assert {"local_project_identity","research_context","research_room","research_material","project_entity"} <= roles
    assert all(item["product_key"] == "research_librarian" for item in plan["bindings"])
    assert all(edge["provenance"]["declared_not_inferred"] is True for edge in plan["dependencies"])
    assert plan["governance"]["synchronization_does_not_determine_truth"] is True


def test_project_sync_creates_frozen_core_state_and_replays_idempotently(monkeypatch, tmp_path: Path) -> None:
    local = _store(tmp_path)
    monkeypatch.setattr(sync, "store", local)
    monkeypatch.setattr(integration, "store", local)

    class FakeCore:
        def __init__(self):
            self.project_calls=0; self.state_calls=0; self.version_calls=0; self.bindings=[]; self.dependencies=[]; self.freeze_calls=0; self.snapshot_calls=0
        async def create_unified_research_project(self, payload):
            self.project_calls += 1
            data = payload.get("data") or payload
            return {"id": data["project_entity_id"], "project_entity_id": data["project_entity_id"], "metadata": data["metadata"]}
        async def research_project_bundle(self, project_id):
            return {"project":{"project_entity_id":project_id,"metadata":{"source_local_project_id":"project-880"}}}
        async def create_project_state(self, payload):
            self.state_calls += 1; return {"id":"core-state-880", **payload}
        async def create_project_state_version(self, state_id, payload):
            self.version_calls += 1; return {"id":"core-version-1","state_id":state_id,"version":1,**payload}
        async def add_project_state_binding(self, state_id, version, payload):
            self.bindings.append(payload); return {"id":f"b{len(self.bindings)}",**payload}
        async def add_project_state_dependency(self, state_id, version, payload):
            self.dependencies.append(payload); return {"id":f"d{len(self.dependencies)}",**payload}
        async def freeze_project_state_version(self, state_id, version, payload=None):
            self.freeze_calls += 1; return {"state_id":state_id,"version":version,"status":"frozen","content_hash":"f"*64}
        async def snapshot_project_state(self, state_id, payload=None):
            self.snapshot_calls += 1; return {"id":"snapshot-880","state_id":state_id,"revision":1,"content_hash":"e"*64}

    fake=FakeCore()
    request=CoreProjectSynchronizationRequest(local_project_id="project-880")
    first=asyncio.run(sync.synchronize_project_research_objects(request, fake))
    second=asyncio.run(sync.synchronize_project_research_objects(request, fake))
    assert first["idempotent_replay"] is False
    assert first["state_id"] == "core-state-880" and first["version"] == 1
    assert first["frozen"]["status"] == "frozen"
    assert first["snapshot"]["id"] == "snapshot-880"
    assert second["idempotent_replay"] is True
    assert fake.project_calls == 1 and fake.state_calls == 1 and fake.version_calls == 1
    assert fake.freeze_calls == 1 and fake.snapshot_calls == 1
    assert len(fake.bindings) >= 5 and len(fake.dependencies) >= 4
    tracker=local.platform_core_binding("research-project-state","project-880")
    assert tracker and tracker["sync_state"] == "synced" and tracker["core_version"] == 1


def test_dry_run_never_calls_core(monkeypatch, tmp_path: Path) -> None:
    local = _store(tmp_path)
    monkeypatch.setattr(sync, "store", local)
    result=asyncio.run(sync.synchronize_project_research_objects(CoreProjectSynchronizationRequest(local_project_id="project-880",dry_run=True), object()))
    assert result["dry_run"] is True
    assert result["plan"]["bindings"]


def test_v880_routes_and_capability_boundaries() -> None:
    from app.main import app
    paths={getattr(route,"path","") for route in app.routes}
    assert "/v1/core/research-sync/capabilities" in paths
    assert "/v1/core/research-sync/plan" in paths
    assert "/v1/core/research-sync/synchronize" in paths
    body=sync.capabilities()
    assert body["schema"] == CORE_RESEARCH_SYNC_SCHEMA
    assert body["immutable_project_state_versions"] is True
    assert body["automatic_truth_promotion"] is False
    assert body["automatic_workflow_advancement"] is False
