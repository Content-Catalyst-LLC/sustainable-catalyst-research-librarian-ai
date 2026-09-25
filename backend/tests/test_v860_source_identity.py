from __future__ import annotations

from pathlib import Path
import pytest

from app.source_identity import (
    SourceGraphStore,
    SourceIdentityConflict,
    identity_candidate,
    normalize_identifier,
    normalize_url,
)


def store_at(tmp_path: Path) -> SourceGraphStore:
    return SourceGraphStore(sqlite_path=tmp_path / "source_graph.sqlite3")


def test_normalizes_stable_identifiers_and_tracking_urls():
    assert normalize_identifier("doi", "https://doi.org/10.1234/ABC.9") == "10.1234/abc.9"
    assert normalize_identifier("arxiv", "arXiv:2401.01234v3") == "2401.01234"
    assert normalize_identifier("pmid", "PMID: 12345678") == "12345678"
    assert normalize_identifier("isbn", "978-1-4028-9462-6") == "9781402894626"
    assert normalize_url("https://EXAMPLE.org/paper/?utm_source=x&b=2&a=1#frag") == "https://example.org/paper?a=1&b=2"


def test_same_doi_resolves_to_one_canonical_source(tmp_path: Path):
    graph = store_at(tmp_path)
    first = graph.resolve({"title": "First title", "identifiers": {"doi": ["10.1000/ABC"]}})
    second = graph.resolve({"title": "Updated title", "identifiers": {"doi": ["https://doi.org/10.1000/abc"]}})
    assert first["canonical_source_id"] == second["canonical_source_id"]
    assert second["resolution"] == "stable-identifier"
    assert second["source"]["title"] == "Updated title"


def test_bibliographic_fingerprint_deduplicates_identifierless_copies(tmp_path: Path):
    graph = store_at(tmp_path)
    a = graph.resolve({"title": "Systems Thinking for Resilience", "authors": ["Ada Researcher"], "publication_year": 2026, "source_url": ""})
    b = graph.resolve({"title": "Systems Thinking for Resilience", "authors": ["Ada Researcher"], "publication_year": 2026, "filename": "accepted-manuscript.pdf"})
    assert a["canonical_source_id"] == b["canonical_source_id"]
    assert b["resolution"] == "bibliographic-fingerprint"
    assert len(b["source"]["instances"]) == 1


def test_conflicting_strong_identifiers_fail_closed(tmp_path: Path):
    graph = store_at(tmp_path)
    graph.resolve({"title": "A", "identifiers": {"doi": ["10.1000/a"]}})
    graph.resolve({"title": "B", "identifiers": {"doi": ["10.1000/b"]}})
    with pytest.raises(SourceIdentityConflict):
        graph.resolve({"title": "Conflict", "identifiers": {"doi": ["10.1000/a", "10.1000/b"]}})


def test_reference_identifier_creates_stub_then_hydrates_same_node(tmp_path: Path):
    graph = store_at(tmp_path)
    citing = graph.resolve({
        "title": "Citing paper",
        "identifiers": {"doi": ["10.2000/citing"]},
        "references": [{"index": 1, "raw": "Referenced work. doi:10.3000/target", "identifiers": {"doi": ["10.3000/target"]}}],
    })
    view = graph.graph(citing["canonical_source_id"])
    assert view["outgoing_count"] == 1
    stub_id = view["outgoing"][0]["cited_source_id"]
    assert graph.get(stub_id)["state"] == "stub"

    hydrated = graph.resolve({"title": "Referenced work", "authors": ["Researcher, B"], "identifiers": {"doi": ["https://doi.org/10.3000/TARGET"]}})
    assert hydrated["canonical_source_id"] == stub_id
    assert hydrated["source"]["state"] == "resolved"
    assert graph.graph(stub_id)["incoming_count"] == 1


def test_parsed_document_reference_identifiers_do_not_identify_citing_work():
    candidate = identity_candidate({
        "parsed_document": {
            "title": "Main study",
            "authors": ["A. Author"],
            "identifiers": {"doi": ["10.4000/main", "10.5000/cited"]},
            "references": [{"raw": "Cited", "identifiers": {"doi": ["10.5000/cited"]}}],
        }
    })
    assert candidate["identifiers"]["doi"] == ["10.4000/main"]


def test_multiple_instances_can_share_canonical_work(tmp_path: Path):
    graph = store_at(tmp_path)
    source = graph.resolve({"title": "A work", "identifiers": {"doi": ["10.6000/work"]}, "source_url": "https://publisher.example/work"})
    graph.resolve({"title": "A work", "identifiers": {"doi": ["10.6000/work"]}, "source_url": "https://repository.example/work.pdf", "filename": "work.pdf"})
    current = graph.get(source["canonical_source_id"])
    assert len(current["instances"]) == 2


def test_api_exposes_source_identity_capabilities_and_resolution():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    headers = {"X-SC-RL-Key": "test-key"}
    cap = client.get("/v1/sources/capabilities", headers=headers)
    assert cap.status_code == 200
    body = cap.json()
    assert body["version"] == "10.0.0"
    assert body["schema"] == "sc-research-librarian-source-identity/1.0"
    assert body["citation_graph"] is True

    resolved = client.post(
        "/v1/sources/resolve",
        headers=headers,
        json={"title": "API identity test", "identifiers": {"doi": ["10.7777/api.identity"]}},
    )
    assert resolved.status_code == 200
    result = resolved.json()["result"]
    assert result["canonical_source_id"].startswith("source:")
    source_id = result["canonical_source_id"]
    graph = client.get(f"/v1/sources/{source_id}/graph", headers=headers)
    assert graph.status_code == 200
    assert graph.json()["graph"]["canonical_source_id"] == source_id
