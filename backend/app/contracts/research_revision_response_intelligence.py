from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

REVISION_RESPONSE_SCHEMA = "sc-research-librarian-research-revision-response-intelligence/1.0"
REVISION_RESPONSE_SNAPSHOT_SCHEMA = "sc-research-librarian-research-revision-response-intelligence-snapshot/1.0"

RevisionState = Literal["draft", "responding", "revising", "verification", "review", "closed", "archived"]
ResponsePosition = Literal["addressed", "partially-addressed", "disagreed", "clarified", "not-applicable", "deferred"]
ChangeType = Literal[
    "text-added", "text-modified", "text-removed", "text-relocated", "analysis-rerun", "data-update",
    "code-update", "figure-update", "table-update", "citation-update", "methods-update", "no-artifact-change", "other",
]
ArtifactType = Literal["manuscript", "supplement", "dataset", "code", "notebook", "figure", "table", "analysis-output", "response-letter", "other"]
VerificationStatus = Literal["completed", "partial", "failed-to-run", "cancelled"]
ResolutionJudgment = Literal["satisfied", "partially-satisfied", "not-satisfied", "deferred", "not-assessed"]
Decision = Literal["pending", "approved", "rejected", "waived"]

class RevisionResponseCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    project_ref: str = Field(default="", max_length=2000)
    critique_project_ref: str = Field(min_length=1, max_length=255)
    baseline_revision_ref: str = Field(default="", max_length=2000)
    baseline_revision_hash: str = Field(default="", max_length=255)
    revised_artifact_ref: str = Field(default="", max_length=2000)
    revised_artifact_hash: str = Field(default="", max_length=255)
    review_round_ref: str = Field(default="", max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

class RevisionResponseItemAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    critique_ids: list[str] = Field(min_length=1, max_length=5000)
    revision_requirement_ids: list[str] = Field(default_factory=list, max_length=5000)
    response_position: ResponsePosition
    response_text: str = Field(min_length=1, max_length=50000)
    rationale: str = Field(default="", max_length=30000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)

class RevisionChangeClaimAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    response_item_id: str = Field(min_length=1, max_length=255)
    change_type: ChangeType
    target_ref: str = Field(default="", max_length=2000)
    location_ref: str = Field(default="", max_length=2000)
    before_ref: str = Field(default="", max_length=2000)
    before_hash: str = Field(default="", max_length=255)
    after_ref: str = Field(default="", max_length=2000)
    after_hash: str = Field(default="", max_length=255)
    claimed_change: str = Field(min_length=1, max_length=30000)
    rationale: str = Field(default="", max_length=30000)

class RevisionArtifactReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    response_item_id: str = Field(min_length=1, max_length=255)
    artifact_type: ArtifactType
    artifact_ref: str = Field(min_length=1, max_length=2000)
    artifact_hash: str = Field(default="", max_length=255)
    diff_ref: str = Field(default="", max_length=2000)
    observed_changed_locations: list[str] = Field(default_factory=list, max_length=5000)
    metrics: dict[str, Any] = Field(default_factory=dict)
    provenance_note: str = Field(default="", max_length=10000)

class RevisionVerificationRequestAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    requested_check: str = Field(min_length=1, max_length=20000)
    response_item_ids: list[str] = Field(min_length=1, max_length=5000)
    runtime_target: str = Field(default="workspace", max_length=255)
    expected_artifacts: list[str] = Field(default_factory=list, max_length=5000)
    rationale: str = Field(default="", max_length=20000)

class RevisionVerificationReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    verification_request_id: str = Field(min_length=1, max_length=255)
    execution_ref: str = Field(min_length=1, max_length=2000)
    status: VerificationStatus
    observed_summary: str = Field(default="", max_length=30000)
    metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list, max_length=5000)
    provenance_note: str = Field(default="", max_length=10000)

class RevisionResolutionReviewAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    response_item_id: str = Field(min_length=1, max_length=255)
    reviewer_ref: str = Field(min_length=1, max_length=255)
    judgment: ResolutionJudgment
    rationale: str = Field(min_length=1, max_length=30000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)

class RevisionResponseDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    object_type: Literal["verification-request", "resolution-review", "response-package"]
    object_id: str = Field(min_length=1, max_length=255)
    decision: Decision
    rationale: str = Field(default="", max_length=20000)

class RevisionResponseStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: RevisionState
    note: str = Field(default="", max_length=20000)

class RevisionResponseSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    revision_response_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="research-revision-response-intelligence-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
