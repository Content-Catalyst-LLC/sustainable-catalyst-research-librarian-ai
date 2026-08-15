from __future__ import annotations

import os
import uuid

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module
from app.federated_discovery import (
    FEDERATED_RESULT_SCHEMA,
    deduplicate_results,
    normalize_arxiv,
    normalize_crossref,
    normalize_europe_pmc,
    normalize_open_library,
    normalize_openalex,
    result_to_library_payload,
)

client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


def test_provider_normalizers_preserve_identity_and_external_boundary() -> None:
    openalex = normalize_openalex({"results": [{
        "id": "https://openalex.org/W1", "display_name": "Shared Work", "publication_year": 2025,
        "doi": "https://doi.org/10.1000/xyz", "type": "article",
        "authorships": [{"author": {"display_name": "Ada Researcher"}}],
        "open_access": {"is_oa": True, "oa_status": "gold"},
        "primary_location": {"landing_page_url": "https://example.org/work"},
    }]})[0]
    crossref = normalize_crossref({"message": {"items": [{
        "DOI": "10.1000/XYZ", "title": ["Shared Work"], "type": "journal-article",
        "author": [{"given": "Ada", "family": "Researcher"}], "issued": {"date-parts": [[2025]]},
        "URL": "https://doi.org/10.1000/xyz",
    }]}})[0]
    epmc = normalize_europe_pmc({"resultList": {"result": [{
        "id": "12345", "source": "MED", "title": "Biomedical Work", "pubYear": "2024",
        "authorString": "A Researcher, B Scholar", "doi": "10.2000/abc", "isOpenAccess": "Y",
    }]}})[0]
    books = normalize_open_library({"docs": [{"key": "/works/OL1W", "title": "Systems Book", "author_name": ["Book Author"], "first_publish_year": 2019, "isbn": ["978-1-23456-789-7"]}]})[0]
    atom = '''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom"><entry><id>https://arxiv.org/abs/2601.00001</id><updated>2026-01-01T00:00:00Z</updated><published>2026-01-01T00:00:00Z</published><title>Arxiv Work</title><summary>Preprint abstract.</summary><author><name>Pre Print</name></author><arxiv:doi>10.3000/arxiv</arxiv:doi></entry></feed>'''
    arxiv = normalize_arxiv(atom)[0]

    for row in [openalex, crossref, epmc, books, arxiv]:
        assert row["schema"] == FEDERATED_RESULT_SCHEMA
        assert row["provider_id"]
        assert row["provider_record_id"]
        assert row["governance"]["external_discovery_only"] is True
        assert row["governance"]["not_sustainable_catalyst_editorial"] is True
        assert row["governance"]["not_verified_evidence"] is True

    merged = deduplicate_results([openalex, crossref])
    assert len(merged) == 1
    assert set(merged[0]["providers"]) == {"openalex", "crossref"}
    assert len(merged[0]["provider_records"]) == 2

    library_payload = result_to_library_payload(merged[0], owner_ref="wp-user-1", project_id="project-1")
    assert library_payload["source_scope"] == "external-reference"
    assert library_payload["visibility"] == "private"
    assert library_payload["payload"]["governance"]["not_editorial_approval"] is True
    assert set(library_payload["payload"]["providers"]) == {"openalex", "crossref"}


def test_federated_search_persists_and_requires_explicit_result_save(monkeypatch) -> None:
    suffix = _suffix()
    owner = f"wp-user-fed-{suffix}"
    project = client.post("/v1/projects", headers=HEADERS, json={"title": f"Federated project {suffix}", "owner_ref": owner}).json()
    context = client.post("/v1/research/contexts", headers=HEADERS, json={
        "title": "Federated context", "owner_ref": owner, "scopes": ["current-project"], "project_id": project["project_id"], "active": True,
    }).json()

    result = normalize_crossref({"message": {"items": [{
        "DOI": f"10.5555/{suffix}", "title": ["Federated Result"], "type": "journal-article",
        "author": [{"given": "Test", "family": "Author"}], "issued": {"date-parts": [[2026]]},
        "URL": f"https://doi.org/10.5555/{suffix}",
    }]}})[0]

    async def fake_run_federated_search(**kwargs):
        return {
            "schema": "sc-federated-research-search/1.0",
            "search_id": f"federated-search-{suffix}",
            "query": kwargs["query"],
            "providers": ["crossref"],
            "provider_outcomes": [{"provider_id": "crossref", "ok": True, "count": 1, "error": ""}],
            "status": "complete",
            "result_count": 1,
            "results": [result],
            "created_utc": "2026-08-15T12:00:00+00:00",
            "governance": {"external_discovery_only": True, "explicit_library_save_required": True},
        }

    monkeypatch.setattr(main_module, "run_federated_search", fake_run_federated_search)
    searched = client.post("/v1/federation/search", headers=HEADERS, json={
        "query": "federated research", "owner_ref": owner, "context_id": context["context_id"], "providers": ["crossref"],
    })
    assert searched.status_code == 200, searched.text
    body = searched.json()
    assert body["project_id"] == project["project_id"]
    assert body["result_count"] == 1
    assert "source_scope" not in body["results"][0]  # discovery is not a Library import
    assert body["results"][0]["governance"]["external_discovery_only"] is True

    before = client.get(f"/v1/library/objects?owner_ref={owner}&source_scope=external-reference", headers=HEADERS)
    assert before.status_code == 200
    assert not any(item.get("title") == "Federated Result" for item in before.json()["objects"])

    saved = client.post(f"/v1/federation/searches/{body['search_id']}/results/{result['result_id']}/save", headers=HEADERS, json={
        "owner_ref": owner, "context_id": context["context_id"], "tags": ["federated"],
    })
    assert saved.status_code == 200, saved.text
    imported = saved.json()
    assert imported["schema"] == "sc-federated-library-import/1.0"
    assert imported["library_object"]["source_scope"] == "external-reference"
    assert imported["library_object"]["owner_ref"] == owner
    assert imported["library_object"]["relationships"]["project_ids"] == [project["project_id"]]
    assert imported["governance"]["not_editorial_approval"] is True

    backup = client.post(f"/v1/projects/{project['project_id']}/backup", headers=HEADERS)
    assert backup.status_code == 200, backup.text
    assert any(item["search_id"] == body["search_id"] for item in backup.json()["payload"]["federated_searches"])


def test_federated_search_owner_boundary(monkeypatch) -> None:
    suffix = _suffix()
    owner = f"wp-user-fed-owner-{suffix}"
    outsider = f"wp-user-fed-outsider-{suffix}"

    async def fake_run_federated_search(**kwargs):
        return {"schema": "sc-federated-research-search/1.0", "search_id": f"federated-search-{suffix}", "query": kwargs["query"], "providers": ["open-library"], "provider_outcomes": [], "status": "complete", "result_count": 0, "results": [], "created_utc": "2026-08-15T12:00:00+00:00", "governance": {"external_discovery_only": True}}

    monkeypatch.setattr(main_module, "run_federated_search", fake_run_federated_search)
    searched = client.post("/v1/federation/search", headers=HEADERS, json={"query": "books", "owner_ref": owner, "providers": ["open-library"]})
    assert searched.status_code == 200
    search_id = searched.json()["search_id"]
    denied = client.get(f"/v1/federation/searches/{search_id}?owner_ref={outsider}", headers=HEADERS)
    assert denied.status_code == 403


def test_federated_links_reject_non_http_schemes() -> None:
    row = normalize_crossref({"message": {"items": [{
        "DOI": "10.9999/safe", "title": ["Unsafe Link Record"], "type": "journal-article",
        "URL": "javascript:alert(1)",
    }]}})[0]
    assert row["landing_url"] == ""
    library_payload = result_to_library_payload(row, owner_ref="wp-user-link-safety")
    assert library_payload["provenance"]["canonical_url"] == ""
