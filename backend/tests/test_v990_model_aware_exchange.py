from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.ai_research_context import AIResearchContextCreateRequest
from app.contracts.rag_evaluation import RAGEvaluationCreateRequest
from app.contracts.ai_research_experiment import AIResearchExperimentCreateRequest
from app.contracts.model_aware_exchange import (
    ModelAwareResearchRecordRequest, CrossProductExchangeCreateRequest,
    CrossProductExchangeReceiptRequest, ModelAwareSnapshotRequest,
)
from app.services.ai_research_context import AIResearchContextStore
from app.services.rag_evaluation import RAGEvaluationStore
from app.services.ai_research_experiment import AIResearchExperimentStore
from app.services.model_aware_exchange import ModelAwareResearchStore, capabilities
from app.services.document_jobs import execute_job


def make_store(tmp_path):
    contexts=AIResearchContextStore(tmp_path/"ctx.sqlite3")
    ctx=contexts.create_context(AIResearchContextCreateRequest(
        actor_ref="researcher",research_question="How does model lineage affect a research finding?",
        corpus_ref="corpus:research",chunking_strategy_ref="chunk:v2",embedding_model_ref="core:model-version:embed-a",
        retriever_ref="retriever:hybrid",prompt_ref="core:prompt:research",prompt_version_ref="core:prompt-version:8",
        model_ref="core:model:llm-a",model_version_ref="core:model-version:llm-a-2"))
    evaluations=RAGEvaluationStore(tmp_path/"eval.sqlite3",context_store=contexts)
    ev=evaluations.create_evaluation(RAGEvaluationCreateRequest(actor_ref="researcher",context_id=ctx["context_id"],label="grounding"))
    experiments=AIResearchExperimentStore(tmp_path/"exp.sqlite3",context_store=contexts,evaluation_store=evaluations)
    exp=experiments.create_experiment(AIResearchExperimentCreateRequest(actor_ref="researcher",title="Model comparison",objective="Trace model-aware research lineage.",base_context_id=ctx["context_id"]))
    store=ModelAwareResearchStore(tmp_path/"mair.sqlite3",context_store=contexts,evaluation_store=evaluations,experiment_store=experiments)
    return store,ctx,ev,exp


def record_req(ctx,ev,exp):
    return ModelAwareResearchRecordRequest(
        actor_ref="researcher",title="Model-aware sustainability finding",project_ref="core:project:1",
        context_id=ctx["context_id"],experiment_id=exp["experiment_id"],model_ref="core:model:llm-a",
        model_version_ref="core:model-version:llm-a-2",dataset_ref="core:dataset:sustainability",
        dataset_version_ref="core:dataset-version:14",prompt_ref="core:prompt:research",prompt_version_ref="core:prompt-version:8",
        inference_run_ref="core:inference-run:9921",evaluation_ids=[ev["evaluation_id"]],evidence_refs=["core:evidence:1"],
        claim_refs=["core:claim:2"],finding_refs=["core:finding:3"],statistical_refs=["core:stat:4"],visual_refs=["core:visual:5"])


def test_model_aware_record_is_idempotent_and_external_core_refs(tmp_path):
    store,ctx,ev,exp=make_store(tmp_path)
    a=store.create_record(record_req(ctx,ev,exp)); b=store.create_record(record_req(ctx,ev,exp))
    assert a["record_id"]==b["record_id"] and len(a["record_hash"])==64
    assert a["governance"]["core_ai_objects_remain_external"] is True
    assert a["governance"]["automatic_model_selection"] is False


def test_lineage_groups_ai_research_and_governed_objects(tmp_path):
    store,ctx,ev,exp=make_store(tmp_path); rec=store.create_record(record_req(ctx,ev,exp)); line=store.lineage(rec["record_id"])
    assert line["ai"]["model_version_ref"]=="core:model-version:llm-a-2"
    assert line["ai"]["experiment_id"]==exp["experiment_id"]
    assert line["research_objects"]["finding_refs"]==["core:finding:3"]
    assert line["governance"]["quality_or_truth_not_inferred"] is True


def test_exchange_readiness_is_structural_not_acceptance(tmp_path):
    store,ctx,ev,exp=make_store(tmp_path); rec=store.create_record(record_req(ctx,ev,exp)); ready=store.exchange_readiness(rec["record_id"],"workspace")
    assert ready["ready"] is True and ready["governance"]["automatic_delivery"] is False
    assert ready["governance"]["readiness_is_structural_not_destination_acceptance"] is True


def test_cross_product_packet_creation_is_not_delivery(tmp_path):
    store,ctx,ev,exp=make_store(tmp_path); rec=store.create_record(record_req(ctx,ev,exp))
    packet=store.create_exchange(CrossProductExchangeCreateRequest(actor_ref="r",record_id=rec["record_id"],destination="research-lab",purpose="Analyze evaluation robustness",included_sections=["ai","research_objects"]))
    assert packet["destination"]=="research-lab" and packet["governance"]["packet_creation_is_not_delivery"] is True
    assert packet["receipts"]==[] and "ai" in packet["payload"]


def test_destination_receipt_is_explicit_and_does_not_validate_research(tmp_path):
    store,ctx,ev,exp=make_store(tmp_path); rec=store.create_record(record_req(ctx,ev,exp))
    packet=store.create_exchange(CrossProductExchangeCreateRequest(actor_ref="r",record_id=rec["record_id"],destination="workspace",purpose="Reproduce inference"))
    receipt=store.add_receipt(packet["exchange_id"],CrossProductExchangeReceiptRequest(actor_ref="workspace",status="imported",external_receipt_ref="workspace:receipt:1",destination_object_refs=["workspace:project:7"]))
    assert receipt["status"]=="imported" and receipt["governance"]["receipt_is_not_research_validation"] is True
    assert len(store.get_exchange(packet["exchange_id"])["receipts"])==1


def test_platform_core_exchange_requires_project_ref(tmp_path):
    store,ctx,ev,exp=make_store(tmp_path); req=record_req(ctx,ev,exp); req.project_ref=""; rec=store.create_record(req)
    ready=store.exchange_readiness(rec["record_id"],"platform-core")
    assert ready["ready"] is False and "project-ref-required-for-core-exchange" in ready["blockers"]


def test_snapshot_and_durable_job(tmp_path,monkeypatch):
    store,ctx,ev,exp=make_store(tmp_path); rec=store.create_record(record_req(ctx,ev,exp)); store.create_exchange(CrossProductExchangeCreateRequest(actor_ref="r",record_id=rec["record_id"],destination="knowledge-library",purpose="Publish reusable research lineage"))
    snap=store.freeze_snapshot(ModelAwareSnapshotRequest(actor_ref="r",record_id=rec["record_id"])); assert len(snap["snapshot_hash"])==64 and len(snap["exchanges"])==1
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_model_aware_research_store",lambda:store)
    claim=JobClaim(job_id="job-990",job_type="model-aware-research-snapshot",payload={"snapshot":{"actor_ref":"r","record_id":rec["record_id"]}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-model-aware-research-snapshot/1.0" and events[-1]==("model-aware-research-snapshot-ready",95)
    assert "model-aware-research-snapshot" in JOB_TYPES


def test_capabilities_and_authenticated_v990_api_surface():
    cap=capabilities(); assert cap["automatic_delivery"] is False and cap["automatic_model_selection"] is False and "platform-core" in cap["exchange_destinations"]
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/model-aware-research/capabilities","/v1/core/model-aware-research/records","/v1/core/model-aware-research/records/{record_id}",
        "/v1/core/model-aware-research/records/{record_id}/lineage","/v1/core/model-aware-research/records/{record_id}/exchange-readiness",
        "/v1/core/cross-product-exchange/exchanges","/v1/core/cross-product-exchange/exchanges/{exchange_id}",
        "/v1/core/cross-product-exchange/exchanges/{exchange_id}/receipts","/v1/core/model-aware-research/snapshots/freeze",
    }
    assert not(required-paths),required-paths
    client=TestClient(app); resp=client.get("/v1/core/model-aware-research/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert resp.status_code==200 and resp.json()["core_ai_object_refs_are_external"] is True
