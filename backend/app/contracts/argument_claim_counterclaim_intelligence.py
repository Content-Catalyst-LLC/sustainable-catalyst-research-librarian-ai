from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA = "sc-research-librarian-argument-claim-counterclaim-intelligence/1.0"
ARGUMENT_CLAIM_COUNTERCLAIM_SNAPSHOT_SCHEMA = "sc-research-librarian-argument-claim-counterclaim-intelligence-snapshot/1.0"

ClaimRole = Literal["thesis", "claim", "subclaim", "counterclaim", "rebuttal", "qualification"]
ClaimType = Literal["descriptive", "interpretive", "causal", "comparative", "predictive", "normative", "methodological"]
EvidenceRelation = Literal["supports", "contradicts", "qualifies", "contextualizes", "is_insufficient_for"]
ClaimRelation = Literal["supports", "challenges", "rebuts", "qualifies", "depends_on", "is_alternative_to"]
ReviewState = Literal["draft", "in_review", "approved", "archived"]
ClaimDecision = Literal["pending", "accepted_for_analysis", "rejected_from_analysis"]
TensionState = Literal["open", "partially_resolved", "resolved"]


class ArgumentIntelligenceCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    research_question: str = Field(default="", max_length=20000)
    core_project_id: str = Field(default="", max_length=255)
    literature_intelligence_id: str = Field(default="", max_length=255)
    systematic_review_id: str = Field(default="", max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArgumentClaimAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    statement: str = Field(min_length=1, max_length=30000)
    title: str = Field(default="", max_length=2000)
    role: ClaimRole = "claim"
    claim_type: ClaimType = "descriptive"
    work_ids: list[str] = Field(default_factory=list, max_length=5000)
    source_refs: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(default="", max_length=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimEvidenceLinkRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    claim_id: str = Field(min_length=1, max_length=255)
    source_ref: str = Field(min_length=1, max_length=2000)
    relation: EvidenceRelation
    evidence_ref: str = Field(default="", max_length=2000)
    source_locator_ref: str = Field(default="", max_length=2000)
    rationale: str = Field(default="", max_length=10000)
    declared_strength: str = Field(default="", max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimRelationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    source_claim_id: str = Field(min_length=1, max_length=255)
    target_claim_id: str = Field(min_length=1, max_length=255)
    relation: ClaimRelation
    rationale: str = Field(default="", max_length=10000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def no_self_relation(self):
        if self.source_claim_id == self.target_claim_id:
            raise ValueError("Claim self-relations are not permitted.")
        return self


class ClaimAssumptionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=20000)
    assumption_type: str = Field(default="contextual", max_length=255)
    claim_id: str = Field(default="", max_length=255)
    rationale: str = Field(default="", max_length=10000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)


class ClaimDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    claim_id: str = Field(min_length=1, max_length=255)
    decision: ClaimDecision
    rationale: str = Field(default="", max_length=10000)


class ArgumentTensionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1, max_length=20000)
    claim_ids: list[str] = Field(min_length=2, max_length=100)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    state: TensionState = "open"
    rationale: str = Field(default="", max_length=10000)


class ArgumentIntelligenceStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: ReviewState
    note: str = Field(default="", max_length=10000)


class ArgumentIntelligenceSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    argument_intelligence_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="argument-claim-counterclaim-intelligence-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
