from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

UNIFIED_SCHOLARLY_AI_ENVIRONMENT_SCHEMA = "sc-research-librarian-unified-scholarly-ai-research-environment/1.0"
UNIFIED_SCHOLARLY_AI_DOSSIER_SCHEMA = "sc-research-librarian-unified-scholarly-ai-research-dossier/1.0"
UNIFIED_SCHOLARLY_AI_SNAPSHOT_SCHEMA = "sc-research-librarian-unified-scholarly-ai-research-snapshot/1.0"

ComponentType = Literal[
    "research-workflow", "scholarly-study", "scholarly-publication", "knowledge-graph-node",
    "ai-research-context", "rag-evaluation", "ai-research-experiment", "model-aware-research",
    "cross-product-exchange", "research-question-plan", "research-design-plan", "core-object",
]

class UnifiedResearchEnvironmentCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    research_question: str = Field(default="", max_length=20000)
    project_ref: str = Field(min_length=1, max_length=2000)
    workflow_id: str = Field(default="", max_length=255)
    study_id: str = Field(default="", max_length=255)
    publication_id: str = Field(default="", max_length=255)
    context_ids: list[str] = Field(default_factory=list, max_length=5000)
    evaluation_ids: list[str] = Field(default_factory=list, max_length=5000)
    experiment_ids: list[str] = Field(default_factory=list, max_length=5000)
    model_aware_record_ids: list[str] = Field(default_factory=list, max_length=5000)
    exchange_ids: list[str] = Field(default_factory=list, max_length=5000)
    question_plan_ids: list[str] = Field(default_factory=list, max_length=5000)
    research_design_plan_ids: list[str] = Field(default_factory=list, max_length=5000)
    knowledge_graph_node_refs: list[str] = Field(default_factory=list, max_length=5000)
    core_object_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class UnifiedResearchEnvironmentBindingRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    component_type: ComponentType
    ref: str = Field(min_length=1, max_length=2000)
    role: str = Field(default="", max_length=255)
    note: str = Field(default="", max_length=10000)

class UnifiedResearchEnvironmentSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    environment_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="unified-scholarly-ai-research-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
