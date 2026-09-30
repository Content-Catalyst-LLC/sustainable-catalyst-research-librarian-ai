from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

RESEARCH_INTEGRITY_AUDIT_SCHEMA = "sc-research-librarian-research-integrity-methodological-audit/1.0"
RESEARCH_INTEGRITY_AUDIT_SNAPSHOT_SCHEMA = "sc-research-librarian-research-integrity-methodological-audit-snapshot/1.0"

AuditState = Literal["draft", "in_review", "remediation", "closed", "archived"]
TargetType = Literal[
    "research-question-plan", "research-design-plan", "evidence-search-strategy-plan", "systematic-review-plan",
    "study-protocol", "statistical-analysis-plan-intelligence", "causal-research-design", "simulation-model-study-plan",
    "reproduction-replication-plan", "cross-study-synthesis-plan", "scholarly-study", "scholarly-publication",
    "dataset", "code-artifact", "source-record", "core-object", "other",
]
AuditDomain = Literal[
    "preregistration-consistency", "outcome-reporting", "analysis-plan-consistency", "sampling-and-eligibility",
    "missing-data", "multiplicity", "model-assumptions", "causal-identification", "simulation-validation",
    "reproducibility", "replication", "data-availability", "code-availability", "synthesis-integrity",
    "provenance-and-lineage", "reporting-completeness", "conflict-disclosure", "other",
]
ObservationStatus = Literal["consistent", "inconsistent", "unclear", "not-applicable", "not-assessed"]
FindingKind = Literal[
    "declared-deviation", "missing-documentation", "unresolved-assumption", "method-inconsistency",
    "reporting-gap", "reproducibility-gap", "transparency-gap", "provenance-gap", "unverified-claim", "other",
]
FindingSignificance = Literal["note", "review-needed", "material-concern", "not-assessed"]
AppraisalJudgment = Literal["adequate", "some-concerns", "serious-concerns", "unclear", "not-assessed"]
Decision = Literal["pending", "approved", "rejected", "waived"]
FindingDisposition = Literal["open", "resolved", "accepted-risk", "not-applicable"]
VerificationStatus = Literal["completed", "partial", "failed-to-run", "cancelled"]
RemediationStatus = Literal["planned", "in-progress", "completed", "declined", "not-applicable"]

class ResearchIntegrityTargetBinding(BaseModel):
    target_type: TargetType
    target_ref: str = Field(min_length=1, max_length=2000)
    role: str = Field(default="", max_length=255)
    source_hash: str = Field(default="", max_length=255)
    note: str = Field(default="", max_length=10000)

class ResearchIntegrityTargetAddRequest(ResearchIntegrityTargetBinding):
    actor_ref: str = Field(min_length=1, max_length=255)

class ResearchIntegrityAuditCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    audit_question: str = Field(min_length=1, max_length=20000)
    audit_scope: str = Field(default="methodological integrity and research-process consistency", max_length=10000)
    project_ref: str = Field(default="", max_length=2000)
    targets: list[ResearchIntegrityTargetBinding] = Field(default_factory=list, max_length=5000)
    governing_protocol_ref: str = Field(default="", max_length=2000)
    audit_standard_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchIntegrityCriterionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    domain: AuditDomain
    label: str = Field(min_length=1, max_length=1000)
    audit_question: str = Field(min_length=1, max_length=10000)
    expectation_basis: str = Field(min_length=1, max_length=20000)
    applicable_target_refs: list[str] = Field(default_factory=list, max_length=5000)
    reviewer_priority: Literal["routine", "elevated", "high"] = "routine"

class ResearchIntegrityObservationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    criterion_id: str = Field(min_length=1, max_length=255)
    target_ref: str = Field(default="", max_length=2000)
    status: ObservationStatus = "not-assessed"
    expected_or_declared: str = Field(default="", max_length=20000)
    observed_or_reported: str = Field(default="", max_length=20000)
    description: str = Field(min_length=1, max_length=30000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)

class ResearchIntegrityFindingAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    criterion_id: str = Field(min_length=1, max_length=255)
    finding_kind: FindingKind
    significance: FindingSignificance = "not-assessed"
    finding: str = Field(min_length=1, max_length=30000)
    rationale: str = Field(min_length=1, max_length=30000)
    affected_target_refs: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)

class ResearchIntegrityMethodologicalAppraisalAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    domain: AuditDomain
    judgment: AppraisalJudgment
    rationale: str = Field(min_length=1, max_length=30000)
    target_refs: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)

class ResearchIntegrityVerificationRequestAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    requested_check: str = Field(min_length=1, max_length=20000)
    target_refs: list[str] = Field(default_factory=list, max_length=5000)
    runtime_target: str = Field(default="workspace", max_length=255)
    expected_artifacts: list[str] = Field(default_factory=list, max_length=5000)
    rationale: str = Field(default="", max_length=20000)

class ResearchIntegrityVerificationReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    verification_request_id: str = Field(min_length=1, max_length=255)
    execution_ref: str = Field(min_length=1, max_length=2000)
    status: VerificationStatus
    observed_summary: str = Field(default="", max_length=30000)
    metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list, max_length=5000)
    provenance_note: str = Field(default="", max_length=10000)

class ResearchIntegrityRemediationActionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    finding_ids: list[str] = Field(min_length=1, max_length=5000)
    action: str = Field(min_length=1, max_length=30000)
    owner_ref: str = Field(default="", max_length=255)
    target_date: str = Field(default="", max_length=255)
    verification_requirement: str = Field(default="", max_length=10000)

class ResearchIntegrityRemediationStatusRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    remediation_action_id: str = Field(min_length=1, max_length=255)
    status: RemediationStatus
    note: str = Field(default="", max_length=20000)

class ResearchIntegrityFindingDispositionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    finding_id: str = Field(min_length=1, max_length=255)
    disposition: FindingDisposition
    rationale: str = Field(min_length=1, max_length=20000)

class ResearchIntegrityDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    object_type: Literal["criterion", "finding", "appraisal", "verification-request", "remediation-action"]
    object_id: str = Field(min_length=1, max_length=255)
    decision: Decision
    rationale: str = Field(default="", max_length=20000)

class ResearchIntegrityAuditStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: AuditState
    note: str = Field(default="", max_length=20000)

class ResearchIntegrityAuditSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    audit_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="research-integrity-methodological-audit-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
