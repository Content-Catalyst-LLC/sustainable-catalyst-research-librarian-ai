from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.research_question_hypothesis import ResearchQuestionPlanCreateRequest, ResearchVariableSpec
from app.contracts.research_design_methodology import ResearchDesignPlanCreateRequest
from app.contracts.evidence_search_strategy import (
    EvidenceSearchStrategyCreateRequest, SearchConceptAddRequest, SearchSourceTargetAddRequest,
    SearchQueryAddRequest, SearchEligibilityCriterionRequest, SearchExecutionReceiptRequest,
    EvidenceSearchReviewStateRequest, EvidenceSearchSnapshotRequest,
)
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.research_question_hypothesis import ResearchQuestionHypothesisStore
from app.services.research_design_methodology import ResearchDesignMethodologyStore
from app.services.evidence_search_strategy import EvidenceSearchStrategyStore, capabilities
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore
from app.services.document_jobs import execute_job

def qrequest():
    return ResearchQuestionPlanCreateRequest(actor_ref="researcher",project_ref="core:project:grad-3",title="Grid evidence question",broad_question="How does renewable-energy penetration affect electricity-price volatility under different grid-storage scenarios?",question_type="causal",population="regional electricity markets",context="high-renewable power systems",variables=[ResearchVariableSpec(name="renewable penetration",role="exposure"),ResearchVariableSpec(name="price volatility",role="outcome"),ResearchVariableSpec(name="storage availability",role="moderator")],evidence_requirements=["empirical estimates of price volatility","storage capacity or availability data"])

def make(tmp_path):
    qs=ResearchQuestionHypothesisStore(tmp_path/"q.sqlite3"); q=qs.create(qrequest())
    ds=ResearchDesignMethodologyStore(tmp_path/"d.sqlite3",question_store=qs); d=ds.create(ResearchDesignPlanCreateRequest(actor_ref="r",project_ref="core:project:grad-3",question_plan_id=q["plan_id"],title="Grid methodology"))
    es=EvidenceSearchStrategyStore(tmp_path/"s.sqlite3",question_store=qs,design_store=ds)
    rec=es.create(EvidenceSearchStrategyCreateRequest(actor_ref="r",project_ref="core:project:grad-3",question_plan_id=q["plan_id"],research_design_plan_id=d["plan_id"],title="Grid evidence search protocol"))
    return qs,q,ds,d,es,rec

def test_scaffold_builds_reproducible_concepts_targets_queries_and_criteria(tmp_path):
    _,q,_,_,es,rec=make(tmp_path)
    assert {x["name"] for x in rec["concepts"]} >= {"renewable penetration","price volatility","storage availability"}
    assert {x["source_family"] for x in rec["source_targets"]} >= {"knowledge-library","federated-discovery"}
    assert rec["queries"] and " AND " in rec["queries"][0]["query_text"]
    assert rec["inclusion_criteria"] and rec["exclusion_criteria"]
    assert rec["research_question"]==q["broad_question"]
    assert rec["governance"]["automatic_external_search_execution"] is False

def test_coverage_maps_evidence_requirements_without_claiming_sufficiency(tmp_path):
    _,_,_,_,es,rec=make(tmp_path); cov=es.coverage(rec["strategy_id"])
    assert cov["total"] >= 2 and cov["covered"]==cov["total"]
    assert cov["governance"]["coverage_is_protocol_mapping_not_evidence_sufficiency"] is True

def test_additions_and_receipts_are_idempotent_audit_records(tmp_path):
    _,_,_,_,es,rec=make(tmp_path); sid=rec["strategy_id"]
    c=SearchConceptAddRequest(actor_ref="r",name="battery storage",terms=["battery storage","energy storage system"])
    a=es.add_concept(sid,c); b=es.add_concept(sid,c); assert len(a["concepts"])==len(b["concepts"])
    t=SearchSourceTargetAddRequest(actor_ref="r",name="Institutional repository",source_family="institutional-repository",target_ref="repository:test")
    a=es.add_source_target(sid,t); b=es.add_source_target(sid,t); assert len(a["source_targets"])==len(b["source_targets"])
    q=SearchQueryAddRequest(actor_ref="r",label="Storage synonym query",query_text='"battery storage" AND volatility',target_refs=["knowledge-library"])
    rec=es.add_query(sid,q); qid=rec["queries"][-1]["query_id"]
    r=SearchExecutionReceiptRequest(actor_ref="r",query_id=qid,target_ref="knowledge-library",execution_ref="search-run:1",result_count=15,imported_count=0)
    a=es.add_execution_receipt(sid,r); b=es.add_execution_receipt(sid,r); assert len(a["execution_receipts"])==len(b["execution_receipts"])
    assert a["execution_receipts"][-1]["imported_count"]==0

def test_readiness_requires_human_protocol_approval(tmp_path):
    _,_,_,_,es,rec=make(tmp_path); sid=rec["strategy_id"]
    pending=es.readiness(sid); assert pending["ready_for_protocol_review"] is True and pending["ready_for_search_handoff"] is False
    es.set_review_state(sid,EvidenceSearchReviewStateRequest(actor_ref="r",state="approved",note="Human-reviewed protocol."))
    ready=es.readiness(sid); assert ready["ready_for_search_handoff"] is True

def test_handoffs_prepare_queries_without_execution_or_import(tmp_path):
    _,_,_,_,es,rec=make(tmp_path); sid=rec["strategy_id"]
    out=es.execution_handoffs(sid); assert out["handoffs"] and out["delivery_performed"] is False and out["search_executed"] is False and out["sources_imported"] is False
    assert out["governance"]["automatic_source_acceptance"] is False

def test_platform_core_protocol_candidate_is_not_evidence_promotion(tmp_path):
    _,_,_,_,es,rec=make(tmp_path); sid=rec["strategy_id"]
    out=es.core_candidate(sid); assert out["candidate"]["object_type"]=="evidence-search-protocol" and out["promotion_performed"] is False
    assert out["handoff_status"]=="requires-human-approval"
    es.set_review_state(sid,EvidenceSearchReviewStateRequest(actor_ref="r",state="approved")); assert es.core_candidate(sid)["handoff_status"]=="human-approved-candidate"

def test_snapshot_and_durable_job(tmp_path,monkeypatch):
    _,_,_,_,es,rec=make(tmp_path); sid=rec["strategy_id"]
    snap=es.freeze_snapshot(EvidenceSearchSnapshotRequest(actor_ref="r",strategy_id=sid)); assert len(snap["snapshot_hash"])==64
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_evidence_search_strategy_store",lambda:es)
    claim=JobClaim(job_id="job-1030",job_type="evidence-search-strategy-snapshot",payload={"snapshot":{"actor_ref":"r","strategy_id":sid}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-evidence-search-strategy-snapshot/1.0" and events[-1]==("evidence-search-strategy-snapshot-ready",95)
    assert "evidence-search-strategy-snapshot" in JOB_TYPES

def test_capabilities_and_authenticated_api_surface():
    cap=capabilities(); assert cap["milestone"]=="10.3" and cap["automatic_external_search_execution"] is False and cap["automatic_source_acceptance"] is False
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}; required={"/v1/core/evidence-search-strategy/capabilities","/v1/core/evidence-search-strategy/strategies","/v1/core/evidence-search-strategy/strategies/{strategy_id}/queries","/v1/core/evidence-search-strategy/strategies/{strategy_id}/coverage","/v1/core/evidence-search-strategy/strategies/{strategy_id}/readiness","/v1/core/evidence-search-strategy/strategies/{strategy_id}/execution-handoffs","/v1/core/evidence-search-strategy/strategies/{strategy_id}/core-candidate","/v1/core/evidence-search-strategy/snapshots/freeze"}
    assert not(required-paths),required-paths
    client=TestClient(app); assert client.get("/v1/core/evidence-search-strategy/capabilities").status_code==401
    ok=client.get("/v1/core/evidence-search-strategy/capabilities",headers={"X-SC-RL-Key":"test-key"}); assert ok.status_code==200 and ok.json()["human_search_protocol_approval_required"] is True

def test_unified_environment_can_bind_evidence_search_strategy(tmp_path):
    qs,q,ds,d,es,rec=make(tmp_path)
    envs=UnifiedScholarlyAIEnvironmentStore(tmp_path/"e.sqlite3",question_store=qs,design_store=ds,search_store=es)
    env=envs.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="r",title="Program",project_ref="core:project:grad-3",research_question=q["broad_question"],question_plan_ids=[q["plan_id"]],research_design_plan_ids=[d["plan_id"]],evidence_search_strategy_ids=[rec["strategy_id"]]))
    line=envs.lineage(env["environment_id"]); assert line["research_design"]["search_strategies"][0]["strategy"]["strategy_id"]==rec["strategy_id"]
    assert envs.readiness(env["environment_id"])["dimensions"]["evidence_search_strategy_bound"] is True
