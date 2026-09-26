from __future__ import annotations

import asyncio
import json
import os

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

import httpx
import pytest
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim
from app.clients.platform_core import PlatformCoreClient
from app.contracts.argument_synthesis import (
    ARGUMENT_SYNTHESIS_SCHEMA,
    CORE_ARGUMENT_CONTRACT,
    ArgumentSynthesisPlan,
    ArgumentSynthesisPlanRequest,
    CoreArgumentSynthesisPromotionRequest,
)
from app.services.argument_synthesis import build_plan, capabilities, contradiction_candidates, promote_plan
from app.services.document_jobs import execute_job


def _request() -> ArgumentSynthesisPlanRequest:
    return ArgumentSynthesisPlanRequest(
        core_project_id="project-8100",
        title="Intervention evidence",
        thesis_text="The intervention may reduce emissions under some baseline conditions.",
        argument_type="analytical",
        nodes=[
            {"local_ref":"claim-a","core_object_type":"claim","core_object_id":"core-claim-a","role":"premise"},
            {"local_ref":"finding-b","core_object_type":"finding","core_object_id":"core-finding-b","role":"support"},
            {"local_ref":"claim-c","core_object_type":"claim","core_object_id":"core-claim-c","role":"objection"},
        ],
        relations=[
            {"source_local_ref":"finding-b","target_local_ref":"claim-a","relation":"supports","rationale":"Reviewer-declared support."},
            {"source_local_ref":"claim-c","target_local_ref":"claim-a","relation":"contradicts","rationale":"Reviewer-declared contradiction."},
        ],
        tensions=[{"title":"Baseline dependence","description":"Sources disagree about whether the effect persists across baseline conditions.","source_refs":["core-claim-a","core-claim-c"]}],
        synthesis={"title":"Reviewer synthesis","synthesis_text":"Evidence is mixed and appears conditional on baseline context.","component_local_refs":["claim-a","finding-b","claim-c"]},
    )


def test_plan_is_pending_and_declared_relations_are_not_inferred() -> None:
    result = build_plan(_request())
    assert result["schema"] == ARGUMENT_SYNTHESIS_SCHEMA
    plan = result["plan"]
    assert plan["review_decision"] == "pending"
    assert [x["relation"] for x in plan["relations"]] == ["supports", "contradicts"]
    assert all(x["relation_supplied_explicitly"] is True for x in plan["relations"])
    assert plan["provenance"]["argument_generated_by_model"] is False
    assert plan["provenance"]["relations_inferred_by_model"] is False
    assert result["governance"]["automatic_contradiction_resolution"] is False


def test_relation_refs_must_exist() -> None:
    with pytest.raises(ValueError, match="must reference supplied nodes"):
        ArgumentSynthesisPlanRequest(
            core_project_id="p",
            title="T",
            nodes=[{"local_ref":"a","core_object_type":"claim","core_object_id":"ca"}],
            relations=[{"source_local_ref":"a","target_local_ref":"missing","relation":"supports"}],
        )


def test_core_promotion_requires_explicit_human_approval() -> None:
    plan = ArgumentSynthesisPlan.model_validate(build_plan(_request())["plan"])
    with pytest.raises(ValueError, match="review_decision='approved'"):
        CoreArgumentSynthesisPromotionRequest(plan=plan)


def test_approved_plan_creates_core_argument_graph_tension_and_researcher_synthesis() -> None:
    raw = build_plan(_request())["plan"]
    raw["review_decision"] = "approved"
    raw["reviewer_ref"] = "researcher:8100"
    plan = ArgumentSynthesisPlan.model_validate(raw)

    class FakeCore:
        def __init__(self): self.nodes=[]; self.edges=[]; self.tensions=[]; self.components=[]
        async def create_argument(self, project_id, payload): self.argument=(project_id,payload); return {"id":"arg-1",**payload}
        async def add_argument_node(self, argument_id, payload):
            out={"id":f"node-{len(self.nodes)+1}",**payload}; self.nodes.append(out); return out
        async def add_argument_edge(self, argument_id, payload): self.edges.append(payload); return {"id":f"edge-{len(self.edges)}",**payload}
        async def add_argument_tension(self, argument_id, payload): self.tensions.append(payload); return {"id":f"tension-{len(self.tensions)}",**payload}
        async def create_argument_synthesis(self, argument_id, payload): self.synthesis=payload; return {"id":"syn-1",**payload}
        async def add_argument_synthesis_component(self, synthesis_id, payload): self.components.append(payload); return {"id":f"component-{len(self.components)}",**payload}

    fake=FakeCore()
    result=asyncio.run(promote_plan(CoreArgumentSynthesisPromotionRequest(plan=plan),fake))
    assert result["argument"]["status"] == "draft"
    assert len(result["nodes"]) == 3
    assert [x["relation"] for x in fake.edges] == ["supports", "contradicts"]
    assert all(x["metadata"]["relation_supplied_explicitly"] is True for x in fake.edges)
    assert result["tensions"][0]["status"] == "open"
    assert result["synthesis"]["synthesis_text"].startswith("Evidence is mixed")
    assert result["governance"]["contradictions_resolved"] is False
    assert result["governance"]["conclusion_generated"] is False
    assert result["governance"]["truth_determined"] is False


def test_core_client_targets_argument_contract_and_contradiction_candidates() -> None:
    seen=[]
    def handler(request:httpx.Request)->httpx.Response:
        seen.append((request.method,request.url.path))
        if request.method == "GET": return httpx.Response(200,json={"contract":CORE_ARGUMENT_CONTRACT,"items":[]})
        data=(json.loads(request.content) if request.content else {}).get("data") or {}
        return httpx.Response(200,json={"id":"core-created",**data})
    c=PlatformCoreClient(base_url="http://core.test",write_api_key="secret",retry_limit=0,transport=httpx.MockTransport(handler))
    asyncio.run(c.argument_readiness())
    asyncio.run(c.research_contradiction_candidates("p1"))
    asyncio.run(c.create_argument("p1",{"argument_key":"a","title":"A"}))
    asyncio.run(c.add_argument_node("a1",{"node_key":"n","node_type":"claim","source_ref":"c"}))
    asyncio.run(c.add_argument_edge("a1",{"edge_key":"e","source_node_id":"n1","target_node_id":"n2","relation":"supports"}))
    asyncio.run(c.add_argument_tension("a1",{"tension_key":"t","title":"T","description":"D"}))
    asyncio.run(c.create_argument_synthesis("a1",{"synthesis_key":"s","title":"S","synthesis_text":"Text"}))
    assert seen == [
        ("GET","/v1/research/arguments/readiness"),
        ("GET","/v1/research/intelligence/projects/p1/contradiction-candidates"),
        ("POST","/v1/research/arguments/projects/p1"),
        ("POST","/v1/research/arguments/a1/nodes"),
        ("POST","/v1/research/arguments/a1/edges"),
        ("POST","/v1/research/arguments/a1/tensions"),
        ("POST","/v1/research/arguments/a1/syntheses"),
    ]


def test_contradiction_inspection_async_executor_and_api_routes() -> None:
    class FakeCore:
        async def research_contradiction_candidates(self, project_id): return {"contract":"sc.research.finding-claim-evidence.v1","project_id":project_id,"items":[{"candidate":"x"}]}
    inspected=asyncio.run(contradiction_candidates("p8100",FakeCore()))
    assert inspected["core"]["items"] == [{"candidate":"x"}]
    assert inspected["review_required_before_tension_registration"] is True

    claim=JobClaim(job_id="job-8100",job_type="argument-synthesis-plan",payload=_request().model_dump(mode="json"),attempts=1,max_attempts=3,worker_id="worker")
    events=[]
    result=asyncio.run(execute_job(claim,lambda stage,percent: events.append((stage,percent))))
    assert result["plan"]["review_decision"] == "pending"
    assert events[-1] == ("review-queue-ready",95)

    from app.main import app
    paths={getattr(route,"path","") for route in app.routes}
    assert "/v1/core/argument-synthesis/capabilities" in paths
    assert "/v1/core/argument-synthesis/plan" in paths
    assert "/v1/core/argument-synthesis/promote" in paths
    assert "/v1/core/argument-synthesis/contradictions/{core_project_id:path}" in paths
    response=TestClient(app).get("/v1/core/argument-synthesis/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert response.status_code == 200
    body=response.json()
    assert body["release"] == "10.3.0"
    assert body["human_review_required_for_core_promotion"] is True
    assert body["automatic_argument_ranking"] is False
    assert body["automatic_truth_determination"] is False
