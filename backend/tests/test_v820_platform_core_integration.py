import asyncio
from pathlib import Path

import httpx

from app.clients.platform_core import PlatformCoreClient, compatibility
from app.contracts.platform_core import (
    CORE_INTEGRATION_SCHEMA,
    CoreResearchObjectPromotionRequest,
    CoreUnifiedProjectSyncRequest,
)
from app.store import KnowledgeStore
import app.services.platform_core_integration as integration


def test_core_330_compatibility_contract() -> None:
    check = compatibility("3.3.0")
    assert check.compatible is True
    assert compatibility("3.2.9").compatible is False
    assert compatibility("4.0.0").compatible is False


def test_platform_core_client_uses_private_v1_contract_and_write_key() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/health":
            return httpx.Response(200, json={"ok": True, "version": "3.3.0"})
        if request.url.path == "/v1/research-objects":
            assert request.headers["X-SC-API-Key"] == "core-secret"
            return httpx.Response(200, json={"id": "sc:research-project:test", "object_type": "research-project"})
        return httpx.Response(404, json={"detail": "not found"})

    client = PlatformCoreClient(
        base_url="http://core.test",
        write_api_key="core-secret",
        retry_limit=0,
        transport=httpx.MockTransport(handler),
    )
    health = asyncio.run(client.health())
    assert health["version"] == "3.3.0"
    created = asyncio.run(client.create_research_object({"object_type": "research-project", "name": "Test"}))
    assert created["id"] == "sc:research-project:test"
    assert [request.url.path for request in seen] == ["/health", "/v1/research-objects"]


def test_platform_core_binding_store_is_durable_and_summarized(tmp_path: Path) -> None:
    local = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    saved = local.save_platform_core_binding({
        "schema": "sc-research-librarian-core-binding/1.0",
        "binding_key": "research-project:local-1",
        "local_kind": "research-project",
        "local_id": "local-1",
        "core_kind": "unified-research-project",
        "core_id": "sc:research-project:one",
        "sync_state": "synced",
        "contract_version": CORE_INTEGRATION_SCHEMA,
        "payload_hash": "a" * 64,
        "idempotency_key": "rl-8.2:test",
        "created_utc": "2026-09-22T20:00:00+00:00",
        "updated_utc": "2026-09-22T20:00:00+00:00",
        "last_error": "",
    })
    assert saved["core_id"] == "sc:research-project:one"
    assert local.platform_core_binding("research-project", "local-1")["sync_state"] == "synced"
    summary = local.platform_core_integration_summary()
    assert summary["binding_count"] == 1
    assert summary["sync_state_counts"]["synced"] == 1


def test_research_object_promotion_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    local = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    monkeypatch.setattr(integration, "store", local)

    class FakeCore:
        def __init__(self):
            self.calls = 0

        async def create_research_object(self, payload):
            self.calls += 1
            return {"id": payload["entity_id"], "object_type": payload["object_type"], "metadata": payload["metadata"]}

        async def research_object(self, entity_id):
            return {"id": entity_id, "object_type": "research-project"}

    fake = FakeCore()
    request = CoreResearchObjectPromotionRequest(
        local_object_id="rl-project-42",
        object_type="research-project",
        name="Carbon Systems Review",
        attributes={"owner_product": "research-librarian", "lifecycle_state": "draft"},
    )
    first = asyncio.run(integration.promote_research_object(request, fake))
    second = asyncio.run(integration.promote_research_object(request, fake))
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True
    assert fake.calls == 1
    assert first["binding"]["core_id"].startswith("sc:research-project:research-librarian:")


def test_unified_project_sync_binds_core_project(monkeypatch, tmp_path: Path) -> None:
    local = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    monkeypatch.setattr(integration, "store", local)

    class FakeCore:
        async def create_unified_research_project(self, payload):
            return {"project": {"id": payload["project_entity_id"]}, "unified_profile": {"owner_product": "research-librarian"}}

        async def research_project_bundle(self, project_id):
            return {"project": {"entity_id": project_id}}

    request = CoreUnifiedProjectSyncRequest(
        local_project_id="masters-carbon-project",
        title="Carbon and Sustainability Research",
        research_question="How can evidence be synthesized reproducibly?",
    )
    result = asyncio.run(integration.synchronize_unified_project(request, FakeCore()))
    assert result["binding"]["sync_state"] == "synced"
    assert result["binding"]["core_id"].startswith("sc:research-project:research-librarian:")
    assert result["core"]["unified_profile"]["owner_product"] == "research-librarian"
