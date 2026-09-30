from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

SCHOLARLY_CRITIQUE_SCHEMA = "sc-research-librarian-peer-review-scholarly-critique-intelligence/1.0"
SCHOLARLY_CRITIQUE_SNAPSHOT_SCHEMA = "sc-research-librarian-peer-review-scholarly-critique-intelligence-snapshot/1.0"

CritiqueState = Literal["draft", "in_review", "author_response", "revision_review", "editorial_review", "closed", "archived"]
TargetType = Literal[
    "scholarly-study", "scholarly-publication", "manuscript-revision", "research-integrity-audit",
    "cross-study-synthesis-plan", "reproduction-replication-plan", "study-protocol",
    "statistical-analysis-plan-intelligence", "causal-research-design", "simulation-model-study-plan",
    "core-object", "other",
]
ReviewRoundType = Literal["initial", "revision", "methods", "statistics", "replication", "editorial", "other"]
ReviewerRole = Literal["peer-reviewer", "methods-reviewer", "statistical-reviewer", "replication-reviewer", "editorial-reviewer", "other"]
CritiqueDomain = Literal[
    "framing-and-contribution", "literature-positioning", "research-question-alignment", "methods",
    "statistics", "causal-inference", "evidence-support", "interpretation", "limitations",
    "reproducibility", "transparency", "data-and-code", "figures-and-tables", "citations",
    "reporting-completeness", "ethics-and-disclosure", "other",
]
CommentKind = Literal["question", "suggestion", "concern", "required-change", "commendation", "other"]
Significance = Literal["note", "minor", "major", "critical", "not-assessed"]
ResolutionStatus = Literal["open", "addressed", "partially-addressed", "accepted-with-rationale", "not-applicable"]
Decision = Literal["pending", "approved", "rejected", "waived"]
VerificationStatus = Literal["completed", "partial", "failed-to-run", "cancelled"]
RequirementStatus = Literal["open", "in-progress", "addressed", "waived", "not-applicable"]

class ScholarlyCritiqueTargetBinding(BaseModel):
    target_type: TargetType
    target_ref: str = Field(min_length=1, max_length=2000)
    role: str = Field(default="", max_length=255)
    source_hash: str = Field(default="", max_length=255)
    note: str = Field(default="", max_length=10000)

class ScholarlyCritiqueCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    review_question: str = Field(min_length=1, max_length=20000)
    review_scope: str = Field(default="scholarly critique and peer-review traceability", max_length=10000)
    project_ref: str = Field(default="", max_length=2000)
    targets: list[ScholarlyCritiqueTargetBinding] = Field(default_factory=list, max_length=5000)
    upstream_peer_review_refs: list[str] = Field(default_factory=list, max_length=5000)
    research_integrity_audit_refs: list[str] = Field(default_factory=list, max_length=5000)
    review_standard_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ScholarlyCritiqueRoundAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    round_type: ReviewRoundType = "initial"
    label: str = Field(default="", max_length=1000)
    target_revision_ref: str = Field(default="", max_length=2000)
    target_revision_hash: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=20000)

class ScholarlyCritiqueDimensionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    domain: CritiqueDomain
    label: str = Field(min_length=1, max_length=1000)
    review_prompt: str = Field(min_length=1, max_length=20000)
    expectation_basis: str = Field(default="", max_length=20000)
    target_refs: list[str] = Field(default_factory=list, max_length=5000)

class ScholarlyReviewerCritiqueAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    round_id: str = Field(min_length=1, max_length=255)
    dimension_id: str = Field(min_length=1, max_length=255)
    reviewer_ref: str = Field(min_length=1, max_length=255)
    reviewer_role: ReviewerRole = "peer-reviewer"
    anonymous_label: str = Field(default="", max_length=255)
    comment_kind: CommentKind
    significance: Significance = "not-assessed"
    location_ref: str = Field(default="", max_length=2000)
    critique: str = Field(min_length=1, max_length=40000)
    rationale: str = Field(default="", max_length=30000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    requested_actions: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)

class ScholarlyAuthorResponseAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    critique_id: str = Field(min_length=1, max_length=255)
    response: str = Field(min_length=1, max_length=50000)
    response_status: ResolutionStatus = "open"
    revision_ref: str = Field(default="", max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)

class ScholarlyRevisionRequirementAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    critique_ids: list[str] = Field(min_length=1, max_length=5000)
    requirement: str = Field(min_length=1, max_length=30000)
    rationale: str = Field(default="", max_length=30000)
    owner_ref: str = Field(default="", max_length=255)
    target_revision_ref: str = Field(default="", max_length=2000)
    verification_requirement: str = Field(default="", max_length=10000)

class ScholarlyRevisionRequirementStatusRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    revision_requirement_id: str = Field(min_length=1, max_length=255)
    status: RequirementStatus
    note: str = Field(default="", max_length=20000)

class ScholarlyCritiqueVerificationRequestAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    requested_check: str = Field(min_length=1, max_length=20000)
    target_refs: list[str] = Field(default_factory=list, max_length=5000)
    critique_ids: list[str] = Field(default_factory=list, max_length=5000)
    runtime_target: str = Field(default="workspace", max_length=255)
    expected_artifacts: list[str] = Field(default_factory=list, max_length=5000)
    rationale: str = Field(default="", max_length=20000)

class ScholarlyCritiqueVerificationReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    verification_request_id: str = Field(min_length=1, max_length=255)
    execution_ref: str = Field(min_length=1, max_length=2000)
    status: VerificationStatus
    observed_summary: str = Field(default="", max_length=30000)
    metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list, max_length=5000)
    provenance_note: str = Field(default="", max_length=10000)

class ScholarlyCritiqueSynthesisAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    round_id: str = Field(default="", max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    synthesis: str = Field(min_length=1, max_length=50000)
    critique_ids: list[str] = Field(default_factory=list, max_length=5000)
    areas_of_agreement: list[str] = Field(default_factory=list, max_length=5000)
    areas_of_disagreement: list[str] = Field(default_factory=list, max_length=5000)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)

class ScholarlyCritiqueDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    object_type: Literal["round", "dimension", "critique", "revision-requirement", "verification-request", "critique-synthesis"]
    object_id: str = Field(min_length=1, max_length=255)
    decision: Decision
    rationale: str = Field(default="", max_length=20000)

class ScholarlyCritiqueStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: CritiqueState
    note: str = Field(default="", max_length=20000)

class ScholarlyCritiqueSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    critique_project_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="peer-review-scholarly-critique-intelligence-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
