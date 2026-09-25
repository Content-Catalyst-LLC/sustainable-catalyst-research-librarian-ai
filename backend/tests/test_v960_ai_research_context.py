from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient
from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.ai_research_context import AIResearchContextCreateRequest, AIRetrievalRunCreateRequest, RetrievedEvidenceItem, AIContextSnapshotRequest
from app.services.ai_research_context import AIResearchContextStore, capabilities
from app.services.document_jobs import execute_job


def context_req():
    return AIResearchContextCreateRequest(actor_ref="researcher",research_question="How does retrieval configuration affect evidence grounding?",project_ref="project:p1",corpus_ref="corpus:sustainability",corpus_version_ref="corpus-version:12",dataset_ref="dataset:q1",chunking_strategy_ref="chunking:semantic-v2",embedding_model_ref="core:model-version:embed-3",retriever_ref="retriever:hybrid-v1",reranker_ref="reranker:cross-encoder-v2",prompt_ref="core:prompt:research-answer",prompt_version_ref="core:prompt-version:7",model_ref="core:model:llm-a",model_version_ref="core:model-version:llm-a-2026-09",generation_parameters={"temperature":0.2,"max_tokens":1200})


def test_context_identity_is_deterministic_and_external_refs_are_preserved(tmp_path):
    store=AIResearchContextStore(tmp_path/"ctx.sqlite3")
    a=store.create_context(context_req()); b=store.create_context(context_req())
    assert a["context_id"]==b["context_id"] and len(a["record_hash"])==64
    assert a["model_version_ref"]=="core:model-version:llm-a-2026-09"
    assert a["governance"]["librarian_mints_model_identity"] is False


def test_retrieval_run_records_evidence_and_context_hash(tmp_path):
    store=AIResearchContextStore(tmp_path/"ctx.sqlite3"); ctx=store.create_context(context_req())
    run=store.register_run(AIRetrievalRunCreateRequest(actor_ref="researcher",context_id=ctx["context_id"],query_text="retrieval grounding",retrieval_parameters={"top_k":5},evidence=[RetrievedEvidenceItem(evidence_ref="evidence:e1",source_ref="source:s1",chunk_ref="chunk:3",rank=1,score=0.91,score_kind="reranker",content_hash="abc")],inference_run_ref="core:inference:44",output_hash="out-hash"))
    assert run["context_hash"]==ctx["record_hash"] and run["evidence"][0]["evidence_ref"]=="evidence:e1"
    assert run["governance"]["retrieval_scores_are_descriptive"] is True


def test_duplicate_evidence_rejected():
    ctx="ctx-x"
    try:
        AIRetrievalRunCreateRequest(actor_ref="r",context_id=ctx,query_text="q",evidence=[RetrievedEvidenceItem(evidence_ref="e:1",rank=1),RetrievedEvidenceItem(evidence_ref="e:1",rank=2)])
        assert False
    except ValueError: pass


def test_unknown_context_fails_closed(tmp_path):
    store=AIResearchContextStore(tmp_path/"ctx.sqlite3")
    try:
        store.register_run(AIRetrievalRunCreateRequest(actor_ref="r",context_id="missing",query_text="q")); assert False
    except ValueError: pass


def test_lineage_reconstructs_exact_context_and_runs(tmp_path):
    store=AIResearchContextStore(tmp_path/"ctx.sqlite3"); ctx=store.create_context(context_req())
    store.register_run(AIRetrievalRunCreateRequest(actor_ref="r",context_id=ctx["context_id"],query_text="q1",evidence=[RetrievedEvidenceItem(evidence_ref="e:1",rank=1)]))
    store.register_run(AIRetrievalRunCreateRequest(actor_ref="r",context_id=ctx["context_id"],query_text="q2",evidence=[RetrievedEvidenceItem(evidence_ref="e:2",rank=1)]))
    out=store.lineage(ctx["context_id"])
    assert out["run_count"]==2 and out["reproducibility"]["all_runs_content_hashed"] is True


def test_snapshot_and_durable_job(tmp_path,monkeypatch):
    store=AIResearchContextStore(tmp_path/"ctx.sqlite3"); ctx=store.create_context(context_req())
    snap=store.freeze_snapshot(AIContextSnapshotRequest(actor_ref="r",context_id=ctx["context_id"],label="frozen"))
    assert len(snap["snapshot_hash"])==64 and snap["governance"]["snapshot_is_reproducibility_record_not_quality_certification"] is True
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_ai_research_context_store",lambda:store)
    claim=JobClaim(job_id="job-960",job_type="ai-research-context-snapshot",payload={"snapshot":{"actor_ref":"r","context_id":ctx["context_id"]}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-ai-context-snapshot/1.0" and events[-1]==("ai-research-context-snapshot-ready",95) and "ai-research-context-snapshot" in JOB_TYPES


def test_authenticated_v960_api_surface():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={"/v1/core/ai-research-context/capabilities","/v1/core/ai-research-context/contexts","/v1/core/ai-research-context/contexts/{context_id}","/v1/core/ai-research-context/retrieval-runs","/v1/core/ai-research-context/contexts/{context_id}/lineage","/v1/core/ai-research-context/snapshots/freeze"}
    assert not(required-paths),required-paths
    client=TestClient(app); resp=client.get("/v1/core/ai-research-context/capabilities",headers={"X-SC-RL-Key":"test-key"})
    body=resp.json(); assert resp.status_code==200 and body["automatic_model_registration"] is False and body["model_training_execution"] is False
