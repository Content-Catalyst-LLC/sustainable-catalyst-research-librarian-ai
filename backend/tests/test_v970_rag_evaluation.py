from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient
from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.ai_research_context import AIResearchContextCreateRequest, AIRetrievalRunCreateRequest, RetrievedEvidenceItem
from app.contracts.rag_evaluation import (
    RAGEvaluationCreateRequest, RAGEvaluationCaseRequest, RAGClaimAssessmentRequest,
    RAGCitationAssessmentRequest, RAGEvaluationComparisonRequest, RAGEvaluationSnapshotRequest,
)
from app.services.ai_research_context import AIResearchContextStore
from app.services.rag_evaluation import RAGEvaluationStore, capabilities
from app.services.document_jobs import execute_job


def build_context_store(tmp_path):
    c=AIResearchContextStore(tmp_path/"ctx.sqlite3")
    ctx=c.create_context(AIResearchContextCreateRequest(
        actor_ref="researcher", research_question="Does retrieval improve evidence grounding?",
        corpus_ref="corpus:sustainability", corpus_version_ref="corpus:v12",
        chunking_strategy_ref="chunking:semantic-v2", embedding_model_ref="core:model-version:embed-3",
        retriever_ref="retriever:hybrid-v1", reranker_ref="reranker:cross-v2",
        prompt_ref="core:prompt:answer", prompt_version_ref="core:prompt-version:7",
        model_ref="core:model:llm-a", model_version_ref="core:model-version:llm-a-2026-09",
    ))
    run=c.register_run(AIRetrievalRunCreateRequest(
        actor_ref="researcher", context_id=ctx["context_id"], query_text="q",
        evidence=[RetrievedEvidenceItem(evidence_ref="e:1",rank=1),RetrievedEvidenceItem(evidence_ref="e:2",rank=2),RetrievedEvidenceItem(evidence_ref="e:3",rank=3)],
        inference_run_ref="core:inference:44",
    ))
    return c,ctx,run


def test_evaluation_identity_links_v960_context(tmp_path):
    contexts,ctx,_=build_context_store(tmp_path); store=RAGEvaluationStore(tmp_path/"eval.sqlite3",contexts)
    req=RAGEvaluationCreateRequest(actor_ref="r",context_id=ctx["context_id"],label="Benchmark A",evaluation_dataset_ref="dataset:rag-eval:v1")
    a=store.create_evaluation(req); b=store.create_evaluation(req)
    assert a["evaluation_id"]==b["evaluation_id"] and a["context_hash"]==ctx["record_hash"]
    assert a["governance"]["automatic_model_ranking"] is False


def test_case_computes_retrieval_metrics_from_declared_relevance(tmp_path):
    contexts,ctx,run=build_context_store(tmp_path); store=RAGEvaluationStore(tmp_path/"eval.sqlite3",contexts)
    ev=store.create_evaluation(RAGEvaluationCreateRequest(actor_ref="r",context_id=ctx["context_id"],label="Eval"))
    case=store.add_case(ev["evaluation_id"],RAGEvaluationCaseRequest(actor_ref="r",query_text="q",retrieval_run_id=run["run_id"],expected_evidence_refs=["e:1","e:3","e:9"],retrieved_evidence_refs=["e:2","e:1","e:3"],k=3,latency_ms=120,cost_amount=0.02,cost_currency="USD"))
    m=case["retrieval_metrics"]
    assert round(m["precision_at_k"],6)==round(2/3,6) and round(m["recall_at_k"],6)==round(2/3,6)
    assert m["reciprocal_rank"]==0.5 and m["ndcg_at_k"] is not None


def test_case_rejects_retrieval_run_from_outside_context(tmp_path):
    contexts,ctx,_=build_context_store(tmp_path); store=RAGEvaluationStore(tmp_path/"eval.sqlite3",contexts)
    ev=store.create_evaluation(RAGEvaluationCreateRequest(actor_ref="r",context_id=ctx["context_id"],label="Eval"))
    try:
        store.add_case(ev["evaluation_id"],RAGEvaluationCaseRequest(actor_ref="r",query_text="q",retrieval_run_id="airun-missing")); assert False
    except ValueError: pass


def test_grounding_and_citation_reviews_are_explicit_and_descriptive(tmp_path):
    contexts,ctx,_=build_context_store(tmp_path); store=RAGEvaluationStore(tmp_path/"eval.sqlite3",contexts)
    ev=store.create_evaluation(RAGEvaluationCreateRequest(actor_ref="r",context_id=ctx["context_id"],label="Eval"))
    case=store.add_case(ev["evaluation_id"],RAGEvaluationCaseRequest(actor_ref="r",query_text="q",expected_evidence_refs=["e:1"],retrieved_evidence_refs=["e:1"],k=1))
    claim=store.add_claim_assessment(ev["evaluation_id"],RAGClaimAssessmentRequest(actor_ref="reviewer",case_id=case["case_id"],claim_ref="claim:1",support_status="unsupported",rationale="No supporting passage."))
    cite=store.add_citation_assessment(ev["evaluation_id"],RAGCitationAssessmentRequest(actor_ref="reviewer",case_id=case["case_id"],citation_ref="citation:1",evidence_ref="e:1",status="correct"))
    summary=store.summary(ev["evaluation_id"])
    assert claim["governance"]["not_truth_certification"] is True and cite["governance"]["not_source_quality_score"] is True
    assert summary["grounding"]["unsupported_claim_rate"]==1.0 and summary["citations"]["correct_rate"]==1.0
    assert summary["governance"]["no_composite_quality_score"] is True


def test_comparison_never_selects_winner(tmp_path):
    contexts,ctx,_=build_context_store(tmp_path); store=RAGEvaluationStore(tmp_path/"eval.sqlite3",contexts)
    a=store.create_evaluation(RAGEvaluationCreateRequest(actor_ref="r",context_id=ctx["context_id"],label="A"))
    b=store.create_evaluation(RAGEvaluationCreateRequest(actor_ref="r",context_id=ctx["context_id"],label="B",benchmark_ref="b:2"))
    out=store.comparison(RAGEvaluationComparisonRequest(actor_ref="r",evaluation_ids=[a["evaluation_id"],b["evaluation_id"]]))
    assert len(out["evaluations"])==2 and out["governance"]["winner_selected"] is False and out["governance"]["ranking_generated"] is False


def test_snapshot_and_durable_job(tmp_path,monkeypatch):
    contexts,ctx,_=build_context_store(tmp_path); store=RAGEvaluationStore(tmp_path/"eval.sqlite3",contexts)
    ev=store.create_evaluation(RAGEvaluationCreateRequest(actor_ref="r",context_id=ctx["context_id"],label="Eval"))
    snap=store.freeze_snapshot(RAGEvaluationSnapshotRequest(actor_ref="r",evaluation_id=ev["evaluation_id"]))
    assert len(snap["snapshot_hash"])==64 and snap["governance"]["snapshot_is_evaluation_record_not_model_certification"] is True
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_rag_evaluation_store",lambda:store)
    claim=JobClaim(job_id="job-970",job_type="rag-evaluation-snapshot",payload={"snapshot":{"actor_ref":"r","evaluation_id":ev["evaluation_id"]}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-rag-evaluation-snapshot/1.0" and events[-1]==("rag-evaluation-snapshot-ready",95) and "rag-evaluation-snapshot" in JOB_TYPES


def test_capabilities_refuse_automatic_verdicts():
    c=capabilities()
    assert c["automatic_truth_judgment"] is False and c["automatic_model_ranking"] is False and c["automatic_quality_grade"] is False
    assert "unsupported-claim-rate" in c["evaluation_dimensions"]


def test_authenticated_v970_api_surface():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/rag-evaluation/capabilities","/v1/core/rag-evaluation/evaluations","/v1/core/rag-evaluation/evaluations/{evaluation_id}",
        "/v1/core/rag-evaluation/evaluations/{evaluation_id}/cases","/v1/core/rag-evaluation/evaluations/{evaluation_id}/claim-assessments",
        "/v1/core/rag-evaluation/evaluations/{evaluation_id}/citation-assessments","/v1/core/rag-evaluation/evaluations/{evaluation_id}/summary",
        "/v1/core/rag-evaluation/comparisons","/v1/core/rag-evaluation/snapshots/freeze",
    }
    assert not(required-paths),required-paths
    client=TestClient(app); resp=client.get("/v1/core/rag-evaluation/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert resp.status_code==200 and resp.json()["metrics_are_evidence_not_verdicts"] is True
