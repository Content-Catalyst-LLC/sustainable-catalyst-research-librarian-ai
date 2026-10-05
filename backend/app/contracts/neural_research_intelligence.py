from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

NEURAL_RESEARCH_SCHEMA = "sc-research-librarian-neural-research-intelligence/1.0"
NEURAL_RESEARCH_SNAPSHOT_SCHEMA = "sc-research-librarian-neural-research-snapshot/1.0"
NEURAL_RUNTIME_HANDOFF_SCHEMA = "sc-research-librarian-neural-runtime-handoff/1.0"

NeuralResearchState = Literal["draft", "active", "review", "closed", "archived"]
RuntimeTarget = Literal["workspace", "research-lab", "workbench", "external"]
NeuralOperation = Literal[
    "training", "fine-tuning", "inference", "embedding-generation",
    "evaluation", "explainability", "representation-analysis", "benchmarking",
]

class NeuralResearchCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    project_ref: str = Field(default="", max_length=2000)
    research_question_ref: str = Field(default="", max_length=2000)
    objective: str = Field(default="", max_length=30000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class NeuralModelReferenceAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    framework: str = Field(default="", max_length=255)
    model_ref: str = Field(min_length=1, max_length=4000)
    model_hash: str = Field(default="", max_length=255)
    model_family: str = Field(default="", max_length=1000)
    architecture: str = Field(default="", max_length=4000)
    task_types: list[str] = Field(default_factory=list, max_length=100)
    checkpoint_ref: str = Field(default="", max_length=4000)
    core_model_ref: str = Field(default="", max_length=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class NeuralDatasetReferenceAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    dataset_ref: str = Field(min_length=1, max_length=4000)
    dataset_hash: str = Field(default="", max_length=255)
    split: str = Field(default="", max_length=255)
    feature_schema_ref: str = Field(default="", max_length=4000)
    transformation_refs: list[str] = Field(default_factory=list, max_length=500)
    core_dataset_ref: str = Field(default="", max_length=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class NeuralRepresentationReferenceAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    source_refs: list[str] = Field(min_length=1, max_length=5000)
    model_reference_id: str = Field(default="", max_length=255)
    dimensions: int = Field(default=0, ge=0, le=10000000)
    metric: str = Field(default="", max_length=255)
    vector_store_ref: str = Field(default="", max_length=4000)
    transformation_refs: list[str] = Field(default_factory=list, max_length=5000)
    core_embedding_ref: str = Field(default="", max_length=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class NeuralInferenceReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    model_reference_id: str = Field(min_length=1, max_length=255)
    input_refs: list[str] = Field(default_factory=list, max_length=5000)
    output_refs: list[str] = Field(default_factory=list, max_length=5000)
    runtime_target: RuntimeTarget = "workspace"
    execution_ref: str = Field(min_length=1, max_length=4000)
    checkpoint_ref: str = Field(default="", max_length=4000)
    parameters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    provenance_note: str = Field(default="", max_length=20000)

class NeuralRuntimeHandoffPrepareRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    target: RuntimeTarget
    operation: NeuralOperation
    objective: str = Field(min_length=1, max_length=30000)
    model_reference_ids: list[str] = Field(default_factory=list, max_length=5000)
    dataset_reference_ids: list[str] = Field(default_factory=list, max_length=5000)
    representation_reference_ids: list[str] = Field(default_factory=list, max_length=5000)
    expected_artifacts: list[str] = Field(default_factory=list, max_length=5000)
    note: str = Field(default="", max_length=20000)

class NeuralResearchStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: NeuralResearchState
    note: str = Field(default="", max_length=20000)

class NeuralResearchSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    neural_research_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="neural-research-intelligence-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
