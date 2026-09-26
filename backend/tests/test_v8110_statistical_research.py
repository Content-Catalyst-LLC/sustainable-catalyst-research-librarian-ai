from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient
from app.async_jobs import JobClaim
from app.contracts.statistical_research import StatisticalAnalysisPlanRequest, StatisticalAnalysisPlan, CoreStatisticalValidationPromotionRequest
from app.services.statistical_research import build_plan, capabilities, promote_validation, readiness, add_interpretation
from app.services.document_jobs import execute_job

def req():
    return StatisticalAnalysisPlanRequest(core_project_id="p811",title="Policy effect",research_question="Did policy reduce emissions?",runtime_target="catalyst-analytics-r",analysis_type="difference-in-differences",datasets=[{"local_ref":"panel","core_object_id":"dataset:panel","evidence_refs":["e1"],"variables":["emissions","treated","time"]}],methods=["difference-in-differences"],assumptions=[{"assumption_ref":"parallel-trends","statement":"Parallel trends is required.","status":"not_assessed"}],requested_outputs=["diagnostics","coefficients","intervals"],evidence_refs=["e1"])

def test_plan_is_review_gated_and_nonexecuting():
    out=build_plan(req()); p=out["plan"]
    assert out["release"]=="10.7.0"
    assert p["review_decision"]=="pending"
    assert p["execution_policy"]["execution_allowed_in_librarian"] is False
    assert p["execution_policy"]["runtime_must_return_validated_bundle"] is True
    assert p["provenance"]["statistical_significance_inferred"] is False
    assert capabilities()["automatic_causality_inference"] is False

def test_promotion_requires_explicit_review():
    p=StatisticalAnalysisPlan.model_validate(build_plan(req())["plan"])
    try:
        CoreStatisticalValidationPromotionRequest(plan=p,result_ref="result:1",validation_evidence={})
        assert False
    except Exception: pass

def test_core_readiness_and_promotion_routes():
    class Fake:
        async def statistical_reasoning_readiness(self): return {"contract":"sc.core.statistical-reasoning-object-model.v1","evidence_only":True,"human_review_required":True}
        async def ingest_statistical_validation(self,payload): return {"contract":"sc.core.statistical-reasoning-object-model.v1","reasoning":{"reasoning_ref":payload["reasoning_ref"]}}
        async def record_statistical_interpretation(self,ref,payload): return {"reasoning_ref":ref,**payload}
    r=asyncio.run(readiness(Fake())); assert r["compatible_contract"] is True
    p=StatisticalAnalysisPlan.model_validate({**build_plan(req())["plan"],"review_decision":"approved","reviewer_ref":"researcher:1"})
    evidence={"schema_version":"1.0","bundle_type":"statistical_validation_evidence","contract":"sc.analytics-r.statistical-diagnostics-validation.v1","id":"diag:1","analysis_ref":"analysis:1","diagnostics":[],"assumptions":[],"robustness":[],"comparisons":[],"review_status":"reviewed","summary":{},"provenance":{},"boundary":{}}
    out=asyncio.run(promote_validation(CoreStatisticalValidationPromotionRequest(plan=p,result_ref="result:1",validation_evidence=evidence),Fake()))
    assert out["governance"]["core_infers_statistical_significance"] is False

def test_interpretation_forces_human_authored():
    class Fake:
        async def record_statistical_interpretation(self,ref,payload): return payload
    from app.contracts.statistical_research import CoreInterpretationRequest
    out=asyncio.run(add_interpretation(CoreInterpretationRequest(reasoning_ref="r1",interpretation_ref="i1",statement="Researcher interpretation",author_ref="u1"),Fake()))
    assert out["human_authored"] is True

def test_async_job_and_api_surface():
    claim=JobClaim(job_id="j811",job_type="statistical-analysis-plan",payload=req().model_dump(mode="json"),attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda s,p:events.append((s,p))))
    assert out["plan"]["runtime_target"]=="catalyst-analytics-r" and events[-1]==("runtime-handoff-ready",95)
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    for path in ["/v1/core/statistical-research/capabilities","/v1/core/statistical-research/readiness","/v1/core/statistical-research/plan","/v1/core/statistical-research/promote-validation","/v1/core/statistical-research/coefficients","/v1/core/statistical-research/intervals","/v1/core/statistical-research/interpretations"]: assert path in paths
    body=TestClient(app).get("/v1/core/statistical-research/capabilities",headers={"X-SC-RL-Key":"test-key"}).json()
    assert body["release"]=="10.7.0" and body["librarian_executes_arbitrary_analysis"] is False
