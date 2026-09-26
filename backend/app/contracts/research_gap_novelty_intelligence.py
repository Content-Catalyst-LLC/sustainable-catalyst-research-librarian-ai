from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA = "sc-research-librarian-research-gap-novelty-intelligence/1.0"
RESEARCH_GAP_NOVELTY_SNAPSHOT_SCHEMA = "sc-research-librarian-research-gap-novelty-intelligence-snapshot/1.0"

GapType = Literal["evidence","methodological","population","context","geographic","temporal","data","measurement","replication","contradiction","theoretical","implementation","other"]
GapDecision = Literal["pending","accepted","rejected"]
NoveltyType = Literal["research-question","method","dataset","population","context","synthesis","mechanism","replication","application","other"]
NoveltyDecision = Literal["pending","accepted","rejected"]
ReviewState = Literal["draft","in_review","approved","archived"]

class ResearchGapNoveltyCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    project_ref: str = Field(min_length=1, max_length=2000)
    research_question: str = Field(default="", max_length=20000)
    core_project_id: str = Field(default="", max_length=255)
    argument_intelligence_id: str = Field(default="", max_length=255)
    literature_intelligence_id: str = Field(default="", max_length=255)
    systematic_review_id: str = Field(default="", max_length=255)
    research_design_plan_id: str = Field(default="", max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchGapCandidateAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    gap_type: GapType
    label: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1, max_length=20000)
    claim_ids: list[str] = Field(default_factory=list, max_length=5000)
    work_ids: list[str] = Field(default_factory=list, max_length=5000)
    tension_ids: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    rationale: str = Field(default="", max_length=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchGapDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    gap_id: str = Field(min_length=1, max_length=255)
    decision: Literal["accepted","rejected"]
    rationale: str = Field(default="", max_length=10000)

class NoveltyCandidateAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    novelty_type: NoveltyType
    label: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1, max_length=20000)
    gap_ids: list[str] = Field(default_factory=list, max_length=5000)
    claim_ids: list[str] = Field(default_factory=list, max_length=5000)
    work_ids: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    comparison_basis: str = Field(default="", max_length=20000)
    rationale: str = Field(default="", max_length=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class NoveltyDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    novelty_candidate_id: str = Field(min_length=1, max_length=255)
    decision: Literal["accepted","rejected"]
    rationale: str = Field(default="", max_length=10000)

class OriginalResearchOpportunityAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    research_question: str = Field(min_length=1, max_length=20000)
    gap_ids: list[str] = Field(default_factory=list, max_length=5000)
    novelty_candidate_ids: list[str] = Field(default_factory=list, max_length=5000)
    method_candidate_refs: list[str] = Field(default_factory=list, max_length=5000)
    data_requirement_refs: list[str] = Field(default_factory=list, max_length=5000)
    rationale: str = Field(default="", max_length=10000)
    feasibility_notes: str = Field(default="", max_length=20000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchGapNoveltyStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: ReviewState
    note: str = Field(default="", max_length=10000)

class ResearchGapNoveltySnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    gap_novelty_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="research-gap-novelty-intelligence-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
