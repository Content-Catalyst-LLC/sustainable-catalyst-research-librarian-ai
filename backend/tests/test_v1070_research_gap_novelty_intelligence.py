from pathlib import Path
import asyncio
from fastapi.testclient import TestClient
from app.async_jobs import JOB_TYPES, JobClaim
from app.contracts.research_gap_novelty_intelligence import (
    RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA, RESEARCH_GAP_NOVELTY_SNAPSHOT_SCHEMA,
    ResearchGapNoveltyCreateRequest, ResearchGapCandidateAddRequest, ResearchGapDecisionRequest,
    NoveltyCandidateAddRequest, NoveltyDecisionRequest, OriginalResearchOpportunityAddRequest,
    ResearchGapNoveltyStateRequest, ResearchGapNoveltySnapshotRequest,
)
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.research_gap_novelty_intelligence import ResearchGapNoveltyIntelligenceStore, capabilities
from app.services.document_jobs import execute_job
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakeArguments:
    def get(self, aid):
        if aid!="arg-1": raise ValueError("missing argument")
        return {"argument_intelligence_id":"arg-1","record_hash":"arg-hash","research_question":"How does X affect Y?","literature_intelligence_id":"lit-1","systematic_review_id":"review-1","core_project_id":"core-p","claims":[{"claim_id":"claim-a","statement":"X affects Y."},{"claim_id":"claim-b","statement":"X does not affect Y."}],"evidence_links":[{"claim_id":"claim-a","relation":"supports"}],"tensions":[{"tension_id":"ten-1","state":"open","description":"Findings conflict across contexts."}]}
class FakeLiterature:
    def get(self, iid):
        if iid!="lit-1": raise ValueError("missing literature")
        return {"intelligence_id":"lit-1","record_hash":"lit-hash","research_question":"How does X affect Y?","systematic_review_id":"review-1","research_design_plan_id":"design-1","works":[{"work_id":"work-a","source_ref":"source:a"},{"work_id":"work-b","source_ref":"source:b"}],"literature_strands":[{"strand_id":"strand-1","work_ids":["work-a"]}],"gaps":[{"gap_id":"lit-gap-1","gap_type":"population","description":"Population B is underrepresented."}]}

def make_store(tmp_path): return ResearchGapNoveltyIntelligenceStore(tmp_path/"gapnov.sqlite3", argument_store=FakeArguments(), literature_store=FakeLiterature())
def create_project(s): return s.create(ResearchGapNoveltyCreateRequest(actor_ref="r",title="Gap and novelty",project_ref="project:1",argument_intelligence_id="arg-1"))

def test_create_inherits_argument_and_literature_lineage(tmp_path):
    s=make_store(tmp_path); rec=create_project(s)
    assert rec["schema"]==RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA
    assert rec["research_question"]=="How does X affect Y?" and rec["literature_intelligence_id"]=="lit-1"
    assert rec["argument_intelligence_fingerprint"]=="arg-hash" and rec["literature_intelligence_fingerprint"]=="lit-hash"
    assert rec["governance"]["automatic_novelty_certification"] is False

def test_structural_signals_surface_observations_not_certified_gaps(tmp_path):
    s=make_store(tmp_path); gid=create_project(s)["gap_novelty_id"]; out=s.structural_signals(gid)
    kinds={x["signal_type"] for x in out["signals"]}
    assert "unresolved-contradiction-or-tension" in kinds and "claim-without-recorded-evidence-link" in kinds and "human-declared-literature-gap" in kinds and "sparse-literature-strand" in kinds
    assert out["governance"]["signals_are_structural_observations_not_validated_research_gaps"] is True

def test_gap_candidates_validate_upstream_refs_and_require_human_decision(tmp_path):
    s=make_store(tmp_path); gid=create_project(s)["gap_novelty_id"]
    req=ResearchGapCandidateAddRequest(actor_ref="r",gap_type="contradiction",label="Context contradiction",description="The findings conflict across contexts.",claim_ids=["claim-a","claim-b"],tension_ids=["ten-1"],work_ids=["work-a"])
    a=s.add_gap_candidate(gid,req); b=s.add_gap_candidate(gid,req); gap=a["gap_candidates"][0]
    assert len(b["gap_candidates"])==1 and gap["decision"]=="pending" and gap["validated_gap"] is False
    decided=s.decide_gap(gid,ResearchGapDecisionRequest(actor_ref="reviewer",gap_id=gap["gap_id"],decision="accepted",rationale="Supported as a scoped gap."))
    assert decided["gap_candidates"][0]["validated_gap"] is True
    try: s.add_gap_candidate(gid,ResearchGapCandidateAddRequest(actor_ref="r",gap_type="data",label="Bad",description="Unknown reference.",claim_ids=["missing"]))
    except ValueError as exc: assert "claim_ids" in str(exc)
    else: raise AssertionError("unknown upstream reference should fail")

def test_novelty_candidate_requires_explicit_comparison_basis_and_human_acceptance(tmp_path):
    s=make_store(tmp_path); gid=create_project(s)["gap_novelty_id"]
    rec=s.add_gap_candidate(gid,ResearchGapCandidateAddRequest(actor_ref="r",gap_type="population",label="Population gap",description="Population B is underrepresented.",work_ids=["work-a"])); gap=rec["gap_candidates"][0]; s.decide_gap(gid,ResearchGapDecisionRequest(actor_ref="reviewer",gap_id=gap["gap_id"],decision="accepted"))
    try: s.add_novelty_candidate(gid,NoveltyCandidateAddRequest(actor_ref="r",novelty_type="population",label="New population",description="Study Population B.",gap_ids=[gap["gap_id"]],comparison_basis=""))
    except ValueError as exc: assert "comparison_basis" in str(exc)
    else: raise AssertionError("comparison basis should be required")
    rec=s.add_novelty_candidate(gid,NoveltyCandidateAddRequest(actor_ref="r",novelty_type="population",label="New population",description="Study Population B.",gap_ids=[gap["gap_id"]],comparison_basis="Compared with the registered literature corpus, Population B is not represented in the scoped studies.")); n=rec["novelty_candidates"][0]
    assert n["decision"]=="pending" and n["novelty_certified"] is False
    rec=s.decide_novelty(gid,NoveltyDecisionRequest(actor_ref="reviewer",novelty_candidate_id=n["novelty_candidate_id"],decision="accepted",rationale="Accepted as a planning candidate."))
    assert rec["novelty_candidates"][0]["novelty_certified"] is False

def test_original_research_opportunity_is_planning_candidate_not_originality_proof(tmp_path):
    s=make_store(tmp_path); gid=create_project(s)["gap_novelty_id"]
    rec=s.add_gap_candidate(gid,ResearchGapCandidateAddRequest(actor_ref="r",gap_type="replication",label="Replication gap",description="No replication is registered for this scoped claim.",claim_ids=["claim-a"])); gap=rec["gap_candidates"][0]; s.decide_gap(gid,ResearchGapDecisionRequest(actor_ref="r",gap_id=gap["gap_id"],decision="accepted"))
    rec=s.add_novelty_candidate(gid,NoveltyCandidateAddRequest(actor_ref="r",novelty_type="replication",label="Independent replication",description="Replicate the result in a second setting.",gap_ids=[gap["gap_id"]],comparison_basis="The scoped registry contains no accepted replication record.")); n=rec["novelty_candidates"][0]
    out=s.add_research_opportunity(gid,OriginalResearchOpportunityAddRequest(actor_ref="r",title="Replication study",research_question="Does X affect Y in setting B?",gap_ids=[gap["gap_id"]],novelty_candidate_ids=[n["novelty_candidate_id"]],rationale="Addresses the scoped replication gap."))
    assert len(out["research_opportunities"])==1 and out["research_opportunities"][0]["originality_certified"] is False
    assert out["governance"]["research_opportunities_are_planning_candidates_not_originality_certification"] is True

def test_landscape_readiness_handoff_core_candidate_and_snapshot(tmp_path):
    s=make_store(tmp_path); gid=create_project(s)["gap_novelty_id"]
    rec=s.add_gap_candidate(gid,ResearchGapCandidateAddRequest(actor_ref="r",gap_type="data",label="Data gap",description="No longitudinal data are registered.",work_ids=["work-b"])); gap=rec["gap_candidates"][0]
    assert s.readiness(gid)["ready_for_governed_handoff"] is False
    s.decide_gap(gid,ResearchGapDecisionRequest(actor_ref="reviewer",gap_id=gap["gap_id"],decision="accepted")); s.set_state(gid,ResearchGapNoveltyStateRequest(actor_ref="reviewer",state="approved",note="Ready for planning."))
    assert s.readiness(gid)["ready_for_governed_handoff"] is True
    assert s.landscape(gid)["governance"]["automatic_priority_ranking"] is False
    hand=s.research_planning_handoff(gid); assert hand["write_performed"] is False and len(hand["accepted_gap_candidates"])==1
    cand=s.core_candidate(gid); assert cand["handoff_status"]=="human-approved-candidate" and cand["promotion_performed"] is False
    snap=s.freeze_snapshot(ResearchGapNoveltySnapshotRequest(actor_ref="reviewer",gap_novelty_id=gid)); assert snap["schema"]==RESEARCH_GAP_NOVELTY_SNAPSHOT_SCHEMA and len(snap["snapshot_hash"])==64

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); gid=create_project(s)["gap_novelty_id"]
    assert "research-gap-novelty-intelligence-snapshot" in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_research_gap_novelty_intelligence_store",lambda:s)
    events=[]; claim=JobClaim(job_id="job-1070",job_type="research-gap-novelty-intelligence-snapshot",payload={"snapshot":{"actor_ref":"r","gap_novelty_id":gid}},attempts=1,max_attempts=3,worker_id="w")
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out["schema"]==RESEARCH_GAP_NOVELTY_SNAPSHOT_SCHEMA and events[-1]==("research-gap-novelty-intelligence-snapshot-ready",95)
    from app.main import app; paths={getattr(r,"path","") for r in app.routes}; required={"/v1/core/research-gap-novelty-intelligence/capabilities","/v1/core/research-gap-novelty-intelligence/projects","/v1/core/research-gap-novelty-intelligence/projects/{gap_novelty_id}/structural-signals","/v1/core/research-gap-novelty-intelligence/projects/{gap_novelty_id}/landscape","/v1/core/research-gap-novelty-intelligence/projects/{gap_novelty_id}/research-planning-handoff","/v1/core/research-gap-novelty-intelligence/snapshots/freeze"}
    assert not(required-paths),required-paths
    client=TestClient(app); assert client.get("/v1/core/research-gap-novelty-intelligence/capabilities").status_code==401
    ok=client.get("/v1/core/research-gap-novelty-intelligence/capabilities",headers={"X-SC-RL-Key":"test-key"}); assert ok.status_code==200 and ok.json()["automatic_novelty_certification"] is False

def test_unified_environment_accepts_research_gap_novelty_binding(tmp_path):
    s=make_store(tmp_path); gid=create_project(s)["gap_novelty_id"]
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/"env.sqlite3", research_gap_novelty_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="r",title="Unified",project_ref="p",research_gap_novelty_ids=[gid]))
    line=env.lineage(rec["environment_id"]); ready=env.readiness(rec["environment_id"])
    assert len(line["research_design"]["research_gap_novelty_intelligence"])==1 and ready["dimensions"]["research_gap_novelty_bound"] is True
    assert capabilities()["research_opportunities_are_planning_candidates_not_originality_certification"] is True

def test_capability_guardrails_are_explicit():
    cap=capabilities(); assert cap["human_gap_acceptance_required"] is True and cap["human_novelty_acceptance_required"] is True
    assert cap["automatic_gap_certification"] is False and cap["automatic_novelty_certification"] is False and cap["automatic_originality_claims"] is False and cap["automatic_priority_ranking"] is False and cap["automatic_truth_promotion"] is False
