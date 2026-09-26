from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA = "sc-research-librarian-systematic-review-evidence-synthesis/1.0"
SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SNAPSHOT_SCHEMA = "sc-research-librarian-systematic-review-evidence-synthesis-snapshot/1.0"

ScreeningStage = Literal["title-abstract", "full-text"]
ScreeningDecision = Literal["include", "exclude", "uncertain"]
ReviewState = Literal["draft", "under-review", "approved", "rejected"]
BiasJudgment = Literal["low", "some-concerns", "high", "unclear", "not-assessed"]
EvidenceCertainty = Literal["high", "moderate", "low", "very-low", "unrated"]
SynthesisType = Literal["narrative", "quantitative", "meta-analysis", "mixed", "other"]

class SystematicReviewCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    project_ref: str = Field(min_length=1, max_length=2000)
    evidence_search_strategy_id: str = Field(default="", max_length=255)
    question_plan_id: str = Field(default="", max_length=255)
    research_design_plan_id: str = Field(default="", max_length=255)
    environment_id: str = Field(default="", max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    review_question: str = Field(default="", max_length=20000)
    review_type: str = Field(default="systematic-review", max_length=255)
    protocol_framework: str = Field(default="systematic-review-protocol", max_length=255)
    inclusion_criteria: list[str] = Field(default_factory=list, max_length=1000)
    exclusion_criteria: list[str] = Field(default_factory=list, max_length=1000)
    evidence_requirements: list[str] = Field(default_factory=list, max_length=2000)
    extraction_fields: list[str] = Field(default_factory=list, max_length=1000)
    scaffold_protocol: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

class ReviewCandidateAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    source_ref: str = Field(min_length=1, max_length=2000)
    title: str = Field(default="", max_length=2000)
    abstract_excerpt: str = Field(default="", max_length=20000)
    publication_year: int | None = Field(default=None, ge=0, le=3000)
    identifiers: dict[str, str] = Field(default_factory=dict)
    retrieval_ref: str = Field(default="", max_length=2000)
    duplicate_group_ref: str = Field(default="", max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ReviewScreeningDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    candidate_id: str = Field(min_length=1, max_length=255)
    stage: ScreeningStage
    decision: ScreeningDecision
    reason_code: str = Field(default="", max_length=255)
    reason: str = Field(default="", max_length=10000)
    reviewer_ref: str = Field(default="", max_length=2000)

class ReviewExtractionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    candidate_id: str = Field(min_length=1, max_length=255)
    fields: dict[str, Any] = Field(default_factory=dict)
    population: str = Field(default="", max_length=10000)
    exposure_or_intervention: str = Field(default="", max_length=10000)
    comparator: str = Field(default="", max_length=10000)
    outcomes: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)
    design: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=20000)
    source_locator_refs: list[str] = Field(default_factory=list, max_length=5000)

class ReviewBiasAssessmentRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    candidate_id: str = Field(min_length=1, max_length=255)
    instrument: str = Field(default="reviewer-declared", max_length=1000)
    domain: str = Field(min_length=1, max_length=1000)
    judgment: BiasJudgment = "not-assessed"
    rationale: str = Field(default="", max_length=10000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)

class ReviewEvidenceGradeRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    outcome_ref: str = Field(min_length=1, max_length=2000)
    framework: str = Field(default="reviewer-declared", max_length=1000)
    certainty: EvidenceCertainty = "unrated"
    rationale: str = Field(default="", max_length=10000)
    study_refs: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)

class ReviewSynthesisPlanRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    synthesis_type: SynthesisType
    included_candidate_ids: list[str] = Field(default_factory=list, max_length=5000)
    outcome_refs: list[str] = Field(default_factory=list, max_length=5000)
    analysis_candidates: list[str] = Field(default_factory=list, max_length=1000)
    heterogeneity_considerations: list[str] = Field(default_factory=list, max_length=1000)
    execution_target: str = Field(default="workspace", max_length=255)
    notes: str = Field(default="", max_length=20000)

class SystematicReviewStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: ReviewState
    note: str = Field(default="", max_length=10000)

class SystematicReviewSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    review_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="systematic-review-evidence-synthesis-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
