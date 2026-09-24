from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

PEER_REVIEW_SCHEMA = "sc-research-librarian-peer-review-replication-validation/1.0"
PEER_REVIEW_PACKAGE_SCHEMA = "sc-research-librarian-peer-review-validation-package/1.0"
PEER_REVIEW_READINESS_SCHEMA = "sc-research-librarian-peer-review-readiness/1.0"


class ReviewRoundCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    round_type: Literal["initial", "revision", "replication", "methods", "other"] = "initial"
    label: str = Field(default="", max_length=500)
    target_revision_hash: str = Field(default="", max_length=128)
    notes: str = Field(default="", max_length=10_000)
    idempotency_key: str | None = Field(default=None, max_length=500)


class ReviewerAssignmentRequest(BaseModel):
    assigned_by_ref: str = Field(min_length=1, max_length=255)
    reviewer_ref: str = Field(min_length=1, max_length=255)
    role: Literal["peer-reviewer", "methods-reviewer", "statistical-reviewer", "replication-reviewer", "editor"] = "peer-reviewer"
    expertise: list[str] = Field(default_factory=list, max_length=100)
    conflict_status: Literal["none-declared", "potential", "confirmed", "not-assessed"] = "not-assessed"
    conflict_statement: str = Field(default="", max_length=10_000)
    anonymous_label: str = Field(default="", max_length=255)


class StructuredPeerReviewRequest(BaseModel):
    reviewer_ref: str = Field(min_length=1, max_length=255)
    recommendation: Literal["accept", "minor-revision", "major-revision", "reject", "no-recommendation"]
    summary: str = Field(min_length=1, max_length=30_000)
    strengths: list[str] = Field(default_factory=list, max_length=200)
    major_concerns: list[str] = Field(default_factory=list, max_length=200)
    minor_concerns: list[str] = Field(default_factory=list, max_length=500)
    requested_actions: list[str] = Field(default_factory=list, max_length=500)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    result_refs: list[str] = Field(default_factory=list, max_length=2000)
    methods_assessment: Literal["not-assessed", "adequate", "concerns", "major-concerns"] = "not-assessed"
    reproducibility_assessment: Literal["not-assessed", "reproducible", "partially-reproducible", "not-reproducible", "blocked"] = "not-assessed"
    statistical_assessment: Literal["not-assessed", "adequate", "concerns", "major-concerns"] = "not-assessed"
    confidence: Literal["low", "moderate", "high", "not-declared"] = "not-declared"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthorResponseRequest(BaseModel):
    author_ref: str = Field(min_length=1, max_length=255)
    review_id: str = Field(min_length=1, max_length=255)
    response_text: str = Field(min_length=1, max_length=50_000)
    addressed_actions: list[str] = Field(default_factory=list, max_length=500)
    unresolved_actions: list[str] = Field(default_factory=list, max_length=500)
    revision_ref: str = Field(default="", max_length=1000)


class RevisionSubmissionRequest(BaseModel):
    author_ref: str = Field(min_length=1, max_length=255)
    revision_label: str = Field(default="revision", max_length=500)
    scholarly_revision_hash: str = Field(default="", max_length=128)
    manuscript_section_refs: list[str] = Field(default_factory=list, max_length=5000)
    response_refs: list[str] = Field(default_factory=list, max_length=5000)
    change_summary: str = Field(min_length=1, max_length=40_000)
    artifact_ref: str = Field(default="", max_length=2000)


class ReplicationAttemptRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    replication_type: Literal["direct", "conceptual", "computational", "reanalysis", "robustness", "other"]
    status: Literal["planned", "in-progress", "completed", "failed", "withdrawn"] = "completed"
    outcome: Literal["not-assessed", "consistent", "partially-consistent", "inconsistent", "inconclusive", "technical-failure"] = "not-assessed"
    protocol_ref: str = Field(default="", max_length=2000)
    runtime_ref: str = Field(default="", max_length=2000)
    artifact_ref: str = Field(default="", max_length=2000)
    source_refs: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    result_refs: list[str] = Field(default_factory=list, max_length=2000)
    deviations: list[str] = Field(default_factory=list, max_length=500)
    summary: str = Field(min_length=1, max_length=40_000)
    limitations: list[str] = Field(default_factory=list, max_length=500)
    content_hash: str = Field(default="", max_length=128)


class EditorialDecisionRequest(BaseModel):
    editor_ref: str = Field(min_length=1, max_length=255)
    decision: Literal["accept", "minor-revision", "major-revision", "reject", "withdrawn", "no-decision"]
    rationale: str = Field(min_length=1, max_length=30_000)
    based_on_review_ids: list[str] = Field(default_factory=list, max_length=1000)
    based_on_replication_ids: list[str] = Field(default_factory=list, max_length=1000)
    supersedes_decision_id: str = Field(default="", max_length=255)


class PeerReviewPackageFreezeRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    package_label: str = Field(default="peer-review-validation-package", max_length=255)
    note: str = Field(default="", max_length=10_000)
    require_decision: bool = True
    require_all_reviews_responded: bool = False

    @model_validator(mode="after")
    def actor_required(self):
        if not self.actor_ref.strip():
            raise ValueError("actor_ref is required")
        return self
