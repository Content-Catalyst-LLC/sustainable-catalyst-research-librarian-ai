from __future__ import annotations
import asyncio, os
from pathlib import Path

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient
from app.async_jobs import JOB_TYPES, JobClaim
from app.contracts.argument_claim_counterclaim_intelligence import (
    ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA, ARGUMENT_CLAIM_COUNTERCLAIM_SNAPSHOT_SCHEMA,
    ArgumentIntelligenceCreateRequest, ArgumentClaimAddRequest, ClaimEvidenceLinkRequest,
    ClaimRelationAddRequest, ClaimAssumptionAddRequest, ClaimDecisionRequest,
    ArgumentTensionAddRequest, ArgumentIntelligenceStateRequest, ArgumentIntelligenceSnapshotRequest,
)
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.argument_claim_counterclaim_intelligence import ArgumentClaimCounterclaimIntelligenceStore, capabilities
from app.services.document_jobs import execute_job
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakeLiterature:
    def get(self, iid):
        if iid != "lit-1": raise ValueError("missing literature")
        return {
            "intelligence_id":"lit-1", "record_hash":"lit-hash", "research_question":"Does X affect Y?",
            "systematic_review_id":"review-1", "works":[
                {"work_id":"work-a","source_ref":"source:a","title":"Study A"},
                {"work_id":"work-b","source_ref":"source:b","title":"Study B"},
            ]
        }

def make_store(tmp_path: Path):
    return ArgumentClaimCounterclaimIntelligenceStore(tmp_path/"argintel.sqlite3", literature_store=FakeLiterature())

def create_project(store):
    return store.create(ArgumentIntelligenceCreateRequest(actor_ref="researcher:1", title="Argument project", literature_intelligence_id="lit-1", core_project_id="core-p"))

def add_claims(store, aid):
    a=store.add_claim(aid, ArgumentClaimAddRequest(actor_ref="r", statement="Intervention X reduces outcome Y under the studied conditions.", role="thesis", claim_type="causal", work_ids=["work-a"], source_refs=["source:a"]))
    c1=a["claims"][0]["claim_id"]
    b=store.add_claim(aid, ArgumentClaimAddRequest(actor_ref="r", statement="Study B reports no persistent reduction in outcome Y under alternative conditions.", role="counterclaim", claim_type="comparative", work_ids=["work-b"], source_refs=["source:b"]))
    c2=next(x["claim_id"] for x in b["claims"] if x["role"]=="counterclaim")
    return c1,c2

def test_create_inherits_literature_lineage_without_auto_claims(tmp_path):
    s=make_store(tmp_path); rec=create_project(s)
    assert rec["schema"]==ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA
    assert rec["research_question"]=="Does X affect Y?" and rec["systematic_review_id"]=="review-1"
    assert rec["literature_intelligence_fingerprint"]=="lit-hash" and rec["claims"]==[]
    assert rec["governance"]["counterclaims_are_not_automatically_generated"] is True

def test_claims_work_validation_and_idempotency(tmp_path):
    s=make_store(tmp_path); aid=create_project(s)["argument_intelligence_id"]
    req=ArgumentClaimAddRequest(actor_ref="r", statement="Claim A is observed in Study A.", role="claim", work_ids=["work-a"])
    one=s.add_claim(aid,req); two=s.add_claim(aid,req)
    assert len(one["claims"])==1 and len(two["claims"])==1 and two["claims"][0]["truth_status"]=="undetermined"
    try: s.add_claim(aid,ArgumentClaimAddRequest(actor_ref="r",statement="Bad work reference claim.",work_ids=["work-missing"]))
    except ValueError as exc: assert "work_ids" in str(exc)
    else: raise AssertionError("unknown work id should fail")

def test_claim_evidence_matrix_is_descriptive_not_strength_score(tmp_path):
    s=make_store(tmp_path); aid=create_project(s)["argument_intelligence_id"]; c1,c2=add_claims(s,aid)
    s.add_evidence_link(aid,ClaimEvidenceLinkRequest(actor_ref="r",claim_id=c1,source_ref="source:a",relation="supports",evidence_ref="ev:a",declared_strength="moderate"))
    s.add_evidence_link(aid,ClaimEvidenceLinkRequest(actor_ref="r",claim_id=c1,source_ref="source:b",relation="contradicts",evidence_ref="ev:b"))
    m=s.claim_evidence_matrix(aid); row=next(x for x in m["rows"] if x["claim_id"]==c1)
    assert row["evidence_relation_counts"]=={"supports":1,"contradicts":1}
    assert row["truth_status"]=="undetermined" and m["governance"]["automatic_claim_ranking"] is False

def test_argument_map_counterclaim_relations_assumptions_and_tensions(tmp_path):
    s=make_store(tmp_path); aid=create_project(s)["argument_intelligence_id"]; c1,c2=add_claims(s,aid)
    s.add_claim_relation(aid,ClaimRelationAddRequest(actor_ref="r",source_claim_id=c2,target_claim_id=c1,relation="challenges",rationale="Alternative conditions challenge generality."))
    s.add_assumption(aid,ClaimAssumptionAddRequest(actor_ref="r",claim_id=c1,text="The populations are sufficiently comparable.",assumption_type="comparability"))
    s.add_tension(aid,ArgumentTensionAddRequest(actor_ref="r",title="Context dependence",description="The studies disagree across conditions.",claim_ids=[c1,c2]))
    amap=s.argument_map(aid); reg=s.contradiction_register(aid)
    assert len(amap["nodes"])==2 and amap["edges"][0]["relation"]=="challenges" and len(amap["assumptions"])==1
    assert len(reg["claim_challenges"])==1 and len(reg["tensions"])==1 and reg["governance"]["contradictions_are_registered_not_resolved"] is True

def test_claim_decision_is_for_analysis_not_truth_status(tmp_path):
    s=make_store(tmp_path); aid=create_project(s)["argument_intelligence_id"]; c1,_=add_claims(s,aid)
    rec=s.decide_claim(aid,ClaimDecisionRequest(actor_ref="reviewer",claim_id=c1,decision="accepted_for_analysis",rationale="Within scope."))
    claim=next(x for x in rec["claims"] if x["claim_id"]==c1)
    assert claim["decision"]=="accepted_for_analysis" and claim["truth_status"]=="undetermined"
    assert rec["governance"]["claim_acceptance_is_for_analysis_not_truth_status"] is True

def test_synthesis_handoff_is_non_writing_and_explicit(tmp_path):
    s=make_store(tmp_path); aid=create_project(s)["argument_intelligence_id"]; c1,c2=add_claims(s,aid)
    s.add_claim_relation(aid,ClaimRelationAddRequest(actor_ref="r",source_claim_id=c2,target_claim_id=c1,relation="rebuts",rationale="Direct rebuttal."))
    out=s.argument_synthesis_handoff(aid)
    assert out["target"]=="argument-synthesis-plan" and out["write_performed"] is False
    assert out["thesis_text"].startswith("Intervention X") and out["relations"][0]["relation"]=="contradicts"
    assert out["governance"]["automatic_relation_inference"] is False

def test_readiness_core_candidate_and_immutable_snapshot(tmp_path):
    s=make_store(tmp_path); aid=create_project(s)["argument_intelligence_id"]; c1,_=add_claims(s,aid)
    s.add_evidence_link(aid,ClaimEvidenceLinkRequest(actor_ref="r",claim_id=c1,source_ref="source:a",relation="supports"))
    assert s.readiness(aid)["ready_for_governed_handoff"] is False
    s.set_state(aid,ArgumentIntelligenceStateRequest(actor_ref="reviewer",state="approved",note="Structurally ready."))
    assert s.readiness(aid)["ready_for_governed_handoff"] is True
    cand=s.core_candidate(aid); assert cand["handoff_status"]=="human-approved-candidate" and cand["promotion_performed"] is False
    req=ArgumentIntelligenceSnapshotRequest(actor_ref="reviewer",argument_intelligence_id=aid)
    a=s.freeze_snapshot(req)
    assert a["schema"]==ARGUMENT_CLAIM_COUNTERCLAIM_SNAPSHOT_SCHEMA and len(a["snapshot_hash"])==64 and a["record"]["argument_intelligence_id"]==aid

def test_durable_job_and_authenticated_api_surface(tmp_path, monkeypatch):
    s=make_store(tmp_path); aid=create_project(s)["argument_intelligence_id"]
    assert "argument-claim-counterclaim-intelligence-snapshot" in JOB_TYPES
    import app.services.document_jobs as dj
    monkeypatch.setattr(dj, "get_argument_claim_counterclaim_intelligence_store", lambda: s)
    events=[]
    claim=JobClaim(job_id="job-1060",job_type="argument-claim-counterclaim-intelligence-snapshot",payload={"snapshot":{"actor_ref":"r","argument_intelligence_id":aid}},attempts=1,max_attempts=3,worker_id="w")
    out=asyncio.run(execute_job(claim,lambda stage,percent: events.append((stage,percent))))
    assert out["schema"]==ARGUMENT_CLAIM_COUNTERCLAIM_SNAPSHOT_SCHEMA and events[-1]==("argument-claim-counterclaim-intelligence-snapshot-ready",95)
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/argument-claim-counterclaim-intelligence/capabilities",
        "/v1/core/argument-claim-counterclaim-intelligence/projects",
        "/v1/core/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/claim-evidence-matrix",
        "/v1/core/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/argument-map",
        "/v1/core/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/argument-synthesis-handoff",
        "/v1/core/argument-claim-counterclaim-intelligence/snapshots/freeze",
    }
    assert not(required-paths), required-paths
    client=TestClient(app); assert client.get("/v1/core/argument-claim-counterclaim-intelligence/capabilities").status_code==401
    ok=client.get("/v1/core/argument-claim-counterclaim-intelligence/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert ok.status_code==200 and ok.json()["automatic_truth_promotion"] is False

def test_unified_environment_accepts_argument_intelligence_binding(tmp_path):
    s=make_store(tmp_path); aid=create_project(s)["argument_intelligence_id"]
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/"env.sqlite3", argument_intelligence_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="r",title="Unified",project_ref="p",argument_intelligence_ids=[aid]))
    line=env.lineage(rec["environment_id"]); ready=env.readiness(rec["environment_id"])
    assert len(line["research_design"]["argument_intelligence"])==1
    assert ready["dimensions"]["argument_intelligence_bound"] is True
    assert capabilities()["claim_acceptance_is_for_analysis_not_truth_status"] is True
