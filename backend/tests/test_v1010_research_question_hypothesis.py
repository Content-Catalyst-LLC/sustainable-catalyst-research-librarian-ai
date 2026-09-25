from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.research_question_hypothesis import (
    ResearchQuestionPlanCreateRequest, ResearchSubquestionAddRequest, ResearchHypothesisAddRequest,
    ResearchEvidenceRequirementRequest, ResearchQuestionReviewStateRequest, ResearchQuestionSnapshotRequest,
    ResearchVariableSpec,
)
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.research_question_hypothesis import ResearchQuestionHypothesisStore, capabilities
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore
from app.services.document_jobs import execute_job


def request(scaffold=True):
    return ResearchQuestionPlanCreateRequest(
        actor_ref="researcher", project_ref="core:project:grad-1", environment_id="env-1",
        title="Energy price volatility question",
        broad_question="How does renewable-energy penetration affect electricity-price volatility under different grid-storage scenarios?",
        question_type="causal", population="regional electricity markets", context="high-renewable power systems",
        geography="multi-region", time_horizon="annual and hourly observations",
        constructs=["renewable penetration","price volatility","storage availability"],
        variables=[
            ResearchVariableSpec(name="renewable penetration",role="exposure",unit="percent"),
            ResearchVariableSpec(name="electricity-price volatility",role="outcome",unit="price dispersion"),
            ResearchVariableSpec(name="storage availability",role="moderator",unit="capacity"),
        ], scaffold_candidates=scaffold,
    )


def test_create_is_idempotent_and_preserves_governance(tmp_path):
    store=ResearchQuestionHypothesisStore(tmp_path/"rq.sqlite3")
    a=store.create(request()); b=store.create(request())
    assert a["plan_id"]==b["plan_id"] and len(a["record_hash"])==64
    assert a["governance"]["candidate_intelligence_not_scientific_judgment"] is True
    assert a["governance"]["platform_core_is_governed_question_hypothesis_authority"] is True
    assert a["governance"]["automatic_core_write"] is False


def test_causal_scaffold_adds_subquestions_evidence_and_candidate_hypotheses(tmp_path):
    store=ResearchQuestionHypothesisStore(tmp_path/"rq.sqlite3"); rec=store.create(request())
    assert len(rec["subquestions"])>=3
    assert len(rec["evidence_requirements"])>=3
    assert {x["hypothesis_type"] for x in rec["hypotheses"]}=={"causal","null"}
    assert all(x["origin"]=="deterministic-scaffold" for x in rec["hypotheses"])
    assert all(x["human_review_status"]=="unreviewed" for x in rec["hypotheses"])


def test_exploratory_question_does_not_force_hypothesis(tmp_path):
    store=ResearchQuestionHypothesisStore(tmp_path/"rq.sqlite3")
    rec=store.create(ResearchQuestionPlanCreateRequest(actor_ref="r",project_ref="core:p:2",title="Explore",broad_question="What patterns characterize community energy resilience?",question_type="exploratory",population="communities",constructs=["resilience"]))
    assert rec["hypotheses"]==[]
    assert store.readiness(rec["plan_id"])["dimensions"]["hypothesis_strategy_defined"] is True


def test_additions_are_idempotent_and_reviewable(tmp_path):
    store=ResearchQuestionHypothesisStore(tmp_path/"rq.sqlite3"); rec=store.create(request(False)); pid=rec["plan_id"]
    sq=ResearchSubquestionAddRequest(actor_ref="r",question="Does storage moderate the relationship?",purpose="effect-modification")
    store.add_subquestion(pid,sq); again=store.add_subquestion(pid,sq)
    assert len(again["subquestions"])==1
    h=ResearchHypothesisAddRequest(actor_ref="r",label="H1",statement="Storage moderates the relationship between renewable penetration and price volatility.",hypothesis_type="alternative")
    store.add_hypothesis(pid,h); again=store.add_hypothesis(pid,h)
    assert len(again["hypotheses"])==1 and again["hypotheses"][0]["human_review_status"]=="reviewed"
    ev=ResearchEvidenceRequirementRequest(actor_ref="r",requirement="Hourly market price and generation mix data")
    store.add_evidence_requirement(pid,ev); final=store.add_evidence_requirement(pid,ev)
    assert final["evidence_requirements"]==["Hourly market price and generation mix data"]


def test_readiness_separates_structural_review_from_scientific_validity(tmp_path):
    store=ResearchQuestionHypothesisStore(tmp_path/"rq.sqlite3"); rec=store.create(request()); pid=rec["plan_id"]
    ready=store.readiness(pid)
    assert ready["ready_for_review"] is True and ready["ready_for_core_candidate_handoff"] is False
    assert "human-review-approval" in ready["blockers"]
    assert ready["governance"]["readiness_is_structural_not_scientific_validity"] is True
    store.set_review_state(pid,ResearchQuestionReviewStateRequest(actor_ref="researcher",state="approved",note="Reviewed for research planning."))
    approved=store.readiness(pid)
    assert approved["ready_for_core_candidate_handoff"] is True


def test_core_candidates_are_proposals_not_promotions(tmp_path):
    store=ResearchQuestionHypothesisStore(tmp_path/"rq.sqlite3"); rec=store.create(request()); pid=rec["plan_id"]
    before=store.core_candidates(pid)
    assert before["handoff_status"]=="requires-human-approval" and before["promotion_performed"] is False
    assert before["candidates"][0]["object_type"]=="research-question"
    assert {x["object_type"] for x in before["candidates"]}=={"research-question","hypothesis"}
    store.set_review_state(pid,ResearchQuestionReviewStateRequest(actor_ref="r",state="approved"))
    after=store.core_candidates(pid)
    assert after["handoff_status"]=="human-approved-candidate-set"
    assert after["governance"]["platform_core_remains_authority"] is True


def test_snapshot_and_durable_job(tmp_path,monkeypatch):
    store=ResearchQuestionHypothesisStore(tmp_path/"rq.sqlite3"); rec=store.create(request()); pid=rec["plan_id"]
    snap=store.freeze_snapshot(ResearchQuestionSnapshotRequest(actor_ref="r",plan_id=pid))
    assert len(snap["snapshot_hash"])==64 and snap["plan"]["plan_id"]==pid
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_research_question_hypothesis_store",lambda:store)
    claim=JobClaim(job_id="job-1010",job_type="research-question-hypothesis-snapshot",payload={"snapshot":{"actor_ref":"r","plan_id":pid}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-research-question-hypothesis-snapshot/1.0"
    assert events[-1]==("research-question-hypothesis-snapshot-ready",95)
    assert "research-question-hypothesis-snapshot" in JOB_TYPES


def test_v1010_capabilities_and_authenticated_api_surface():
    cap=capabilities(); assert cap["milestone"]=="10.1" and cap["automatic_hypothesis_acceptance"] is False and cap["automatic_core_write"] is False
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/research-question-hypothesis/capabilities","/v1/core/research-question-hypothesis/plans",
        "/v1/core/research-question-hypothesis/plans/{plan_id}","/v1/core/research-question-hypothesis/plans/{plan_id}/subquestions",
        "/v1/core/research-question-hypothesis/plans/{plan_id}/hypotheses","/v1/core/research-question-hypothesis/plans/{plan_id}/evidence-requirements",
        "/v1/core/research-question-hypothesis/plans/{plan_id}/review-state","/v1/core/research-question-hypothesis/plans/{plan_id}/readiness",
        "/v1/core/research-question-hypothesis/plans/{plan_id}/core-candidates","/v1/core/research-question-hypothesis/snapshots/freeze",
    }
    assert not(required-paths),required-paths
    client=TestClient(app)
    assert client.get("/v1/core/research-question-hypothesis/capabilities").status_code==401
    resp=client.get("/v1/core/research-question-hypothesis/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert resp.status_code==200 and resp.json()["platform_core_is_governed_question_hypothesis_authority"] is True


def test_unified_environment_can_bind_question_plan(tmp_path):
    qstore=ResearchQuestionHypothesisStore(tmp_path/"rq.sqlite3"); plan=qstore.create(request())
    envstore=UnifiedScholarlyAIEnvironmentStore(tmp_path/"env.sqlite3",question_store=qstore)
    env=envstore.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="r",title="Program",research_question="Energy volatility",project_ref="core:project:grad-1",question_plan_ids=[plan["plan_id"]]))
    lineage=envstore.lineage(env["environment_id"])
    assert lineage["research_design"]["question_plans"][0]["plan"]["plan_id"]==plan["plan_id"]
    assert envstore.readiness(env["environment_id"])["dimensions"]["question_plan_bound"] is True
    assert "research-question-plan" in capabilities_for_env(envstore)


def capabilities_for_env(store):
    from app.services.unified_scholarly_ai_environment import capabilities
    return capabilities()["component_types"]
