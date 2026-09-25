from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.research_question_hypothesis import ResearchQuestionPlanCreateRequest, ResearchVariableSpec
from app.contracts.research_design_methodology import (
    ResearchDesignPlanCreateRequest, MethodologyCandidateAddRequest, ResearchDesignValidityThreatRequest,
    ResearchDesignPreferenceRequest, ResearchDesignReviewStateRequest, ResearchDesignSnapshotRequest,
)
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.research_question_hypothesis import ResearchQuestionHypothesisStore
from app.services.research_design_methodology import ResearchDesignMethodologyStore, capabilities
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore
from app.services.document_jobs import execute_job

def qrequest():
    return ResearchQuestionPlanCreateRequest(actor_ref="researcher",project_ref="core:project:grad-2",title="Energy price volatility",broad_question="How does renewable-energy penetration affect electricity-price volatility under different grid-storage scenarios?",question_type="causal",population="regional electricity markets",context="high-renewable power systems",variables=[ResearchVariableSpec(name="renewable penetration",role="exposure"),ResearchVariableSpec(name="price volatility",role="outcome"),ResearchVariableSpec(name="storage availability",role="moderator")])

def make(tmp_path):
    qs=ResearchQuestionHypothesisStore(tmp_path/"q.sqlite3"); q=qs.create(qrequest())
    ds=ResearchDesignMethodologyStore(tmp_path/"d.sqlite3",question_store=qs)
    rec=ds.create(ResearchDesignPlanCreateRequest(actor_ref="researcher",project_ref="core:project:grad-2",question_plan_id=q["plan_id"],title="Energy volatility research design"))
    return qs,q,ds,rec

def test_causal_question_scaffolds_multiple_unranked_candidate_designs(tmp_path):
    _,q,ds,rec=make(tmp_path)
    assert len(rec["candidate_designs"])==2
    assert {x["method_family"] for x in rec["candidate_designs"]}=={"observational","quasi-experimental"}
    cmp=ds.comparison(rec["plan_id"])
    assert cmp["governance"]["comparison_does_not_rank_or_select_methods"] is True
    assert rec["research_question"]==q["broad_question"]

def test_method_candidates_preserve_assumptions_validity_threats_and_execution_boundaries(tmp_path):
    _,_,ds,rec=make(tmp_path); first=rec["candidate_designs"][0]
    assert first["assumptions"] and first["validity_threats"] and first["data_requirements"]
    assert set(first["execution_targets"]) >= {"workspace","research-lab"}
    assert rec["governance"]["automatic_method_selection"] is False
    assert rec["governance"]["specialist_runtimes_retain_execution"] is True

def test_user_candidate_and_validity_threat_registry_are_idempotent(tmp_path):
    _,_,ds,rec=make(tmp_path); pid=rec["plan_id"]
    c=MethodologyCandidateAddRequest(actor_ref="r",label="Survey candidate",method_family="survey",design_type="repeated cross-sectional survey",data_requirements=["probability sample"],assumptions=["sampling frame coverage"],validity_threats=["nonresponse"],analysis_candidates=["weighted estimates"],execution_targets=["workspace"])
    a=ds.add_candidate(pid,c); b=ds.add_candidate(pid,c); assert len(a["candidate_designs"])==len(b["candidate_designs"])
    t=ResearchDesignValidityThreatRequest(actor_ref="r",threat="Policy adoption may be endogenous",category="confounding",mitigation="Document identification strategy")
    a=ds.add_validity_threat(pid,t); b=ds.add_validity_threat(pid,t); assert len(a["validity_threat_registry"])==1 and len(b["validity_threat_registry"])==1

def test_readiness_requires_human_method_preference_and_approval(tmp_path):
    _,_,ds,rec=make(tmp_path); pid=rec["plan_id"]
    initial=ds.readiness(pid); assert initial["ready_for_execution_handoff"] is False and "preferred-design-selected" in initial["blockers"]
    candidate=rec["candidate_designs"][0]["candidate_id"]; ds.set_preference(pid,ResearchDesignPreferenceRequest(actor_ref="r",candidate_id=candidate,rationale="Selected for planning review, not scientific certification."))
    pending=ds.readiness(pid); assert pending["ready_for_review"] is True and pending["ready_for_execution_handoff"] is False
    ds.set_review_state(pid,ResearchDesignReviewStateRequest(actor_ref="r",state="approved",note="Human-reviewed research design."))
    approved=ds.readiness(pid); assert approved["ready_for_execution_handoff"] is True

def test_execution_handoffs_are_packets_not_execution(tmp_path):
    _,_,ds,rec=make(tmp_path); pid=rec["plan_id"]; cid=rec["candidate_designs"][0]["candidate_id"]
    ds.set_preference(pid,ResearchDesignPreferenceRequest(actor_ref="r",candidate_id=cid)); ds.set_review_state(pid,ResearchDesignReviewStateRequest(actor_ref="r",state="approved"))
    out=ds.execution_handoffs(pid); assert out["handoffs"] and out["delivery_performed"] is False and out["execution_performed"] is False
    assert out["governance"]["specialist_runtime_acceptance_is_separate"] is True

def test_platform_core_candidate_is_not_automatic_promotion(tmp_path):
    _,_,ds,rec=make(tmp_path); pid=rec["plan_id"]; cid=rec["candidate_designs"][1]["candidate_id"]
    ds.set_preference(pid,ResearchDesignPreferenceRequest(actor_ref="r",candidate_id=cid)); before=ds.core_candidate(pid)
    assert before["candidate"]["object_type"]=="research-design" and before["promotion_performed"] is False and before["handoff_status"]=="requires-human-approval"
    ds.set_review_state(pid,ResearchDesignReviewStateRequest(actor_ref="r",state="approved")); after=ds.core_candidate(pid); assert after["handoff_status"]=="human-approved-candidate"

def test_snapshot_and_durable_job(tmp_path,monkeypatch):
    _,_,ds,rec=make(tmp_path); pid=rec["plan_id"]
    snap=ds.freeze_snapshot(ResearchDesignSnapshotRequest(actor_ref="r",plan_id=pid)); assert len(snap["snapshot_hash"])==64
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_research_design_methodology_store",lambda:ds)
    claim=JobClaim(job_id="job-1020",job_type="research-design-methodology-snapshot",payload={"snapshot":{"actor_ref":"r","plan_id":pid}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-research-design-methodology-snapshot/1.0" and events[-1]==("research-design-methodology-snapshot-ready",95)
    assert "research-design-methodology-snapshot" in JOB_TYPES

def test_capabilities_and_authenticated_api_surface():
    cap=capabilities(); assert cap["milestone"]=="10.2" and cap["automatic_method_selection"] is False and cap["automatic_execution"] is False
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}; required={"/v1/core/research-design-methodology/capabilities","/v1/core/research-design-methodology/plans","/v1/core/research-design-methodology/plans/{plan_id}/candidates","/v1/core/research-design-methodology/plans/{plan_id}/validity-threats","/v1/core/research-design-methodology/plans/{plan_id}/preference","/v1/core/research-design-methodology/plans/{plan_id}/review-state","/v1/core/research-design-methodology/plans/{plan_id}/comparison","/v1/core/research-design-methodology/plans/{plan_id}/readiness","/v1/core/research-design-methodology/plans/{plan_id}/execution-handoffs","/v1/core/research-design-methodology/plans/{plan_id}/core-candidate","/v1/core/research-design-methodology/snapshots/freeze"}
    assert not(required-paths),required-paths
    client=TestClient(app); assert client.get("/v1/core/research-design-methodology/capabilities").status_code==401
    ok=client.get("/v1/core/research-design-methodology/capabilities",headers={"X-SC-RL-Key":"test-key"}); assert ok.status_code==200 and ok.json()["human_method_selection_required"] is True

def test_unified_environment_can_bind_research_design_plan(tmp_path):
    qs,q,ds,rec=make(tmp_path)
    envs=UnifiedScholarlyAIEnvironmentStore(tmp_path/"e.sqlite3",question_store=qs,design_store=ds)
    env=envs.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="r",title="Program",project_ref="core:project:grad-2",research_question=q["broad_question"],question_plan_ids=[q["plan_id"]],research_design_plan_ids=[rec["plan_id"]]))
    line=envs.lineage(env["environment_id"]); assert line["research_design"]["methodology_plans"][0]["plan"]["plan_id"]==rec["plan_id"]
    assert envs.readiness(env["environment_id"])["dimensions"]["research_design_plan_bound"] is True
