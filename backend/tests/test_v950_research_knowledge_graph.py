from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient
from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.research_knowledge_graph import (
    KnowledgeGraphNodeRequest, KnowledgeGraphEdgeRequest, KnowledgeGraphProposalRequest,
    KnowledgeGraphProposalDecisionRequest, PublicationGraphMaterializationRequest, KnowledgeGraphSnapshotRequest,
)
from app.services.research_knowledge_graph import ResearchKnowledgeGraphStore
from app.services.document_jobs import execute_job


def node(actor,ref,kind,label=None):
    return KnowledgeGraphNodeRequest(actor_ref=actor,node_ref=ref,kind=kind,label=label or ref)


def test_nodes_edges_are_durable_and_duplicate_edge_is_idempotent(tmp_path):
    store=ResearchKnowledgeGraphStore(tmp_path/"graph.sqlite3")
    store.upsert_node(node("researcher","publication:p1","publication","Publication One"))
    store.upsert_node(node("researcher","study:s1","study","Study One"))
    req=KnowledgeGraphEdgeRequest(actor_ref="researcher",source_ref="publication:p1",target_ref="study:s1",relation="derived-from",source_basis="study-lineage")
    e1=store.add_edge(req); e2=store.add_edge(req)
    assert e1["edge_id"]==e2["edge_id"]
    n=store.neighborhood("publication:p1")
    assert len(n["edges"])==1 and n["edges"][0]["relation"]=="derived-from"


def test_self_edge_and_unknown_nodes_fail_closed(tmp_path):
    store=ResearchKnowledgeGraphStore(tmp_path/"graph.sqlite3")
    store.upsert_node(node("r","claim:c1","claim"))
    try:
        KnowledgeGraphEdgeRequest(actor_ref="r",source_ref="claim:c1",target_ref="claim:c1",relation="supports"); assert False
    except ValueError: pass
    try:
        store.add_edge(KnowledgeGraphEdgeRequest(actor_ref="r",source_ref="claim:c1",target_ref="claim:c2",relation="supports")); assert False
    except ValueError: pass


def test_proposal_is_not_fact_until_human_acceptance(tmp_path):
    store=ResearchKnowledgeGraphStore(tmp_path/"graph.sqlite3")
    store.upsert_node(node("r","finding:f1","finding")); store.upsert_node(node("r","claim:c1","claim"))
    p=store.propose_edge(KnowledgeGraphProposalRequest(actor_ref="model-assistant",source_ref="finding:f1",target_ref="claim:c1",relation="supports",proposal_basis="Candidate semantic relation from reviewed evidence context."))
    assert p["status"]=="pending-review" and store.neighborhood("finding:f1")["edges"]==[]
    p=store.decide_proposal(p["proposal_id"],KnowledgeGraphProposalDecisionRequest(actor_ref="human-reviewer",decision="accept",rationale="Relation is explicitly supported by the cited evidence."))
    assert p["status"]=="accepted" and len(store.neighborhood("finding:f1")["edges"])==1


def test_rejected_proposal_never_enters_graph(tmp_path):
    store=ResearchKnowledgeGraphStore(tmp_path/"graph.sqlite3")
    store.upsert_node(node("r","publication:p1","publication")); store.upsert_node(node("r","publication:p2","publication"))
    p=store.propose_edge(KnowledgeGraphProposalRequest(actor_ref="assistant",source_ref="publication:p1",target_ref="publication:p2",relation="related-to",proposal_basis="Topic overlap"))
    store.decide_proposal(p["proposal_id"],KnowledgeGraphProposalDecisionRequest(actor_ref="reviewer",decision="reject",rationale="Topic overlap alone is insufficient."))
    assert store.neighborhood("publication:p1")["edges"]==[]


def test_publication_materialization_uses_declared_lineage_only(tmp_path,monkeypatch):
    class PubStore:
        def get(self,pid):
            return {"publication_id":pid,"study_id":"study:950","title":"Graph publication","state":"published","canonical_url":"https://example.org/p950","contributors":[{"contributor_ref":"person:a","display_name":"Author A","role":"author","orcid":""}],"references":[{"title":"Source One","source_ref":"source:one","doi":"","evidence_refs":["evidence:e1"]}],"core_evidence_refs":["evidence:e1"],"core_research_object_refs":["claim:c1"],"statistical_reasoning_refs":["stats:s1"],"visual_refs":["visual:v1"]}
    import app.services.research_knowledge_graph as kg
    monkeypatch.setattr(kg,"get_scholarly_publication_store",lambda:PubStore())
    store=ResearchKnowledgeGraphStore(tmp_path/"graph.sqlite3")
    out=store.materialize_publication("publication:p950",PublicationGraphMaterializationRequest(actor_ref="librarian"))
    intel=store.publication_intelligence("publication:p950")
    assert out["edge_count"]>=6 and out["governance"]["no_semantic_inference"] is True
    assert intel["governance"]["no_impact_score"] is True and "cites" in intel["relations"] and "visualizes" in intel["relations"]


def test_snapshot_contains_only_accepted_graph_and_async_job(tmp_path,monkeypatch):
    store=ResearchKnowledgeGraphStore(tmp_path/"graph.sqlite3")
    store.upsert_node(node("r","publication:p1","publication")); store.upsert_node(node("r","source:s1","source")); store.add_edge(KnowledgeGraphEdgeRequest(actor_ref="r",source_ref="publication:p1",target_ref="source:s1",relation="cites",source_basis="citation"))
    store.upsert_node(node("r","claim:c1","claim")); store.propose_edge(KnowledgeGraphProposalRequest(actor_ref="assistant",source_ref="publication:p1",target_ref="claim:c1",relation="supports",proposal_basis="candidate"))
    snap=store.freeze_snapshot(KnowledgeGraphSnapshotRequest(actor_ref="r")); assert len(snap["edges"])==1 and len(snap["snapshot_hash"])==64 and snap["governance"]["proposals_excluded"] is True
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_research_knowledge_graph_store",lambda:store)
    claim=JobClaim(job_id="job-950",job_type="research-knowledge-graph-snapshot",payload={"snapshot":{"actor_ref":"r","label":"snapshot"}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-research-knowledge-graph-snapshot/1.0" and events[-1]==("research-knowledge-graph-snapshot-ready",95) and "research-knowledge-graph-snapshot" in JOB_TYPES


def test_authenticated_v950_api_surface():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/research-knowledge-graph/capabilities",
        "/v1/core/research-knowledge-graph/nodes",
        "/v1/core/research-knowledge-graph/edges",
        "/v1/core/research-knowledge-graph/edge-proposals",
        "/v1/core/research-knowledge-graph/edge-proposals/{proposal_id}/decision",
        "/v1/core/research-knowledge-graph/publications/{publication_id}/materialize",
        "/v1/core/research-knowledge-graph/nodes/{node_ref:path}/neighborhood",
        "/v1/core/research-knowledge-graph/publications/{publication_id}/intelligence",
        "/v1/core/research-knowledge-graph/snapshots/freeze",
    }
    assert not(required-paths),required-paths
    client=TestClient(app); resp=client.get("/v1/core/research-knowledge-graph/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert resp.status_code==200 and resp.json()["automatic_semantic_inference"] is False
