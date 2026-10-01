import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
import asyncio
from fastapi.testclient import TestClient
from app.contracts.research_revision_response_intelligence import *
from app.services.research_revision_response_intelligence import ResearchRevisionResponseIntelligenceStore,capabilities
from app.async_jobs import JOB_TYPES,JobClaim
from app.services.document_jobs import execute_job

def critique(ref):
    if ref=="missing": raise ValueError("missing")
    return {"record_hash":"critique-hash","reviewer_critiques":[{"critique_id":"c1"},{"critique_id":"c2"}],"revision_requirements":[{"revision_requirement_id":"r1"}]}

def make_store(tmp_path): return ResearchRevisionResponseIntelligenceStore(tmp_path/"rr.sqlite3",critique_resolver=critique)
def make_project(s):
    return s.create(RevisionResponseCreateRequest(actor_ref="author",title="Revision response",project_ref="p",critique_project_ref="critique-1",baseline_revision_ref="rev1",baseline_revision_hash="h1",revised_artifact_ref="rev2",revised_artifact_hash="h2"))

def seed(s,rid):
    r=s.add_response_item(rid,RevisionResponseItemAddRequest(actor_ref="author",critique_ids=["c1"],revision_requirement_ids=["r1"],response_position="addressed",response_text="We revised the methods section."))
    return r["response_items"][0]["response_item_id"]

def test_create_guardrails(tmp_path):
    s=make_store(tmp_path); r=make_project(s)
    assert r["schema"]==REVISION_RESPONSE_SCHEMA and r["critique_source_hash"]=="critique-hash"
    assert r["governance"]["author_response_does_not_equal_reviewer_satisfaction"] is True
    assert r["governance"]["automatic_accept_reject"] is False

def test_missing_critique_fails_closed(tmp_path):
    s=make_store(tmp_path)
    try:s.create(RevisionResponseCreateRequest(actor_ref="a",title="x",critique_project_ref="missing"))
    except ValueError as e: assert "critique project" in str(e)
    else:raise AssertionError("expected failure")

def test_response_and_change_claim_are_not_resolution(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)["revision_response_id"]; item=seed(s,rid)
    r=s.add_change_claim(rid,RevisionChangeClaimAddRequest(actor_ref="author",response_item_id=item,change_type="text-modified",location_ref="methods:12",before_hash="b",after_hash="a",claimed_change="Added deviation rationale."))
    assert r["change_claims"][0]["claim_verified"] is False
    assert s.unresolved_register(rid)["count"]==1

def test_artifact_receipt_and_human_resolution_are_separate(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)["revision_response_id"]; item=seed(s,rid)
    s.add_artifact_receipt(rid,RevisionArtifactReceiptAddRequest(actor_ref="system",response_item_id=item,artifact_type="manuscript",artifact_ref="rev2",artifact_hash="h2",diff_ref="diff1",observed_changed_locations=["methods:12"]))
    assert s.change_evidence_matrix(rid)["rows"]==[]
    r=s.add_resolution_review(rid,RevisionResolutionReviewAddRequest(actor_ref="reviewer",response_item_id=item,reviewer_ref="reviewer",judgment="satisfied",rationale="The requested explanation is present.",evidence_refs=["rev2"]))
    assert r["resolution_reviews"][0]["human_authored"] is True
    assert s.unresolved_register(rid)["count"]==0

def test_verification_requires_approval(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)["revision_response_id"]; item=seed(s,rid)
    r=s.add_verification_request(rid,RevisionVerificationRequestAddRequest(actor_ref="reviewer",label="Re-run",requested_check="Re-run model.",response_item_ids=[item]))
    vid=r["verification_requests"][0]["verification_request_id"]
    assert s.verification_handoffs(rid)["packets"]==[]
    s.decide(rid,RevisionResponseDecisionRequest(actor_ref="editor",object_type="verification-request",object_id=vid,decision="approved"))
    assert len(s.verification_handoffs(rid)["packets"])==1
    r=s.add_verification_receipt(rid,RevisionVerificationReceiptAddRequest(actor_ref="runner",verification_request_id=vid,execution_ref="run1",status="completed"))
    assert r["verification_receipts"][0]["receipt_is_observation_not_resolution_verdict"] is True

def test_package_core_snapshot(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)["revision_response_id"]; item=seed(s,rid)
    s.add_change_claim(rid,RevisionChangeClaimAddRequest(actor_ref="author",response_item_id=item,change_type="text-modified",claimed_change="Changed text."))
    assert s.readiness(rid)["ready_for_human_review"] is True
    p=s.response_package(rid); assert p["editorial_decision"] is None and p["governance"]["no_accept_reject_recommendation_generated"] is True
    c=s.core_candidate(rid); assert c["reviewer_satisfaction_not_inferred"] is True and c["truth_promoted"] is False
    snap=s.freeze_snapshot(RevisionResponseSnapshotRequest(actor_ref="author",revision_response_id=rid)); assert len(snap["snapshot_hash"])==64

def test_job_and_api(tmp_path,monkeypatch):
    s=make_store(tmp_path); rid=make_project(s)["revision_response_id"]; seed(s,rid)
    assert "research-revision-response-intelligence-snapshot" in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_research_revision_response_intelligence_store",lambda:s)
    events=[]; claim=JobClaim(job_id="j",job_type="research-revision-response-intelligence-snapshot",payload={"snapshot":{"actor_ref":"a","revision_response_id":rid}},attempts=1,max_attempts=3,worker_id="w")
    out=asyncio.run(execute_job(claim,lambda st,p:events.append((st,p))))
    assert out["schema"]==REVISION_RESPONSE_SNAPSHOT_SCHEMA and events[-1]==("research-revision-response-intelligence-snapshot-ready",95)
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={"/v1/core/research-revision-response-intelligence/capabilities","/v1/core/research-revision-response-intelligence/projects","/v1/core/research-revision-response-intelligence/projects/{revision_response_id}/response-package","/v1/core/research-revision-response-intelligence/snapshots/freeze"}
    assert not(required-paths)
    client=TestClient(app)
    assert client.get("/v1/core/research-revision-response-intelligence/capabilities").status_code in {401,503}
    ok=client.get("/v1/core/research-revision-response-intelligence/capabilities",headers={"X-SC-RL-Key":"test-key"}); assert ok.status_code==200

def test_unified_binding(tmp_path):
    from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
    from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore
    s=make_store(tmp_path); rid=make_project(s)["revision_response_id"]; seed(s,rid)
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/"env.sqlite3",revision_response_store=s)
    r=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="x",title="u",project_ref="p",revision_response_ids=[rid]))
    line=env.lineage(r["environment_id"]); ready=env.readiness(r["environment_id"])
    assert len(line["scholarly"]["revision_responses"])==1
    assert ready["dimensions"]["revision_response_bound"] is True

def test_capabilities():
    c=capabilities()
    assert c["milestone"]=="11.9" and c["human_resolution_reviews"] is True
    assert c["automatic_comment_satisfaction"] is False and c["automatic_accept_reject"] is False and c["automatic_truth_promotion"] is False
