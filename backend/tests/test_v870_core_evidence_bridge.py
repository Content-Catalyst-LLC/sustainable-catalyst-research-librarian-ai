from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from app.clients.platform_core import PlatformCoreClient
from app.contracts.evidence_bridge import (
    CORE_EVIDENCE_BRIDGE_SCHEMA,
    CorePassageEvidencePromotionRequest,
    CoreSourceSnapshotPromotionRequest,
)
from app.source_identity import SourceGraphStore
from app.store import KnowledgeStore
import app.services.core_evidence_bridge as bridge


def _source_graph(tmp_path: Path) -> tuple[SourceGraphStore, dict]:
    graph = SourceGraphStore(sqlite_path=tmp_path / "source-graph.sqlite3")
    resolved = graph.resolve({
        "title": "Evidence Systems Study",
        "authors": ["Ada Researcher"],
        "publication_year": 2026,
        "identifiers": {"doi": ["10.8700/evidence.bridge"]},
        "source_url": "https://example.org/evidence-study",
        "media_type": "text/html",
        "content_fingerprint": "a" * 64,
    })
    return graph, resolved


def test_platform_core_client_uses_evidence_ledger_contracts() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/v1/source-snapshots":
            assert request.headers["X-SC-API-Key"] == "core-secret"
            body = __import__("json").loads(request.content)
            return httpx.Response(201, json={"id": body["id"], "content_hash": "a" * 64, "metadata": body["metadata"]})
        if request.url.path == "/v1/evidence-records":
            assert request.headers["X-SC-API-Key"] == "core-secret"
            body = __import__("json").loads(request.content)
            return httpx.Response(201, json={"id": body["id"], "review_status": body["review_status"], "provenance": body["provenance"]})
        return httpx.Response(404, json={"detail": "not found"})

    client = PlatformCoreClient(base_url="http://core.test", write_api_key="core-secret", retry_limit=0, transport=httpx.MockTransport(handler))
    snap = asyncio.run(client.create_source_snapshot({"id": "sc:snapshot:test", "content_hash": "a" * 64, "metadata": {}, "actor": "test"}))
    evidence = asyncio.run(client.create_evidence_record({"id": "sc:evidence:test", "evidence_type": "source-passage", "stance": "neutral", "source_snapshot_id": snap["id"], "review_status": "unreviewed", "provenance": {}, "actor": "test"}))
    assert evidence["review_status"] == "unreviewed"
    assert seen == ["/v1/source-snapshots", "/v1/evidence-records"]


def test_source_snapshot_promotion_is_idempotent_and_bound(monkeypatch, tmp_path: Path) -> None:
    graph, resolved = _source_graph(tmp_path)
    local = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    monkeypatch.setattr(bridge, "get_source_graph_store", lambda: graph)
    monkeypatch.setattr(bridge, "store", local)

    class FakeCore:
        def __init__(self): self.calls = 0
        async def create_source_snapshot(self, payload):
            self.calls += 1
            return {"id": payload["id"], "content_hash": payload["content_hash"], "metadata": payload["metadata"]}
        async def source_snapshot(self, snapshot_id):
            return {"id": snapshot_id, "metadata": {"canonical_source_id": resolved["canonical_source_id"]}}

    fake = FakeCore()
    request = CoreSourceSnapshotPromotionRequest(
        canonical_source_id=resolved["canonical_source_id"],
        local_snapshot_id="library-copy-1",
        content_hash="a" * 64,
    )
    first = asyncio.run(bridge.promote_source_snapshot(request, fake))
    second = asyncio.run(bridge.promote_source_snapshot(request, fake))
    assert first["schema"] == CORE_EVIDENCE_BRIDGE_SCHEMA
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True
    assert fake.calls == 1
    binding = local.platform_core_binding("source-snapshot", "library-copy-1")
    assert binding and binding["sync_state"] == "synced"
    assert binding["canonical_source_id"] == resolved["canonical_source_id"]


def test_citation_stub_cannot_be_promoted_as_snapshot(monkeypatch, tmp_path: Path) -> None:
    graph = SourceGraphStore(sqlite_path=tmp_path / "source-graph.sqlite3")
    citing = graph.resolve({
        "title": "Citing work",
        "identifiers": {"doi": ["10.8700/citing"]},
        "references": [{"index": 1, "raw": "Stub target doi:10.8700/stub", "identifiers": {"doi": ["10.8700/stub"]}}],
    })
    stub_id = graph.graph(citing["canonical_source_id"])["outgoing"][0]["cited_source_id"]
    monkeypatch.setattr(bridge, "get_source_graph_store", lambda: graph)
    with pytest.raises(ValueError, match="stubs cannot be promoted"):
        asyncio.run(bridge.promote_source_snapshot(CoreSourceSnapshotPromotionRequest(canonical_source_id=stub_id, content_hash="b" * 64), object()))


def test_passage_promotion_requires_snapshot_and_preserves_governance_defaults(monkeypatch, tmp_path: Path) -> None:
    graph, resolved = _source_graph(tmp_path)
    local = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    monkeypatch.setattr(bridge, "get_source_graph_store", lambda: graph)
    monkeypatch.setattr(bridge, "store", local)
    request = CorePassageEvidencePromotionRequest(
        local_evidence_id="passage-17",
        canonical_source_id=resolved["canonical_source_id"],
        source_snapshot_local_id="snapshot-17",
        statement="Observed passage text used as a governed evidence candidate.",
        passage_id="p17",
        section_path=["Results", "Sensitivity"],
        page_start=7,
        page_end=7,
    )
    with pytest.raises(bridge.CoreBindingConflict):
        asyncio.run(bridge.promote_passage_evidence(request, object()))

    local.save_platform_core_binding({
        "schema": "sc-research-librarian-core-binding/1.0",
        "binding_key": "source-snapshot:snapshot-17",
        "local_kind": "source-snapshot",
        "local_id": "snapshot-17",
        "core_kind": "source-snapshot",
        "core_id": "sc:snapshot:core:17",
        "sync_state": "synced",
        "contract_version": "sc-research-librarian-platform-core/1.0",
        "payload_hash": "c" * 64,
        "idempotency_key": "snapshot-17",
        "created_utc": "2026-09-23T14:00:00+00:00",
        "updated_utc": "2026-09-23T14:00:00+00:00",
        "canonical_source_id": resolved["canonical_source_id"],
    })

    class FakeCore:
        def __init__(self): self.payload = None; self.calls = 0
        async def create_evidence_record(self, payload):
            self.calls += 1; self.payload = payload
            return {"id": payload["id"], "stance": payload["stance"], "review_status": payload["review_status"], "provenance": payload["provenance"], "metadata": payload["metadata"]}
        async def evidence_record(self, evidence_id):
            return {"id": evidence_id, "provenance": {"canonical_source_id": resolved["canonical_source_id"]}}

    fake = FakeCore()
    first = asyncio.run(bridge.promote_passage_evidence(request, fake))
    second = asyncio.run(bridge.promote_passage_evidence(request, fake))
    assert first["idempotent_replay"] is False and second["idempotent_replay"] is True
    assert fake.calls == 1
    assert fake.payload["stance"] == "neutral"
    assert fake.payload["review_status"] == "unreviewed"
    assert "confidence" not in fake.payload
    assert fake.payload["source_snapshot_id"] == "sc:snapshot:core:17"
    assert fake.payload["provenance"]["automated_truth_judgment"] is False
    assert fake.payload["metadata"]["stance_supplied_explicitly"] is False
    assert fake.payload["metadata"]["confidence_supplied_explicitly"] is False


def test_bridge_capabilities_make_authority_boundary_explicit() -> None:
    cap = bridge.evidence_bridge_capabilities()
    assert cap["schema"] == CORE_EVIDENCE_BRIDGE_SCHEMA
    assert cap["automatic_claim_creation"] is False
    assert cap["automatic_stance_inference"] is False
    assert cap["automatic_confidence_inference"] is False
    assert cap["core_is_governed_evidence_authority"] is True


def test_api_registers_v870_evidence_bridge_routes() -> None:
    from fastapi.testclient import TestClient
    from app.main import app
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/v1/core/evidence/capabilities" in paths
    assert "/v1/core/evidence/source-snapshots/promote" in paths
    assert "/v1/core/evidence/passages/promote" in paths
    response = TestClient(app).get("/v1/core/evidence/capabilities", headers={"X-SC-RL-Key": "test-key"})
    assert response.status_code == 200
    body = response.json()
    assert body["release"] == "11.0.0"
    assert body["default_stance"] == "neutral"
    assert body["default_review_status"] == "unreviewed"
