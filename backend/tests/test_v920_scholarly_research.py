from __future__ import annotations

import asyncio
import os

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.async_jobs import AsyncJobStore, JobClaim, JOB_TYPES
from app.contracts.scholarly_research import (
    ScholarlyStudyCreateRequest,
    ScholarlyProtocol,
    ScholarlyProtocolFreezeRequest,
    ScholarlyDeviationRequest,
    ScholarlyResultRequest,
    ScholarlyInterpretationRequest,
    ScholarlyManuscriptSectionRequest,
    ScholarlyPackageFreezeRequest,
)
from app.services.scholarly_research import ScholarlyResearchStore
from app.services.document_jobs import execute_job


def create_request(**overrides):
    data = dict(
        core_project_id="core-920",
        local_project_id="local-920",
        title="Original research study",
        research_question="How does the measured outcome change under the declared conditions?",
        study_type="observational",
        protocol=ScholarlyProtocol(
            aims=["Estimate the declared association."],
            hypotheses=["The primary outcome differs across the declared exposure."],
            population_or_system="Declared study population",
            methods="Pre-specified observational research design.",
            analysis_plan="Estimate effect and uncertainty using the registered specialist runtime.",
            data_management_plan="Preserve source hashes and immutable result artifacts.",
            ethics_review_status="not-applicable",
            deviations_policy="Record all post-freeze design or analysis changes explicitly.",
        ),
        authors=["Researcher A"],
        affiliations=["Independent research lab"],
        funding_statement="No external funding declared.",
        conflict_of_interest_statement="No conflicts declared.",
        source_refs=["source:920"],
        core_evidence_refs=["evidence:920"],
        idempotency_key="study-920",
    )
    data.update(overrides)
    return ScholarlyStudyCreateRequest(**data)


def make_store(tmp_path):
    return ScholarlyResearchStore(tmp_path / "scholarly.sqlite3")


def test_create_is_idempotent_and_revised(tmp_path):
    store = make_store(tmp_path)
    a, replay1 = store.create(create_request())
    b, replay2 = store.create(create_request())
    assert replay1 is False and replay2 is True
    assert a["study_id"] == b["study_id"]
    revisions = store.revisions(a["study_id"])
    assert revisions[0]["revision_number"] == 1
    assert len(revisions[0]["revision_hash"]) == 64


def test_protocol_freeze_precedes_results_and_deviations(tmp_path):
    store = make_store(tmp_path)
    study, _ = store.create(create_request(idempotency_key="freeze-920"))
    sid = study["study_id"]
    try:
        store.add_result(sid, ScholarlyResultRequest(actor_ref="r", result_type="descriptive", title="Early", summary="Too early"))
        assert False, "result registration before protocol freeze should fail"
    except ValueError:
        pass
    frozen = store.freeze_protocol(sid, ScholarlyProtocolFreezeRequest(reviewer_ref="reviewer", note="Protocol reviewed."))
    assert frozen["protocol_frozen"] is True and len(frozen["protocol_hash"]) == 64
    changed = store.add_deviation(sid, ScholarlyDeviationRequest(actor_ref="r", category="analysis", description="Added a pre-declared sensitivity check.", rationale="Robustness", impact_assessment="Does not alter primary estimand."))
    assert len(changed["deviations"]) == 1


def test_results_and_human_interpretation_keep_lineage(tmp_path):
    store = make_store(tmp_path)
    study, _ = store.create(create_request(idempotency_key="results-920"))
    sid = study["study_id"]
    store.freeze_protocol(sid, ScholarlyProtocolFreezeRequest(reviewer_ref="reviewer"))
    study = store.add_result(sid, ScholarlyResultRequest(
        actor_ref="researcher", result_type="statistical", title="Primary model",
        summary="The registered runtime returned the archived estimate.",
        runtime_ref="analytics-r:run-920", artifact_ref="artifact:920", content_hash="a"*64,
        statistical_reasoning_ref="core-stat:920", evidence_refs=["evidence:920"], limitations=["Observational design"],
    ))
    result_id = study["results"][0]["result_id"]
    study = store.add_interpretation(sid, ScholarlyInterpretationRequest(
        author_ref="researcher", text="The result is consistent with the stated hypothesis but does not establish causality.",
        result_refs=[result_id], evidence_refs=["evidence:920"], uncertainty_or_qualification="Residual confounding remains possible.",
    ))
    assert study["interpretations"][0]["author_ref"] == "researcher"
    assert study["interpretations"][0]["result_refs"] == [result_id]


def test_publication_readiness_and_frozen_package(tmp_path):
    store = make_store(tmp_path)
    study, _ = store.create(create_request(idempotency_key="package-920"))
    sid = study["study_id"]
    store.freeze_protocol(sid, ScholarlyProtocolFreezeRequest(reviewer_ref="reviewer"))
    study = store.add_result(sid, ScholarlyResultRequest(
        actor_ref="researcher", result_type="statistical", title="Primary", summary="Archived result.",
        runtime_ref="workspace:run-920", artifact_ref="artifact:result-920", statistical_reasoning_ref="core-stat:920",
    ))
    rid = study["results"][0]["result_id"]
    store.add_interpretation(sid, ScholarlyInterpretationRequest(author_ref="researcher", text="Human-authored interpretation.", result_refs=[rid]))
    for section in ["methods", "results", "discussion", "limitations"]:
        store.add_manuscript_section(sid, ScholarlyManuscriptSectionRequest(author_ref="researcher", section=section, heading=section.title(), text=f"Human-authored {section} section.", citation_refs=["source:920"]))
    readiness = store.readiness(sid)
    assert readiness["ready"] is True and readiness["blockers"] == []
    package = store.freeze_package(sid, ScholarlyPackageFreezeRequest(reviewer_ref="reviewer", note="Ready for reproducibility archive."))
    assert package["schema"] == "sc-research-librarian-scholarly-research-package/1.0"
    assert len(package["package_hash"]) == 64
    assert package["governance"]["package_is_not_peer_review"] is True
    assert store.get(sid)["state"] == "complete"


def test_async_scholarly_package_job(tmp_path, monkeypatch):
    store = make_store(tmp_path)
    import app.services.scholarly_research as sr
    import app.services.document_jobs as dj
    monkeypatch.setattr(sr, "_store", store)
    monkeypatch.setattr(dj, "get_scholarly_research_store", lambda: store)
    study, _ = store.create(create_request(idempotency_key="async-package-920"))
    sid = study["study_id"]
    store.freeze_protocol(sid, ScholarlyProtocolFreezeRequest(reviewer_ref="reviewer"))
    study = store.add_result(sid, ScholarlyResultRequest(actor_ref="r", result_type="descriptive", title="Result", summary="Archived result."))
    rid = study["results"][0]["result_id"]
    store.add_interpretation(sid, ScholarlyInterpretationRequest(author_ref="r", text="Interpretation", result_refs=[rid]))
    for section in ["methods", "results", "discussion", "limitations"]:
        store.add_manuscript_section(sid, ScholarlyManuscriptSectionRequest(author_ref="r", section=section, text=section))
    claim = JobClaim(job_id="job-920", job_type="scholarly-research-package", payload={"study_id": sid, "freeze": {"reviewer_ref": "reviewer"}}, attempts=1, max_attempts=3, worker_id="worker")
    events = []
    out = asyncio.run(execute_job(claim, lambda stage, pct: events.append((stage, pct))))
    assert out["study_id"] == sid and events[-1] == ("scholarly-package-ready", 95)
    assert "scholarly-research-package" in JOB_TYPES


def test_authenticated_scholarly_api_surface():
    from app.main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    required = {
        "/v1/core/scholarly-research/capabilities",
        "/v1/core/scholarly-research/studies",
        "/v1/core/scholarly-research/studies/{study_id}",
        "/v1/core/scholarly-research/studies/{study_id}/protocol/freeze",
        "/v1/core/scholarly-research/studies/{study_id}/deviations",
        "/v1/core/scholarly-research/studies/{study_id}/results",
        "/v1/core/scholarly-research/studies/{study_id}/interpretations",
        "/v1/core/scholarly-research/studies/{study_id}/manuscript-sections",
        "/v1/core/scholarly-research/studies/{study_id}/reviews",
        "/v1/core/scholarly-research/studies/{study_id}/publication-readiness",
        "/v1/core/scholarly-research/studies/{study_id}/packages/freeze",
        "/v1/core/scholarly-research/studies/{study_id}/revisions",
        "/v1/core/scholarly-research/studies/{study_id}/packages",
    }
    assert not (required - paths)
    body = TestClient(app).get("/v1/core/scholarly-research/capabilities", headers={"X-SC-RL-Key": "test-key"}).json()
    assert body["durable_study_registry"] is True
    assert body["automatic_authorship"] is False
    assert body["automatic_truth_promotion"] is False
