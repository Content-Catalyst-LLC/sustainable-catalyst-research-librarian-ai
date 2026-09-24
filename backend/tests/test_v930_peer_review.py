from __future__ import annotations

import asyncio
import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.scholarly_research import (
    ScholarlyStudyCreateRequest, ScholarlyProtocol, ScholarlyProtocolFreezeRequest,
    ScholarlyResultRequest,
)
from app.contracts.peer_review import (
    ReviewRoundCreateRequest, ReviewerAssignmentRequest, StructuredPeerReviewRequest,
    AuthorResponseRequest, RevisionSubmissionRequest, ReplicationAttemptRequest,
    EditorialDecisionRequest, PeerReviewPackageFreezeRequest,
)
from app.services.scholarly_research import ScholarlyResearchStore
from app.services.peer_review import PeerReviewStore
from app.services.document_jobs import execute_job


def study_request(key: str) -> ScholarlyStudyCreateRequest:
    return ScholarlyStudyCreateRequest(
        core_project_id="core-930", title="Reviewable original study",
        research_question="Does the registered analysis support the stated research question?",
        study_type="observational",
        protocol=ScholarlyProtocol(
            aims=["Evaluate the registered relationship."],
            hypotheses=["The declared primary association is non-zero."],
            population_or_system="Declared population",
            methods="Registered observational protocol.",
            analysis_plan="Use the declared specialist runtime and preserve diagnostics.",
            data_management_plan="Preserve source and result hashes.",
            ethics_review_status="not-applicable",
            deviations_policy="Record all post-freeze changes.",
        ),
        authors=["Author A"], affiliations=["Independent Lab"],
        funding_statement="No external funding.", conflict_of_interest_statement="No conflicts declared.",
        source_refs=["source:930"], core_evidence_refs=["evidence:930"], idempotency_key=key,
    )


def stores(tmp_path, monkeypatch):
    scholarly = ScholarlyResearchStore(tmp_path / "scholarly.sqlite3")
    study, _ = scholarly.create(study_request("study-930"))
    scholarly.freeze_protocol(study["study_id"], ScholarlyProtocolFreezeRequest(reviewer_ref="protocol-reviewer"))
    study = scholarly.add_result(study["study_id"], ScholarlyResultRequest(
        actor_ref="author", result_type="statistical", title="Primary result", summary="Archived estimate.",
        runtime_ref="analytics-r:930", artifact_ref="artifact:930", evidence_refs=["evidence:930"],
    ))
    import app.services.peer_review as pr
    monkeypatch.setattr(pr, "get_scholarly_research_store", lambda: scholarly)
    peer = PeerReviewStore(tmp_path / "peer.sqlite3")
    return scholarly, peer, study


def create_round_assignment(peer, sid):
    round_item, replayed = peer.create_round(sid, ReviewRoundCreateRequest(actor_ref="editor", label="Round 1", idempotency_key="round-1"))
    assert replayed is False
    peer.assign_reviewer(sid, round_item["round_id"], ReviewerAssignmentRequest(
        assigned_by_ref="editor", reviewer_ref="reviewer-1", role="peer-reviewer",
        expertise=["methods"], conflict_status="none-declared", conflict_statement="No conflict declared.",
    ))
    return round_item


def test_round_creation_idempotency_and_assignment(tmp_path, monkeypatch):
    _, peer, study = stores(tmp_path, monkeypatch); sid=study["study_id"]
    r1, replay1 = peer.create_round(sid, ReviewRoundCreateRequest(actor_ref="editor", label="Initial", idempotency_key="r1"))
    r2, replay2 = peer.create_round(sid, ReviewRoundCreateRequest(actor_ref="editor", label="Initial", idempotency_key="r1"))
    assert replay1 is False and replay2 is True and r1["round_id"] == r2["round_id"]
    record = peer.assign_reviewer(sid, r1["round_id"], ReviewerAssignmentRequest(assigned_by_ref="editor", reviewer_ref="reviewer", conflict_status="none-declared"))
    assert record["assignments"][0]["reviewer_ref"] == "reviewer"
    assert len(record["record_fingerprint"]) == 64


def test_review_requires_assignment_and_blocks_confirmed_conflict(tmp_path, monkeypatch):
    _, peer, study = stores(tmp_path, monkeypatch); sid=study["study_id"]
    round_item, _ = peer.create_round(sid, ReviewRoundCreateRequest(actor_ref="editor"))
    try:
        peer.submit_review(sid, round_item["round_id"], StructuredPeerReviewRequest(reviewer_ref="unassigned", recommendation="major-revision", summary="Review"))
        assert False
    except ValueError:
        pass
    peer.assign_reviewer(sid, round_item["round_id"], ReviewerAssignmentRequest(assigned_by_ref="editor", reviewer_ref="conflicted", conflict_status="confirmed", conflict_statement="Declared conflict"))
    try:
        peer.submit_review(sid, round_item["round_id"], StructuredPeerReviewRequest(reviewer_ref="conflicted", recommendation="no-recommendation", summary="Should not submit"))
        assert False
    except ValueError:
        pass


def test_structured_review_author_response_and_revision_lineage(tmp_path, monkeypatch):
    _, peer, study = stores(tmp_path, monkeypatch); sid=study["study_id"]
    rnd=create_round_assignment(peer,sid)
    record=peer.submit_review(sid,rnd["round_id"],StructuredPeerReviewRequest(
        reviewer_ref="reviewer-1", recommendation="major-revision", summary="Methods need clarification.",
        strengths=["Clear question"], major_concerns=["Clarify missing-data handling"], requested_actions=["Add missing-data sensitivity analysis"],
        methods_assessment="concerns", reproducibility_assessment="partially-reproducible",
    ))
    review_id=record["reviews"][0]["review_id"]
    record=peer.add_response(sid,AuthorResponseRequest(author_ref="author",review_id=review_id,response_text="We added the requested analysis.",addressed_actions=["Add missing-data sensitivity analysis"]))
    response_id=record["responses"][0]["response_id"]
    record=peer.add_revision(sid,RevisionSubmissionRequest(author_ref="author",change_summary="Added sensitivity analysis and methods clarification.",response_refs=[response_id],artifact_ref="manuscript:v2"))
    assert record["revisions"][0]["response_refs"] == [response_id]
    assert len(record["reviews"][0]["review_hash"]) == 64


def test_replication_records_declared_outcome_without_truth_inference(tmp_path, monkeypatch):
    _, peer, study = stores(tmp_path, monkeypatch); sid=study["study_id"]
    rid=study["results"][0]["result_id"]
    record=peer.add_replication(sid,ReplicationAttemptRequest(
        actor_ref="replicator", replication_type="computational", status="completed", outcome="partially-consistent",
        runtime_ref="workspace:replication-930", artifact_ref="artifact:replication-930", result_refs=[rid],
        summary="Independent rerun produced a similar direction with wider uncertainty.", limitations=["Different package minor version"],
    ))
    assert record["replications"][0]["outcome"] == "partially-consistent"
    cap=__import__("app.services.peer_review",fromlist=["capabilities"]).capabilities()
    assert cap["automatic_replication_judgment"] is False and cap["automatic_truth_promotion"] is False


def test_readiness_human_decision_and_frozen_package(tmp_path, monkeypatch):
    _, peer, study = stores(tmp_path, monkeypatch); sid=study["study_id"]
    rnd=create_round_assignment(peer,sid)
    record=peer.submit_review(sid,rnd["round_id"],StructuredPeerReviewRequest(reviewer_ref="reviewer-1",recommendation="minor-revision",summary="Minor clarification requested."))
    review_id=record["reviews"][0]["review_id"]
    peer.add_response(sid,AuthorResponseRequest(author_ref="author",review_id=review_id,response_text="Clarification added."))
    pre=peer.readiness(sid)
    assert pre["ready"] is False and "editorial_decision_recorded" in pre["blockers"]
    record=peer.add_decision(sid,EditorialDecisionRequest(editor_ref="editor",decision="accept",rationale="Reviewer concern addressed.",based_on_review_ids=[review_id]))
    ready=peer.readiness(sid)
    assert ready["ready"] is True
    package=peer.freeze_package(sid,PeerReviewPackageFreezeRequest(actor_ref="editor",require_all_reviews_responded=True))
    assert package["schema"] == "sc-research-librarian-peer-review-validation-package/1.0"
    assert package["governance"]["package_is_not_validity_certification"] is True
    assert len(package["package_hash"]) == 64


def test_async_peer_review_package_job(tmp_path, monkeypatch):
    _, peer, study = stores(tmp_path, monkeypatch); sid=study["study_id"]
    rnd=create_round_assignment(peer,sid)
    record=peer.submit_review(sid,rnd["round_id"],StructuredPeerReviewRequest(reviewer_ref="reviewer-1",recommendation="accept",summary="No blocking concerns."))
    review_id=record["reviews"][0]["review_id"]
    peer.add_decision(sid,EditorialDecisionRequest(editor_ref="editor",decision="accept",rationale="Review complete.",based_on_review_ids=[review_id]))
    import app.services.document_jobs as dj
    monkeypatch.setattr(dj,"get_peer_review_store",lambda:peer)
    claim=JobClaim(job_id="job-930",job_type="peer-review-validation-package",payload={"study_id":sid,"freeze":{"actor_ref":"editor"}},attempts=1,max_attempts=3,worker_id="worker")
    events=[]
    out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["study_id"]==sid and events[-1]==("peer-review-validation-package-ready",95)
    assert "peer-review-validation-package" in JOB_TYPES


def test_authenticated_peer_review_api_surface():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/scholarly-validation/capabilities",
        "/v1/core/scholarly-validation/studies/{study_id}",
        "/v1/core/scholarly-validation/studies/{study_id}/rounds",
        "/v1/core/scholarly-validation/studies/{study_id}/rounds/{round_id}/assignments",
        "/v1/core/scholarly-validation/studies/{study_id}/rounds/{round_id}/reviews",
        "/v1/core/scholarly-validation/studies/{study_id}/responses",
        "/v1/core/scholarly-validation/studies/{study_id}/revisions",
        "/v1/core/scholarly-validation/studies/{study_id}/replications",
        "/v1/core/scholarly-validation/studies/{study_id}/editorial-decisions",
        "/v1/core/scholarly-validation/studies/{study_id}/readiness",
        "/v1/core/scholarly-validation/studies/{study_id}/packages/freeze",
        "/v1/core/scholarly-validation/studies/{study_id}/events",
        "/v1/core/scholarly-validation/studies/{study_id}/packages",
    }
    assert not(required-paths), required-paths
    body=TestClient(app).get("/v1/core/scholarly-validation/capabilities",headers={"X-SC-RL-Key":"test-key"}).json()
    assert body["durable_peer_review_registry"] is True
    assert body["machine_peer_review_certification"] is False
    assert body["automatic_truth_promotion"] is False
