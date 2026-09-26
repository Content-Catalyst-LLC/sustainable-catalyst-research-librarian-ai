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
from app.contracts.visual_research import (
    VISUAL_RESEARCH_SCHEMA,
    CORE_SCENE_CONTRACT,
    CORE_UNIFIED_VISUAL_CONTRACT,
    VisualResearchPlan,
    VisualResearchPlanRequest,
    CoreVisualResearchPromotionRequest,
)
from app.services.document_jobs import execute_job
from app.services.visual_research import build_plan, capabilities, promote_plan, readiness


def _request() -> VisualResearchPlanRequest:
    return VisualResearchPlanRequest(
        core_project_id="project-8120",
        core_session_id="session-8120",
        title="Evidence landscape",
        research_question="How do sources, claims and statistical results relate?",
        visual_kind="evidence-map",
        entities=[
            {"local_ref":"src-a","entity_type":"source","core_object_id":"source:a","label":"Study A","role":"source"},
            {"local_ref":"claim-a","entity_type":"claim","core_object_id":"claim:a","label":"Claim A","role":"claim"},
            {"local_ref":"stat-a","entity_type":"statistical-reasoning","core_object_id":"stat:a","label":"Model result","role":"analysis"},
        ],
        relations=[
            {"relation_ref":"rel-1","source_local_ref":"src-a","target_local_ref":"claim-a","relation":"supports","rationale":"Reviewer-declared evidence relation."},
            {"relation_ref":"rel-2","source_local_ref":"stat-a","target_local_ref":"claim-a","relation":"qualifies","rationale":"Reviewer-declared analytical qualification."},
        ],
        views=[
            {"view_ref":"evidence","kind":"evidence-map","title":"Evidence to claim","entity_refs":["src-a","claim-a"],"relation_refs":["rel-1"],"linked_view_refs":["statistics"]},
            {"view_ref":"statistics","kind":"statistical-result-view","title":"Statistical context","entity_refs":["stat-a","claim-a"],"relation_refs":["rel-2"],"linked_view_refs":["evidence"]},
        ],
        source_content_hashes={"source:a":"abc123"},
    )


def test_visual_plan_is_renderer_neutral_pending_and_explicit_relation_only():
    result = build_plan(_request())
    assert result["schema"] == VISUAL_RESEARCH_SCHEMA
    assert result["release"] == "10.4.0"
    plan = result["plan"]
    assert plan["review_decision"] == "pending"
    assert plan["renderer_policy"]["renderer_neutral"] is True
    assert plan["renderer_policy"]["layout_computed_by_librarian"] is False
    assert all(x["relation_supplied_explicitly"] is True for x in plan["relations"])
    assert plan["provenance"]["visual_relations_inferred"] is False
    assert capabilities()["automatic_visual_truth_promotion"] is False


def test_visual_request_rejects_unknown_relation_or_view_refs():
    with pytest.raises(ValueError, match="must reference supplied entities"):
        VisualResearchPlanRequest(
            core_project_id="p", title="T",
            entities=[{"local_ref":"a","entity_type":"source","label":"A"}],
            relations=[{"relation_ref":"r","source_local_ref":"a","target_local_ref":"missing","relation":"supports"}],
        )


def test_promotion_requires_human_review_and_session_when_binding():
    plan = VisualResearchPlan.model_validate(build_plan(_request())["plan"])
    with pytest.raises(ValueError, match="review_decision='approved'"):
        CoreVisualResearchPromotionRequest(plan=plan)
    raw = plan.model_dump(mode="json")
    raw["review_decision"] = "approved"
    raw["reviewer_ref"] = "researcher:8120"
    raw["core_session_id"] = None
    with pytest.raises(ValueError, match="core_session_id"):
        CoreVisualResearchPromotionRequest(plan=VisualResearchPlan.model_validate(raw))


def test_readiness_and_core_promotion_use_visual_contracts_without_rendering():
    class FakeCore:
        def __init__(self): self.elements=[]; self.relations=[]; self.layers=[]; self.bindings=[]
        async def visual_reasoning_readiness(self): return {"renderer_neutral":True,"automatic_truth_promotion":False,"graph_native":True}
        async def unified_visual_reasoning_readiness(self): return {"contract":CORE_UNIFIED_VISUAL_CONTRACT,"scene_contract":CORE_SCENE_CONTRACT}
        async def create_visual_reasoning_object(self,payload): self.visual=payload; return {"visual_entity_id":"visual-1",**payload}
        async def add_visual_reasoning_layer(self,vid,payload): self.layers.append(payload); return {"layer_id":f"layer-{len(self.layers)}",**payload}
        async def add_visual_reasoning_element(self,vid,payload): self.elements.append(payload); return {"element_id":f"element-{len(self.elements)}",**payload}
        async def add_visual_reasoning_relation(self,vid,payload): self.relations.append(payload); return {"relation_id":f"relation-{len(self.relations)}",**payload}
        async def create_visual_reasoning_snapshot(self,vid,payload): return {"snapshot_id":"snap-1",**payload}
        async def bind_unified_visual(self,payload): self.bindings.append(payload); return {"binding_id":"bind-1",**payload}

    fake = FakeCore()
    ready = asyncio.run(readiness(fake))
    assert ready["renderer_neutral"] is True
    raw = build_plan(_request())["plan"]
    raw["review_decision"] = "approved"
    raw["reviewer_ref"] = "researcher:8120"
    plan = VisualResearchPlan.model_validate(raw)
    out = asyncio.run(promote_plan(CoreVisualResearchPromotionRequest(plan=plan), fake))
    assert out["visual"]["visual_entity_id"] == "visual-1"
    assert len(out["layers"]) == 2 and len(out["elements"]) == 3 and len(out["relations"]) == 2
    assert all(x["metadata"]["relation_supplied_explicitly"] is True for x in fake.relations)
    assert out["session_binding"]["visual_ref"] == "visual-1"
    assert out["governance"]["layout_executed_by_librarian"] is False
    assert out["governance"]["truth_determined"] is False


def test_platform_core_client_targets_existing_visual_surfaces():
    seen=[]
    def handler(request:httpx.Request)->httpx.Response:
        seen.append((request.method,request.url.path))
        if request.method == "GET": return httpx.Response(200,json={"renderer_neutral":True,"contract":CORE_UNIFIED_VISUAL_CONTRACT})
        data=(json.loads(request.content) if request.content else {}).get("data") or {}
        if request.url.path == "/v1/visual-reasoning/objects": return httpx.Response(200,json={"visual_entity_id":"v1",**data})
        return httpx.Response(200,json={"id":"created",**data})
    c=PlatformCoreClient(base_url="http://core.test",write_api_key="secret",retry_limit=0,transport=httpx.MockTransport(handler))
    asyncio.run(c.visual_reasoning_readiness())
    asyncio.run(c.unified_visual_reasoning_readiness())
    asyncio.run(c.create_visual_reasoning_object({"title":"V"}))
    asyncio.run(c.add_visual_reasoning_layer("v1",{"title":"L"}))
    asyncio.run(c.add_visual_reasoning_element("v1",{"label":"E"}))
    asyncio.run(c.add_visual_reasoning_relation("v1",{"relation":"supports"}))
    asyncio.run(c.create_visual_reasoning_snapshot("v1",{}))
    asyncio.run(c.bind_unified_visual({"session_id":"s1","visual_ref":"v1"}))
    assert seen == [
        ("GET","/v1/visual-reasoning/readiness"),
        ("GET","/v1/visual-runtime/unified/readiness"),
        ("POST","/v1/visual-reasoning/objects"),
        ("POST","/v1/visual-reasoning/objects/v1/layers"),
        ("POST","/v1/visual-reasoning/objects/v1/elements"),
        ("POST","/v1/visual-reasoning/objects/v1/relations"),
        ("POST","/v1/visual-reasoning/objects/v1/snapshots"),
        ("POST","/v1/research/unified-runtime/visual-bindings"),
    ]


def test_async_visual_plan_and_api_surface():
    claim=JobClaim(job_id="job-8120",job_type="visual-research-plan",payload=_request().model_dump(mode="json"),attempts=1,max_attempts=3,worker_id="worker")
    events=[]
    result=asyncio.run(execute_job(claim,lambda stage,percent: events.append((stage,percent))))
    assert result["plan"]["visual_kind"] == "evidence-map"
    assert events[-1] == ("human-review-ready",95)

    from app.main import app
    paths={getattr(route,"path","") for route in app.routes}
    for path in [
        "/v1/core/visual-research/capabilities",
        "/v1/core/visual-research/readiness",
        "/v1/core/visual-research/plan",
        "/v1/core/visual-research/promote",
    ]:
        assert path in paths
    response=TestClient(app).get("/v1/core/visual-research/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert response.status_code == 200
    body=response.json()
    assert body["release"] == "10.4.0"
    assert body["renderer_neutral_specs"] is True
    assert body["librarian_renders_visuals"] is False
