from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

AI_RESEARCH_EXPERIMENT_SCHEMA = "sc-research-librarian-ai-research-experiment/1.0"
AI_RESEARCH_TRIAL_SCHEMA = "sc-research-librarian-ai-research-trial/1.0"
AI_EXPERIMENT_HANDOFF_SCHEMA = "sc-research-librarian-ai-experiment-handoff/1.0"
AI_EXPERIMENT_RUN_RECEIPT_SCHEMA = "sc-research-librarian-ai-experiment-run-receipt/1.0"
AI_EXPERIMENT_EVALUATION_BINDING_SCHEMA = "sc-research-librarian-ai-experiment-evaluation-binding/1.0"
AI_EXPERIMENT_SNAPSHOT_SCHEMA = "sc-research-librarian-ai-experiment-snapshot/1.0"

ExperimentState = Literal["draft", "ready", "running", "paused", "completed", "cancelled"]
RunStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
TargetRuntime = Literal["workspace", "research-lab", "workbench", "external"]

class AIResearchExperimentCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    objective: str = Field(min_length=1, max_length=20000)
    research_question: str = Field(default="", max_length=20000)
    project_ref: str = Field(default="", max_length=2000)
    study_ref: str = Field(default="", max_length=2000)
    base_context_id: str = Field(default="", max_length=255)
    evaluation_dataset_ref: str = Field(default="", max_length=2000)
    evaluation_dataset_version_ref: str = Field(default="", max_length=2000)
    hypothesis_refs: list[str] = Field(default_factory=list, max_length=5000)
    controlled_variables: dict[str, Any] = Field(default_factory=dict)
    declared_outcomes: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class AIResearchTrialCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=500)
    context_id: str = Field(default="", max_length=255)
    model_ref: str = Field(default="", max_length=2000)
    model_version_ref: str = Field(default="", max_length=2000)
    prompt_version_ref: str = Field(default="", max_length=2000)
    embedding_model_ref: str = Field(default="", max_length=2000)
    retriever_ref: str = Field(default="", max_length=2000)
    reranker_ref: str = Field(default="", max_length=2000)
    dataset_version_ref: str = Field(default="", max_length=2000)
    runtime_ref: str = Field(default="", max_length=2000)
    environment_ref: str = Field(default="", max_length=2000)
    parameters: dict[str, Any] = Field(default_factory=dict)
    seed: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class AIExperimentExecutionHandoffRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    trial_id: str = Field(min_length=1, max_length=255)
    target_runtime: TargetRuntime = "workspace"
    target_ref: str = Field(default="", max_length=2000)
    execution_contract_ref: str = Field(default="", max_length=2000)
    requested_artifacts: list[str] = Field(default_factory=list, max_length=5000)
    resource_budget: dict[str, Any] = Field(default_factory=dict)
    notes: str = Field(default="", max_length=20000)

class AIExperimentRunReceiptRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    trial_id: str = Field(min_length=1, max_length=255)
    handoff_id: str = Field(default="", max_length=255)
    status: RunStatus
    external_run_ref: str = Field(default="", max_length=2000)
    runtime_ref: str = Field(default="", max_length=2000)
    environment_ref: str = Field(default="", max_length=2000)
    model_artifact_refs: list[str] = Field(default_factory=list, max_length=5000)
    output_refs: list[str] = Field(default_factory=list, max_length=5000)
    log_ref: str = Field(default="", max_length=2000)
    started_utc: str = Field(default="", max_length=255)
    finished_utc: str = Field(default="", max_length=255)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: str = Field(default="", max_length=20000)

class AIExperimentEvaluationBindingRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    trial_id: str = Field(min_length=1, max_length=255)
    run_receipt_id: str = Field(default="", max_length=255)
    evaluation_id: str = Field(min_length=1, max_length=255)
    interpretation_ref: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=20000)

class AIExperimentStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: ExperimentState
    note: str = Field(default="", max_length=10000)

class AIExperimentSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    experiment_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="ai-research-experiment-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
