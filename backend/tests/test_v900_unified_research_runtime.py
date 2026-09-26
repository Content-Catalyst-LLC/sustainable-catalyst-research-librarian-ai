from __future__ import annotations

import asyncio
import os

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim
from app.contracts.research_intelligence_extraction import ResearchIntelligenceExtractionRequest
from app.contracts.unified_research_runtime import (
    UNIFIED_RESEARCH_RUNTIME_SCHEMA,
    UnifiedResearchRuntimeExecutionRequest,
    UnifiedResearchRuntimePlan,
    UnifiedResearchRuntimePlanRequest,
    UnifiedResearchStagePayloads,
)
from app.services.document_jobs import execute_job
from app.services.unified_research_runtime import build_runtime_plan, capabilities, execute_safe_runtime, readiness


def _plan_request() -> UnifiedResearchRuntimePlanRequest:
    return UnifiedResearchRuntimePlanRequest(
        core_project_id="core-project-900",
        core_session_id="core-session-900",
        local_project_id="local-project-900",
        title="Unified research run",
        research_question="How does the evidence support or qualify the research question?",
        source_refs=["source:a"],
        core_evidence_refs=["evidence:a"],
        source_content_hashes={"source:a":"abc123"},
    )


def test_unified_plan_has_ordered_stage_graph_and_governance_boundaries():
    out = build_runtime_plan(_plan_request())
    assert out["schema"] == UNIFIED_RESEARCH_RUNTIME_SCHEMA
    assert out["release"] == "11.0.0"
    plan = out["plan"]
    assert plan["stage_order"][0] == "discovery"
    assert plan["stage_order"][-1] == "reproducibility"
    assert len(plan["stages"]) == 12
    assert plan["governance"]["core_write_performed_by_unified_execute"] is False
    assert capabilities()["automatic_truth_promotion"] is False
    assert capabilities()["specialist_computation_retained"] is True
    assert len(plan["reproducibility"]["plan_hash"]) == 64


def test_duplicate_stages_are_rejected():
    with pytest.raises(ValueError, match="must not contain duplicates"):
        UnifiedResearchRuntimePlanRequest(
            core_project_id="p", title="T", research_question="Q",
            requested_stages=["retrieval","retrieval"],
        )


def test_safe_execution_builds_retrieval_and_candidate_plan_without_core_writes():
    plan = UnifiedResearchRuntimePlan.model_validate(build_runtime_plan(_plan_request())["plan"])
    extraction = ResearchIntelligenceExtractionRequest(
        core_project_id="core-project-900",
        research_question=plan.research_question,
        passages=[{
            "local_evidence_id":"ev-local-1",
            "core_evidence_id":"evidence:a",
            "canonical_source_id":"source:a",
            "text":"The observed result was associated with a measurable reduction in energy demand across the study period.",
        }],
        max_candidates=5,
    )
    req = UnifiedResearchRuntimeExecutionRequest(
        plan=plan,
        payloads=UnifiedResearchStagePayloads(research_intelligence=extraction),
        execute_stages=["retrieval","research-intelligence"],
    )
    out = execute_safe_runtime(req)
    assert out["release"] == "11.0.0"
    assert out["stage_results"]["retrieval"]["status"] == "completed"
    assert out["stage_results"]["research-intelligence"]["status"] == "completed"
    candidates = out["stage_results"]["research-intelligence"]["result"]["candidates"]
    assert candidates and all(x["review_decision"] == "pending" for x in candidates)
    assert out["run_manifest"]["core_writes_performed"] is False
    assert len(out["run_manifest"]["run_fingerprint"]) == 64


def test_stage_payload_project_identity_must_match_plan():
    plan = UnifiedResearchRuntimePlan.model_validate(build_runtime_plan(_plan_request())["plan"])
    wrong = ResearchIntelligenceExtractionRequest(
        core_project_id="wrong-project",
        passages=[{"local_evidence_id":"e","text":"A sufficiently long evidence sentence exists for deterministic extraction here."}],
    )
    with pytest.raises(ValueError, match="must target plan.core_project_id"):
        UnifiedResearchRuntimeExecutionRequest(
            plan=plan,
            payloads=UnifiedResearchStagePayloads(research_intelligence=wrong),
            execute_stages=["research-intelligence"],
        )


def test_readiness_aggregates_required_core_capabilities():
    required = [
        "research_objects", "unified_research_projects", "research_lineage", "research_arguments",
        "research_conclusions", "reproducible_research", "statistical_reasoning", "visual_reasoning_objects",
        "unified_visual_reasoning", "cross_product_exchange", "project_state", "finding_claim_evidence_intelligence",
    ]
    class FakeCore:
        async def health(self): return {"version":"3.3.0","ok":True}
        async def capability_readiness(self): return {name:{"ok":True,"data":{"contract":"ok"}} for name in required}
    out = asyncio.run(readiness(FakeCore()))
    assert out["ready"] is True
    assert out["core_compatible"] is True
    assert out["missing_or_failed_core_capabilities"] == []


def test_async_runtime_and_authenticated_api_surface():
    plan = UnifiedResearchRuntimePlan.model_validate(build_runtime_plan(_plan_request())["plan"])
    payload = UnifiedResearchRuntimeExecutionRequest(plan=plan, execute_stages=["retrieval"]).model_dump(mode="json")
    claim = JobClaim(job_id="job-900", job_type="unified-research-runtime", payload=payload, attempts=1, max_attempts=3, worker_id="worker")
    events=[]
    out=asyncio.run(execute_job(claim, lambda stage,percent: events.append((stage,percent))))
    assert out["run_manifest"]["core_writes_performed"] is False
    assert events[-1] == ("reproducible-run-manifest-ready",95)

    from app.main import app
    paths={getattr(route,"path","") for route in app.routes}
    for path in [
        "/v1/core/unified-research/capabilities",
        "/v1/core/unified-research/readiness",
        "/v1/core/unified-research/plan",
        "/v1/core/unified-research/execute",
    ]:
        assert path in paths
    response=TestClient(app).get("/v1/core/unified-research/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert response.status_code == 200
    body=response.json()
    assert body["release"] == "11.0.0"
    assert body["durable_async_runtime"] is True
    assert body["automatic_core_writes"] is False
