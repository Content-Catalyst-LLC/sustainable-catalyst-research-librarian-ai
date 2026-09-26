from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

EVIDENCE_SEARCH_STRATEGY_SCHEMA = "sc-research-librarian-evidence-search-strategy/1.0"
EVIDENCE_SEARCH_STRATEGY_SNAPSHOT_SCHEMA = "sc-research-librarian-evidence-search-strategy-snapshot/1.0"

SourceFamily = Literal[
    "knowledge-library", "federated-discovery", "scholarly-database", "government",
    "institutional-repository", "archival", "web", "domain-repository", "other",
]
CriterionMode = Literal["include", "exclude"]
ReviewState = Literal["draft", "under-review", "approved", "rejected"]

class SearchConceptSpec(BaseModel):
    name: str = Field(min_length=1, max_length=1000)
    description: str = Field(default="", max_length=10000)
    terms: list[str] = Field(default_factory=list, max_length=1000)
    excluded_terms: list[str] = Field(default_factory=list, max_length=1000)

class SearchSourceTargetSpec(BaseModel):
    name: str = Field(min_length=1, max_length=1000)
    source_family: SourceFamily
    target_ref: str = Field(default="", max_length=2000)
    rationale: str = Field(default="", max_length=10000)
    required: bool = False

class SearchQuerySpec(BaseModel):
    label: str = Field(min_length=1, max_length=1000)
    query_text: str = Field(min_length=1, max_length=20000)
    target_refs: list[str] = Field(default_factory=list, max_length=1000)
    concept_names: list[str] = Field(default_factory=list, max_length=1000)
    evidence_requirement_refs: list[str] = Field(default_factory=list, max_length=1000)
    filters: dict[str, Any] = Field(default_factory=dict)

class EvidenceSearchStrategyCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    project_ref: str = Field(min_length=1, max_length=2000)
    question_plan_id: str = Field(default="", max_length=255)
    research_design_plan_id: str = Field(default="", max_length=255)
    environment_id: str = Field(default="", max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    research_question: str = Field(default="", max_length=20000)
    concepts: list[SearchConceptSpec] = Field(default_factory=list, max_length=200)
    source_targets: list[SearchSourceTargetSpec] = Field(default_factory=list, max_length=200)
    queries: list[SearchQuerySpec] = Field(default_factory=list, max_length=500)
    evidence_requirements: list[str] = Field(default_factory=list, max_length=2000)
    inclusion_criteria: list[str] = Field(default_factory=list, max_length=1000)
    exclusion_criteria: list[str] = Field(default_factory=list, max_length=1000)
    languages: list[str] = Field(default_factory=lambda: ["English"], max_length=100)
    date_start: str = Field(default="", max_length=64)
    date_end: str = Field(default="", max_length=64)
    source_types: list[str] = Field(default_factory=list, max_length=500)
    scaffold_strategy: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

class SearchConceptAddRequest(SearchConceptSpec):
    actor_ref: str = Field(min_length=1, max_length=255)

class SearchSourceTargetAddRequest(SearchSourceTargetSpec):
    actor_ref: str = Field(min_length=1, max_length=255)

class SearchQueryAddRequest(SearchQuerySpec):
    actor_ref: str = Field(min_length=1, max_length=255)

class SearchEligibilityCriterionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    mode: CriterionMode
    criterion: str = Field(min_length=1, max_length=10000)
    rationale: str = Field(default="", max_length=10000)

class SearchExecutionReceiptRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    query_id: str = Field(min_length=1, max_length=255)
    target_ref: str = Field(default="", max_length=2000)
    execution_ref: str = Field(default="", max_length=2000)
    executed_utc: str = Field(default="", max_length=128)
    result_count: int = Field(default=0, ge=0)
    imported_count: int = Field(default=0, ge=0)
    note: str = Field(default="", max_length=10000)

class EvidenceSearchReviewStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: ReviewState
    note: str = Field(default="", max_length=10000)

class EvidenceSearchSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    strategy_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="evidence-search-strategy-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
