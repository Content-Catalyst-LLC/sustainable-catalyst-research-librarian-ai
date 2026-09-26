from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.research_question_hypothesis import ResearchQuestionPlanCreateRequest, ResearchVariableSpec
from app.contracts.research_design_methodology import ResearchDesignPlanCreateRequest
from app.contracts.evidence_search_strategy import EvidenceSearchStrategyCreateRequest
from app.contracts.systematic_review_evidence_synthesis import (
    SystematicReviewCreateRequest, ReviewCandidateAddRequest, ReviewScreeningDecisionRequest,
    ReviewExtractionRequest, ReviewBiasAssessmentRequest, ReviewEvidenceGradeRequest,
    ReviewSynthesisPlanRequest, SystematicReviewStateRequest, SystematicReviewSnapshotRequest,
)
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.research_question_hypothesis import ResearchQuestionHypothesisStore
from app.services.research_design_methodology import ResearchDesignMethodologyStore
from app.services.evidence_search_strategy import EvidenceSearchStrategyStore
from app.services.systematic_review_evidence_synthesis import SystematicReviewEvidenceSynthesisStore, capabilities
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore
from app.services.document_jobs import execute_job

def qrequest():
    return ResearchQuestionPlanCreateRequest(actor_ref="researcher",project_ref="core:project:grad-4",title="Grid evidence question",broad_question="How does renewable-energy penetration affect electricity-price volatility under different grid-storage scenarios?",question_type="causal",population="regional electricity markets",context="high-renewable power systems",variables=[ResearchVariableSpec(name="renewable penetration",role="exposure"),ResearchVariableSpec(name="price volatility",role="outcome"),ResearchVariableSpec(name="storage availability",role="moderator")],evidence_requirements=["empirical estimates of price volatility","storage capacity or availability data"])

def make(tmp_path):
    qs=ResearchQuestionHypothesisStore(tmp_path/"q.sqlite3"); q=qs.create(qrequest())
    ds=ResearchDesignMethodologyStore(tmp_path/"d.sqlite3",question_store=qs); d=ds.create(ResearchDesignPlanCreateRequest(actor_ref="r",project_ref="core:project:grad-4",question_plan_id=q["plan_id"],title="Grid methodology"))
    es=EvidenceSearchStrategyStore(tmp_path/"s.sqlite3",question_store=qs,design_store=ds); s=es.create(EvidenceSearchStrategyCreateRequest(actor_ref="r",project_ref="core:project:grad-4",question_plan_id=q["plan_id"],research_design_plan_id=d["plan_id"],title="Grid evidence search protocol"))
    rs=SystematicReviewEvidenceSynthesisStore(tmp_path/"r.sqlite3",search_store=es,question_store=qs,design_store=ds)
    review=rs.create(SystematicReviewCreateRequest(actor_ref="r",project_ref="core:project:grad-4",evidence_search_strategy_id=s["strategy_id"],title="Grid systematic review"))
    return qs,q,ds,d,es,s,rs,review

def add_included(rs,review_id):
    rec=rs.add_candidate(review_id,ReviewCandidateAddRequest(actor_ref="r",source_ref="library:doc:1",title="Storage and price volatility",publication_year=2025,retrieval_ref="search-run:1"))
    cid=rec["candidates"][0]["candidate_id"]
    rs.screen(review_id,ReviewScreeningDecisionRequest(actor_ref="reviewer-a",candidate_id=cid,stage="title-abstract",decision="include",reason="Potentially eligible."))
    rs.screen(review_id,ReviewScreeningDecisionRequest(actor_ref="reviewer-a",candidate_id=cid,stage="full-text",decision="include",reason="Meets protocol criteria."))
    return cid

def test_create_inherits_v103_protocol_and_scaffolds_extraction_fields(tmp_path):
    _,q,_,d,_,s,_,review=make(tmp_path)
    assert review["review_question"]==q["broad_question"]
    assert review["question_plan_id"]==q["plan_id"] and review["research_design_plan_id"]==d["plan_id"]
    assert review["inclusion_criteria"]==s["inclusion_criteria"] and review["exclusion_criteria"]==s["exclusion_criteria"]
    assert "study_design" in review["extraction_fields"] and review["search_protocol_fingerprint"]==s["record_hash"]
    assert review["governance"]["automatic_study_inclusion"] is False

def test_candidate_registry_screening_and_flow_are_auditable(tmp_path):
    *_,rs,review=make(tmp_path); rid=review["review_id"]
    req=ReviewCandidateAddRequest(actor_ref="r",source_ref="library:doc:1",title="Study")
    a=rs.add_candidate(rid,req); b=rs.add_candidate(rid,req); assert len(a["candidates"])==len(b["candidates"])==1
    cid=a["candidates"][0]["candidate_id"]
    rs.screen(rid,ReviewScreeningDecisionRequest(actor_ref="human-reviewer",candidate_id=cid,stage="title-abstract",decision="include"))
    rs.screen(rid,ReviewScreeningDecisionRequest(actor_ref="human-reviewer",candidate_id=cid,stage="full-text",decision="include"))
    flow=rs.flow(rid); assert flow["flow"]["included_candidates"]==1 and flow["governance"]["screening_decisions_are_human_records"] is True

def test_extraction_bias_and_certainty_are_recorded_not_inferred(tmp_path):
    *_,rs,review=make(tmp_path); rid=review["review_id"]; cid=add_included(rs,rid)
    rs.add_extraction(rid,ReviewExtractionRequest(actor_ref="r",candidate_id=cid,fields={"sample_size":240},population="regional markets",outcomes=[{"name":"price volatility","estimate":-0.12}],source_locator_refs=["library:doc:1#p12"]))
    rs.add_bias_assessment(rid,ReviewBiasAssessmentRequest(actor_ref="reviewer-a",candidate_id=cid,instrument="ROBINS-I",domain="confounding",judgment="some-concerns",rationale="Residual confounding remains possible."))
    rs.add_evidence_grade(rid,ReviewEvidenceGradeRequest(actor_ref="reviewer-a",outcome_ref="price-volatility",framework="GRADE",certainty="moderate",rationale="Reviewer-recorded certainty.",study_refs=[cid]))
    assert rs.extraction_matrix(rid)["rows"][0]["extraction"]["human_recorded"] is True
    assert rs.bias_summary(rid)["judgment_counts"]["some-concerns"]==1
    assert rs.certainty_summary(rid)["certainty_counts"]["moderate"]==1
    assert rs.bias_summary(rid)["governance"]["summary_does_not_compute_or_override_bias_judgments"] is True

def test_synthesis_handoff_requires_complete_human_approved_review(tmp_path):
    *_,rs,review=make(tmp_path); rid=review["review_id"]; cid=add_included(rs,rid)
    rs.add_extraction(rid,ReviewExtractionRequest(actor_ref="r",candidate_id=cid,fields={"effect_estimate":-0.12},outcomes=[{"name":"price volatility"}]))
    rs.add_synthesis_plan(rid,ReviewSynthesisPlanRequest(actor_ref="r",label="Primary synthesis",synthesis_type="meta-analysis",included_candidate_ids=[cid],outcome_refs=["price-volatility"],analysis_candidates=["random-effects meta-analysis candidate","heterogeneity diagnostics"],execution_target="analytics-r"))
    assert rs.readiness(rid)["ready_for_synthesis_handoff"] is False
    rs.set_review_state(rid,SystematicReviewStateRequest(actor_ref="principal-reviewer",state="approved",note="Protocol, screening and extraction reviewed."))
    ready=rs.readiness(rid); out=rs.synthesis_handoffs(rid)
    assert ready["ready_for_synthesis_handoff"] is True and out["handoffs"][0]["target"]=="analytics-r"
    assert out["analysis_executed"] is False and out["meta_analysis_executed"] is False

def test_core_candidate_preserves_platform_core_authority(tmp_path):
    *_,rs,review=make(tmp_path); rid=review["review_id"]
    out=rs.core_candidate(rid); assert out["candidate"]["object_type"]=="systematic-review-evidence-synthesis" and out["promotion_performed"] is False
    assert out["governance"]["platform_core_remains_authority"] is True
    rs.set_review_state(rid,SystematicReviewStateRequest(actor_ref="r",state="approved")); assert rs.core_candidate(rid)["handoff_status"]=="human-approved-candidate"

def test_snapshot_and_durable_job(tmp_path,monkeypatch):
    *_,rs,review=make(tmp_path); rid=review["review_id"]
    snap=rs.freeze_snapshot(SystematicReviewSnapshotRequest(actor_ref="r",review_id=rid)); assert len(snap["snapshot_hash"])==64
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_systematic_review_evidence_synthesis_store",lambda:rs)
    claim=JobClaim(job_id="job-1040",job_type="systematic-review-evidence-synthesis-snapshot",payload={"snapshot":{"actor_ref":"r","review_id":rid}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-systematic-review-evidence-synthesis-snapshot/1.0" and events[-1]==("systematic-review-evidence-synthesis-snapshot-ready",95)
    assert "systematic-review-evidence-synthesis-snapshot" in JOB_TYPES

def test_capabilities_and_authenticated_api_surface():
    cap=capabilities(); assert cap["milestone"]=="10.4" and cap["automatic_study_inclusion"] is False and cap["automatic_meta_analysis_execution"] is False
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}; required={"/v1/core/systematic-review-evidence-synthesis/capabilities","/v1/core/systematic-review-evidence-synthesis/reviews","/v1/core/systematic-review-evidence-synthesis/reviews/{review_id}/screening-decisions","/v1/core/systematic-review-evidence-synthesis/reviews/{review_id}/extraction-matrix","/v1/core/systematic-review-evidence-synthesis/reviews/{review_id}/readiness","/v1/core/systematic-review-evidence-synthesis/reviews/{review_id}/synthesis-handoffs","/v1/core/systematic-review-evidence-synthesis/reviews/{review_id}/core-candidate","/v1/core/systematic-review-evidence-synthesis/snapshots/freeze"}
    assert not(required-paths),required-paths
    client=TestClient(app); assert client.get("/v1/core/systematic-review-evidence-synthesis/capabilities").status_code==401
    ok=client.get("/v1/core/systematic-review-evidence-synthesis/capabilities",headers={"X-SC-RL-Key":"test-key"}); assert ok.status_code==200 and ok.json()["human_screening_decisions_required"] is True

def test_no_auto_scientific_judgment_guardrails_are_explicit():
    cap=capabilities()
    for key in ["automatic_study_inclusion","automatic_risk_of_bias_judgment","automatic_evidence_certainty_grading","automatic_meta_analysis_execution","automatic_truth_promotion"]: assert cap[key] is False
    assert cap["knowledge_library_remains_source_authority"] is True and cap["platform_core_remains_authority"] is True

def test_unified_environment_can_bind_systematic_review(tmp_path):
    qs,q,ds,d,es,s,rs,review=make(tmp_path)
    envs=UnifiedScholarlyAIEnvironmentStore(tmp_path/"e.sqlite3",question_store=qs,design_store=ds,search_store=es,systematic_review_store=rs)
    env=envs.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="r",title="Program",project_ref="core:project:grad-4",research_question=q["broad_question"],question_plan_ids=[q["plan_id"]],research_design_plan_ids=[d["plan_id"]],evidence_search_strategy_ids=[s["strategy_id"]],systematic_review_ids=[review["review_id"]]))
    line=envs.lineage(env["environment_id"]); assert line["research_design"]["systematic_reviews"][0]["review"]["review_id"]==review["review_id"]
    assert envs.readiness(env["environment_id"])["dimensions"]["systematic_review_bound"] is True
