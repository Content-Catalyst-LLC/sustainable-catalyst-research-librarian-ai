import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
import asyncio
from fastapi.testclient import TestClient
from app.contracts.peer_review_scholarly_critique_intelligence import *
from app.services.peer_review_scholarly_critique_intelligence import PeerReviewScholarlyCritiqueIntelligenceStore,capabilities
from app.async_jobs import JOB_TYPES,JobClaim
from app.services.document_jobs import execute_job

def fake_resolvers():
    def resolver(ref):
        if ref=="missing": raise ValueError("missing")
        return {"record_hash":f"hash-{ref}"}
    return {"scholarly-study":resolver,"research-integrity-audit":resolver}
def make_store(tmp_path): return PeerReviewScholarlyCritiqueIntelligenceStore(tmp_path/"critique.sqlite3",target_resolvers=fake_resolvers())
def make_project(s):
    return s.create(ScholarlyCritiqueCreateRequest(actor_ref="editor",title="Scholarly critique",review_question="What revisions and checks are supported?",project_ref="p",targets=[ScholarlyCritiqueTargetBinding(target_type="scholarly-study",target_ref="study-1"),ScholarlyCritiqueTargetBinding(target_type="research-integrity-audit",target_ref="audit-1")],upstream_peer_review_refs=["peer-review-1"],research_integrity_audit_refs=["audit-1"]))
def seed(s,pid):
    r=s.add_round(pid,ScholarlyCritiqueRoundAddRequest(actor_ref="editor",label="Round 1")); rid=r["review_rounds"][0]["round_id"]
    r=s.add_dimension(pid,ScholarlyCritiqueDimensionAddRequest(actor_ref="editor",domain="methods",label="Methods",review_prompt="Methods?",expectation_basis="Protocol")); did=r["critique_dimensions"][0]["dimension_id"]
    r=s.add_reviewer_critique(pid,ScholarlyReviewerCritiqueAddRequest(actor_ref="r1",round_id=rid,dimension_id=did,reviewer_ref="r1",comment_kind="concern",significance="major",critique="Explain the deviation.",requested_actions=["Explain."])); return rid,did,r["reviewer_critiques"][0]["critique_id"]

def test_create_guardrails(tmp_path):
    s=make_store(tmp_path); r=make_project(s)
    assert r["schema"]==SCHOLARLY_CRITIQUE_SCHEMA and len(r["targets"])==2
    assert r["governance"]["automatic_accept_reject"] is False and r["governance"]["automatic_reviewer_ranking"] is False
def test_missing_known_target_fails_closed(tmp_path):
    s=make_store(tmp_path)
    try:s.create(ScholarlyCritiqueCreateRequest(actor_ref="x",title="x",review_question="q",targets=[ScholarlyCritiqueTargetBinding(target_type="scholarly-study",target_ref="missing")]))
    except ValueError as e: assert "critique target" in str(e)
    else: raise AssertionError("expected failure")
def test_response_requirement_separation(tmp_path):
    s=make_store(tmp_path); pid=make_project(s)["critique_project_id"]; rid,did,cid=seed(s,pid)
    s.add_author_response(pid,ScholarlyAuthorResponseAddRequest(actor_ref="a",critique_id=cid,response="Addressed",response_status="addressed"))
    r=s.add_revision_requirement(pid,ScholarlyRevisionRequirementAddRequest(actor_ref="e",critique_ids=[cid],requirement="Document deviation")); q=r["revision_requirements"][0]["revision_requirement_id"]
    s.set_revision_requirement_status(pid,ScholarlyRevisionRequirementStatusRequest(actor_ref="a",revision_requirement_id=q,status="addressed"))
    assert s.get(pid)["revision_requirements"][0]["completion_is_not_acceptance"] is True
def test_verification_requires_approval(tmp_path):
    s=make_store(tmp_path); pid=make_project(s)["critique_project_id"]; rid,did,cid=seed(s,pid)
    r=s.add_verification_request(pid,ScholarlyCritiqueVerificationRequestAddRequest(actor_ref="r",label="rerun",requested_check="rerun",critique_ids=[cid])); vid=r["verification_requests"][0]["verification_request_id"]
    assert s.verification_handoffs(pid)["packets"]==[]
    s.decide(pid,ScholarlyCritiqueDecisionRequest(actor_ref="e",object_type="verification-request",object_id=vid,decision="approved"))
    r=s.add_verification_receipt(pid,ScholarlyCritiqueVerificationReceiptAddRequest(actor_ref="runner",verification_request_id=vid,execution_ref="run",status="completed"))
    assert r["verification_receipts"][0]["receipt_is_observation_not_review_verdict"] is True
def test_matrix_synthesis_snapshot(tmp_path):
    s=make_store(tmp_path); pid=make_project(s)["critique_project_id"]; rid,did,cid=seed(s,pid)
    s.add_critique_synthesis(pid,ScholarlyCritiqueSynthesisAddRequest(actor_ref="e",round_id=rid,title="S",synthesis="Preserve disagreement",critique_ids=[cid],areas_of_disagreement=["Interpretation"]))
    assert s.cross_review_matrix(pid)["governance"]["no_majority_vote"] is True
    assert s.readiness(pid)["ready_for_editorial_review"] is True
    assert s.editorial_handoff(pid)["editorial_decision"] is None
    assert s.core_candidate(pid)["truth_promoted"] is False
    assert len(s.freeze_snapshot(ScholarlyCritiqueSnapshotRequest(actor_ref="e",critique_project_id=pid))["snapshot_hash"])==64
def test_job_and_api(tmp_path,monkeypatch):
    s=make_store(tmp_path); pid=make_project(s)["critique_project_id"]; seed(s,pid)
    assert "peer-review-scholarly-critique-intelligence-snapshot" in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_peer_review_scholarly_critique_intelligence_store",lambda:s)
    events=[]; c=JobClaim(job_id="j",job_type="peer-review-scholarly-critique-intelligence-snapshot",payload={"snapshot":{"actor_ref":"e","critique_project_id":pid}},attempts=1,max_attempts=3,worker_id="w")
    out=asyncio.run(execute_job(c,lambda st,p:events.append((st,p))))
    assert out["schema"]==SCHOLARLY_CRITIQUE_SNAPSHOT_SCHEMA and events[-1]==("peer-review-scholarly-critique-intelligence-snapshot-ready",95)
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={"/v1/core/peer-review-scholarly-critique-intelligence/capabilities","/v1/core/peer-review-scholarly-critique-intelligence/critique-projects","/v1/core/peer-review-scholarly-critique-intelligence/critique-projects/{critique_project_id}/editorial-handoff","/v1/core/peer-review-scholarly-critique-intelligence/snapshots/freeze"}
    assert not(required-paths)
    client=TestClient(app); assert client.get("/v1/core/peer-review-scholarly-critique-intelligence/capabilities").status_code in {401,503}
    ok=client.get("/v1/core/peer-review-scholarly-critique-intelligence/capabilities",headers={"X-SC-RL-Key":"test-key"}); assert ok.status_code==200
def test_unified_binding(tmp_path):
    from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
    from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore
    s=make_store(tmp_path); pid=make_project(s)["critique_project_id"]; seed(s,pid)
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/"env.sqlite3",scholarly_critique_store=s)
    r=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="x",title="u",project_ref="p",scholarly_critique_ids=[pid]))
    assert len(env.lineage(r["environment_id"])["scholarly"]["scholarly_critiques"])==1
    assert env.readiness(r["environment_id"])["dimensions"]["scholarly_critique_bound"] is True
def test_capabilities():
    c=capabilities(); assert c["milestone"]=="11.8" and c["automatic_accept_reject"] is False and c["automatic_reviewer_ranking"] is False and c["automatic_truth_promotion"] is False
