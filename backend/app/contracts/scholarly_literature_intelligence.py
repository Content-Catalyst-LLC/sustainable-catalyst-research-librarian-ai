from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA = "sc-research-librarian-scholarly-literature-intelligence/1.0"
SCHOLARLY_LITERATURE_INTELLIGENCE_SNAPSHOT_SCHEMA = "sc-research-librarian-scholarly-literature-intelligence-snapshot/1.0"

CitationFunction = Literal["background","method","support","challenge","extension","comparison","definition","data","other"]
LiteratureState = Literal["draft","under-review","approved","rejected"]
GapType = Literal["empirical","methodological","population","geographic","theoretical","replication","contradiction","data","other"]
CandidateDecision = Literal["pending","accepted","rejected"]

class LiteratureIntelligenceCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    project_ref: str = Field(min_length=1, max_length=2000)
    systematic_review_id: str = Field(default="", max_length=255)
    question_plan_id: str = Field(default="", max_length=255)
    research_design_plan_id: str = Field(default="", max_length=255)
    evidence_search_strategy_id: str = Field(default="", max_length=255)
    environment_id: str = Field(default="", max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    research_question: str = Field(default="", max_length=20000)
    seed_source_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class LiteratureWorkAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    source_ref: str = Field(min_length=1, max_length=2000)
    title: str = Field(default="", max_length=2000)
    publication_year: int | None = Field(default=None, ge=0, le=3000)
    authors: list[str] = Field(default_factory=list, max_length=1000)
    identifiers: dict[str, str] = Field(default_factory=dict)
    publication_type: str = Field(default="", max_length=255)
    study_or_review_ref: str = Field(default="", max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class CitationContextAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    citing_work_id: str = Field(min_length=1, max_length=255)
    cited_work_id: str = Field(min_length=1, max_length=255)
    function: CitationFunction = "other"
    context_excerpt: str = Field(default="", max_length=20000)
    source_locator_ref: str = Field(default="", max_length=2000)
    rationale: str = Field(default="", max_length=10000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)

class LiteratureStrandAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    description: str = Field(default="", max_length=10000)
    work_ids: list[str] = Field(default_factory=list, max_length=5000)
    rationale: str = Field(default="", max_length=10000)

class LiteratureGapAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    gap_type: GapType
    label: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1, max_length=20000)
    work_ids: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    rationale: str = Field(default="", max_length=10000)

class SeminalCandidateAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    work_id: str = Field(min_length=1, max_length=255)
    rationale: str = Field(min_length=1, max_length=10000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)

class RelatedWorkCandidateAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    source_work_id: str = Field(min_length=1, max_length=255)
    target_work_id: str = Field(min_length=1, max_length=255)
    relation: str = Field(default="related-to", max_length=255)
    basis: str = Field(min_length=1, max_length=10000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)

class RelatedWorkDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    candidate_id: str = Field(min_length=1, max_length=255)
    decision: Literal["accepted","rejected"]
    rationale: str = Field(default="", max_length=10000)

class LiteratureIntelligenceStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: LiteratureState
    note: str = Field(default="", max_length=10000)

class LiteratureIntelligenceSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    intelligence_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="scholarly-literature-intelligence-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
