from __future__ import annotations

import os
import uuid

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.evidence_quality import compare_sources, evidence_gaps, evaluate_source
from app.main import app


client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def _suffix() -> str:
    return uuid.uuid4().hex[:12]


def _source(title: str, level: str, provider: str, year: str, methodology: str = "available") -> dict:
    return {
        "object_type": "source",
        "title": title,
        "source_scope": "my-library",
        "provenance": {"provider": provider, "origin_system": "knowledge-library", "canonical_url": f"https://example.org/{title.lower().replace(' ', '-')}"},
        "payload": {
            "source_type": "research-report",
            "evidence_level": level,
            "publisher": provider,
            "publication_date": year,
            "methodology": {"state": methodology, "description": "Methods are documented." if methodology == "available" else ""},
            "citation": {"doi": "10.0000/example" if level == "primary" else ""},
            "access_state": "open",
            "limitations": ["Geographic coverage is limited."],
        },
    }


def test_source_evaluation_is_descriptive_and_never_truth_scored() -> None:
    evaluated = evaluate_source(_source("Primary evidence", "primary", "Institute A", "2025"))
    assert evaluated["schema"] == "sc-source-evaluation/1.0"
    assert evaluated["evidence_level"] == "primary"
    assert evaluated["publisher"] == "Institute A"
    assert evaluated["methodology"]["state"] == "available"
    assert evaluated["citation"]["available"] is True
    assert evaluated["governance"]["truth_score"] is None
    assert evaluated["governance"]["human_judgment_required"] is True
    assert "score" not in evaluated


def test_evidence_comparison_exposes_dimensions_without_automatic_winner() -> None:
    report = compare_sources([
        _source("Primary evidence", "primary", "Institute A", "2025"),
        _source("Secondary synthesis", "secondary", "Institute B", "2023", "partial"),
    ], "Compare these sources")
    assert report["schema"] == "sc-evidence-comparison/1.0"
    assert report["source_count"] == 2
    assert report["corpus"]["independent_provider_count"] == 2
    assert report["corpus"]["evidence_levels"]["primary"] == 1
    assert report["corpus"]["evidence_levels"]["secondary"] == 1
    assert report["governance"]["no_automatic_winner"] is True
    assert report["governance"]["no_truth_score"] is True
    assert any(item["dimension"] == "methodology" for item in report["dimensions"])


def test_evidence_gap_detection_surfaces_structural_missingness() -> None:
    weak = {
        "object_type": "source",
        "title": "Underspecified source",
        "source_scope": "my-library",
        "provenance": {"provider": "Single Provider"},
        "payload": {},
    }
    report = evidence_gaps([weak, {**weak, "title": "Second underspecified source"}], "Compare conflicting claims")
    ids = {item["gap_id"] for item in report["gaps"]}
    assert "no-primary-evidence" in ids
    assert "provider-concentration" in ids
    assert "methodology-visibility" in ids
    assert "undated-corpus" in ids
    assert "citation-metadata" in ids
    assert "limitations-undocumented" in ids
    assert "contrast-coverage" in ids
    assert report["governance"]["absence_of_gap_is_not_proof"] is True


def test_api_evaluates_saved_library_objects_and_can_persist_project_reports() -> None:
    suffix = _suffix()
    owner = f"wp-user-v730-{suffix}"
    project = client.post("/v1/projects", headers=HEADERS, json={"title": f"Quality project {suffix}", "owner_ref": owner}).json()
    saved = []
    for source in [
        _source("Field dataset", "primary", "Institute A", "2025"),
        _source("Review article", "secondary", "Institute B", "2024"),
    ]:
        source["owner_ref"] = owner
        response = client.post("/v1/library/objects", headers=HEADERS, json=source)
        assert response.status_code == 200, response.text
        saved.append(response.json())

    object_ids = [item["object_id"] for item in saved]
    evaluation = client.post("/v1/research/sources/evaluate", headers=HEADERS, json={"object_ids": object_ids})
    assert evaluation.status_code == 200, evaluation.text
    assert evaluation.json()["source_count"] == 2
    assert evaluation.json()["governance"]["truth_score"] is False

    comparison = client.post("/v1/research/evidence/compare", headers=HEADERS, json={"object_ids": object_ids, "project_id": project["project_id"], "question": "Compare methods", "persist": True})
    assert comparison.status_code == 200, comparison.text
    assert comparison.json()["project_entity"]["entity_type"] == "evidence-comparison"

    gaps = client.post("/v1/research/evidence/gaps", headers=HEADERS, json={"object_ids": object_ids, "project_id": project["project_id"], "persist": True})
    assert gaps.status_code == 200, gaps.text
    assert gaps.json()["project_entity"]["entity_type"] == "evidence-gap-report"


def test_context_quality_summary_uses_resolved_context_and_preserves_source_metadata() -> None:
    suffix = _suffix()
    owner = f"wp-user-v730-context-{suffix}"
    for source in [
        _source("Context primary", "primary", "Institute A", "2025"),
        _source("Context synthesis", "secondary", "Institute B", "2024"),
    ]:
        source["owner_ref"] = owner
        source["source_scope"] = "my-library"
        response = client.post("/v1/library/objects", headers=HEADERS, json=source)
        assert response.status_code == 200, response.text

    context = client.post("/v1/research/contexts", headers=HEADERS, json={"title": "Evidence review", "owner_ref": owner, "scopes": ["my-library"], "active": True}).json()
    quality = client.get(f"/v1/research/contexts/{context['context_id']}/evidence-quality", headers=HEADERS)
    assert quality.status_code == 200, quality.text
    body = quality.json()
    assert body["schema"] == "sc-research-quality-signals/1.0"
    assert body["source_count"] >= 2
    assert body["summary"]["governance"]["no_truth_score"] is True
    assert body["comparison"]["corpus"]["independent_provider_count"] >= 2

    resolved = client.get(f"/v1/research/contexts/{context['context_id']}/resolve", headers=HEADERS).json()
    prompt_objects = resolved["prompt_context"]["objects"]
    target = next(item for item in prompt_objects if item["title"] == "Context primary")
    assert target["quality_signals"]["evidence_level"] == "primary"
    assert target["quality_signals"]["methodology_state"] == "available"
    assert "not a truth or credibility score" in target["quality_signals"]["quality_note"]


def test_platform_api_advertises_v730_quality_contracts() -> None:
    response = client.get("/v1/platform/api", headers=HEADERS)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == "10.3.0"
    assert body["schema"] == "sc-connected-research-api/2.0"
    assert "source-evaluations" in body["resources"]
    assert "evidence-comparisons" in body["resources"]
    assert "evidence-gaps" in body["resources"]
    assert body["evidence_quality"]["truth_score"] is False
