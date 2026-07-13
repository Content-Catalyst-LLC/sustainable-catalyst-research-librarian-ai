import os
from pathlib import Path
import shutil
import tempfile

CALIBRATION_TEST_DATA_DIR = Path("/tmp/sc-rl-tests-v641-calibration")
shutil.rmtree(CALIBRATION_TEST_DATA_DIR, ignore_errors=True)
os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")
os.environ.setdefault("SC_RL_DATA_DIR", str(CALIBRATION_TEST_DATA_DIR))

from fastapi.testclient import TestClient

from app.calibration import evidence_gate, sanitize_retrieval_config
from app.chunking import chunk_record
from app.main import app
from app.models import KnowledgeRecord
from app.provider import _source_context, verify_citations
from app.retrieval import retrieve_with_diagnostics
from app.store import KnowledgeStore


def record(record_id: str, title: str, content: str, **kwargs) -> KnowledgeRecord:
    return KnowledgeRecord(
        id=record_id,
        title=title,
        url=f"https://sustainablecatalyst.com/{record_id}/",
        content=content,
        **kwargs,
    )


def test_calibration_config_is_sanitized_and_persistent() -> None:
    path = Path(tempfile.mkdtemp()) / "calibration.sqlite3"
    local = KnowledgeStore(path)
    saved = local.set_retrieval_config(
        {
            "profile": "editorial-test",
            "weights": {"lexical": 31, "semantic": 0},
            "rrf_k": 42,
            "exclusions": {"post_types": ["draft", "draft"], "url_prefixes": ["https://example.com/private"]},
        }
    )
    reopened = KnowledgeStore(path)
    assert saved["profile"] == "editorial-test"
    assert reopened.retrieval_config()["weights"]["lexical"] == 31
    assert reopened.retrieval_config()["rrf_k"] == 42
    assert reopened.retrieval_config()["exclusions"]["post_types"] == ["draft"]


def test_exclusions_and_post_type_weights_affect_ranking() -> None:
    records = [
        record("article", "Energy Storage", "Battery systems and storage.", post_type="article"),
        record("page", "Energy Storage Guide", "Battery systems and storage.", post_type="page"),
        record("excluded", "Energy Storage Archive", "Battery systems and storage.", post_type="archive"),
    ]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    config = sanitize_retrieval_config(
        {
            "post_type_weights": {"article": 2.0, "page": 0.5},
            "exclusions": {"post_types": ["archive"]},
        }
    )
    results, diagnostics = retrieve_with_diagnostics("energy storage", records, chunks, 5, calibration=config)
    assert results[0].id == "article"
    assert "excluded" not in [item.id for item in results]
    assert diagnostics["records_excluded"] == 1
    assert diagnostics["exclusion_reasons"]["post-type"] == 1


def test_near_duplicate_title_ambiguity_is_reported() -> None:
    records = [
        record("guide", "Systems Thinking Guide", "Feedback loops and leverage points."),
        record("handbook", "Systems Thinking Handbook", "Feedback loops and leverage points."),
    ]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    config = sanitize_retrieval_config(
        {"thresholds": {"ambiguity_margin": 1000, "near_duplicate_title_similarity": 0.5}}
    )
    results, diagnostics = retrieve_with_diagnostics("systems thinking", records, chunks, 5, calibration=config)
    assert len(results) == 2
    assert diagnostics["ambiguous"] is True
    assert diagnostics["ambiguity_candidates"]


def test_minimum_evidence_gate_blocks_weak_or_ambiguous_results() -> None:
    records = [record("one", "Water Systems", "A short note about water systems.")]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    config = sanitize_retrieval_config({"thresholds": {"minimum_sources": 2, "minimum_score": 5000}})
    matches, diagnostics = retrieve_with_diagnostics("water systems", records, chunks, 5, calibration=config)
    gate = evidence_gate(matches, diagnostics, config)
    assert gate["ok"] is False
    assert "insufficient-source-count" in gate["reasons"]


def test_unsupported_paragraph_and_numeric_claim_are_rejected() -> None:
    records = [record("verified", "Verified Record", "Evidence discusses systems, feedback, and resilience.")]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    matches, _ = retrieve_with_diagnostics("Verified Record", records, chunks, 5)
    unsupported = verify_citations(
        "The platform contains 99 independently certified indicators and guarantees perfect forecasts. [SC1]",
        matches,
    )
    assert unsupported["ok"] is False
    assert unsupported["unsupported_paragraphs"]
    assert unsupported["unsupported_numeric_claims"]


def test_context_budget_limits_supplied_evidence() -> None:
    records = [record(f"r{index}", f"Record {index}", "evidence " * 800) for index in range(3)]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    matches, _ = retrieve_with_diagnostics("evidence", records, chunks, 3)
    context = _source_context(matches, {"limits": {"max_context_characters": 2200, "max_passage_characters": 500}})
    assert len(context) <= 2600
    assert context.count("SOURCE SC") < 4


def test_benchmark_endpoint_compares_and_persists_runs() -> None:
    client = TestClient(app)
    headers = {"X-SC-RL-Key": "test-key"}
    seed = client.post(
        "/v1/knowledge/sync",
        headers=headers,
        json={
            "mode": "upsert",
            "job_id": "calibration-benchmark-seed",
            "records": [
                {
                    "id": "benchmark:stability",
                    "title": "Stability Analysis with Eigenvalues",
                    "url": "https://sustainablecatalyst.com/stability-analysis-with-eigenvalues/",
                    "summary": "A systems modeling article about eigenvalue stability.",
                    "series": "Linear Algebra for Systems Modeling",
                }
            ],
        },
    )
    assert seed.status_code == 200
    response = client.post(
        "/v1/retrieval/benchmark",
        headers=headers,
        json={
            "cases": [
                {
                    "query": "Stability Analysis with Eigenvalues",
                    "expected_record_id": "benchmark:stability",
                    "expected_title": "Stability Analysis with Eigenvalues",
                    "tags": ["exact-title"],
                }
            ],
            "include_semantic": False,
            "limit": 5,
            "persist": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["lexical"]["hit_at_1"] == 1.0
    assert body["metrics"]["hybrid"]["mrr"] == 1.0
    history = client.get("/v1/retrieval/benchmark/history", headers=headers)
    assert history.status_code == 200
    assert history.json()["runs"]


def test_exact_title_remains_decisive_under_near_duplicate_competition() -> None:
    records = [
        record("guide", "Systems Thinking Guide", "Feedback loops and leverage points."),
        record("guide-expanded", "Systems Thinking Guide Expanded", "Feedback loops and leverage points."),
    ]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    matches, diagnostics = retrieve_with_diagnostics(
        "Systems Thinking Guide",
        records,
        chunks,
        5,
        calibration={"thresholds": {"ambiguity_margin": 1000, "near_duplicate_title_similarity": 0.4}},
    )
    assert matches[0].id == "guide"
    assert matches[0].exact_title_match is True
    assert diagnostics["ambiguous"] is False


def test_exact_title_bypasses_general_minimum_score_but_not_exclusions() -> None:
    records = [record("canonical", "Planetary Boundaries", "Safe operating space for humanity.")]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    config = sanitize_retrieval_config({"thresholds": {"minimum_score": 5000}})
    matches, diagnostics = retrieve_with_diagnostics("Planetary Boundaries", records, chunks, 5, calibration=config)
    assert matches and matches[0].exact_title_match is True
    assert evidence_gate(matches, diagnostics, config)["ok"] is True


def test_supported_numeric_claim_passes_numeric_verification() -> None:
    records = [record("count", "Boundary Record", "The framework describes 9 planetary boundaries.")]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    matches, _ = retrieve_with_diagnostics("9 planetary boundaries", records, chunks, 5)
    verification = verify_citations(
        "The cited framework describes 9 planetary boundaries and their operating context. [SC1]",
        matches,
    )
    assert verification["unsupported_numeric_claims"] == []
