from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim
from app.clients.platform_core import PlatformCoreClient
from app.contracts.research_intelligence_extraction import (
    CORE_RESEARCH_INTELLIGENCE_CONTRACT,
    RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA,
    CoreResearchCandidatePromotionRequest,
    EvidencePassageInput,
    ResearchIntelligenceCandidate,
    ResearchIntelligenceExtractionRequest,
)
from app.services.document_jobs import execute_job
from app.store import KnowledgeStore
import app.services.research_intelligence_extraction as extraction


def _store(tmp_path: Path) -> KnowledgeStore:
    local = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    local.save_platform_core_binding({
        "schema":"sc-research-librarian-core-binding/1.0",
        "binding_key":"evidence-record:passage-1",
        "local_kind":"evidence-record",
        "local_id":"passage-1",
        "core_kind":"evidence-record",
        "core_id":"sc:evidence:passage-1",
        "sync_state":"synced",
        "contract_version":"sc-research-librarian-core-evidence-bridge/1.0",
        "payload_hash":"a"*64,
        "idempotency_key":"passage-1",
        "created_utc":"2026-09-23T14:00:00+00:00",
        "updated_utc":"2026-09-23T14:00:00+00:00",
    })
    return local


def test_deterministic_extraction_returns_pending_candidates_and_resolves_core_evidence(monkeypatch, tmp_path: Path) -> None:
    local=_store(tmp_path)
    monkeypatch.setattr(extraction,"store",local)
    request=ResearchIntelligenceExtractionRequest(
        core_project_id="core-project-890",
        research_question="What changed?",
        passages=[EvidencePassageInput(
            local_evidence_id="passage-1",
            text="We found that emissions decreased by 18 percent after the intervention. The results suggest the effect may depend on baseline conditions.",
            canonical_source_id="source-890",
            passage_id="p-1",
            page_start=7,
            page_end=7,
        )],
    )
    result=extraction.extract_candidates(request)
    assert result["schema"]==RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA
    assert result["candidate_count"]==2
    assert [c["candidate_type"] for c in result["candidates"]]==["finding","claim"]
    assert all(c["review_decision"]=="pending" for c in result["candidates"])
    assert result["candidates"][0]["evidence"][0]["core_evidence_id"]=="sc:evidence:passage-1"
    assert result["candidates"][0]["evidence"][0]["relation"]=="contextualizes"
    assert result["candidates"][0]["evidence"][0]["relation_supplied_explicitly"] is False
    assert "may" in result["candidates"][1]["uncertainty_cues"]
    assert result["governance"]["automatic_truth_determination"] is False


def test_explicit_relation_hint_is_preserved_not_inferred(monkeypatch, tmp_path: Path) -> None:
    local=_store(tmp_path); monkeypatch.setattr(extraction,"store",local)
    result=extraction.extract_candidates(ResearchIntelligenceExtractionRequest(
        core_project_id="core-project-890",
        passages=[EvidencePassageInput(local_evidence_id="passage-1",text="Observed concentrations increased substantially after the controlled exposure.",relation_hint="supports")],
    ))
    ev=result["candidates"][0]["evidence"][0]
    assert ev["relation"]=="supports" and ev["relation_supplied_explicitly"] is True


def test_core_promotion_requires_explicit_approved_review() -> None:
    candidate=ResearchIntelligenceCandidate(candidate_id="c1",candidate_type="claim",text="A candidate proposition.",claim_type="descriptive",evidence=[{"core_evidence_id":"e1"}])
    with pytest.raises(ValueError,match="review_decision='approved'"):
        CoreResearchCandidatePromotionRequest(core_project_id="p1",candidate=candidate)


def test_approved_candidate_promotes_as_proposed_and_links_governed_evidence(monkeypatch, tmp_path: Path) -> None:
    local=_store(tmp_path); monkeypatch.setattr(extraction,"store",local)
    candidate=ResearchIntelligenceCandidate(
        candidate_id="claim-890",
        candidate_type="claim",
        text="The intervention may reduce emissions.",
        claim_type="interpretive",
        classification_basis=["claim-cue:may"],
        uncertainty_cues=["may"],
        evidence=[{"local_evidence_id":"passage-1","core_evidence_id":"sc:evidence:passage-1","relation":"contextualizes"}],
        review_decision="approved",
        reviewer_ref="researcher:1",
    )
    class FakeCore:
        def __init__(self): self.claim=None; self.links=[]
        async def create_research_claim(self, project_id,payload):
            self.claim=(project_id,payload); return {"id":"core-claim-890",**payload}
        async def create_research_finding(self, project_id,payload):
            raise AssertionError("not expected")
        async def create_research_evidence_link(self, project_id,payload):
            self.links.append((project_id,payload)); return {"id":f"link-{len(self.links)}",**payload}
    fake=FakeCore()
    result=asyncio.run(extraction.promote_candidate(CoreResearchCandidatePromotionRequest(core_project_id="core-project-890",candidate=candidate),fake))
    assert result["core_object_type"]=="claim"
    assert fake.claim[1]["status"]=="proposed"
    assert fake.claim[1]["polarity"]=="not_applicable"
    assert fake.claim[1]["provenance"]["automated_truth_judgment"] is False
    assert fake.links[0][1]["relation"]=="contextualizes"
    assert result["governance"]["truth_determined"] is False


def test_platform_core_client_targets_v277_research_intelligence_contract() -> None:
    seen=[]
    def handler(request:httpx.Request)->httpx.Response:
        seen.append(request.url.path)
        if request.url.path.endswith('/readiness'): return httpx.Response(200,json={"contract":CORE_RESEARCH_INTELLIGENCE_CONTRACT})
        body=__import__('json').loads(request.content) if request.content else {}
        data=body.get('data') or {}
        return httpx.Response(200,json={"id":"core-object",**data})
    client=PlatformCoreClient(base_url="http://core.test",write_api_key="secret",retry_limit=0,transport=httpx.MockTransport(handler))
    asyncio.run(client.research_intelligence_readiness())
    asyncio.run(client.create_research_finding("p1",{"finding_key":"f1","title":"T","statement":"S"}))
    asyncio.run(client.create_research_claim("p1",{"claim_key":"c1","claim_text":"C"}))
    asyncio.run(client.create_research_evidence_link("p1",{"evidence_link_key":"e1","evidence_ref":"evidence:1","target_type":"claim","target_id":"c","relation":"contextualizes"}))
    assert seen==[
        "/v1/research/intelligence/readiness",
        "/v1/research/intelligence/projects/p1/findings",
        "/v1/research/intelligence/projects/p1/claims",
        "/v1/research/intelligence/projects/p1/evidence-links",
    ]


def test_v890_async_executor_and_api_routes(monkeypatch, tmp_path: Path) -> None:
    local=_store(tmp_path); monkeypatch.setattr(extraction,"store",local)
    claim=JobClaim(job_id="job-890",job_type="research-intelligence-extraction",payload={
        "core_project_id":"core-project-890",
        "passages":[{"local_evidence_id":"passage-1","text":"Observed emissions decreased after the intervention."}],
    },attempts=1,max_attempts=3,worker_id="worker-890")
    events=[]
    result=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert result["candidate_count"]==1
    assert events[-1]==("review-queue-ready",95)

    from app.main import app
    paths={getattr(route,"path","") for route in app.routes}
    assert "/v1/core/research-intelligence/capabilities" in paths
    assert "/v1/core/research-intelligence/extract" in paths
    assert "/v1/core/research-intelligence/promote" in paths
    response=TestClient(app).get("/v1/core/research-intelligence/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert response.status_code==200
    body=response.json()
    assert body["release"]=="10.0.0"
    assert body["human_review_required_for_core_promotion"] is True
    assert body["automatic_truth_determination"] is False
