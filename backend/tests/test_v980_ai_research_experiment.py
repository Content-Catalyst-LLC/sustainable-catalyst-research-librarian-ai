from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.ai_research_context import AIResearchContextCreateRequest
from app.contracts.rag_evaluation import RAGEvaluationCreateRequest
from app.contracts.ai_research_experiment import (
    AIResearchExperimentCreateRequest, AIResearchTrialCreateRequest,
    AIExperimentExecutionHandoffRequest, AIExperimentRunReceiptRequest,
    AIExperimentEvaluationBindingRequest, AIExperimentStateRequest, AIExperimentSnapshotRequest,
)
from app.services.ai_research_context import AIResearchContextStore
from app.services.rag_evaluation import RAGEvaluationStore
from app.services.ai_research_experiment import AIResearchExperimentStore, capabilities
from app.services.document_jobs import execute_job


def make_stores(tmp_path):
    contexts=AIResearchContextStore(tmp_path/"ctx.sqlite3")
    ctx=contexts.create_context(AIResearchContextCreateRequest(
        actor_ref="researcher", research_question="Which retrieval configuration grounds claims best?",
        corpus_ref="corpus:research", chunking_strategy_ref="chunking:v2", embedding_model_ref="core:model-version:embed-a",
        retriever_ref="retriever:hybrid", prompt_ref="core:prompt:answer", prompt_version_ref="core:prompt-version:4",
        model_ref="core:model:llm-a", model_version_ref="core:model-version:llm-a-1"
    ))
    evaluations=RAGEvaluationStore(tmp_path/"eval.sqlite3", context_store=contexts)
    ev=evaluations.create_evaluation(RAGEvaluationCreateRequest(actor_ref="researcher",context_id=ctx["context_id"],label="baseline"))
    experiments=AIResearchExperimentStore(tmp_path/"exp.sqlite3",context_store=contexts,evaluation_store=evaluations)
    return contexts, evaluations, experiments, ctx, ev


def exp_req(ctx_id):
    return AIResearchExperimentCreateRequest(actor_ref="researcher",title="Embedding comparison",objective="Compare declared retrieval configurations reproducibly.",research_question="Which retrieval configuration has stronger evidence grounding?",base_context_id=ctx_id,evaluation_dataset_ref="dataset:eval-1",evaluation_dataset_version_ref="dataset-version:3",controlled_variables={"top_k":10},declared_outcomes=["precision@10","unsupported-claim-rate"])


def test_experiment_identity_and_external_ai_boundaries(tmp_path):
    _,_,store,ctx,_=make_stores(tmp_path)
    a=store.create_experiment(exp_req(ctx["context_id"])); b=store.create_experiment(exp_req(ctx["context_id"]))
    assert a["experiment_id"]==b["experiment_id"] and len(a["record_hash"])==64
    assert a["governance"]["core_ai_objects_remain_external"] is True
    assert a["governance"]["librarian_executes_training"] is False


def test_trial_records_parameterized_configuration_and_context(tmp_path):
    _,_,store,ctx,_=make_stores(tmp_path); exp=store.create_experiment(exp_req(ctx["context_id"]))
    trial=store.add_trial(exp["experiment_id"],AIResearchTrialCreateRequest(actor_ref="r",label="embedding-a",context_id=ctx["context_id"],model_version_ref="core:model-version:llm-a-1",embedding_model_ref="core:model-version:embed-a",retriever_ref="retriever:hybrid",parameters={"top_k":10},seed=427))
    assert trial["context_id"]==ctx["context_id"] and trial["seed"]==427 and len(trial["record_hash"])==64


def test_handoff_is_request_not_execution(tmp_path):
    _,_,store,ctx,_=make_stores(tmp_path); exp=store.create_experiment(exp_req(ctx["context_id"])); trial=store.add_trial(exp["experiment_id"],AIResearchTrialCreateRequest(actor_ref="r",label="a",context_id=ctx["context_id"]))
    handoff=store.create_handoff(exp["experiment_id"],AIExperimentExecutionHandoffRequest(actor_ref="r",trial_id=trial["trial_id"],target_runtime="workspace",target_ref="workspace:project-7",execution_contract_ref="core:runtime-contract:python",requested_artifacts=["model-output","run-log"]))
    assert handoff["governance"]["handoff_is_request_not_execution_receipt"] is True and handoff["governance"]["automatic_execution"] is False


def test_run_receipt_preserves_external_status_without_inference(tmp_path):
    _,_,store,ctx,_=make_stores(tmp_path); exp=store.create_experiment(exp_req(ctx["context_id"])); trial=store.add_trial(exp["experiment_id"],AIResearchTrialCreateRequest(actor_ref="r",label="a",context_id=ctx["context_id"]))
    handoff=store.create_handoff(exp["experiment_id"],AIExperimentExecutionHandoffRequest(actor_ref="r",trial_id=trial["trial_id"]))
    receipt=store.add_receipt(exp["experiment_id"],AIExperimentRunReceiptRequest(actor_ref="workspace",trial_id=trial["trial_id"],handoff_id=handoff["handoff_id"],status="failed",external_run_ref="workspace:run-42",error="out of memory"))
    assert receipt["status"]=="failed" and receipt["governance"]["success_not_inferred"] is True


def test_evaluation_binding_requires_registered_v97_evaluation(tmp_path):
    _,_,store,ctx,ev=make_stores(tmp_path); exp=store.create_experiment(exp_req(ctx["context_id"])); trial=store.add_trial(exp["experiment_id"],AIResearchTrialCreateRequest(actor_ref="r",label="a",context_id=ctx["context_id"]))
    binding=store.add_evaluation_binding(exp["experiment_id"],AIExperimentEvaluationBindingRequest(actor_ref="r",trial_id=trial["trial_id"],evaluation_id=ev["evaluation_id"]))
    assert binding["evaluation_id"]==ev["evaluation_id"] and binding["governance"]["evaluation_is_evidence_not_winner_selection"] is True
    try:
        store.add_evaluation_binding(exp["experiment_id"],AIExperimentEvaluationBindingRequest(actor_ref="r",trial_id=trial["trial_id"],evaluation_id="missing")); assert False
    except ValueError: pass


def test_state_machine_requires_trial_before_ready_and_no_terminal_reopen(tmp_path):
    _,_,store,ctx,_=make_stores(tmp_path); exp=store.create_experiment(exp_req(ctx["context_id"]))
    try:
        store.set_state(exp["experiment_id"],AIExperimentStateRequest(actor_ref="r",state="ready")); assert False
    except ValueError: pass
    store.add_trial(exp["experiment_id"],AIResearchTrialCreateRequest(actor_ref="r",label="a",context_id=ctx["context_id"]))
    assert store.set_state(exp["experiment_id"],AIExperimentStateRequest(actor_ref="r",state="ready"))["state"]=="ready"
    store.set_state(exp["experiment_id"],AIExperimentStateRequest(actor_ref="r",state="running")); done=store.set_state(exp["experiment_id"],AIExperimentStateRequest(actor_ref="r",state="completed")); assert done["state"]=="completed"
    try:
        store.set_state(exp["experiment_id"],AIExperimentStateRequest(actor_ref="r",state="running")); assert False
    except ValueError: pass


def test_summary_snapshot_and_durable_job(tmp_path,monkeypatch):
    _,_,store,ctx,_=make_stores(tmp_path); exp=store.create_experiment(exp_req(ctx["context_id"])); trial=store.add_trial(exp["experiment_id"],AIResearchTrialCreateRequest(actor_ref="r",label="a",context_id=ctx["context_id"]))
    store.add_receipt(exp["experiment_id"],AIExperimentRunReceiptRequest(actor_ref="workspace",trial_id=trial["trial_id"],status="succeeded",external_run_ref="workspace:run-1"))
    summary=store.summary(exp["experiment_id"]); assert summary["run_status_counts"]["succeeded"]==1 and summary["governance"]["winner_selected"] is False
    snap=store.freeze_snapshot(AIExperimentSnapshotRequest(actor_ref="r",experiment_id=exp["experiment_id"])); assert len(snap["snapshot_hash"])==64
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_ai_research_experiment_store",lambda:store)
    claim=JobClaim(job_id="job-980",job_type="ai-research-experiment-snapshot",payload={"snapshot":{"actor_ref":"r","experiment_id":exp["experiment_id"]}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-ai-experiment-snapshot/1.0" and events[-1]==("ai-research-experiment-snapshot-ready",95) and "ai-research-experiment-snapshot" in JOB_TYPES


def test_authenticated_v980_api_surface():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/ai-research-experiments/capabilities",
        "/v1/core/ai-research-experiments/experiments",
        "/v1/core/ai-research-experiments/experiments/{experiment_id}",
        "/v1/core/ai-research-experiments/experiments/{experiment_id}/trials",
        "/v1/core/ai-research-experiments/experiments/{experiment_id}/execution-handoffs",
        "/v1/core/ai-research-experiments/experiments/{experiment_id}/run-receipts",
        "/v1/core/ai-research-experiments/experiments/{experiment_id}/evaluation-bindings",
        "/v1/core/ai-research-experiments/experiments/{experiment_id}/summary",
        "/v1/core/ai-research-experiments/experiments/{experiment_id}/state",
        "/v1/core/ai-research-experiments/snapshots/freeze",
    }
    assert not(required-paths),required-paths
    client=TestClient(app); resp=client.get("/v1/core/ai-research-experiments/capabilities",headers={"X-SC-RL-Key":"test-key"})
    body=resp.json(); assert resp.status_code==200 and body["automatic_execution"] is False and body["automatic_best_model_selection"] is False
