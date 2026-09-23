from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA = "sc-research-librarian-finding-claim-evidence-extraction/1.0"
CORE_RESEARCH_INTELLIGENCE_CONTRACT = "sc.research.finding-claim-evidence.v1"

EvidenceRelation = Literal[
    "supports",
    "contradicts",
    "qualifies",
    "is_insufficient_for",
    "contextualizes",
    "derived_from",
]


class EvidencePassageInput(BaseModel):
    local_evidence_id: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=40_000)
    core_evidence_id: str | None = Field(default=None, max_length=255)
    canonical_source_id: str | None = Field(default=None, max_length=255)
    source_title: str | None = Field(default=None, max_length=500)
    passage_id: str | None = Field(default=None, max_length=255)
    chunk_id: str | None = Field(default=None, max_length=255)
    section_path: list[str] = Field(default_factory=list, max_length=40)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    relation_hint: EvidenceRelation | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def page_range_is_ordered(self):
        if self.page_start is not None and self.page_end is not None and self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self


class ResearchIntelligenceExtractionRequest(BaseModel):
    core_project_id: str = Field(min_length=1, max_length=255)
    research_question: str = Field(default="", max_length=5000)
    passages: list[EvidencePassageInput] = Field(min_length=1, max_length=200)
    max_candidates: int = Field(default=50, ge=1, le=200)
    minimum_sentence_words: int = Field(default=6, ge=3, le=50)
    include_findings: bool = True
    include_claims: bool = True

    @model_validator(mode="after")
    def at_least_one_candidate_kind(self):
        if not self.include_findings and not self.include_claims:
            raise ValueError("At least one of include_findings/include_claims must be true")
        return self


class ResearchIntelligenceCandidate(BaseModel):
    candidate_id: str
    candidate_type: Literal["finding", "claim"]
    text: str
    title: str | None = None
    finding_type: Literal[
        "observation", "result", "pattern", "anomaly", "estimate", "model_output", "synthesis", "negative_result", "limitation"
    ] | None = None
    claim_type: Literal[
        "descriptive", "interpretive", "causal", "comparative", "predictive", "normative", "methodological"
    ] | None = None
    classification_basis: list[str] = Field(default_factory=list)
    uncertainty_cues: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    review_decision: Literal["pending", "approved", "rejected"] = "pending"
    reviewer_ref: str | None = Field(default=None, max_length=255)
    reviewer_note: str | None = Field(default=None, max_length=5000)
    provenance: dict[str, Any] = Field(default_factory=dict)


class CoreResearchCandidatePromotionRequest(BaseModel):
    core_project_id: str = Field(min_length=1, max_length=255)
    candidate: ResearchIntelligenceCandidate
    created_by: str = Field(default="research-librarian", min_length=1, max_length=255)
    evidence_relation: EvidenceRelation | None = None
    declared_strength: str | None = Field(default=None, max_length=255)
    assessment_basis: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def candidate_requires_explicit_review(self):
        if self.candidate.review_decision != "approved":
            raise ValueError("Core promotion requires candidate.review_decision='approved'.")
        if not str(self.candidate.reviewer_ref or "").strip():
            raise ValueError("Core promotion requires candidate.reviewer_ref.")
        return self
